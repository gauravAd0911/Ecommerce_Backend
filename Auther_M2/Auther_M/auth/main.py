from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auth.routes.v1_auth import admin_workspace_router, public_router, router as v1_auth_router
from auth.models import user as user_models
from database import Base, engine

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=str(ROOT_DIR / ".env"), override=True)


def _parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "[\"http://localhost:5173\", \"http://127.0.0.1:5173\"]")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(origin) for origin in parsed if origin]
    except ValueError:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return []


DEFAULT_FAILURE_MESSAGE = "Request failed."

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(v1_auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(public_router, prefix="/auth", tags=["Unified Auth"])
app.include_router(admin_workspace_router, prefix="/api/v1/auth", tags=["Admin Workspace"])


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def _is_auth_request(request: Request) -> bool:
    return request.url.path.startswith("/auth") or request.url.path.startswith("/api/v1/auth")


def _error_payload(*, code: str, message: str, details: list[dict] | None = None):
    errors = {
        detail.get("field"): detail.get("message", "Invalid value.")
        for detail in (details or [])
        if detail.get("field")
    }
    return {
        "success": False,
        "message": message,
        "data": None,
        "errors": errors,
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if not _is_auth_request(request):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    if isinstance(exc.detail, dict):
        detail = exc.detail
        error_detail = detail.get("error") or {}
        payload = {
            "success": False,
            "message": detail.get("message", DEFAULT_FAILURE_MESSAGE),
            "data": None,
            "errors": {
                field_error.get("field"): field_error.get("message", "Invalid value.")
                for field_error in (detail.get("fieldErrors") or error_detail.get("details", []))
                if field_error.get("field")
            },
            "error": {
                "code": detail.get("code") or error_detail.get("code", "SERVER_ERROR"),
                "message": error_detail.get("message") or detail.get("message", DEFAULT_FAILURE_MESSAGE),
                "details": detail.get("fieldErrors") or error_detail.get("details", []),
            },
        }
    else:
        status_code_map = {
            400: ("BAD_REQUEST", str(exc.detail)),
            401: ("UNAUTHORIZED", str(exc.detail)),
            403: ("FORBIDDEN", str(exc.detail)),
            404: ("NOT_FOUND", str(exc.detail)),
            429: ("RATE_LIMITED", str(exc.detail)),
        }
        code, message = status_code_map.get(exc.status_code, ("SERVER_ERROR", DEFAULT_FAILURE_MESSAGE))
        payload = _error_payload(code=code, message=message)

    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if not _is_auth_request(request):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    field_errors = []
    for error in exc.errors():
        location = error.get("loc", [])
        field_name = location[-1] if location else "request"
        field_errors.append({
            "field": str(field_name),
            "message": error.get("msg", "Invalid value."),
        })

    return JSONResponse(
        status_code=422,
        content=_error_payload(
            code="VALIDATION_ERROR",
            message="Please correct the highlighted details.",
            details=field_errors,
        ),
    )


@app.get("/")
def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


@app.get("/welcome")
def welcome_page(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})
