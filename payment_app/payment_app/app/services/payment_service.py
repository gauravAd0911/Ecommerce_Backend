"""Payment service (Razorpay) backed by database records.

Implements:
- Idempotent provider order creation (Idempotency-Key).
- Server-side signature verification.
- Webhook persistence and signature verification.
- Status + reconciliation for uncertain outcomes.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import razorpay
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import RAZORPAY_KEY, RAZORPAY_SECRET, RAZORPAY_WEBHOOK_SECRET
from app.models.cart import Cart
from app.models.order import Order
from app.models.payment import Payment, PaymentEvent, PaymentProvider, PaymentState


_DEFAULT_CURRENCY = "INR"
_IDEMPOTENCY_HEADER = "Idempotency-Key"
_MAX_IDEMPOTENCY_KEY_LENGTH = 80
_PROVIDER_ORDER_RETRY_COOLDOWN_SECONDS = 30


def _utcnow() -> datetime:
    """Return naive UTC datetime for DB storage without `datetime.utcnow()`."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


class PaymentService:
    """Single-responsibility service for payment operations."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

    @staticmethod
    def _generate_payment_reference() -> str:
        return f"payref_{secrets.token_hex(12)}"

    @staticmethod
    def _generate_order_number() -> str:
        return f"ORD-{_utcnow():%Y%m%d}-{secrets.token_hex(3).upper()}"

    @staticmethod
    def _validate_idempotency_key(idempotency_key: str | None) -> str:
        if not idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required header: {_IDEMPOTENCY_HEADER}.",
            )
        key = idempotency_key.strip()
        if not key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency key cannot be empty.")
        if len(key) > _MAX_IDEMPOTENCY_KEY_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Idempotency key too long (max {_MAX_IDEMPOTENCY_KEY_LENGTH}).",
            )
        return key

    def create_order_from_cart(
        self,
        *,
        user_id: int,
        currency: str = _DEFAULT_CURRENCY,
        idempotency_key: str | None,
    ) -> Payment:
        """Compute cart total and create an idempotent Razorpay order."""

        total = self._compute_cart_total(user_id=user_id, currency=currency)
        amount_minor = self._decimal_to_minor(total)
        legacy_key = idempotency_key or self._legacy_cart_idempotency_key(user_id=user_id, currency=currency)
        return self.create_razorpay_order(
            amount_minor=amount_minor,
            currency=currency,
            idempotency_key=legacy_key,
            metadata={"user_id": user_id},
        )

    def _compute_cart_total(self, *, user_id: int, currency: str) -> Decimal:
        price_column = self._resolve_cart_price_column()
        query = text(
            f"SELECT SUM({price_column} * quantity) AS total "
            "FROM carts WHERE user_id = :user_id AND UPPER(currency) = :currency"
        )
        total = self.db.execute(query, {"user_id": user_id, "currency": currency.upper()}).scalar_one_or_none()
        if total is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty.")
        if total <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart total must be greater than 0.")
        return Decimal(str(total))

    def _resolve_cart_price_column(self) -> str:
        """Resolve the cart price column name (supports legacy schemas).

        Prefers `price`, falls back to legacy `unit_price`.
        """

        candidate = self.db.execute(
            text(
                "SELECT COLUMN_NAME "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'carts' "
                "AND COLUMN_NAME IN ('price', 'unit_price') "
                "ORDER BY CASE COLUMN_NAME WHEN 'price' THEN 0 ELSE 1 END "
                "LIMIT 1"
            )
        ).scalar_one_or_none()

        if candidate == "price":
            return "price"
        if candidate == "unit_price":
            return "unit_price"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cart schema mismatch: expected `carts.price` (or legacy `carts.unit_price`).",
        )

    @staticmethod
    def _decimal_to_minor(value: Decimal) -> int:
        return int((value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _legacy_cart_idempotency_key(self, *, user_id: int, currency: str) -> str:
        price_column = self._resolve_cart_price_column()
        items = self.db.execute(
            text(
                f"SELECT id, item_name, {price_column} AS price, quantity, currency "
                "FROM carts WHERE user_id = :user_id ORDER BY id ASC"
            ),
            {"user_id": user_id},
        ).mappings().all()
        hasher = hashlib.sha256()
        hasher.update(f"user:{user_id}|currency:{currency.upper()}".encode("utf-8"))
        for row in items:
            hasher.update(
                f"|{row['id']}:{row['item_name']}:{row['price']}:{row['quantity']}:{row['currency']}".encode("utf-8")
            )
        return f"legacy_{hasher.hexdigest()[:32]}"

    def create_razorpay_order(
        self,
        *,
        amount_minor: int,
        currency: str,
        idempotency_key: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> Payment:
        key = self._validate_idempotency_key(idempotency_key)
        normalized_currency = (currency or _DEFAULT_CURRENCY).upper()

        existing = (
            self.db.query(Payment)
            .filter(Payment.provider == PaymentProvider.RAZORPAY, Payment.idempotency_key == key)
            .first()
        )
        if existing and existing.provider_order_id:
            return existing
        if existing and not self._can_retry_provider_order(existing):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment order creation is in progress. Retry with the same idempotency key.",
            )

        payment = existing or self._create_payment_stub(
            amount_minor=amount_minor, currency=normalized_currency, idempotency_key=key, metadata=metadata
        )
        self._attempt_provider_order_create(payment)
        return payment

    def _create_payment_stub(
        self, *, amount_minor: int, currency: str, idempotency_key: str, metadata: dict[str, Any] | None
    ) -> Payment:
        payment = Payment(
            payment_reference=self._generate_payment_reference(),
            provider=PaymentProvider.RAZORPAY,
            idempotency_key=idempotency_key,
            amount_minor=amount_minor,
            currency=currency,
            status=PaymentState.CREATING,
            provider_order_create_attempts=0,
            provider_metadata=metadata or {},
        )
        self.db.add(payment)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = (
                self.db.query(Payment)
                .filter(Payment.provider == PaymentProvider.RAZORPAY, Payment.idempotency_key == idempotency_key)
                .first()
            )
            if not existing:
                raise
            return existing
        self.db.refresh(payment)
        return payment

    @staticmethod
    def _can_retry_provider_order(payment: Payment) -> bool:
        if payment.provider_order_last_attempt_at is None:
            return True
        cooldown = timedelta(seconds=_PROVIDER_ORDER_RETRY_COOLDOWN_SECONDS)
        return _utcnow() - payment.provider_order_last_attempt_at >= cooldown

    def _attempt_provider_order_create(self, payment: Payment) -> None:
        if payment.provider_order_id:
            return

        payment.provider_order_create_attempts += 1
        payment.provider_order_last_attempt_at = _utcnow()
        self.db.commit()

        try:
            provider_order = self.client.order.create(
                {
                    "amount": int(payment.amount_minor),
                    "currency": payment.currency,
                    "receipt": payment.payment_reference,
                }
            )
        except Exception as exc:
            self._mark_failed(payment, error=f"Razorpay order creation failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create Razorpay order. Retry safely with the same idempotency key.",
            ) from exc

        provider_order_id = provider_order.get("id") if isinstance(provider_order, dict) else None
        if not isinstance(provider_order_id, str) or not provider_order_id.strip():
            self._mark_failed(payment, error="Razorpay order creation returned an invalid order id.")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create Razorpay order. Retry safely with the same idempotency key.",
            )

        payment.provider_order_id = provider_order_id.strip()
        payment.status = PaymentState.CREATED
        payment.provider_metadata = {**(payment.provider_metadata or {}), "razorpay_order": provider_order}
        self.db.commit()

    def _mark_failed(self, payment: Payment, *, error: str) -> None:
        payment.status = PaymentState.FAILED
        payment.failed_at = _utcnow()
        payment.last_error = (error or "")[:500]
        self.db.commit()

    def get_payment_by_reference(self, payment_reference: str) -> Payment:
        payment = self.db.query(Payment).filter(Payment.payment_reference == payment_reference).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment reference not found.")
        return payment

    def get_payment_by_provider_order_id(self, razorpay_order_id: str) -> Payment:
        payment = (
            self.db.query(Payment)
            .filter(Payment.provider == PaymentProvider.RAZORPAY, Payment.provider_order_id == razorpay_order_id)
            .first()
        )
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found for this order id.")
        return payment

    def verify_razorpay_payment(
        self,
        *,
        payment_reference: str | None,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> tuple[Payment, Order | None]:
        payment = (
            self.get_payment_by_reference(payment_reference)
            if payment_reference
            else self.get_payment_by_provider_order_id(razorpay_order_id)
        )

        if payment.provider_order_id and payment.provider_order_id != razorpay_order_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay order id mismatch.")

        if payment.status == PaymentState.VERIFIED:
            order = self.db.query(Order).filter(Order.payment_reference == payment.payment_reference).first()
            return payment, order

        if not self._is_valid_razorpay_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay signature.")

        payment.provider_payment_id = razorpay_payment_id
        payment.status = PaymentState.VERIFIED
        payment.verified_at = _utcnow()
        payment.provider_metadata = {
            **(payment.provider_metadata or {}),
            "verification": {"razorpay_order_id": razorpay_order_id, "razorpay_payment_id": razorpay_payment_id},
        }
        self.db.commit()
        self.db.refresh(payment)

        order = None
        if int((payment.provider_metadata or {}).get("user_id") or 0) > 0:
            order = self._get_or_create_order_for_payment(payment)
        return payment, order

    @staticmethod
    def _is_valid_razorpay_payment_signature(
        *, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str
    ) -> bool:
        if not RAZORPAY_SECRET:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Razorpay is not configured.")
        body = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
        digest = hmac.new(RAZORPAY_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, razorpay_signature)

    def _get_or_create_order_for_payment(self, payment: Payment) -> Order:
        existing = self.db.query(Order).filter(Order.payment_reference == payment.payment_reference).first()
        if existing:
            return existing

        user_id = int((payment.provider_metadata or {}).get("user_id") or 0)
        if user_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment verified but order cannot be finalized without a user id.",
            )

        order = Order(
            user_id=user_id,
            order_number=self._generate_order_number(),
            payment_reference=payment.payment_reference,
            total_amount_minor=payment.amount_minor,
            currency=payment.currency,
            status="paid",
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def reconcile_payment(self, payment_reference: str) -> Payment:
        payment = self.get_payment_by_reference(payment_reference)
        if not self._should_reconcile(payment):
            return payment

        provider_order = self._try_fetch_provider_order(payment)
        if provider_order is None:
            self._set_payment_unknown(payment)
            return payment

        provider_payments = self._try_fetch_provider_payments(payment)
        self._apply_reconcile_from_payments(payment, provider_payments)
        if payment.status != PaymentState.VERIFIED:
            self._apply_reconcile_from_order_status(payment, provider_order)

        payment.provider_metadata = {**(payment.provider_metadata or {}), "razorpay_order_reconcile": provider_order}
        self.db.commit()
        self.db.refresh(payment)
        return payment

    @staticmethod
    def _should_reconcile(payment: Payment) -> bool:
        if payment.provider != PaymentProvider.RAZORPAY:
            return False
        if not payment.provider_order_id:
            return False
        return payment.status not in {PaymentState.VERIFIED, PaymentState.FAILED}

    def _try_fetch_provider_order(self, payment: Payment) -> dict[str, Any] | None:
        try:
            result = self.client.order.fetch(payment.provider_order_id)
        except Exception:
            return None
        return result if isinstance(result, dict) else {}

    def _try_fetch_provider_payments(self, payment: Payment) -> dict[str, Any]:
        try:
            result = self.client.order.payments(payment.provider_order_id)
        except Exception:
            return {}
        return result if isinstance(result, dict) else {}

    def _apply_reconcile_from_payments(self, payment: Payment, provider_payments: dict[str, Any]) -> None:
        payment_items = provider_payments.get("items")
        if not isinstance(payment_items, list):
            return

        for item in payment_items:
            if not isinstance(item, dict):
                continue
            provider_payment_id = item.get("id")
            provider_payment_status = str(item.get("status") or "").lower()
            if provider_payment_status not in {"captured", "authorized"}:
                continue
            if not isinstance(provider_payment_id, str) or not provider_payment_id.strip():
                continue

            payment.provider_payment_id = payment.provider_payment_id or provider_payment_id.strip()
            payment.status = PaymentState.VERIFIED
            payment.verified_at = payment.verified_at or _utcnow()
            break

    def _apply_reconcile_from_order_status(self, payment: Payment, provider_order: dict[str, Any]) -> None:
        order_status = str(provider_order.get("status") or "").lower()
        if order_status == "paid":
            payment.status = PaymentState.VERIFIED
            payment.verified_at = payment.verified_at or _utcnow()
            return
        if order_status == "attempted":
            payment.status = PaymentState.PENDING
            return
        if order_status == "created":
            payment.status = PaymentState.CREATED
            return
        payment.status = PaymentState.UNKNOWN

    def _set_payment_unknown(self, payment: Payment) -> None:
        payment.status = PaymentState.UNKNOWN
        self.db.commit()
        self.db.refresh(payment)

    def store_and_process_razorpay_webhook(self, *, raw_body: bytes, signature: str | None, payload: dict[str, Any]) -> None:
        provider_event_id = self._extract_provider_event_id(raw_body=raw_body, payload=payload)
        signature_ok, signature_reason = self._verify_webhook(raw_body=raw_body, signature=signature)
        event_type = str(payload.get("event") or "unknown")

        payment = self._find_payment_for_webhook_payload(payload)
        event = PaymentEvent(
            payment_id=payment.id if payment else None,
            provider=PaymentProvider.RAZORPAY,
            provider_event_id=provider_event_id,
            event_type=event_type,
            signature_verified=signature_ok,
            payload=payload,
            note=None if signature_ok else signature_reason,
        )
        self.db.add(event)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return

        if not signature_ok or not payment:
            return

        self._apply_webhook_effect(payment=payment, event_type=event_type, payload=payload)

    @staticmethod
    def _verify_webhook(*, raw_body: bytes, signature: str | None) -> tuple[bool, str]:
        if not signature:
            return False, "Missing X-Razorpay-Signature header."
        if not RAZORPAY_WEBHOOK_SECRET:
            return False, "Webhook secret is not configured."
        digest = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, signature):
            return False, "Invalid webhook signature."
        return True, "ok"

    @staticmethod
    def _extract_provider_event_id(*, raw_body: bytes, payload: dict[str, Any]) -> str:
        event_id = payload.get("id")
        if isinstance(event_id, str) and event_id.strip():
            return event_id.strip()
        return hashlib.sha256(raw_body).hexdigest()

    def _find_payment_for_webhook_payload(self, payload: dict[str, Any]) -> Payment | None:
        provider_order_id = self._extract_order_id_from_webhook_payload(payload)
        if not provider_order_id:
            return None
        return (
            self.db.query(Payment)
            .filter(Payment.provider == PaymentProvider.RAZORPAY, Payment.provider_order_id == provider_order_id)
            .first()
        )

    @staticmethod
    def _extract_order_id_from_webhook_payload(payload: dict[str, Any]) -> str | None:
        provider_payload = payload.get("payload")
        if not isinstance(provider_payload, dict):
            return None

        payment_entity = (
            provider_payload.get("payment", {}).get("entity") if isinstance(provider_payload.get("payment"), dict) else None
        )
        if isinstance(payment_entity, dict):
            order_id = payment_entity.get("order_id")
            if isinstance(order_id, str) and order_id.strip():
                return order_id.strip()

        order_entity = provider_payload.get("order", {}).get("entity") if isinstance(provider_payload.get("order"), dict) else None
        if isinstance(order_entity, dict):
            order_id = order_entity.get("id")
            if isinstance(order_id, str) and order_id.strip():
                return order_id.strip()

        return None

    @staticmethod
    def _extract_payment_id_from_webhook_payload(payload: dict[str, Any]) -> str | None:
        provider_payload = payload.get("payload")
        if not isinstance(provider_payload, dict):
            return None
        payment_entity = (
            provider_payload.get("payment", {}).get("entity") if isinstance(provider_payload.get("payment"), dict) else None
        )
        if not isinstance(payment_entity, dict):
            return None
        payment_id = payment_entity.get("id")
        if isinstance(payment_id, str) and payment_id.strip():
            return payment_id.strip()
        return None

    def _apply_webhook_effect(self, *, payment: Payment, event_type: str, payload: dict[str, Any]) -> None:
        provider_payment_id = self._extract_payment_id_from_webhook_payload(payload)
        now = _utcnow()

        if event_type in {"payment.captured", "order.paid"}:
            if payment.status != PaymentState.VERIFIED:
                payment.status = PaymentState.VERIFIED
                payment.verified_at = payment.verified_at or now
                if provider_payment_id:
                    payment.provider_payment_id = payment.provider_payment_id or provider_payment_id
                self.db.commit()
            return

        if event_type == "payment.failed":
            if payment.status not in {PaymentState.VERIFIED, PaymentState.FAILED}:
                payment.status = PaymentState.FAILED
                payment.failed_at = payment.failed_at or now
                self.db.commit()
            return

        if payment.status not in {PaymentState.VERIFIED, PaymentState.FAILED}:
            payment.status = PaymentState.UNKNOWN
            self.db.commit()
