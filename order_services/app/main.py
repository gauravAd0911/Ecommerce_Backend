# app/main.py
import json
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.order_routes import router as order_router
from app.core.database import init_db


def _parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "[\"http://localhost:5173\", \"http://127.0.0.1:5173\"]")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(origin) for origin in parsed if origin]
    except ValueError:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return []


def create_application() -> FastAPI:
    app = FastAPI(
        title="Order Service API",
        version="1.0.0",
        description="Handles order processing, tracking, and history",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_allowed_origins(),
        allow_credentials=True,
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
        if isinstance(detail, dict) and {"success", "message", "error"} <= set(detail.keys()):
            payload = detail
        else:
            payload = _error_payload(
                code={400: "BAD_REQUEST", 401: "UNAUTHORIZED", 404: "NOT_FOUND", 409: "CONFLICT"}.get(exc.status_code, "SERVER_ERROR"),
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
    def startup() -> None:
        init_db()

    app.include_router(order_router)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "Order Service is running"}

    @app.get("/health", tags=["Health"])
    def health_check() -> dict:
        return {
            "success": True,
            "message": "Order service is healthy.",
            "data": {"status": "OK"},
            "error": None,
        }

    return app


app = create_application()
