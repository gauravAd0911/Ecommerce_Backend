"""Catalog Service — FastAPI application factory."""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

load_dotenv()

from app.api.v1.router import api_router, compat_router
from app.core.config import settings
from app.db.session import Base, _engine
from app.models import catalog  # noqa: F401

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="Catalog Service: home page, products, categories, filters.",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    # Database is already initialized by catalog_service.sql during setup
    # No need to recreate tables here
    pass


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(compat_router)


@app.get("/", tags=["Health"])
async def root() -> dict:
    """Human/browser-friendly service landing response."""
    return {
        "success": True,
        "message": "Catalog Service is running.",
        "data": {
            "service": settings.PROJECT_NAME,
            "version": settings.API_VERSION,
            "docs": f"{settings.API_V1_PREFIX}/docs",
            "health": "/health",
            "products": f"{settings.API_V1_PREFIX}/products",
            "categories": f"{settings.API_V1_PREFIX}/categories",
        },
        "error": None,
    }


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Simple health check for scripts, browser checks, and load balancers."""
    return {
        "success": True,
        "message": "Catalog service is healthy.",
        "data": {"status": "ok", "service": settings.PROJECT_NAME},
        "error": None,
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Avoid noisy 404 logs when the service is opened in a browser."""
    return Response(status_code=204)
