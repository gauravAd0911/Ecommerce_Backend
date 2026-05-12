import re

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NON_NULL_UPDATE_FIELDS = {
    "full_name",
    "phone",
    "address_line1",
    "city",
    "state",
    "postal_code",
    "is_default",
}


class AddressCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=10, max_length=15)
    address_line1: str = Field(..., min_length=3, max_length=255)
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=6, max_length=6)
    country: Optional[str] = "India"
    address_type: Optional[str] = "Home"
    is_default: bool = False

    @field_validator("full_name", "address_line1", "city", "state", "country", "address_type")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        phone = value.strip()
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if not re.fullmatch(r"[6-9]\d{9}", digits):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return phone

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        postal_code = value.strip()
        if not re.fullmatch(r"\d{6}", postal_code):
            raise ValueError("Enter a valid 6-digit pincode.")
        return postal_code


class AddressUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, min_length=10, max_length=15)
    address_line1: Optional[str] = Field(default=None, min_length=3, max_length=255)
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    state: Optional[str] = Field(default=None, min_length=2, max_length=100)
    postal_code: Optional[str] = Field(default=None, min_length=6, max_length=6)
    country: Optional[str] = None
    address_type: Optional[str] = None
    is_default: Optional[bool] = None

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one address field must be provided.")
        return self

    @field_validator(*NON_NULL_UPDATE_FIELDS, mode="before")
    @classmethod
    def reject_null_for_required_columns(cls, value, info):
        # Only reject None if the field was explicitly set in the request
        if value is None and info.field_name in info.data:
            raise ValueError(f"{info.field_name} cannot be null.")
        return value

    @field_validator("full_name", "address_line1", "city", "state", "country", "address_type")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        phone = value.strip()
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if not re.fullmatch(r"[6-9]\d{9}", digits):
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return phone

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        postal_code = value.strip()
        if not re.fullmatch(r"\d{6}", postal_code):
            raise ValueError("Enter a valid 6-digit pincode.")
        return postal_code


class AddressResponse(BaseModel):
    id: str
    full_name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: Optional[str] = "India"
    address_type: Optional[str] = "Home"
    is_default: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AddressDeleteResponse(BaseModel):
    message: str
