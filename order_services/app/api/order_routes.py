import json
import os
import logging
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_utils import CurrentUserId, get_active_user_id, get_current_role, resolve_guest_user_id
from app.core.database import SessionLocal
from app.schemas.order_schema import FinalizeOrderRequest
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

PAYMENT_SERVICE_BASE_URL = os.getenv("PAYMENT_SERVICE_BASE_URL", "http://localhost:8006").rstrip("/")
PAYMENT_STATUS_TIMEOUT_SECONDS = float(os.getenv("PAYMENT_STATUS_TIMEOUT_SECONDS", "5"))
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()


def _success(message: str, data):
    return {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
    }


def _failure(status_code: int, code: str, message: str):
    raise HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "message": message,
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "details": [],
            },
        },
    )


def _extract_payment_reference(payload: dict) -> str:
    payment_details = payload.get("paymentDetails") or payload.get("payment_details") or {}
    payment_reference = (
        payload.get("paymentReference")
        or payload.get("payment_reference")
        or payment_details.get("paymentReference")
        or payment_details.get("payment_reference")
    )
    payment_reference = str(payment_reference or "").strip()
    if not payment_reference:
        _failure(
            status.HTTP_409_CONFLICT,
            "PAYMENT_VERIFICATION_FAILED",
            "A verified payment reference is required before order creation.",
        )
    return payment_reference


def _fetch_payment_status(payment_reference: str, authorization: str | None = None) -> dict:
    url = f"{PAYMENT_SERVICE_BASE_URL}/api/v1/payments/{quote(payment_reference, safe='')}/status"
    headers = {"Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization

    try:
        with urlopen(Request(url, headers=headers, method="GET"), timeout=PAYMENT_STATUS_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            _failure(status.HTTP_409_CONFLICT, "PAYMENT_NOT_FOUND", "Payment reference was not found.")
        _failure(status.HTTP_502_BAD_GATEWAY, "PAYMENT_STATUS_UNAVAILABLE", "Unable to verify payment status.")
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        _failure(status.HTTP_502_BAD_GATEWAY, "PAYMENT_STATUS_UNAVAILABLE", "Unable to verify payment status.")

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        _failure(status.HTTP_502_BAD_GATEWAY, "PAYMENT_STATUS_INVALID", "Payment status response was invalid.")
    return data


def _require_verified_payment(
    *,
    payload: dict,
    expected_total: float,
    authorization: str | None,
) -> dict:
    try:
        expected_total_value = round(float(expected_total), 2)
    except (TypeError, ValueError):
        _failure(status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR", "Order total is required.")

    payment_reference = _extract_payment_reference(payload)
    payment_status = _fetch_payment_status(payment_reference, authorization=authorization)

    if str(payment_status.get("status") or "").lower() != "verified":
        _failure(status.HTTP_409_CONFLICT, "PAYMENT_VERIFICATION_FAILED", "Payment is not verified.")

    currency = str(payment_status.get("currency") or "").upper()
    if currency and currency != "INR":
        _failure(status.HTTP_409_CONFLICT, "PAYMENT_CURRENCY_MISMATCH", "Payment currency does not match checkout currency.")

    amount_minor = payment_status.get("amount")
    try:
        paid_total = round(float(amount_minor) / 100, 2)
    except (TypeError, ValueError):
        _failure(status.HTTP_502_BAD_GATEWAY, "PAYMENT_STATUS_INVALID", "Payment amount was invalid.")

    if paid_total != expected_total_value:
        _failure(status.HTTP_409_CONFLICT, "PAYMENT_AMOUNT_MISMATCH", "Payment amount does not match order total.")

    return payment_status


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]




def _find_guest_token(payload: dict | list | None) -> str | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"guestToken", "guest_token"} and value is not None and not isinstance(value, bool):
                token = str(value).strip()
                if token:
                    return token
            if isinstance(value, (dict, list)):
                nested = _find_guest_token(value)
                if nested:
                    return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = _find_guest_token(item)
            if nested:
                return nested
    return None


def _resolve_checkout_actor_id(
    payload: dict,
    authorization: str | None,
    x_user_id: str | None,
) -> str:
    active_user_id = get_active_user_id(authorization=authorization, x_user_id=x_user_id)
    if active_user_id != "guest_user":
        return active_user_id

    guest_token = _find_guest_token(payload)
    if guest_token:
        return resolve_guest_user_id(guest_token)

    shipping_details = payload.get("shippingDetails") or payload.get("shipping_details") or {}
    guest_email = (
        payload.get("guestEmail")
        or payload.get("guest_email")
        or shipping_details.get("email")
        or shipping_details.get("emailAddress")
        or shipping_details.get("email_address")
    )
    if guest_email:
        return resolve_guest_user_id(f"email:{guest_email}")

    return "guest_user"


def _item_dict(item) -> dict:
    return {
        "productId": item.product_id,
        "name": item.product_name,
        "quantity": item.quantity,
        "price": item.price,
    }


def _shipping_details_for_order(order) -> dict:
    raw_address = getattr(order, "shipping_address", None)
    if isinstance(raw_address, dict):
        return raw_address

    if isinstance(raw_address, str) and raw_address.strip():
        try:
            parsed = json.loads(raw_address)
            if isinstance(parsed, dict):
                return {
                    "name": parsed.get("name") or parsed.get("full_name") or parsed.get("fullName") or "",
                    "email": parsed.get("email") or "",
                    "phone": parsed.get("phone") or "",
                    "address": parsed.get("address") or "",
                    "addressLine1": parsed.get("addressLine1") or parsed.get("address_line1") or "",
                    "addressLine2": parsed.get("addressLine2") or parsed.get("address_line2") or "",
                    "city": parsed.get("city") or "",
                    "state": parsed.get("state") or "",
                    "pincode": parsed.get("pincode") or parsed.get("postal_code") or "",
                    "country": parsed.get("country") or "India",
                }
        except json.JSONDecodeError:
            pass

    return {
        "name": "",
        "email": getattr(order, "guest_email", None) or "",
        "phone": getattr(order, "guest_phone", None) or "",
        "address": raw_address or "",
        "addressLine1": raw_address or "",
        "addressLine2": "",
        "city": "",
        "state": "",
        "pincode": "",
        "country": "India",
    }


def _order_summary(order) -> dict:
    return {
        "orderId": str(order.id),
        "id": str(order.id),
        "orderNumber": order.order_number,
        "placedOn": order.created_at.isoformat() if getattr(order, "created_at", None) else None,
        "status": order.status,
        "total": order.total,
        "totalAmount": order.total,
        "subtotal": order.subtotal,
        "shippingAmount": order.shipping_amount,
        "discount": order.discount_amount,
        "tax": order.tax_amount,
        "itemCount": order.item_count,
        "primaryLabel": order.primary_label,
        "paymentReference": order.payment_reference,
        "paymentDetails": _payment_details_for_order(order),
        "shippingDetails": _shipping_details_for_order(order),
        "guestEmail": order.guest_email,
        "guestPhone": order.guest_phone,
        "assignedToEmployeeId": order.assigned_to_employee_id,
        "assignedByAdminId": order.assigned_by_admin_id,
        "statusNote": order.status_note,
    }


def _payment_details_for_order(order) -> dict:
    payment_reference = getattr(order, "payment_reference", None)
    fallback = {
        "provider": getattr(order, "payment_method", None) or "razorpay",
        "providerMode": "live",
        "gatewayOrderId": "",
        "gatewayPaymentId": payment_reference or "",
        "paymentReference": payment_reference,
        "verified": bool(payment_reference),
        "amountPaid": getattr(order, "total", None),
        "currency": "INR",
        "paidAt": order.created_at.isoformat() if getattr(order, "created_at", None) else None,
    }

    if not payment_reference:
        return fallback

    try:
        payment_status = _fetch_payment_status(str(payment_reference))
    except HTTPException:
        return fallback

    amount_minor = payment_status.get("amount")
    try:
        amount_paid = round(float(amount_minor) / 100, 2)
    except (TypeError, ValueError):
        amount_paid = fallback["amountPaid"]

    provider_payment_id = payment_status.get("provider_payment_id")
    return {
        "provider": payment_status.get("provider") or fallback["provider"],
        "providerMode": "live",
        "gatewayOrderId": payment_status.get("razorpay_order_id") or "",
        "gatewayPaymentId": provider_payment_id or payment_reference,
        "providerPaymentId": provider_payment_id,
        "paymentReference": payment_reference,
        "verified": str(payment_status.get("status") or "").lower() == "verified",
        "amountPaid": amount_paid,
        "currency": payment_status.get("currency") or fallback["currency"],
        "paidAt": payment_status.get("verified_at") or payment_status.get("updated_at") or fallback["paidAt"],
    }


def _order_detail(order, service: OrderService) -> dict:
    detail = _order_summary(order)
    detail.update(
        {
            "items": [_item_dict(item) for item in service.order_repo.get_items_for_order(order.id)],
            "shippingAddress": order.shipping_address,
            "shippingDetails": _shipping_details_for_order(order),
            "paymentMethod": order.payment_method,
            "assignedToEmployeeId": order.assigned_to_employee_id,
            "assignedByAdminId": order.assigned_by_admin_id,
            "statusNote": order.status_note,
        }
    )
    return detail


def _require_operational_role(role: str):
    if role not in {"admin", "employee"}:
        _failure(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Admin or employee access is required.")


def _require_internal_token(x_internal_token: str | None):
    if not INTERNAL_SERVICE_TOKEN:
        _failure(status.HTTP_503_SERVICE_UNAVAILABLE, "INTERNAL_AUTH_NOT_CONFIGURED", "Internal service authentication is not configured.")
    if not x_internal_token or x_internal_token.strip() != INTERNAL_SERVICE_TOKEN:
        _failure(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Internal service token is invalid.")


def _allowed_next_statuses(current_status: str):
    transitions = {
        "PLACED": {"CONFIRMED", "PACKED", "CANCELLED", "PAYMENT_FAILED"},
        "CONFIRMED": {"PACKED", "CANCELLED"},
        "PACKED": {"SHIPPED", "CANCELLED"},
        "SHIPPED": {"OUT_FOR_DELIVERY"},
        "OUT_FOR_DELIVERY": {"DELIVERED"},
        "DELIVERED": set(),
        "CANCELLED": set(),
        "PAYMENT_FAILED": set(),
    }
    return transitions.get(str(current_status or "").upper(), set())


@router.post("/finalize")
def finalize(data: FinalizeOrderRequest, db: DBSession, user_id: CurrentUserId):
    try:
        created = OrderService(db).finalize_order(data=data.model_dump(), user_id=user_id)
        return _success("Order finalized successfully.", created)
    except ValueError as exc:
        _failure(400, "ORDER_CREATE_FAILED", str(exc))


@router.post("")
def create_order(
    payload: dict,
    db: DBSession,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    user_id = _resolve_checkout_actor_id(payload, authorization, x_user_id)
    payment_details = payload.get("paymentDetails") or {}
    summary = payload.get("summary") or {}
    shipping_details = payload.get("shippingDetails") or {}
    items = payload.get("items") or summary.get("items") or []
    if not items and payload.get("lineItems"):
        items = payload["lineItems"]

    normalized_items = [
        {
            "product_id": item.get("productId") or item.get("product_id") or item.get("id"),
            "product_name": item.get("productName") or item.get("name") or item.get("label"),
            "price": item.get("price") or item.get("unitPrice") or item.get("unit_price") or 0,
            "quantity": item.get("quantity") or 0,
            "image_url": item.get("imageUrl") or item.get("image_url"),
        }
        for item in items
    ]

    order_total = (
        payload.get("total")
        or summary.get("totalAmount")
        or summary.get("total")
        or payment_details.get("amountPaid")
    )
    payment_status = _require_verified_payment(
        payload=payload,
        expected_total=order_total,
        authorization=authorization,
    )

    service = OrderService(db)
    existing_order = service.order_repo.get_order_by_payment_reference(payment_status["payment_reference"])
    if existing_order:
        return _success("Order already exists for this payment.", _order_detail(existing_order, service))

    guest_token = _find_guest_token(payload)
    order_data = {
        "total": order_total,
        "subtotal": payload.get("subtotal") or summary.get("subtotal"),
        "shipping_amount": payload.get("shippingAmount") or summary.get("shippingAmount") or summary.get("shipping"),
        "discount_amount": payload.get("discountAmount") or summary.get("discountAmount") or summary.get("discount"),
        "tax_amount": payload.get("taxAmount") or summary.get("taxAmount") or summary.get("tax"),
        "payment_method": payload.get("paymentMethod")
        or payment_details.get("provider")
        or "razorpay",
        "shipping_address": payload.get("shippingAddress")
        or json.dumps(shipping_details, ensure_ascii=True),
        "item_count": payload.get("itemCount")
        or sum(int(item.get("quantity") or 0) for item in normalized_items),
        "primary_label": payload.get("primaryLabel")
        or ", ".join(str(item.get("product_name") or "Item") for item in normalized_items[:2]),
        "guest_token": guest_token,
        "guest_email": (shipping_details.get("email") or payload.get("guestEmail") or payload.get("guest_email") or "").lower().strip() or None,
        "guest_phone": shipping_details.get("phone") or payload.get("guestPhone") or payload.get("guest_phone"),
        "payment_reference": payment_status["payment_reference"],
        "items": normalized_items,
    }

    try:
        logger.info(f"[ORDER_CREATE] Starting order finalization for user_id={user_id}")
        created = service.finalize_order(data=order_data, user_id=user_id)
        logger.info(f"[ORDER_CREATE] Order finalized. Response: {created}")
    except ValueError as exc:
        logger.error(f"[ORDER_CREATE] ValueError during finalization: {exc}")
        _failure(400, "ORDER_CREATE_FAILED", str(exc))
    except Exception as exc:
        logger.error(f"[ORDER_CREATE] Unexpected error during finalization: {exc}", exc_info=True)
        _failure(500, "ORDER_CREATE_ERROR", f"Order creation failed: {str(exc)}")

    order_number = created.get("orderNumber")
    logger.info(f"[ORDER_CREATE] Order number generated: {order_number}")
    
    # Ensure session is refreshed after commit
    service.db.expunge_all()
    logger.info(f"[ORDER_CREATE] Session cleared. Attempting to retrieve order {order_number}")
    
    # Try to retrieve the order from database
    order = service.order_repo.get_order_by_number(order_number)
    logger.info(f"[ORDER_CREATE] Order retrieved by number: {order is not None}")
    
    if not order:
        logger.warning(f"[ORDER_CREATE] Order not found by number {order_number}, trying by user_id {user_id}")
        order = service.order_repo.get_order_for_user(order_number, user_id)
        logger.info(f"[ORDER_CREATE] Order retrieved by user_id: {order is not None}")

    if not order:
        logger.error(f"[ORDER_CREATE] CRITICAL: Order {order_number} was saved but NOT found in database!")
        _failure(
            500,
            "ORDER_SAVE_FAILED",
            f"Order creation returned number {order_number} but database retrieval failed. "
            "The order may not have been committed. Check backend logs and database connection.",
        )

    logger.info(f"[ORDER_CREATE] Order successfully created and retrieved: id={order.id}")
    return _success(
        "Order created successfully.",
        _order_detail(order, service),
    )


@router.get("")
def get_orders(
    db: DBSession,
    user_id: CurrentUserId,
    role: Annotated[str, Depends(get_current_role)],
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
):
    service = OrderService(db)
    if role in {"admin", "employee"}:
        return _success(
            "Orders fetched successfully.",
            {"orders": [_order_summary(order) for order in service.order_repo.get_all_orders()]},
        )
    return _success(
        "Orders fetched successfully.",
        {"orders": [_order_summary(order) for order in service.order_repo.get_orders_for_user(user_id, email=x_user_email)]},
    )


@router.get("/{order_id}")
def get_order(
    order_id: str,
    db: DBSession,
    user_id: CurrentUserId,
    role: Annotated[str, Depends(get_current_role)],
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
):
    service = OrderService(db)
    if role in {"admin", "employee"}:
        order = service.order_repo.get_order(order_id) if str(order_id).isdigit() else service.order_repo.get_order_by_number(order_id)
    else:
        order = service.order_repo.get_order_for_user(order_id, user_id, email=x_user_email)
    if not order:
        _failure(404, "ORDER_NOT_FOUND", "Order not found")
    return _success("Order fetched successfully.", _order_detail(order, service))


@router.get("/{order_id}/tracking")
def get_tracking(order_id: str, db: DBSession, user_id: CurrentUserId):
    service = OrderService(db)
    order = service.order_repo.get_order_for_user(order_id, user_id)
    if not order:
        _failure(404, "ORDER_NOT_FOUND", "Order not found")
    return _success(
        "Order tracking fetched successfully.",
        {"tracking": service.tracking_repo.get_tracking(order_id)},
    )


@router.get("/internal/guest-lookup")
def internal_guest_lookup(
    email: str,
    db: DBSession,
    order_number: str | None = None,
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
):
    _require_internal_token(x_internal_token)
    orders = OrderService(db).order_repo.get_guest_orders_by_email(email, order_number=order_number)
    return _success("Guest orders fetched successfully.", {"orders": [_order_summary(order) for order in orders]})


@router.patch("/admin/{order_id}/status")
def update_order_status(
    order_id: str,
    payload: dict,
    db: DBSession,
    role: Annotated[str, Depends(get_current_role)],
):
    _require_operational_role(role)
    service = OrderService(db)
    order = service.order_repo.get_order(order_id) if str(order_id).isdigit() else service.order_repo.get_order_by_number(str(order_id))
    if not order:
        _failure(404, "ORDER_NOT_FOUND", "Order not found")

    next_status = str(payload.get("status") or "").upper()
    if not next_status:
        _failure(400, "VALIDATION_ERROR", "Order status is required.")
    if next_status not in _allowed_next_statuses(order.status):
        _failure(409, "INVALID_ORDER_TRANSITION", f"Cannot change order status from {order.status} to {next_status}.")

    order.status_note = payload.get("note")
    order.last_updated_by = payload.get("actorUserId")
    service.order_repo.update_status(order.id, next_status)
    service.tracking_repo.add_tracking(order.id, next_status, payload.get("note") or f"Status updated to {next_status}")
    db.commit()
    refreshed = service.order_repo.get_order(order.id)
    return _success("Order status updated successfully.", _order_detail(refreshed, service))


@router.patch("/admin/{order_id}/assign")
def assign_order(
    order_id: str,
    payload: dict,
    db: DBSession,
    role: Annotated[str, Depends(get_current_role)],
    actor_user_id: CurrentUserId,
):
    _require_operational_role(role)
    employee_id = str(payload.get("employeeId") or payload.get("employee_id") or "").strip()
    if not employee_id:
        _failure(400, "VALIDATION_ERROR", "Employee id is required.")

    service = OrderService(db)
    order = service.order_repo.get_order(order_id) if str(order_id).isdigit() else service.order_repo.get_order_by_number(str(order_id))
    if not order:
        _failure(404, "ORDER_NOT_FOUND", "Order not found")

    order = service.order_repo.assign_order(order.id, employee_id, actor_user_id)
    return _success("Order assigned successfully.", _order_detail(order, service))


@router.get("/admin/dashboard/summary")
def admin_dashboard_summary(
    db: DBSession,
    role: Annotated[str, Depends(get_current_role)],
):
    _require_operational_role(role)
    service = OrderService(db)
    orders = service.order_repo.get_all_orders()
    total_orders = len(orders)
    gross_revenue = round(sum(float(order.total or 0) for order in orders), 2)
    status_breakdown = {}
    for order in orders:
        status_breakdown[order.status] = status_breakdown.get(order.status, 0) + 1

    return _success(
        "Dashboard summary fetched successfully.",
        {
            "total_orders": total_orders,
            "gross_revenue": gross_revenue,
            "average_order_value": round(gross_revenue / total_orders, 2) if total_orders else 0,
            "status_breakdown": status_breakdown,
        },
    )
