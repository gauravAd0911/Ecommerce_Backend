from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app.api.support_routes import router as support_router, versioned_router
from app.core.database import Base, engine
from app.models import support_model, user_model  # noqa: F401

SERVICE_NAME = "Support Service"

logger = logging.getLogger("support_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title=SERVICE_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_payload(*, code: str, message: str, details=None):
    return {
        "success": False,
        "message": message,
        "data": None,
        "error": {"code": code, "message": message, "details": details or []},
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        "HTTP %s %s -> %s",
        request.method,
        request.url.path,
        exc.detail,
    )
    if isinstance(exc.detail, dict) and {"success", "message", "error"} <= set(exc.detail.keys()):
        payload = exc.detail
    else:
        payload = _error_payload(
            code={400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND"}.get(exc.status_code, "SERVER_ERROR"),
            message=str(exc.detail),
        )
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    logger.warning("Validation error while processing request: %s", exc.errors())
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


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            code="SERVER_ERROR",
            message="An unexpected error occurred while processing your request.",
        ),
    )


def _support_ticket_column_exists(connection, column_name: str) -> bool:
    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'support_tickets'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return int(result.scalar() or 0) > 0


def _add_support_ticket_column_if_missing(connection, column_name: str, definition: str) -> None:
    if not _support_ticket_column_exists(connection, column_name):
        connection.execute(text(f"ALTER TABLE support_tickets ADD COLUMN {column_name} {definition}"))


def _ensure_support_ticket_schema() -> None:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE support_tickets MODIFY COLUMN user_id VARCHAR(64) NULL"))
        _add_support_ticket_column_if_missing(connection, "assigned_to_employee_id", "VARCHAR(64) NULL")
        _add_support_ticket_column_if_missing(connection, "assigned_by_admin_id", "VARCHAR(64) NULL")
        _add_support_ticket_column_if_missing(connection, "internal_note", "TEXT NULL")
        _add_support_ticket_column_if_missing(connection, "resolution_note", "TEXT NULL")
        _add_support_ticket_column_if_missing(connection, "resolved_by", "VARCHAR(64) NULL")
        _add_support_ticket_column_if_missing(connection, "resolved_at", "TIMESTAMP NULL")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    try:
        _ensure_support_ticket_schema()
    except Exception:
        logger.exception("Failed to ensure support ticket schema")


app.include_router(versioned_router)
app.include_router(support_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/")
def root() -> dict:
    return {
        "success": True,
        "message": f"{SERVICE_NAME} is running.",
        "data": {
            "service": SERVICE_NAME,
            "health": "/health",
            "queries": "/queries",
            "adminQueries": "/admin/queries",
        },
        "error": None,
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)
