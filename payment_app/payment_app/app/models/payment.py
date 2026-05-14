"""Payment domain models (Razorpay integration).

These models are designed to support:
- Idempotent provider order creation.
- Backend signature verification.
- Webhook auditing and safe retries.
- Reconciliation after app interruption.
"""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PaymentProvider(str, enum.Enum):
    """Supported payment providers."""

    RAZORPAY = "razorpay"


class PaymentState(str, enum.Enum):
    """Internal payment state for safe order finalization."""

    CREATING = "creating"
    CREATED = "created"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    UNKNOWN = "unknown"


class Payment(Base):
    """Payment record created before finalizing an order."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("provider", "idempotency_key", name="uq_payments_provider_idempotency"),
        UniqueConstraint("provider", "provider_order_id", name="uq_payments_provider_order"),
    )

    id = Column(Integer, primary_key=True, index=True)

    payment_reference = Column(String(120), nullable=False, unique=True, index=True)
    provider = Column(
        SAEnum(
            PaymentProvider,
            name="payment_provider",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
        ),
        nullable=False,
    )
    idempotency_key = Column(String(80), nullable=False)

    provider_order_id = Column(String(64), nullable=True, index=True)
    provider_payment_id = Column(String(64), nullable=True, index=True)

    amount_minor = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(
        SAEnum(
            PaymentState,
            name="payment_state",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
        ),
        nullable=False,
        default=PaymentState.CREATING,
        index=True,
    )

    provider_order_create_attempts = Column(Integer, nullable=False, default=0)
    provider_order_last_attempt_at = Column(DateTime, nullable=True)

    verified_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    last_error = Column(String(500), nullable=True)
    provider_metadata: Any = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    order = relationship("Order", back_populates="payment", uselist=False)
    events = relationship("PaymentEvent", back_populates="payment", cascade="all, delete-orphan")


class PaymentEvent(Base):
    """Stored provider callback/webhook payload for auditing and idempotency."""

    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_payment_events_provider_event"),
    )

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True)

    provider = Column(
        SAEnum(
            PaymentProvider,
            name="payment_event_provider",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
        ),
        nullable=False,
    )
    provider_event_id = Column(String(64), nullable=False)
    event_type = Column(String(80), nullable=False)
    signature_verified = Column(Boolean, nullable=False, default=False)
    payload: Any = Column(JSON, nullable=False)
    note = Column(Text, nullable=True)

    received_at = Column(DateTime, nullable=False, server_default=func.now())

    payment = relationship("Payment", back_populates="events")


__all__ = ["Payment", "PaymentEvent", "PaymentProvider", "PaymentState"]
