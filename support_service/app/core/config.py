from urllib.parse import quote_plus
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # DB
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # ✅ ADD THESE
    APP_NAME: str = "Support Service"
    DEBUG: bool = True

    @property
    def DATABASE_URL(self):
        return (
            f"mysql+pymysql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()