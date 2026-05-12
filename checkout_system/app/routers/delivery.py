from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Product, ServiceablePincode
from app.schemas.schemas import (
    ApiEnvelope,
    DeliveryCheckIn,
    DeliveryCheckOut,
    ServiceablePincodeIn,
    ServiceablePincodeOut,
)

router = APIRouter(tags=["Delivery"])

DbSession = Annotated[Session, Depends(get_db)]

ZONE_SHIPPING = {
    "metro": Decimal("0"),
    "tier1": Decimal("49"),
    "tier2": Decimal("99"),
}


def _success(message: str, data):
    return ApiEnvelope(success=True, message=message, data=data, error=None)


def _require_admin(role: str | None):
    normalized = (role or "").strip().lower()
    if normalized != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Admin access is required.",
                "data": None,
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Admin access is required.",
                    "details": [],
                },
            },
        )


def _seed_dataset():
    def generate(city: str, state: str, zone: str, start: int, count: int):
        return [
            {
                "pincode": str(start + index).zfill(6),
                "city": city,
                "state": state,
                "zone": zone,
                "eta_days_min": 2 if zone == "metro" else 3 if zone == "tier1" else 4,
                "eta_days_max": 3 if zone == "metro" else 4 if zone == "tier1" else 6,
            }
            for index in range(count)
        ]

    return [
        *generate("Mumbai", "Maharashtra", "metro", 400001, 10),
        *generate("Bengaluru", "Karnataka", "metro", 560001, 10),
        *generate("Delhi", "Delhi", "metro", 110001, 10),
        *generate("Hyderabad", "Telangana", "metro", 500001, 10),
        *generate("Chennai", "Tamil Nadu", "metro", 600001, 10),
        *generate("Kolkata", "West Bengal", "metro", 700001, 10),
        *generate("Pune", "Maharashtra", "tier1", 411001, 8),
        *generate("Ahmedabad", "Gujarat", "tier1", 380001, 8),
        *generate("Kochi", "Kerala", "tier2", 682001, 6),
        *generate("Indore", "Madhya Pradesh", "tier2", 452001, 6),
    ]


def seed_serviceable_pincodes(db: Session):
    if db.query(ServiceablePincode).count():
        return

    for entry in _seed_dataset():
        db.add(
            ServiceablePincode(
                pincode=entry["pincode"],
                city=entry["city"],
                state=entry["state"],
                zone=entry["zone"],
                eta_days_min=entry["eta_days_min"],
                eta_days_max=entry["eta_days_max"],
            )
        )
    db.commit()


@router.post("/api/v1/delivery/check", response_model=ApiEnvelope)
@router.post("/check-delivery-availability", response_model=ApiEnvelope)
def check_delivery(payload: DeliveryCheckIn, db: DbSession):
    pincode = db.query(ServiceablePincode).filter(ServiceablePincode.pincode == payload.pincode).first()
    if not pincode or not pincode.is_active:
        response = DeliveryCheckOut(
            is_serviceable=False,
            message="Delivery is not available for this pincode.",
        )
        return _success("Delivery availability checked.", response.model_dump(mode="json"))

    unavailable_items = []
    for item in payload.items:
        product = (
            db.query(Product)
            .filter(Product.id == item.product_id, Product.is_active.is_(True))
            .first()
        )
        if not product:
            unavailable_items.append(
                {
                    "product_id": item.product_id,
                    "reason": "Product is not available.",
                }
            )
            continue
        if int(product.stock_qty or 0) < item.quantity:
            unavailable_items.append(
                {
                    "product_id": item.product_id,
                    "reason": "Requested quantity is not available for this pincode.",
                }
            )

    shipping_fee = (
        Decimal(str(pincode.shipping_fee_override))
        if pincode.shipping_fee_override is not None
        else ZONE_SHIPPING.get(pincode.zone, Decimal("99"))
    )
    response = DeliveryCheckOut(
        is_serviceable=len(unavailable_items) == 0,
        eta_days_min=pincode.eta_days_min,
        eta_days_max=pincode.eta_days_max,
        shipping_fee=shipping_fee,
        message=(
            f"Delivery available in {pincode.city} in {pincode.eta_days_min}-{pincode.eta_days_max} days."
            if not unavailable_items
            else "One or more items cannot be delivered to this pincode right now."
        ),
        unavailable_items=unavailable_items,
    )
    return _success("Delivery availability checked.", response.model_dump(mode="json"))


@router.get("/api/v1/admin/delivery/pincodes", response_model=ApiEnvelope)
def list_pincodes(
    db: DbSession,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
):
    _require_admin(x_role)
    records = db.query(ServiceablePincode).order_by(ServiceablePincode.pincode.asc()).all()
    return _success(
        "Serviceable pincodes fetched successfully.",
        {"items": [ServiceablePincodeOut.model_validate(record).model_dump(mode="json") for record in records]},
    )


@router.post("/api/v1/admin/delivery/pincodes", response_model=ApiEnvelope, status_code=status.HTTP_201_CREATED)
def create_pincode(
    payload: ServiceablePincodeIn,
    db: DbSession,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
):
    _require_admin(x_role)
    record = db.query(ServiceablePincode).filter(ServiceablePincode.pincode == payload.pincode).first()
    if record:
        raise HTTPException(status_code=409, detail="Pincode already exists.")
    record = ServiceablePincode(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return _success(
        "Serviceable pincode created successfully.",
        ServiceablePincodeOut.model_validate(record).model_dump(mode="json"),
    )


@router.patch("/api/v1/admin/delivery/pincodes/{pincode}", response_model=ApiEnvelope)
def update_pincode(
    pincode: str,
    payload: ServiceablePincodeIn,
    db: DbSession,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
):
    _require_admin(x_role)
    record = db.query(ServiceablePincode).filter(ServiceablePincode.pincode == pincode).first()
    if not record:
        raise HTTPException(status_code=404, detail="Pincode not found.")
    for key, value in payload.model_dump().items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return _success(
        "Serviceable pincode updated successfully.",
        ServiceablePincodeOut.model_validate(record).model_dump(mode="json"),
    )


@router.delete("/api/v1/admin/delivery/pincodes/{pincode}", response_model=ApiEnvelope)
def delete_pincode(
    pincode: str,
    db: DbSession,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
):
    _require_admin(x_role)
    record = db.query(ServiceablePincode).filter(ServiceablePincode.pincode == pincode).first()
    if not record:
        raise HTTPException(status_code=404, detail="Pincode not found.")
    db.delete(record)
    db.commit()
    return _success("Serviceable pincode deleted successfully.", {"pincode": pincode})
