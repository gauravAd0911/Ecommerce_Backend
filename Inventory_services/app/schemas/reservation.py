from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReservationCreateRequest(BaseModel):
    """
    Request schema to create reservation.
    """
    product_id: int = Field(..., gt=0)
    warehouse_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    stock_qty: Optional[int] = Field(default=None, ge=0)

    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Unique key for safe retries"
    )


class ReservationResponse(BaseModel):
    """
    Standard reservation response.
    """
    id: int
    product_id: int
    warehouse_id: int
    quantity: int
    status: str
    expires_at: datetime

    model_config = {
        "from_attributes": True  # replaces orm_mode in Pydantic v2
    }


class ReservationActionResponse(BaseModel):
    """
    Generic response for release/commit actions.
    """
    message: str