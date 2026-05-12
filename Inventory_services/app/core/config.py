import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Inventory Service"
    DEBUG: bool = False

    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    DATABASE_URL: str
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    RESERVATION_TTL_SECONDS: int = 900
    IDEMPOTENCY_HEADER: str = "X-Idempotency-Key"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(origin) for origin in value if origin]

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(origin) for origin in parsed if origin]
            except ValueError:
                return [origin.strip() for origin in value.split(",") if origin.strip()]

        return ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
