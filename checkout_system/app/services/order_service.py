"""
order_service.py — Guest order creation and lookup.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.models import Address, GuestCheckoutSession, GuestOrder, OrderStatusHistory
from app.schemas.schemas import AddressIn, GuestOrderIn
from app.services.stock_service import deduct_stock_for_guest_order

SHIPPING_RATE       = Decimal("9.99")
TAX_RATE            = Decimal("0.08")
FREE_SHIP_THRESHOLD = Decimal("75.00")


def _save_address(db: Session, data: AddressIn) -> Address:
    addr = Address(**data.model_dump())
    db.add(addr)
    db.flush()
    return addr


def _new_order_number(db: Session) -> str:
    while True:
        num = f"ORD-{datetime.utcnow().strftime('%y%m')}-{secrets.token_hex(3).upper()}"
        if not db.query(GuestOrder).filter_by(order_number=num).first():
            return num


def create_order(
    db: Session,
    payload: GuestOrderIn,
    session: GuestCheckoutSession,
    ip_address: str | None = None,
) -> GuestOrder:
    items, subtotal = [], Decimal("0")
    for item in payload.items:
        line = item.unit_price * item.quantity
        subtotal += line
        items.append({
            "product_id": item.product_id, "sku": item.sku, "name": item.name,
            "quantity": item.quantity, "unit_price": str(item.unit_price), "line_total": str(line),
        })

    shipping = Decimal("0") if subtotal >= FREE_SHIP_THRESHOLD else SHIPPING_RATE
    tax      = (subtotal + shipping) * TAX_RATE

    ship_addr = _save_address(db, payload.shipping_address)
    bill_addr = _save_address(db, payload.billing_address or payload.shipping_address)

    order = GuestOrder(
        session_id=session.id,
        order_number=_new_order_number(db),
        guest_name=session.guest_name or "Guest",
        guest_email=session.email,
        guest_phone=session.phone,
        email_verified=session.email_verified,
        sms_verified=session.sms_verified,
        shipping_address_id=ship_addr.id,
        billing_address_id=bill_addr.id,
        items=items,
        subtotal=subtotal,
        shipping_amount=shipping,
        tax_amount=tax,
        discount_amount=Decimal("0"),
        total_amount=subtotal + shipping + tax,
        payment_method=payload.payment_method,
        notes=payload.notes,
        ip_address=ip_address,
    )
    db.add(order)
    db.flush()
    db.add(OrderStatusHistory(order_id=order.id, new_status="pending", note="Guest order placed."))
    
    # MVP: Deduct stock for each item after order creation
    deduct_stock_for_guest_order(db, items)
    
    db.commit()
    db.refresh(order)
    return order


def get_orders_by_email(db: Session, email: str) -> list[GuestOrder]:
    return (
        db.query(GuestOrder)
        .filter_by(guest_email=email.lower().strip())
        .order_by(GuestOrder.created_at.desc())
        .limit(20)
        .all()
    )