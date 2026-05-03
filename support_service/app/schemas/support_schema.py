from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SupportCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
    message: str = Field(min_length=1)


class SupportTicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to_employee_id: Optional[str] = Field(default=None, alias="assignedToEmployeeId")
    internal_note: Optional[str] = Field(default=None, alias="internalNote")
    resolution_note: Optional[str] = Field(default=None, alias="resolutionNote")

    class Config:
        populate_by_name = True


class SupportTicketResponse(BaseModel):
    id: int
    user_id: Optional[str] = Field(default=None, alias="userId")
    name: str
    email: str
    phone: Optional[str] = None
    message: str
    status: str
    priority: str
    assigned_to_employee_id: Optional[str] = Field(default=None, alias="assignedToEmployeeId")
    assigned_by_admin_id: Optional[str] = Field(default=None, alias="assignedByAdminId")
    internal_note: Optional[str] = Field(default=None, alias="internalNote")
    resolution_note: Optional[str] = Field(default=None, alias="resolutionNote")
    resolved_by: Optional[str] = Field(default=None, alias="resolvedBy")
    resolved_at: Optional[datetime] = Field(default=None, alias="resolvedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True

