# app/main.py
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.order_routes import router as order_router
from app.core.database import init_db

# Load environment variables from .env file
load_dotenv()


def _parse_allowed_origins() -> list[str]:
    # Default allowed origins for local development and production
    default_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
    ]
    
    raw = os.getenv("ALLOWED_ORIGINS", "")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if origin]
        except (ValueError, TypeError):
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
    
    return default_origins


def create_application() -> FastAPI:
    app = FastAPI(
        title="Order Service API",
        version="1.0.0",
        description="Handles order processing, tracking, and history",
    )

    # Configure CORS middleware with proper defaults
    allowed_origins = _parse_allowed_origins()
    print(f"[CORS] Allowed origins: {allowed_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
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

    # Ensure the schema is initialized as soon as the application is created.
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
