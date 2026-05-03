"""
Support Models

Defines database models for:
- SupportTicket
- SupportOption
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    func,
)
from app.core.database import Base


class SupportTicket(Base):
    """
    Support Ticket Model
    """

    __tablename__ = "support_tickets"

    id = Column(BigInteger, primary_key=True, index=True)

    # Nullable for guest users
    user_id = Column(String(64), nullable=True, index=True)

    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True)

    message = Column(Text, nullable=False)

    status = Column(String(50), default="OPEN")
    priority = Column(String(20), default="MEDIUM")
    assigned_to_employee_id = Column(String(64), nullable=True, index=True)
    assigned_by_admin_id = Column(String(64), nullable=True)
    internal_note = Column(Text, nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_by = Column(String(64), nullable=True)
    resolved_at = Column(TIMESTAMP, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # ❌ Removed relationship (User model not defined yet)


class SupportOption(Base):
    """
    Support Channels (Email, Phone, etc.)
    """

    __tablename__ = "support_options"

    id = Column(BigInteger, primary_key=True, index=True)

    type = Column(String(50), nullable=False)  # email, phone, chat
    value = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False
    )
