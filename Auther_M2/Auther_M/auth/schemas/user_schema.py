from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SignupInitiateRequest(ApiModel):
    full_name: str = Field(alias="fullName", min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=25)
    password: str = Field(min_length=6, max_length=255)


class SignupInitiateResponse(ApiModel):
    context_id: str = Field(alias="context_id")
    message: str
    otp_expiry_seconds: int


class SignupVerifyRequest(ApiModel):
    context_id: str = Field(alias="contextId")
    otp: str = Field(min_length=4, max_length=10)


class LoginRequest(ApiModel):
    identifier: str
    password: str


class ForgotInitiateRequest(ApiModel):
    identifier: str


class ForgotInitiateResponse(ApiModel):
    context_id: str
    message: str
    otp_expiry_seconds: int


class ForgotVerifyRequest(ApiModel):
    context_id: str = Field(alias="contextId")
    otp: str = Field(min_length=4, max_length=10)


class ForgotVerifyResponse(ApiModel):
    reset_token: str
    reset_token_expiry_seconds: int


class PasswordResetRequest(ApiModel):
    reset_token: str
    new_password: str


class RefreshTokenRequest(ApiModel):
    refresh_token: str


class LogoutRequest(ApiModel):
    refresh_token: str


class UpdateProfileRequest(ApiModel):
    full_name: str = Field(alias="fullName", min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=25)


class EmployeeBase(ApiModel):
    full_name: str = Field(alias="fullName", min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=25)
    designation: Optional[str] = Field(default=None, max_length=120)
    department: Optional[str] = Field(default=None, max_length=120)
    manager_id: Optional[str] = Field(default=None, alias="managerId")
    work_location: Optional[str] = Field(default=None, alias="workLocation", max_length=120)


class EmployeeCreateRequest(EmployeeBase):
    password: str = Field(min_length=6, max_length=255)


class EmployeeUpdateRequest(ApiModel):
    full_name: Optional[str] = Field(default=None, alias="fullName", min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, min_length=8, max_length=25)
    password: Optional[str] = Field(default=None, min_length=6, max_length=255)
    designation: Optional[str] = Field(default=None, max_length=120)
    department: Optional[str] = Field(default=None, max_length=120)
    manager_id: Optional[str] = Field(default=None, alias="managerId")
    work_location: Optional[str] = Field(default=None, alias="workLocation", max_length=120)
    is_active: Optional[bool] = Field(default=None, alias="isActive")


class UserOut(ApiModel):
    id: str
    full_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    role: str


class EmployeeOut(UserOut):
    employee_code: str = Field(alias="employeeCode")
    designation: Optional[str] = None
    department: Optional[str] = None
    manager_id: Optional[str] = Field(default=None, alias="managerId")
    work_location: Optional[str] = Field(default=None, alias="workLocation")
    is_active: bool = Field(alias="isActive")


class TokenPair(ApiModel):
    access_token: str
    refresh_token: str


class AuthResponse(ApiModel):
    access_token: str
    refresh_token: str
    user: UserOut


class APIResponse(ApiModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[dict] = None
