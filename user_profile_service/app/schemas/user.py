from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
