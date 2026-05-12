"""Payment APIs (Razorpay integration)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth import get_authenticated_user_id
from app.config import RAZORPAY_KEY
from app.db.session import get_db
from app.schemas.payment import (
    CreatePaymentOrderPayload,
    CreatePaymentOrderResponse,
    PaymentStatusResponse,
    VerifyPaymentPayload,
)
from app.services.payment_service import PaymentService

legacy_router = APIRouter()
api_router = APIRouter()


def _success(message: str, data):
    return {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
    }


@legacy_router.get("/create-order")
def create_order_legacy(
    user_id: Annotated[int, Depends(get_authenticated_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    service = PaymentService(db)
    payment = service.create_order_from_cart(user_id=user_id, currency="INR", idempotency_key=None)
    if not payment.provider_order_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider order could not be created. Retry.",
        )
    return {
        "key": RAZORPAY_KEY,
        "amount": payment.amount_minor,
        "currency": payment.currency,
        "razorpay_order_id": payment.provider_order_id,
        "payment_reference": payment.payment_reference,
    }


@legacy_router.post("/verify")
def verify_legacy(
    payload: VerifyPaymentPayload,
    user_id: Annotated[int, Depends(get_authenticated_user_id)],
    db: Annotated[Session, Depends(get_db)],
):
    service = PaymentService(db)
    payment, order = service.verify_razorpay_payment(
        payment_reference=None,
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
    )
    return {
        "status": "success" if payment.status.value == "verified" else "failed",
        "order_id": order.id if order else None,
    }


@api_router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_payment_order(
    payload: CreatePaymentOrderPayload,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    service = PaymentService(db)
    payment = service.create_razorpay_order(
        amount_minor=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        metadata={},
    )
    if not payment.provider_order_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider order could not be created. Retry safely with the same idempotency key.",
        )
    response = CreatePaymentOrderResponse(
        payment_reference=payment.payment_reference,
        provider=payment.provider.value,
        razorpay_order_id=payment.provider_order_id,
        amount=payment.amount_minor,
        currency=payment.currency,
        key_id=RAZORPAY_KEY,
    )
    return _success("Payment order created successfully.", response.model_dump())


@api_router.post("/intent", status_code=status.HTTP_201_CREATED)
def create_payment_intent(
    payload: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    raw_amount = payload.get("amount")
    if not isinstance(raw_amount, (int, float)) or raw_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than zero.")

    is_mobile_intent = (
        "orderReference" in payload
        or "methodLabel" in payload
        or "reservationId" in payload
    )
    amount_minor = int(round(float(raw_amount) * 100)) if is_mobile_intent else int(raw_amount)
    currency = str(payload.get("currency") or "INR").upper()
    metadata = {
        "frontend_payload": {
            "order_reference": payload.get("orderReference") or payload.get("receipt"),
            "reservation_id": payload.get("reservationId") or (payload.get("notes") or {}).get("reservationId"),
            "guest_token_present": bool(payload.get("guestToken")),
        }
    }
    key = idempotency_key or str(payload.get("orderReference") or payload.get("receipt") or "")

    payment = PaymentService(db).create_razorpay_order(
        amount_minor=amount_minor,
        currency=currency,
        idempotency_key=key or None,
        metadata=metadata,
    )
    if not payment.provider_order_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider order could not be created. Retry safely with the same idempotency key.",
        )

    if is_mobile_intent:
        return _success(
            "Payment intent created successfully.",
            {
                "id": payment.payment_reference,
                "amount": float(raw_amount),
                "provider": payment.provider.value,
                "status": "created",
                "gatewayOrderId": payment.provider_order_id,
                "currency": payment.currency,
            },
        )

    return _success(
        "Payment intent created successfully.",
        {
            "id": payment.provider_order_id,
            "payment_reference": payment.payment_reference,
            "provider": payment.provider.value,
            "amount": payment.amount_minor,
            "currency": payment.currency,
            "key_id": RAZORPAY_KEY,
        },
    )


@api_router.post("/verify")
def verify_payment(
    payload: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
):
    gateway_result = payload.get("gatewayResult") or {}
    payment_reference = payload.get("payment_reference") or payload.get("paymentReference") or payload.get("intentId")
    razorpay_order_id = (
        payload.get("razorpay_order_id")
        or payload.get("razorpayOrderId")
        or gateway_result.get("razorpayOrderId")
        or gateway_result.get("razorpay_order_id")
    )
    razorpay_payment_id = (
        payload.get("razorpay_payment_id")
        or payload.get("razorpayPaymentId")
        or gateway_result.get("razorpayPaymentId")
        or gateway_result.get("razorpay_payment_id")
    )
    razorpay_signature = (
        payload.get("razorpay_signature")
        or payload.get("razorpaySignature")
        or gateway_result.get("razorpaySignature")
        or gateway_result.get("razorpay_signature")
    )
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay verification payload is incomplete.")

    service = PaymentService(db)
    payment, order = service.verify_razorpay_payment(
        payment_reference=payment_reference,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
    )
    verified = payment.status.value == "verified"
    return _success(
        "Payment verified successfully." if verified else "Payment verification failed.",
        {
            "payment_reference": payment.payment_reference,
            "paymentReference": payment.payment_reference,
            "status": "success" if payload.get("intentId") or payload.get("gatewayResult") else payment.status.value,
            "provider_payment_id": payment.provider_payment_id,
            "paymentId": payment.provider_payment_id or payment.payment_reference,
            "verified": verified,
            "verifiedAt": payment.verified_at.isoformat() if payment.verified_at else None,
            "mode": "live",
            "order_id": order.id if order else None,
            "order_number": order.order_number if order else None,
        },
    )


@api_router.get("/{payment_reference}/status")
def get_payment_status(
    payment_reference: str,
    db: Annotated[Session, Depends(get_db)],
    reconcile: Annotated[bool, Query(description="Reconcile by querying provider (best-effort).")] = False,
):
    service = PaymentService(db)
    payment = service.reconcile_payment(payment_reference) if reconcile else service.get_payment_by_reference(payment_reference)
    response = PaymentStatusResponse(
        payment_reference=payment.payment_reference,
        provider=payment.provider.value,
        status=payment.status.value,
        razorpay_order_id=payment.provider_order_id,
        provider_payment_id=payment.provider_payment_id,
        amount=payment.amount_minor,
        currency=payment.currency,
        verified_at=payment.verified_at,
        failed_at=payment.failed_at,
        updated_at=payment.updated_at,
    )
    return _success("Payment status fetched successfully.", response.model_dump(mode="json"))


@api_router.post("/webhooks/razorpay")
@api_router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    signature: Annotated[str | None, Header(alias="X-Razorpay-Signature")] = None,
):
    raw_body = await request.body()
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        payload = {}
    PaymentService(db).store_and_process_razorpay_webhook(raw_body=raw_body, signature=signature, payload=payload)
    return _success("Webhook processed successfully.", {"message": "ok"})


__all__ = ["api_router", "legacy_router"]
