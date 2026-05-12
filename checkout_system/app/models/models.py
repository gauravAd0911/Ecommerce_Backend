import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, CHAR, String, Boolean, Integer, Numeric, Text, DateTime, ForeignKey, SmallInteger, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Enums ──────────────────────────────────────────────────────
class OtpChannel(str, enum.Enum):
    email = "email"
    sms   = "sms"


class OtpPurpose(str, enum.Enum):
    checkout     = "checkout"
    order_lookup = "order_lookup"


class OtpStatus(str, enum.Enum):
    pending  = "pending"
    verified = "verified"
    expired  = "expired"
    locked   = "locked"


# ── Category ───────────────────────────────────────────────────
class Category(Base):
    __tablename__ = "categories"

    id          = Column(CHAR(36), primary_key=True, default=_uuid)
    name        = Column(String(100), nullable=False, unique=True)
    slug        = Column(String(120), nullable=False, unique=True)
    description = Column(Text)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="category")


# ── Product ────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id            = Column(CHAR(36), primary_key=True, default=_uuid)
    category_id   = Column(CHAR(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name          = Column(String(255), nullable=False)
    slug          = Column(String(280), nullable=False, unique=True)
    description   = Column(Text)
    price         = Column(Numeric(12, 2), nullable=False)
    compare_price = Column(Numeric(12, 2))
    sku           = Column(String(100), unique=True)
    stock_qty     = Column(Integer, nullable=False, default=0)
    images        = Column(JSON, default=list)
    is_active     = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")


# ── GuestCheckoutSession ───────────────────────────────────────
class GuestCheckoutSession(Base):
    """One session per guest attempt. Holds dual-channel verification state."""
    __tablename__ = "guest_checkout_sessions"

    id                = Column(CHAR(36), primary_key=True, default=_uuid)
    guest_name        = Column(String(200))
    email             = Column(String(320), nullable=False)
    phone             = Column(String(30),  nullable=False)
    purpose           = Column(String(30),  nullable=False, default="checkout")
    email_verified    = Column(Boolean, nullable=False, default=False)
    sms_verified = Column(Boolean, nullable=False, default=False)
    session_token     = Column(String(512), unique=True)
    session_expires_at= Column(DateTime)
    ip_address        = Column(String(45))
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    otps   = relationship("GuestOtp",   back_populates="session", cascade="all, delete-orphan")
    orders = relationship("GuestOrder", back_populates="session")


# ── GuestOtp ───────────────────────────────────────────────────
class GuestOtp(Base):
    """One row per OTP send per channel per session."""
    __tablename__ = "guest_otps"

    id             = Column(CHAR(36), primary_key=True, default=_uuid)
    session_id     = Column(CHAR(36), ForeignKey("guest_checkout_sessions.id", ondelete="CASCADE"), nullable=False)
    channel        = Column(SAEnum(OtpChannel), nullable=False)
    purpose        = Column(SAEnum(OtpPurpose), nullable=False)
    code_hash      = Column(String(64), nullable=False)
    status         = Column(SAEnum(OtpStatus),  nullable=False, default=OtpStatus.pending)
    attempts       = Column(SmallInteger, nullable=False, default=0)
    resend_count   = Column(SmallInteger, nullable=False, default=0)
    expires_at     = Column(DateTime, nullable=False)
    verified_at    = Column(DateTime)
    last_resent_at = Column(DateTime)
    plain_code     = Column(String(10))   # dev only — NULL in production
    created_at     = Column(DateTime, default=datetime.utcnow)

    session = relationship("GuestCheckoutSession", back_populates="otps")


# ── Address ────────────────────────────────────────────────────
class Address(Base):
    __tablename__ = "addresses"

    id          = Column(CHAR(36), primary_key=True, default=_uuid)
    full_name   = Column(String(200), nullable=False)
    line1       = Column(String(255), nullable=False)
    line2       = Column(String(255))
    city        = Column(String(100), nullable=False)
    state       = Column(String(100))
    postal_code = Column(String(20),  nullable=False)
    country     = Column(String(2),   nullable=False, default="US")
    phone       = Column(String(30))
    created_at  = Column(DateTime, default=datetime.utcnow)


# ── GuestOrder ─────────────────────────────────────────────────
class GuestOrder(Base):
    __tablename__ = "guest_orders"

    id                  = Column(CHAR(36), primary_key=True, default=_uuid)
    session_id          = Column(CHAR(36), ForeignKey("guest_checkout_sessions.id", ondelete="SET NULL"), nullable=True)
    order_number        = Column(String(20),  nullable=False, unique=True)
    guest_name          = Column(String(200), nullable=False)
    guest_email         = Column(String(320), nullable=False)
    guest_phone         = Column(String(30))
    email_verified      = Column(Boolean, nullable=False, default=False)
    sms_verified   = Column(Boolean, nullable=False, default=False)
    shipping_address_id = Column(CHAR(36), ForeignKey("addresses.id"))
    billing_address_id  = Column(CHAR(36), ForeignKey("addresses.id"))
    items               = Column(JSON, nullable=False, default=list)
    subtotal            = Column(Numeric(12, 2), nullable=False)
    shipping_amount     = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount          = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount     = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount        = Column(Numeric(12, 2), nullable=False)
    currency            = Column(String(3),  nullable=False, default="USD")
    status              = Column(String(30), nullable=False, default="pending")
    payment_status      = Column(String(30), nullable=False, default="unpaid")
    payment_method      = Column(String(50))
    notes               = Column(Text)
    ip_address          = Column(String(45))
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session          = relationship("GuestCheckoutSession", back_populates="orders")
    shipping_address = relationship("Address", foreign_keys=[shipping_address_id])
    billing_address  = relationship("Address", foreign_keys=[billing_address_id])
    status_history   = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")


class CheckoutSession(Base):
    """Server-side checkout snapshot used before payment."""

    __tablename__ = "checkout_sessions"

    id = Column(CHAR(36), primary_key=True, default=_uuid)
    user_id = Column(String(100))
    guest_token = Column(String(512))
    address_id = Column(String(100))
    shipping_address = Column(JSON, nullable=True)
    items = Column(JSON, nullable=False, default=list)
    pricing = Column(JSON, nullable=False, default=dict)
    status = Column(String(30), nullable=False, default="created")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CheckoutOrder(Base):
    __tablename__ = "checkout_orders"

    id = Column(CHAR(36), primary_key=True, default=_uuid)
    checkout_session_id = Column(CHAR(36), ForeignKey("checkout_sessions.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(100))
    guest_token = Column(String(512))
    address_id = Column(String(100))
    shipping_address = Column(JSON, nullable=True)
    payment_id = Column(String(100), nullable=False)
    items = Column(JSON, nullable=False, default=list)
    subtotal = Column(Numeric(12, 2), nullable=False)
    shipping_amount = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    status = Column(String(30), nullable=False, default="pending")
    payment_status = Column(String(30), nullable=False, default="unpaid")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id = Column(CHAR(36), primary_key=True, default=_uuid)
    reservation_group_id = Column(CHAR(36), index=True, nullable=False)
    product_id = Column(CHAR(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="active")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ServiceablePincode(Base):
    __tablename__ = "serviceable_pincodes"

    id = Column(CHAR(36), primary_key=True, default=_uuid)
    pincode = Column(String(6), unique=True, index=True, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    zone = Column(String(30), nullable=False, default="tier2")
    is_active = Column(Boolean, nullable=False, default=True)
    cod_available = Column(Boolean, nullable=False, default=True)
    prepaid_available = Column(Boolean, nullable=False, default=True)
    eta_days_min = Column(Integer, nullable=False, default=3)
    eta_days_max = Column(Integer, nullable=False, default=5)
    shipping_fee_override = Column(Numeric(12, 2), nullable=True)
    blocked_reason = Column(Text, nullable=True)
    updated_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── OrderStatusHistory ─────────────────────────────────────────
class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id         = Column(CHAR(36), primary_key=True, default=_uuid)
    order_id   = Column(CHAR(36), ForeignKey("guest_orders.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(String(30))
    new_status = Column(String(30), nullable=False)
    note       = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("GuestOrder", back_populates="status_history")
