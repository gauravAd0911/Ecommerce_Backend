from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import InventoryReservation, Product
from app.schemas.schemas import (
    ApiEnvelope,
    InventoryIssueOut,
    InventoryReservationOut,
    InventoryValidateIn,
    InventoryValidateOut,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory"])

DbSession = Annotated[Session, Depends(get_db)]
RESERVATION_TTL_MINUTES = 10
LIMITED_STOCK_THRESHOLD = 5


def _success(message: str, data):
    return ApiEnvelope(success=True, message=message, data=data, error=None)


def _active_reserved_quantity(db: Session, product_id: str) -> int:
    now = datetime.utcnow()
    reserved_quantity = (
        db.query(func.coalesce(func.sum(InventoryReservation.quantity), 0))
        .filter(
            InventoryReservation.product_id == product_id,
            InventoryReservation.status == "active",
            InventoryReservation.expires_at > now,
        )
        .scalar()
    )
    return int(reserved_quantity or 0)


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


def _validate_items(db: Session, items) -> InventoryValidateOut:
    issues: list[InventoryIssueOut] = []

    for item in items:
        product = _sync_product_snapshot(db, item)
        if not product:
            issues.append(
                InventoryIssueOut(
                    product_id=item.product_id,
                    available_quantity=0,
                    requested_quantity=item.quantity,
                    message="This product is no longer available.",
                    stock_state="out_of_stock",
                )
            )
            continue

        available_quantity = max(int(product.stock_qty or 0) - _active_reserved_quantity(db, product.id), 0)
        if item.quantity > available_quantity:
            issues.append(
                InventoryIssueOut(
                    product_id=product.id,
                    available_quantity=available_quantity,
                    requested_quantity=item.quantity,
                    message=(
                        f"Only {available_quantity} unit(s) of {product.name} are available right now."
                        if available_quantity > 0
                        else f"{product.name} is currently out of stock."
                    ),
                    stock_state="limited" if available_quantity > 0 else "out_of_stock",
                )
            )
        elif available_quantity <= LIMITED_STOCK_THRESHOLD:
            issues.append(
                InventoryIssueOut(
                    product_id=product.id,
                    available_quantity=available_quantity,
                    requested_quantity=item.quantity,
                    message=f"Limited stock: only {available_quantity} unit(s) of {product.name} remain.",
                    stock_state="limited",
                )
            )

    blocking = [issue for issue in issues if issue.requested_quantity > issue.available_quantity]
    return InventoryValidateOut(is_available=len(blocking) == 0, issues=issues)


@router.post("/validate", response_model=ApiEnvelope)
def validate_inventory(payload: InventoryValidateIn, db: DbSession):
    validation = _validate_items(db, payload.items)
    return _success("Inventory validated successfully.", validation.model_dump(mode="json"))


@router.post("/reservations", response_model=ApiEnvelope, status_code=status.HTTP_201_CREATED)
def create_reservation(payload: InventoryValidateIn, db: DbSession):
    validation = _validate_items(db, payload.items)
    blocking = [issue for issue in validation.issues if issue.requested_quantity > issue.available_quantity]
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "message": "Inventory reservation failed.",
                "data": None,
                "error": {
                    "code": "OUT_OF_STOCK",
                    "message": blocking[0].message,
                    "details": [issue.model_dump(mode="json") for issue in blocking],
                },
            },
        )

    reservation_id = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=RESERVATION_TTL_MINUTES)
    for item in payload.items:
        db.add(
            InventoryReservation(
                reservation_group_id=reservation_id,
                product_id=item.product_id,
                quantity=item.quantity,
                expires_at=expires_at,
            )
        )
    db.commit()
    response = InventoryReservationOut(
        reservation_id=reservation_id,
        expires_at=expires_at,
        items=payload.items,
    )
    return _success("Inventory reserved successfully.", response.model_dump(mode="json"))


@router.delete("/reservations/{reservation_id}", response_model=ApiEnvelope)
def release_reservation(reservation_id: str, db: DbSession):
    reservations = db.query(InventoryReservation).filter(InventoryReservation.reservation_group_id == reservation_id).all()
    for reservation in reservations:
        reservation.status = "released"
    db.commit()
    return _success("Inventory reservation released successfully.", {"reservation_id": reservation_id})


@router.post("/reservations/{reservation_id}/commit", response_model=ApiEnvelope)
def commit_reservation(reservation_id: str, db: DbSession):
    reservations = db.query(InventoryReservation).filter(InventoryReservation.reservation_group_id == reservation_id).all()
    if not reservations:
        raise HTTPException(status_code=404, detail="Reservation not found.")

    for reservation in reservations:
        if reservation.status != "active":
            continue
        if reservation.expires_at <= datetime.utcnow():
            reservation.status = "expired"
            db.commit()
            raise HTTPException(status_code=409, detail="Reservation expired.")
        product = db.query(Product).filter(Product.id == reservation.product_id).first()
        if not product or int(product.stock_qty or 0) < reservation.quantity:
            raise HTTPException(status_code=409, detail="Reserved stock is no longer available.")
        product.stock_qty = int(product.stock_qty or 0) - reservation.quantity
        reservation.status = "committed"

    db.commit()
    return _success("Inventory reservation committed successfully.", {"reservation_id": reservation_id})
