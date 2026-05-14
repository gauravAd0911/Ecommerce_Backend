"""Payment API schemas (Razorpay integration)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CreatePaymentOrderPayload(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in minor units (e.g., INR paise).")
    currency: str = Field(default="INR", min_length=3, max_length=10)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class CreatePaymentOrderResponse(BaseModel):
    payment_reference: str
    provider: str
    razorpay_order_id: str
    amount: int
    currency: str
    key_id: str


class VerifyPaymentPayload(BaseModel):
    payment_reference: str | None = Field(default=None, min_length=3, max_length=120)
    razorpay_order_id: str = Field(..., min_length=3, max_length=64)
    razorpay_payment_id: str = Field(..., min_length=3, max_length=64)
    razorpay_signature: str = Field(..., min_length=10, max_length=256)


class VerifyPaymentResponse(BaseModel):
    payment_reference: str
    status: str
    provider_payment_id: str | None = None
    order_id: int | None = None
    order_number: str | None = None


class PaymentStatusResponse(BaseModel):
    payment_reference: str
    provider: str
    status: str
    razorpay_order_id: str | None = None
    provider_payment_id: str | None = None
    amount: int
    currency: str
    verified_at: datetime | None = None
    failed_at: datetime | None = None
    updated_at: datetime

