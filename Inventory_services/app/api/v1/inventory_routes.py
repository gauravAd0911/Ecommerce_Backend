from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.stock_repo import StockRepository
from app.schemas.inventory import StockValidationRequest, StockValidationResponse
from app.schemas.reservation import (
    ReservationActionResponse,
    ReservationCreateRequest,
    ReservationResponse,
)
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory"])

DbSession = Annotated[Session, Depends(get_db)]


def _success_response(data, message: str = "Inventory request completed successfully."):
    return {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
    }


def _validation_error(error: ValidationError):
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=error.errors(),
    )


def _reservation_payload(reservation):
    return {
        "id": reservation.id,
        "reservation_id": str(reservation.id),
        "product_id": reservation.product_id,
        "warehouse_id": reservation.warehouse_id,
        "quantity": reservation.quantity,
        "status": reservation.status,
        "expires_at": reservation.expires_at,
    }


def _parse_reservation_ids(value: str) -> list[int]:
    try:
        reservation_ids = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError:
        reservation_ids = []

    if not reservation_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reservation id must be a number or comma-separated numbers.",
        )

    return reservation_ids


def _batch_response(reservations):
    reservation_ids = ",".join(str(reservation.id) for reservation in reservations)
    return {
        "id": reservation_ids,
        "reservation_id": reservation_ids,
        "status": "ACTIVE",
        "expires_at": min(reservation.expires_at for reservation in reservations),
        "items": [_reservation_payload(reservation) for reservation in reservations],
    }


def _build_stock_payload(item: dict, default_warehouse_id: int) -> StockValidationRequest:
    try:
        return StockValidationRequest.model_validate(
            {
                **item,
                "warehouse_id": item.get("warehouse_id") or default_warehouse_id,
            }
        )
    except ValidationError as error:
        _validation_error(error)


def _build_reservation_payload(item: dict, default_warehouse_id: int, idempotency_key: str | None):
    try:
        return ReservationCreateRequest.model_validate(
            {
                **item,
                "warehouse_id": item.get("warehouse_id") or default_warehouse_id,
                "idempotency_key": item.get("idempotency_key") or idempotency_key,
            }
        )
    except ValidationError as error:
        _validation_error(error)


@router.post("/validate")
def validate_stock(payload: dict, db: DbSession):
    if isinstance(payload.get("items"), list):
        items = payload.get("items") or []
        if not items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Inventory items are required.",
            )

        issues = []
        available_quantities = []
        default_warehouse_id = int(payload.get("warehouse_id") or 1)
        stock_repository = StockRepository(db)

        for item in items:
            stock_payload = _build_stock_payload(item, default_warehouse_id)
            stock = stock_repository.get_stock(stock_payload.product_id, stock_payload.warehouse_id)
            available_quantity = max(stock.available_quantity, 0) if stock else 0
            available_quantities.append(available_quantity)

            if available_quantity < stock_payload.quantity:
                issues.append(
                    {
                        "product_id": stock_payload.product_id,
                        "warehouse_id": stock_payload.warehouse_id,
                        "available_quantity": available_quantity,
                        "requested_quantity": stock_payload.quantity,
                        "message": "Requested quantity is not available.",
                        "stock_state": "limited" if available_quantity > 0 else "out_of_stock",
                    }
                )

        return _success_response(
            {
                "is_available": len(issues) == 0,
                "available_quantity": min(available_quantities or [0]),
                "issues": issues,
            },
            "Inventory validated successfully.",
        )

    try:
        stock_payload = StockValidationRequest.model_validate(payload)
    except ValidationError as error:
        _validation_error(error)

    stock = StockRepository(db).get_stock(stock_payload.product_id, stock_payload.warehouse_id)
    available_quantity = max(stock.available_quantity, 0) if stock else 0
    response = StockValidationResponse(
        is_available=available_quantity >= stock_payload.quantity,
        available_quantity=available_quantity,
    )
    return _success_response(response.model_dump(), "Inventory validated successfully.")


@router.post("/reservations", status_code=201)
def create_reservation(payload: dict, db: DbSession):
    service = ReservationService(db)

    if isinstance(payload.get("items"), list):
        items = payload.get("items") or []
        if not items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Reservation items are required.",
            )

        default_warehouse_id = int(payload.get("warehouse_id") or 1)
        base_idempotency_key = str(payload.get("idempotency_key") or "").strip() or None
        reservations = []

        for index, item in enumerate(items):
            idempotency_key = (
                item.get("idempotency_key")
                or (f"{base_idempotency_key}:{index}" if base_idempotency_key else None)
            )
            reservation_payload = _build_reservation_payload(
                item,
                default_warehouse_id,
                idempotency_key,
            )
            reservations.append(
                service.create_reservation(
                    product_id=reservation_payload.product_id,
                    warehouse_id=reservation_payload.warehouse_id,
                    quantity=reservation_payload.quantity,
                    idempotency_key=reservation_payload.idempotency_key,
                )
            )

        return _success_response(_batch_response(reservations), "Stock reserved successfully.")

    try:
        reservation_payload = ReservationCreateRequest.model_validate(payload)
    except ValidationError as error:
        _validation_error(error)

    reservation = service.create_reservation(
        product_id=reservation_payload.product_id,
        warehouse_id=reservation_payload.warehouse_id,
        quantity=reservation_payload.quantity,
        idempotency_key=reservation_payload.idempotency_key,
    )
    return _success_response(
        ReservationResponse.model_validate(reservation).model_dump(),
        "Stock reserved successfully.",
    )


@router.delete("/reservations/{reservation_id}", response_model=dict)
def release_reservation(reservation_id: str, db: DbSession):
    service = ReservationService(db)
    for current_id in _parse_reservation_ids(reservation_id):
        service.release_reservation(current_id)

    response = ReservationActionResponse(message=f"Reservation {reservation_id} released")
    return _success_response(response.model_dump(), "Reservation released successfully.")


@router.post("/reservations/{reservation_id}/commit", response_model=dict)
def commit_reservation(reservation_id: str, db: DbSession):
    service = ReservationService(db)
    for current_id in _parse_reservation_ids(reservation_id):
        service.commit_reservation(current_id)

    response = ReservationActionResponse(message=f"Reservation {reservation_id} committed")
    return _success_response(response.model_dump(), "Reservation committed successfully.")


@router.post("/reservations/{reservation_id}/release", response_model=dict)
def release_reservation_post(reservation_id: str, db: DbSession):
    service = ReservationService(db)
    for current_id in _parse_reservation_ids(reservation_id):
        service.release_reservation(current_id)

    response = ReservationActionResponse(message=f"Reservation {reservation_id} released")
    return _success_response(response.model_dump(), "Reservation released successfully.")
