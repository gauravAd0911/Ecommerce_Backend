import base64
import hashlib
import hmac
import json
import os
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.schemas.order_schema import FinalizeOrderRequest
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _decode_hs256_subject(token: str) -> str | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            return None
        expected_signature = hmac.new(
            jwt_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_signature = _b64url_decode(parts[2])
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        payload = json.loads(_b64url_decode(parts[1]))
    except (ValueError, json.JSONDecodeError):
        return None

    expires_at = payload.get("exp")
    if isinstance(expires_at, (int, float)) and expires_at < time.time():
        return None
    if payload.get("type") not in {None, "access"}:
        return None
    subject = payload.get("sub") or payload.get("user_id")
    return str(subject) if subject else None


def get_current_user_id(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        user_id = _decode_hs256_subject(authorization.split(" ", 1)[1].strip())
        if user_id:
            return user_id

    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    _failure(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Authenticated user is required.")


CurrentUserId = Annotated[str, Depends(get_current_user_id)]


def _resolve_checkout_actor_id(
    payload: dict,
    authorization: str | None,
    x_user_id: str | None,
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        user_id = _decode_hs256_subject(authorization.split(" ", 1)[1].strip())
        if user_id:
            return user_id

    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    guest_token = str(payload.get("guestToken") or payload.get("guest_token") or "").strip()
    if guest_token:
        return f"guest:{guest_token[:64]}"

    guest_email = str(((payload.get("shippingDetails") or {}).get("email")) or "").strip().lower()
    if guest_email:
        return f"guest:{guest_email[:64]}"

    return f"guest:anonymous:{int(time.time())}"


def get_current_role(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        try:
            payload = json.loads(_b64url_decode(authorization.split(" ", 1)[1].strip().split(".")[1]))
            role = str(payload.get("role") or "").strip().lower()
            if role == "vendor":
                return "employee"
            if role:
                return role
        except (ValueError, json.JSONDecodeError, IndexError):
            pass

    return (x_role or "").strip().lower()


def _item_dict(item) -> dict:
    return {
        "productId": item.product_id,
        "name": item.product_name,
        "quantity": item.quantity,
        "price": item.price,
    }


def _order_summary(order) -> dict:
    return {
        "id": str(order.id),
        "orderNumber": order.order_number,
        "placedOn": order.created_at.isoformat() if getattr(order, "created_at", None) else None,
        "status": order.status,
        "total": order.total,
        "itemCount": order.item_count,
        "primaryLabel": order.primary_label,
        "assignedToEmployeeId": order.assigned_to_employee_id,
        "assignedByAdminId": order.assigned_by_admin_id,
        "statusNote": order.status_note,
    }


def _order_detail(order, service: OrderService) -> dict:
    detail = _order_summary(order)
    detail.update(
        {
            "items": [_item_dict(item) for item in service.order_repo.get_items_for_order(order.id)],
            "shippingAddress": order.shipping_address,
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
    payment_id = (
        payload.get("paymentId")
        or payment_details.get("gatewayPaymentId")
        or payment_details.get("paymentId")
    )
    payment_verified = bool(payment_details.get("verified")) or bool(payment_id)
    if not payment_verified:
        _failure(
            status.HTTP_409_CONFLICT,
            "PAYMENT_VERIFICATION_FAILED",
            "Payment must be verified before order creation.",
        )

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

    order_data = {
        "total": payload.get("total")
        or summary.get("totalAmount")
        or summary.get("total")
        or payment_details.get("amountPaid"),
        "subtotal": payload.get("subtotal") or summary.get("subtotal"),
        "shipping_amount": payload.get("shippingAmount") or summary.get("shippingAmount") or summary.get("shipping"),
        "discount_amount": payload.get("discountAmount") or summary.get("discountAmount") or summary.get("discount"),
        "tax_amount": payload.get("taxAmount") or summary.get("taxAmount") or summary.get("tax"),
        "payment_method": payload.get("paymentMethod")
        or payment_details.get("provider")
        or "razorpay",
        "shipping_address": payload.get("shippingAddress")
        or shipping_details.get("address")
        or str(shipping_details),
        "item_count": payload.get("itemCount")
        or sum(int(item.get("quantity") or 0) for item in normalized_items),
        "primary_label": payload.get("primaryLabel")
        or ", ".join(str(item.get("product_name") or "Item") for item in normalized_items[:2]),
        "items": normalized_items,
    }

    try:
        created = OrderService(db).finalize_order(data=order_data, user_id=user_id)
    except ValueError as exc:
        _failure(400, "ORDER_CREATE_FAILED", str(exc))

    service = OrderService(db)
    order = service.order_repo.get_order_for_user(created["orderNumber"], user_id)
    return _success(
        "Order created successfully.",
        _order_detail(order, service) if order else created,
    )


@router.get("")
def get_orders(db: DBSession, user_id: CurrentUserId, role: Annotated[str, Depends(get_current_role)]):
    service = OrderService(db)
    if role in {"admin", "employee"}:
        return _success(
            "Orders fetched successfully.",
            {"orders": [_order_summary(order) for order in service.order_repo.get_all_orders()]},
        )
    return _success(
        "Orders fetched successfully.",
        {"orders": [_order_summary(order) for order in service.order_repo.get_orders_for_user(user_id)]},
    )


@router.get("/{order_id}")
def get_order(order_id: str, db: DBSession, user_id: CurrentUserId, role: Annotated[str, Depends(get_current_role)]):
    service = OrderService(db)
    if role in {"admin", "employee"}:
        order = service.order_repo.get_order(order_id) if str(order_id).isdigit() else service.order_repo.get_order_by_number(order_id)
    else:
        order = service.order_repo.get_order_for_user(order_id, user_id)
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
