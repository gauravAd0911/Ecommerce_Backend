from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any, Optional, Dict


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None


class DeviceRegister(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    device_token: str = Field(..., min_length=1, max_length=255)
    platform: str = Field(..., min_length=1, max_length=50)

    @field_validator("user_id", "device_token", "platform", mode="before")
    @classmethod
    def coerce_non_empty_string(cls, value) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Field is required.")
        return normalized

class NotificationCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=500)
    type: str = Field(..., min_length=1, max_length=50)

    @field_validator("user_id", "title", "message", "type", mode="before")
    @classmethod
    def coerce_non_empty_string(cls, value) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Field is required.")
        return normalized

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    title: str
    message: str
    type: str
    is_read: bool
    created_at: Optional[datetime] = None
