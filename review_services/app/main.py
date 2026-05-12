"""FastAPI application factory and global exception handlers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    EligibilityError,
    ForbiddenError,
    NotFoundError,
    ReviewServiceError,
)
from app.services.outbox import BrokerClient, OutboxRelayWorker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Start the outbox relay worker on startup and stop it on shutdown."""
    worker = OutboxRelayWorker(broker=BrokerClient())
    relay_task = asyncio.create_task(worker.start(), name="outbox-relay")
    logger.info("Outbox relay task scheduled.")
    try:
        yield
    finally:
        await worker.stop()
        relay_task.cancel()
        try:
            await relay_task
        except asyncio.CancelledError:
            pass
        logger.info("Outbox relay task cancelled.")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(
        title="Review Service",
        description=(
            "Manages product reviews: listing, summarising, creating, "
            "and updating reviews with verified-purchaser gating."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "Review Service"}

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Review Service is running"}

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Attach domain exception mappings to the app."""

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def handle_forbidden(_: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(EligibilityError)
    async def handle_eligibility(_: Request, exc: EligibilityError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(ReviewServiceError)
    async def handle_generic(_: Request, exc: ReviewServiceError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})


app = create_app()
