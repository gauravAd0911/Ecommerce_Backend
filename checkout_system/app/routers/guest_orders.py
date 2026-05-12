"""
Guest Order Routes
------------------
POST /api/v1/guest-orders                 — place order (requires both OTPs verified)
POST /api/v1/guest-orders/request-lookup  — send email OTP for lookup
POST /api/v1/guest-orders/verify-lookup   — verify OTP → return orders
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import GuestCheckoutSession, OtpChannel, OtpPurpose
from app.schemas.schemas import (
    GuestOrderIn, GuestOrderOut, AddressOut,
    LookupRequestIn, LookupRequestOut,
    LookupVerifyIn, LookupVerifyOut,
)
from app.services.otp_service import (
    create_lookup_session, send_otp, verify_otp,
    require_checkout_session, require_lookup_session,
    expire_secs,
)
from app.services.order_service import create_order, get_orders_by_email

router = APIRouter(prefix="/api/v1/guest-orders", tags=["Guest Orders"])
cfg    = get_settings()
ORDER_SERVICE_BASE_URL = os.getenv("ORDER_SERVICE_BASE_URL", "http://localhost:8007").rstrip("/")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
ORDER_LOOKUP_TIMEOUT_SECONDS = float(os.getenv("ORDER_LOOKUP_TIMEOUT_SECONDS", "5"))


def _addr(a) -> AddressOut | None:
    if not a:
        return None
    return AddressOut(
        id=a.id, full_name=a.full_name, line1=a.line1, line2=a.line2,
        city=a.city, state=a.state, postal_code=a.postal_code,
        country=a.country, phone=a.phone, created_at=a.created_at,
    )

def _out(o) -> GuestOrderOut:
    return GuestOrderOut(
        id=o.id, order_number=o.order_number,
        guest_name=o.guest_name, guest_email=o.guest_email, guest_phone=o.guest_phone,
        email_verified=o.email_verified, sms_verified=o.sms_verified,
        items=o.items, subtotal=o.subtotal, shipping_amount=o.shipping_amount,
        tax_amount=o.tax_amount, discount_amount=o.discount_amount,
        total_amount=o.total_amount, currency=o.currency,
        status=o.status, payment_status=o.payment_status,
        shipping_address=_addr(o.shipping_address), created_at=o.created_at,
    )


@router.post("", response_model=GuestOrderOut, status_code=201)
def place_order(payload: GuestOrderIn, request: Request, db: Session = Depends(get_db)):
    """Place a guest order. Requires session_token (issued only after email + WhatsApp verified)."""
    session = require_checkout_session(db, payload.session_token)
    order   = create_order(db, payload, session, ip_address=request.client.host if request.client else None)
    return _out(order)


@router.post("/request-lookup", response_model=LookupRequestOut, status_code=201)
def request_lookup(payload: LookupRequestIn, request: Request, db: Session = Depends(get_db)):
    """Step 1 of order lookup — sends email OTP only (no WhatsApp needed for read-only access)."""
    session = create_lookup_session(
        db, email=str(payload.email),
        ip_address=request.client.host if request.client else None,
    )
    otp = send_otp(db, session=session, channel=OtpChannel.email, purpose=OtpPurpose.order_lookup)

    return LookupRequestOut(
        session_id=session.id, otp_id=otp.id,
        expires_in_secs=expire_secs(),
        dev_code=otp.plain_code if cfg.dev_show_code else None,
        message=f"[DEV] Code: {otp.plain_code}" if cfg.dev_show_code else "Lookup code sent to your email.",
    )


def _lookup_order_service_orders(email: str, order_number: str | None = None) -> list[dict]:
    if not INTERNAL_SERVICE_TOKEN:
        return []

    query = {"email": email}
    if order_number:
        query["order_number"] = order_number
    url = f"{ORDER_SERVICE_BASE_URL}/api/v1/orders/internal/guest-lookup?{urlencode(query, quote_via=quote)}"
    request = UrlRequest(
        url,
        headers={"Accept": "application/json", "X-Internal-Token": INTERNAL_SERVICE_TOKEN},
        method="GET",
    )
    try:
        with urlopen(request, timeout=ORDER_LOOKUP_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []

    data = payload.get("data") if isinstance(payload, dict) else {}
    orders = data.get("orders") if isinstance(data, dict) else []
    return orders if isinstance(orders, list) else []


@router.post("/verify-lookup", response_model=LookupVerifyOut)
def verify_lookup(payload: LookupVerifyIn, db: Session = Depends(get_db)):
    """
    Step 2 — verify email OTP, return all matching guest orders.
    Pass order_number to filter to one specific order.
    """
    session = verify_otp(
        db, session_id=payload.session_id, otp_id=payload.otp_id,
        channel=OtpChannel.email, code=payload.code,
    )
    if not session.session_token:
        raise HTTPException(500, "Session token not issued after verification.")

    require_lookup_session(db, session.session_token)
    local_orders = get_orders_by_email(db, session.email)

    if payload.order_number:
        local_orders = [o for o in local_orders if o.order_number == payload.order_number]

    orders = [order.model_dump(mode="json") for order in [_out(o) for o in local_orders]]
    remote_orders = _lookup_order_service_orders(session.email, payload.order_number)
    known_order_numbers = {order.get("order_number") or order.get("orderNumber") for order in orders}
    for remote_order in remote_orders:
        remote_number = remote_order.get("orderNumber") or remote_order.get("order_number")
        if remote_number not in known_order_numbers:
            orders.append(remote_order)

    return LookupVerifyOut(
        orders=orders,
        message=f"Found {len(orders)} order(s) for {session.email}.",
    )
