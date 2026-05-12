"""Application settings loaded from environment variables."""

import json
from typing import Any, List
from urllib.parse import quote_plus

from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised settings object — one source of truth for all config."""

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "review_service"
    db_user: str = "root"
    db_password: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ------------------------------------------------------------------ #
    # Auth
    # ------------------------------------------------------------------ #
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    # ------------------------------------------------------------------ #
    # Pagination
    # ------------------------------------------------------------------ #
    default_page_size: int = 20
    max_page_size: int = 100

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    allowed_origins: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @validator("allowed_origins", pre=True)
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def database_url(self) -> str:
        """Async MySQL connection URL."""
        return (
            f"mysql+aiomysql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()