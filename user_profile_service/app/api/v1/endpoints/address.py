import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.dependencies.auth import get_db, get_current_user
from app.services import address_service
from app.schemas.address import AddressCreate, AddressDeleteResponse, AddressResponse, AddressUpdate
from app.schemas.common import APIResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize_address(address) -> AddressResponse:
    return AddressResponse.model_validate(address)


def _not_found_error(exc: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "success": False,
            "message": "Address not found",
            "data": None,
            "errors": {},
            "error": {
                "code": "ADDRESS_NOT_FOUND",
                "message": str(exc),
            },
        },
    )


def _database_error(action: str, exc: SQLAlchemyError) -> HTTPException:
    logger.exception("Database error while %s address", action)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "success": False,
            "message": f"Failed to {action} address",
            "data": None,
            "errors": {},
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Database error occurred",
            },
        },
    )


@router.get("/", response_model=APIResponse[List[AddressResponse]])
@router.get("", response_model=APIResponse[List[AddressResponse]])
def get_addresses(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> APIResponse[List[AddressResponse]]:
    try:
        addresses = address_service.get_addresses(db, user_id)
        return APIResponse[List[AddressResponse]](
            success=True,
            message="Addresses retrieved successfully",
            data=[_serialize_address(address) for address in addresses],
        )
    except SQLAlchemyError as exc:
        raise _database_error("retrieve", exc) from exc


@router.get("/{address_id}", response_model=APIResponse[AddressResponse])
def get_address(
    address_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    try:
        address = address_service.get_address(db, user_id, address_id)
        return APIResponse[AddressResponse](
            success=True,
            message="Address retrieved successfully",
            data=_serialize_address(address),
        )
    except ValueError as exc:
        raise _not_found_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_error("retrieve", exc) from exc


@router.post("/", response_model=APIResponse[AddressResponse])
@router.post("", response_model=APIResponse[AddressResponse])
def create_address(
    payload: AddressCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> APIResponse[AddressResponse]:
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict() if hasattr(payload, "dict") else payload
    try:
        address = address_service.create_address(db, user_id, data)
        return APIResponse[AddressResponse](
            success=True,
            message="Address saved successfully",
            data=_serialize_address(address),
        )
    except SQLAlchemyError as exc:
        raise _database_error("create", exc) from exc


@router.patch("/{address_id}", response_model=APIResponse[AddressResponse])
def update_address(
    address_id: str,
    payload: AddressUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> APIResponse[AddressResponse]:
    try:
        data = payload.model_dump(exclude_unset=True)
        address = address_service.update_address(db, user_id, address_id, data)
        return APIResponse[AddressResponse](
            success=True,
            message="Address updated successfully",
            data=_serialize_address(address),
        )
    except ValueError as exc:
        raise _not_found_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_error("update", exc) from exc


@router.delete("/{address_id}", response_model=APIResponse[AddressDeleteResponse])
def delete_address(
    address_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> APIResponse[AddressDeleteResponse]:
    try:
        result = address_service.delete_address(db, user_id, address_id)
        return APIResponse[AddressDeleteResponse](
            success=True,
            message="Address deleted successfully",
            data=AddressDeleteResponse.model_validate(result),
        )
    except ValueError as exc:
        raise _not_found_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_error("delete", exc) from exc


@router.patch("/{address_id}/default", response_model=APIResponse[AddressResponse])
def set_default(
    address_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
) -> APIResponse[AddressResponse]:
    try:
        address = address_service.set_default_address(db, user_id, address_id)
        return APIResponse[AddressResponse](
            success=True,
            message="Default address set successfully",
            data=_serialize_address(address),
        )
    except ValueError as exc:
        raise _not_found_error(exc) from exc
    except SQLAlchemyError as exc:
        raise _database_error("set default", exc) from exc
