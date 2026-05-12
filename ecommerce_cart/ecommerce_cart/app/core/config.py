import json
from typing import Any, List

from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Ecommerce Cart API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "ecommerce_db"
    DB_USER: str = "root"
    DB_PASSWORD: str = "Gaurav@123"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins_validator(cls, v: Any) -> List[str]:
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
        extra = "ignore"


settings = Settings()
