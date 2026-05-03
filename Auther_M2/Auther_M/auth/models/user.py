from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


def _enum_values(enum_cls):
    return [e.value for e in enum_cls]


class Role(str, enum.Enum):
    """Role values stored on the user record."""

    ADMIN = "admin"
    CONSUMER = "consumer"
    VENDOR = "vendor"


PUBLIC_ROLE_MAP = {
    Role.ADMIN: "admin",
    Role.CONSUMER: "customer",
    Role.VENDOR: "employee",
}


def to_public_role(role: Role | str) -> str:
    if isinstance(role, Role):
        return PUBLIC_ROLE_MAP.get(role, role.value)

    normalized = str(role).strip().lower()
    if normalized == "consumer":
        return "customer"
    if normalized == "vendor":
        return "employee"
    return normalized


class OtpPurpose(str, enum.Enum):
    """OTP purposes."""

    SIGNUP = "signup"
    PASSWORD_FORGOT = "password_forgot"


class User(Base):
    """User table."""

    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    full_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), index=True, nullable=True)

    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(Role, values_callable=_enum_values), default=Role.CONSUMER, nullable=False)

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    employee_profile = relationship(
        "EmployeeProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class EmployeeProfile(Base):
    """Operational profile for employee accounts."""

    __tablename__ = "employee_profiles"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    employee_code = Column(String(40), nullable=False, unique=True, index=True)
    designation = Column(String(120), nullable=True)
    department = Column(String(120), nullable=True)
    manager_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True)
    work_location = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="employee_profile")


class OtpContext(Base):
    """OTP context for signup and password reset flows."""

    __tablename__ = "otp_contexts"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    purpose = Column(SQLEnum(OtpPurpose, values_callable=_enum_values), nullable=False)

    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    otp_hash = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)

    resend_available_at = Column(DateTime, nullable=False)
    resend_count = Column(Integer, nullable=False, default=0)

    attempt_count = Column(Integer, nullable=False, default=0)
    verified_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


class AuthSession(Base):
    """Refresh-token backed session (supports rotation + logout revocation)."""

    __tablename__ = "auth_sessions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)

    refresh_token_hash = Column(String(255), nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    last_used_at = Column(DateTime, nullable=True)


class PasswordResetToken(Base):
    """Token created after verifying a forgot-password OTP."""

    __tablename__ = "password_reset_tokens"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)

    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
