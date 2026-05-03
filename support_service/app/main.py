from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.support_routes import router as support_router, versioned_router
from app.core.database import Base, engine
from app.models import support_model, user_model  # noqa: F401

app = FastAPI(title="Support Service")


def _error_payload(*, code: str, message: str, details=None):
    return {
        "success": False,
        "message": message,
        "data": None,
        "error": {"code": code, "message": message, "details": details or []},
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and {"success", "message", "error"} <= set(exc.detail.keys()):
        payload = exc.detail
    else:
        payload = _error_payload(
            code={400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND"}.get(exc.status_code, "SERVER_ERROR"),
            message=str(exc.detail),
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
    Base.metadata.create_all(bind=engine)


app.include_router(versioned_router)
app.include_router(support_router)
