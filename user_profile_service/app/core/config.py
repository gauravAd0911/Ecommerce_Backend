import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application configuration settings."""

    def __init__(self):
        # =========================
        # DATABASE
        # =========================
        self.DATABASE_URL: str = os.getenv("DATABASE_URL")

        # =========================
        # SECURITY
        # =========================
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback-secret")
        self.ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
        )

        # =========================
        # APP SETTINGS
        # =========================
        self.DEBUG: bool = os.getenv("DEBUG", "True") == "True"
        self.APP_NAME: str = os.getenv("APP_NAME", "User Profile Service")
        self.ALLOWED_ORIGINS: list[str] = self._parse_allowed_origins(
            os.getenv("ALLOWED_ORIGINS", "")
        )

        # =========================
        # BUSINESS LOGIC
        # =========================
        self.MAX_ADDRESS_LIMIT: int = int(
            os.getenv("MAX_ADDRESS_LIMIT", 5)
        )

    def _parse_allowed_origins(self, raw_value: str) -> list[str]:
        if not raw_value:
            return ["http://localhost:5173", "http://127.0.0.1:5173"]

        try:
            parsed_value = json.loads(raw_value)
            if isinstance(parsed_value, list):
                return [str(origin).strip() for origin in parsed_value if str(origin).strip()]
        except json.JSONDecodeError:
            pass

        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


# Singleton instance
settings = Settings()
