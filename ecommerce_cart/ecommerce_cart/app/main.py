from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from sqlalchemy import inspect, text

from app.core.database import engine, Base
from app.routers import cart, products

# Auto-create all tables on startup
Base.metadata.create_all(bind=engine)


def _repair_cart_schema() -> None:
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("products")}
    column_definitions = {
        "external_product_id": "VARCHAR(128) NULL",
        "slug": "VARCHAR(255) NULL",
        "image_url": "TEXT NULL",
    }
    with engine.begin() as connection:
        for column_name, definition in column_definitions.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE products ADD COLUMN {column_name} {definition}"))

        refreshed = inspect(connection)
        indexes = {index["name"] for index in refreshed.get_indexes("products")}
        if "idx_products_external_product_id" not in indexes:
            connection.execute(text("CREATE INDEX idx_products_external_product_id ON products (external_product_id)"))
        if "idx_products_slug" not in indexes:
            connection.execute(text("CREATE INDEX idx_products_slug ON products (slug)"))


_repair_cart_schema()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 🛒 Ecommerce Cart API

A production-ready shopping cart service built with **FastAPI** and **MySQL**.

### Cart Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/cart` | Fetch current user's cart |
| `POST` | `/api/v1/cart/items` | Add a product to the cart |
| `POST` | `/api/v1/cart/merge` | Merge a guest cart into an authenticated cart |
| `PATCH` | `/api/v1/cart/items/{product_id}` | Update item quantity |
| `DELETE` | `/api/v1/cart/items/{product_id}` | Remove a specific item |
| `DELETE` | `/api/v1/cart` | Clear entire cart |

### Authentication
Pass `X-User-Id` or `Authorization: Bearer <jwt>` to identify the user. Guest carts use a sanitized `guest_token`.
""",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(cart.router)
app.include_router(products.router)


@app.get("/")
def root():
    return {"message": "Ecommerce Cart API is running"}


# Exception handlers


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
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
        }
        payload = _error_payload(
            code=code_map.get(exc.status_code, "SERVER_ERROR"),
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


@app.get("/", tags=["Health"])
def health_check():
    return {
        "success": True,
        "message": "Cart service is healthy.",
        "data": {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
        "error": None,
    }
