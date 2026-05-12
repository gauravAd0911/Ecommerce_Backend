"""Application-wide configuration loaded from environment variables."""

import json
from functools import lru_cache
from typing import List, Optional, Any

from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Immutable settings resolved once at startup."""

    # ── Service metadata ────────────────────────────────────────────────────
    PROJECT_NAME: str = "Catalog Service"
    API_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # ── MySQL individual fields ──────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "abt_dev"
    DB_USER: str = "root"
    DB_PASS: str = "Root"

    # ── Full DATABASE_URL (optional — auto-built from DB_* if not set) ───────
    DATABASE_URL: Optional[str] = None

    def get_database_url(self) -> str:
        """Return DATABASE_URL from env or build it from individual DB_* fields."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # ── Uvicorn server ───────────────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8014
    APP_RELOAD: bool = True

    # ── Pagination defaults ──────────────────────────────────────────────────
    DEFAULT_PAGE: int = 1
    DEFAULT_LIMIT: int = 20
    MAX_LIMIT: int = 100

    # ── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(origin) for origin in parsed if origin]
            except ValueError:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"   # silently ignore any unrecognised .env keys


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()


settings: Settings = get_settings()