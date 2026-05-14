"""Cart model used for building an order total."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.sql import func

from app.database import Base


class Cart(Base):
    """A single cart line item for a user."""

    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    item_name = Column(String(255), nullable=False, default="Item")
    price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    currency = Column(String(10), nullable=False, default="INR")
    quantity = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


__all__ = ["Cart", "func"]
