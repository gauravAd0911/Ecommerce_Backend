from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.inventory_routes import router as inventory_router
from app.core.config import settings
from app.core.database import Base, engine

# ensure model metadata is imported so SQLAlchemy can create missing tables
import app.models.product  # noqa: F401
import app.models.warehouse  # noqa: F401
import app.models.stock  # noqa: F401
import app.models.reservation  # noqa: F401
import app.models.ledger  # noqa: F401

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.ALLOWED_ORIGINS,
    allow_credentials=False if settings.DEBUG else True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_payload(*, code: str, message: str, details=None):
    return {
        "success": False,
        "message": message,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        payload = _error_payload(
            code=str(detail.get("code") or "REQUEST_FAILED"),
            message=str(detail.get("message") or "Request failed"),
            details=[detail],
        )
    elif isinstance(detail, dict) and {"success", "message", "error"} <= set(detail.keys()):
        payload = detail
    else:
        payload = _error_payload(
            code={
                400: "BAD_REQUEST",
                404: "NOT_FOUND",
                409: "CONFLICT",
                422: "VALIDATION_ERROR",
            }.get(exc.status_code, "SERVER_ERROR"),
            message=str(detail),
        )

    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            code="VALIDATION_ERROR",
            message="Please correct the highlighted details.",
            details=[
                {
                    "field": str(error.get("loc", ["request"])[-1]),
                    "message": error.get("msg", "Invalid value."),
                }
                for error in exc.errors()
            ],
        ),
    )


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def health_check():
    return {
        "success": True,
        "message": "Inventory service is healthy.",
        "data": {"status": "ok"},
        "error": None,
    }


app.include_router(inventory_router)
