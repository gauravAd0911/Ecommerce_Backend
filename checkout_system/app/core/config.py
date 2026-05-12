from functools import lru_cache
from typing import List, Any
import json
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "ShopFlow"
    app_env:  str = "development"
    secret_key: str = "change-me"

    # Database
    database_url: str = "mysql+pymysql://ecommerce_user:Gaurav%40123@localhost:3306/abt_dev?charset=utf8mb4"

    # OTP
    otp_expire_minutes:      int  = 10
    otp_max_attempts:        int  = 5
    otp_max_resends:         int  = 3
    otp_resend_cooldown_secs: int = 60
    dev_show_code:           bool = False

    # Twilio SMS
    sms_enabled:        bool = False
    twilio_account_sid: str  = ""
    twilio_auth_token:  str  = ""
    twilio_sms_from:    str  = ""

    # CORS
    allowed_origins: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # MVP: Stock Management
    enable_stock_reservation: bool = False  # MVP: False | Prod: True
    deduct_stock_on_order: bool = True      # Always deduct

    @validator("allowed_origins", pre=True)
    def parse_allowed_origins(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            import json
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
