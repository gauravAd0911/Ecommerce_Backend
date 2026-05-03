"""Catalog Service — FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(compat_router)
