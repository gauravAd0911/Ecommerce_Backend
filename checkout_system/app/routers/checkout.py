from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import CheckoutSession, Product
from app.models.models import ServiceablePincode
from app.schemas.schemas import (
    ApiEnvelope,
    CheckoutIssueOut,
    CheckoutItemOut,
    CheckoutPricingOut,
    CheckoutSessionIn,
    CheckoutSessionOut,
    CheckoutValidateIn,
    CheckoutValidateOut,
)

router = APIRouter(prefix="/api/v1/checkout", tags=["Checkout"])

CHECKOUT_TTL_MINUTES = 15
FREE_SHIPPING_THRESHOLD = Decimal("999")
DEFAULT_SHIPPING = Decimal("99")
ZONE_SHIPPING = {
    "metro": Decimal("0"),
    "tier1": Decimal("49"),
    "tier2": Decimal("99"),
}


def _slug_from_product_id(product_id: str) -> str:
    return product_id.strip().lower().replace("_", "-")[:280] or "product"


def _stock_snapshot(item) -> int:
    return max(int(item.stock_qty if item.stock_qty is not None else item.quantity), int(item.quantity))


def _sync_product_snapshot(db: Session, item) -> Product | None:
    product = (
        db.query(Product)
        .filter(Product.id == item.product_id, Product.is_active.is_(True))
        .first()
    )

    if product is None and item.name and item.unit_price is not None:
        product = Product(
            id=item.product_id,
            name=item.name,
            slug=_slug_from_product_id(item.product_id),
            price=item.unit_price,
            stock_qty=_stock_snapshot(item),
            is_active=True,
        )
        db.add(product)
        db.flush()
        return product

    if product is not None:
        if item.name:
            product.name = item.name
        if item.unit_price is not None:
            product.price = item.unit_price
        if item.stock_qty is not None:
            product.stock_qty = int(item.stock_qty)
        db.flush()

    return product


def _get_user_id(x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None) -> str | None:
    return x_user_id.strip() if x_user_id else None


def _success(message: str, data: dict):
    return ApiEnvelope(success=True, message=message, data=data, error=None)


def _blocking_issues(issues: list[CheckoutIssueOut]) -> list[CheckoutIssueOut]:
    blocking_codes = {"PRODUCT_NOT_FOUND", "OUT_OF_STOCK", "DELIVERY_UNAVAILABLE"}
    return [issue for issue in issues if issue.code in blocking_codes]


def _validate_items(db: Session, payload: CheckoutValidateIn, products: dict) -> tuple[list[CheckoutIssueOut], Decimal, list[CheckoutItemOut]]:
    issues: list[CheckoutIssueOut] = []
    subtotal = Decimal("0")
    items_out: list[CheckoutItemOut] = []
    for item in payload.items:
        product = products.get(item.product_id)
        if not product:
            issues.append(
                CheckoutIssueOut(
                    code="PRODUCT_NOT_FOUND",
                    message="Product is not available for checkout.",
                    product_id=item.product_id,
                )
            )
            continue

        if product.stock_qty < item.quantity:
            issues.append(
                CheckoutIssueOut(
                    code="OUT_OF_STOCK",
                    message="Requested quantity is not available.",
                    product_id=item.product_id,
                )
            )
            continue

        if product.stock_qty <= 5:
            issues.append(
                CheckoutIssueOut(
                    code="LIMITED_STOCK",
                    message=f"Limited stock: only {product.stock_qty} unit(s) remain.",
                    product_id=item.product_id,
                )
            )

        subtotal += Decimal(product.price) * item.quantity
        items_out.append(
            CheckoutItemOut(
                product_id=product.id,
                name=product.name,
                quantity=item.quantity,
                unit_price=Decimal(product.price),
            )
        )
    return issues, subtotal, items_out


def _validate_delivery(db: Session, payload: CheckoutValidateIn, subtotal: Decimal) -> tuple[Decimal, list[CheckoutIssueOut]]:
    shipping = Decimal("0") if subtotal >= FREE_SHIPPING_THRESHOLD else DEFAULT_SHIPPING
    issues: list[CheckoutIssueOut] = []
    if payload.address and payload.address.postal_code:
        delivery_zone = (
            db.query(ServiceablePincode)
            .filter(
                ServiceablePincode.pincode == payload.address.postal_code,
                ServiceablePincode.is_active.is_(True),
            )
            .first()
        )
        if not delivery_zone:
            issues.append(
                CheckoutIssueOut(
                    code="DELIVERY_UNAVAILABLE",
                    message="Delivery is not available for this pincode.",
                )
            )
        else:
            shipping = (
                Decimal(str(delivery_zone.shipping_fee_override))
                if delivery_zone.shipping_fee_override is not None
                else (Decimal("0") if subtotal >= FREE_SHIPPING_THRESHOLD else ZONE_SHIPPING.get(delivery_zone.zone, DEFAULT_SHIPPING))
            )
    return shipping, issues


def _validate_payload(db: Session, payload: CheckoutValidateIn) -> CheckoutValidateOut:
    products = {}
    for item in payload.items:
        product = _sync_product_snapshot(db, item)
        if product is not None:
            products[product.id] = product

    issues, subtotal, items_out = _validate_items(db, payload, products)
    shipping, delivery_issues = _validate_delivery(db, payload, subtotal)
    issues.extend(delivery_issues)

    pricing = CheckoutPricingOut(
        subtotal=subtotal,
        shipping=shipping,
        tax=Decimal("0"),
        total=subtotal + shipping,
    )
    return CheckoutValidateOut(
        cart_valid=not any(issue.code == "PRODUCT_NOT_FOUND" for issue in issues),
        delivery_valid=not any(issue.code == "DELIVERY_UNAVAILABLE" for issue in issues),
        inventory_valid=not any(issue.code == "OUT_OF_STOCK" for issue in issues),
        pricing=pricing,
        items=items_out,
        issues=issues,
    )


@router.post("/validate", response_model=ApiEnvelope)
def validate_checkout(payload: CheckoutValidateIn, db: Annotated[Session, Depends(get_db)]):
    validation = _validate_payload(db, payload)
    return _success("Checkout validated successfully.", validation.model_dump(mode="json"))


@router.post("/session", response_model=ApiEnvelope, status_code=status.HTTP_201_CREATED)
def create_checkout_session(
    payload: CheckoutSessionIn,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str | None, Depends(_get_user_id)] = None,
):
    validation = _validate_payload(db, payload)
    blocking_issues = _blocking_issues(validation.issues)
    if blocking_issues:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CHECKOUT_VALIDATION_FAILED",
                "message": "Checkout validation failed.",
                "success": False,
                "error": {
                    "code": "CHECKOUT_VALIDATION_FAILED",
                    "message": "Checkout validation failed.",
                    "details": [issue.model_dump() for issue in blocking_issues],
                },
            },
        )

    expires_at = datetime.utcnow() + timedelta(minutes=CHECKOUT_TTL_MINUTES)
    session = CheckoutSession(
        user_id=user_id,
        guest_token=payload.guest_token,
        address_id=payload.address_id,
        shipping_address=payload.address.model_dump(mode="json") if payload.address else None,
        items=[item.model_dump(mode="json") for item in payload.items],
        pricing=validation.pricing.model_dump(mode="json"),
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    response = CheckoutSessionOut(
        checkoutId=session.id,
        reservation_required=True,
        pricing=validation.pricing,
        currency=validation.pricing.currency,
        expires_at=session.expires_at,
        items=[item.model_dump() for item in validation.items],
        address_id=session.address_id,
    )
    return _success("Checkout session created successfully.", response.model_dump(mode="json"))
