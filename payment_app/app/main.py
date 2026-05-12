import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.models.cart import Cart
from app.models.order import Order
from app.models.payment import Payment
from app.routers.payment import api_router as payments_api_router
from app.routers.payment import legacy_router as payments_legacy_router

executor = ThreadPoolExecutor(max_workers=1)
logger = logging.getLogger(__name__)


def _parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(origin) for origin in parsed if origin]
    except ValueError:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, Base.metadata.create_all, engine)
    logger.info("Database tables ready")
    yield


app = FastAPI(
    title="Razorpay Payment API",
    description="Cart -> Order -> Razorpay -> Verify -> DB Update",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_legacy_router, prefix="/payment")
app.include_router(payments_api_router, prefix="/api/v1/payments")


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
            code={400: "BAD_REQUEST", 404: "NOT_FOUND", 409: "CONFLICT", 502: "PAYMENT_PROVIDER_ERROR"}.get(exc.status_code, "SERVER_ERROR"),
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


static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
def home():
    index = os.path.join(static_path, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {
        "success": True,
        "message": "Payment service is healthy.",
        "data": {"status": "ok", "docs": "/docs"},
        "error": None,
    }
