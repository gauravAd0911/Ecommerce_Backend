import hashlib
import hmac
import logging

import razorpay

from app.config import RAZORPAY_KEY, RAZORPAY_SECRET

client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
logger = logging.getLogger(__name__)


def create_razorpay_order(amount_paise: int) -> dict:
    """Create a Razorpay order for a positive amount in paise."""

    if not isinstance(amount_paise, int) or amount_paise <= 0:
        raise ValueError(f"amount_paise must be a positive integer, got: {amount_paise}")

    logger.info("Creating Razorpay order for %s paise", amount_paise)
    order = client.order.create(
        {
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
        }
    )
    logger.info("Razorpay order created: %s", order.get("id"))
    return order


def verify_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    body = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        RAZORPAY_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, razorpay_signature)
