"""Order model used to finalize a purchase after payment verification."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Order(Base):
    """An order created after a server-verified payment."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    order_number = Column(String(40), nullable=False, unique=True, index=True)
    payment_reference = Column(
        String(120),
        ForeignKey("payments.payment_reference", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )

    total_amount_minor = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(50), nullable=False, default="pending")  # pending -> paid/failed/cancelled

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    payment = relationship("Payment", back_populates="order", uselist=False, foreign_keys=[payment_reference])
