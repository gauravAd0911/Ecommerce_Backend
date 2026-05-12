import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routes.notification_routes import router


def _parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "[\"http://localhost:5173\", \"http://127.0.0.1:5173\"]")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(origin) for origin in parsed if origin]
    except ValueError:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return []

app = FastAPI(title="Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Notification Service"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Notification Service is running"}


app.include_router(router)
