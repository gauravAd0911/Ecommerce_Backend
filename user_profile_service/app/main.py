import os
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.api.v1.endpoints import user, address
import app.db.models.address  # noqa: F401
import app.db.models.user  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.schemas.address import AddressCreate, AddressUpdate

app = FastAPI(title="User Profile Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ AUTO CREATE TABLES (VERY IMPORTANT)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'addresses'
                  AND COLUMN_NAME = 'address_type'
                """
            )
        )
        if int(result.scalar() or 0) == 0:
            connection.execute(text("ALTER TABLE addresses ADD COLUMN address_type VARCHAR(40) DEFAULT 'Home'"))


def _error_payload(*, code: str, message: str, details=None):
    details = details or []
    return {
        "success": False,
        "message": message,
        "data": None,
        "errors": {
            detail.get("field"): detail.get("message", "Invalid value.")
            for detail in details
            if detail.get("field")
        },
        "error": {"code": code, "message": message, "details": details},
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    details = [
        {
            "field": str(error.get("loc", ["request"])[-1]),
            "message": error.get("msg", "Invalid value."),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_payload(code="VALIDATION_ERROR", message="Validation failed", details=details),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and exc.detail.get("success") is False:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    message = str(exc.detail or "Request failed")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": message,
            "data": None,
            "errors": {},
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": message,
            },
        },
    )

# ✅ Include routers
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(address.router, prefix="/api/v1/users/me/addresses", tags=["Addresses"])

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "User Profile Service"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "User Profile Service is running"}

account_router = APIRouter(prefix="/account", tags=["Account"])

@account_router.get("/addresses")
def account_get_addresses(
    db=Depends(address.get_db),
    user_id=Depends(address.get_current_user),
):
    return address.get_addresses(db=db, user_id=user_id)


@account_router.post("/addresses")
def account_create_address(
    payload: dict,
    db=Depends(address.get_db),
    user_id=Depends(address.get_current_user),
):
    normalized = {
        "full_name": payload.get("name", payload.get("full_name")),
        "phone": payload.get("phone", payload.get("phone_number")),
        "address_line1": payload.get("line1", payload.get("address_line1")),
        "address_line2": payload.get("line2", payload.get("address_line2")),
        "landmark": payload.get("landmark"),
        "city": payload.get("city"),
        "state": payload.get("state"),
        "postal_code": payload.get("pincode", payload.get("postal_code")),
        "country": payload.get("country", "India"),
        "address_type": payload.get("address_type", payload.get("addressType", payload.get("label", "Home"))),
        "is_default": payload.get("is_default", payload.get("default", False)),
    }
    return address.create_address(payload=AddressCreate.model_validate(normalized), db=db, user_id=user_id)


@account_router.patch("/addresses/{address_id}")
def account_update_address(
    address_id: str,
    payload: dict,
    db=Depends(address.get_db),
    user_id=Depends(address.get_current_user),
):
    normalized = {
        "full_name": payload.get("name", payload.get("full_name")),
        "phone": payload.get("phone", payload.get("phone_number")),
        "address_line1": payload.get("line1", payload.get("address_line1")),
        "address_line2": payload.get("line2", payload.get("address_line2")),
        "landmark": payload.get("landmark"),
        "city": payload.get("city"),
        "state": payload.get("state"),
        "postal_code": payload.get("pincode", payload.get("postal_code")),
        "country": payload.get("country"),
        "address_type": payload.get("address_type", payload.get("addressType", payload.get("label"))),
        "is_default": payload.get("is_default"),
    }
    data = {key: value for key, value in normalized.items() if value is not None}
    return address.update_address(
        address_id=address_id,
        payload=AddressUpdate.model_validate(data),
        db=db,
        user_id=user_id,
    )


@account_router.delete("/addresses/{address_id}")
def account_delete_address(
    address_id: str,
    db=Depends(address.get_db),
    user_id=Depends(address.get_current_user),
):
    return address.delete_address(address_id=address_id, db=db, user_id=user_id)


@account_router.patch("/addresses/{address_id}/default")
def account_set_default_address(
    address_id: str,
    db=Depends(address.get_db),
    user_id=Depends(address.get_current_user),
):
    return address.set_default(address_id=address_id, db=db, user_id=user_id)

app.include_router(account_router)
