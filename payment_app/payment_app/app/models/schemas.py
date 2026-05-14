from pydantic import BaseModel
from typing import Optional


# ── Request ───────────────────────────────────────────────
class VerifyRequest(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str


# ── Responses ─────────────────────────────────────────────
class CreateOrderResponse(BaseModel):
    razorpay_order_id: str
    amount:            int     # in paise
    currency:          str
    db_order_id:       int
    key:               str     # sent to frontend for checkout.js


class VerifyResponse(BaseModel):
    status:   str              # success / failed
    order_id: Optional[int] = None


class StatusResponse(BaseModel):
    order_id:       int
    order_status:   str
    total_amount:   float
    payment_status: Optional[str] = None
    payment_id:     Optional[str] = None
