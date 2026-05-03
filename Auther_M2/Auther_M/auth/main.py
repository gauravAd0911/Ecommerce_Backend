from __future__ import annotations

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

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(v1_auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(public_router, prefix="/auth", tags=["Unified Auth"])
app.include_router(admin_workspace_router, tags=["Admin Workspace"])


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def _is_auth_request(request: Request) -> bool:
    return request.url.path.startswith("/auth") or request.url.path.startswith("/api/v1/auth")


def _error_payload(*, code: str, message: str, details: list[dict] | None = None):
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
async def http_exception_handler(request: Request, exc: HTTPException):
    if not _is_auth_request(request):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    if isinstance(exc.detail, dict):
        detail = exc.detail
        payload = {
            "success": False,
            "message": detail.get("message", "Request failed."),
            "data": None,
            "error": {
                "code": detail.get("code", "SERVER_ERROR"),
                "message": detail.get("message", "Request failed."),
                "details": detail.get("fieldErrors", []),
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
        code, message = status_code_map.get(exc.status_code, ("SERVER_ERROR", "Request failed."))
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
