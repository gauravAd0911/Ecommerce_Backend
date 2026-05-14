import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import Base, engine
from app.routers import checkout, guest_checkout, guest_orders
from app.routers.delivery import router as delivery_router, seed_serviceable_pincodes
from app.routers.inventory import router as inventory_router

cfg = get_settings()

app = FastAPI(
    title=cfg.app_name,
    version="2.0.0",
    description="""
## Guest Checkout — Dual OTP (Email + WhatsApp)

### Checkout flow
1. `POST /api/v1/guest-checkout/request-verification` — send OTPs to email and WhatsApp
2. `POST /api/v1/guest-checkout/verify` — verify email OTP
3. `POST /api/v1/guest-checkout/verify` — verify WhatsApp OTP → receive `session_token`
4. `POST /api/v1/guest-orders` — place order using `session_token`

### Order lookup flow
1. `POST /api/v1/guest-orders/request-lookup` — send email OTP
2. `POST /api/v1/guest-orders/verify-lookup`  — verify → receive order list
""",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if cfg.app_env == "development" else cfg.allowed_origins,
    allow_credentials=False if cfg.app_env == "development" else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guest_checkout.router)
app.include_router(guest_orders.router)
app.include_router(checkout.router)
app.include_router(delivery_router)
app.include_router(inventory_router)


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
            code={400: "BAD_REQUEST", 404: "NOT_FOUND", 409: "CONFLICT"}.get(exc.status_code, "SERVER_ERROR"),
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            code="SERVER_ERROR",
            message="Checkout service failed to process the request.",
            details=[{"field": "server", "message": str(exc)}] if cfg.app_env == "development" else [],
        ),
    )


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        result = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'serviceable_pincodes'
                  AND COLUMN_NAME = 'state'
                """
            )
        )
        if int(result.scalar() or 0) == 0:
            db.execute(text("ALTER TABLE serviceable_pincodes ADD COLUMN state VARCHAR(100) NULL"))
            db.commit()
        seed_serviceable_pincodes(db)
    finally:
        db.close()

_static = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")


@app.get("/health")
def health():
    return {"success": True, "message": "Checkout service is healthy.", "data": {"status": "ok"}, "error": None}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def storefront():
    tpl = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(tpl):
        return HTMLResponse(open(tpl).read())
    return HTMLResponse("<h1>ShopFlow</h1><a href='/docs'>API Docs →</a>")
