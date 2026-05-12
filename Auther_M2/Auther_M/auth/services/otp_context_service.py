from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from auth.models.user import OtpContext, OtpPurpose, User
from auth.services.crypto_service import hash_otp
from auth.services.otp_service import generate_otp, get_otp_expiry_minutes

RESEND_COOLDOWN_SECONDS = 60
RESEND_LIMIT = 3
ATTEMPT_LIMIT = 5


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass(frozen=True)
class OtpInitiateResult:
    context_id: str
    otp: str
    otp_expiry_seconds: int
    phone: str | None = None


def create_or_refresh_context(
    db: Session,
    *,
    purpose: OtpPurpose,
    user: User | None,
    email: str | None,
    phone: str | None,
    now: datetime | None = None,
) -> OtpInitiateResult:
    """Create a new OTP context or refresh an existing one if allowed."""

    now = now or _utcnow()

    context = OtpContext(
        purpose=purpose,
        user_id=getattr(user, "id", None),
        email=email,
        phone=phone,
        expires_at=now,  # replaced below
        resend_available_at=now,
        resend_count=0,
        attempt_count=0,
    )

    otp = generate_otp()
    expiry_minutes = get_otp_expiry_minutes()
    expires_at = now + timedelta(minutes=expiry_minutes)

    context.expires_at = expires_at
    context.resend_available_at = now + timedelta(seconds=RESEND_COOLDOWN_SECONDS)
    context.resend_count = 1
    context.attempt_count = 0

    db.add(context)
    db.flush()  # populate id

    context.otp_hash = hash_otp(context.id, otp)

    db.commit()
    db.refresh(context)

    return OtpInitiateResult(
        context_id=context.id,
        otp=otp,
        otp_expiry_seconds=expiry_minutes * 60,
        phone=context.phone,
    )


def resend_otp(db: Session, context_id: str, now: datetime | None = None) -> OtpInitiateResult:
    """Resend OTP for an existing context with cooldown/limits."""

    now = now or _utcnow()

    context = db.query(OtpContext).filter(OtpContext.id == context_id).first()
    if not context or context.revoked_at or context.verified_at:
        raise ValueError("Invalid context")

    if context.resend_count >= RESEND_LIMIT:
        raise PermissionError("Resend limit reached")

    if context.resend_available_at and now < context.resend_available_at:
        raise PermissionError("Resend cooldown active")

    otp = generate_otp()
    expiry_minutes = get_otp_expiry_minutes()

    context.otp_hash = hash_otp(context.id, otp)
    context.expires_at = now + timedelta(minutes=expiry_minutes)
    context.resend_available_at = now + timedelta(seconds=RESEND_COOLDOWN_SECONDS)
    context.resend_count += 1
    context.attempt_count = 0

    db.commit()

    return OtpInitiateResult(
        context_id=context.id,
        otp=otp,
        otp_expiry_seconds=expiry_minutes * 60,
        phone=context.phone,
    )


def verify_context_otp(db: Session, context_id: str, otp: str, now: datetime | None = None) -> OtpContext:
    """Verify OTP for a context with attempt limits."""

    now = now or _utcnow()

    context = db.query(OtpContext).filter(OtpContext.id == context_id).first()
    if not context or context.revoked_at:
        raise ValueError("Invalid context")

    if context.verified_at:
        return context

    if context.attempt_count >= ATTEMPT_LIMIT:
        raise PermissionError("Too many attempts")

    context.attempt_count += 1

    if context.expires_at < now:
        db.commit()
        raise ValueError("OTP expired")

    expected = context.otp_hash
    if not expected or expected != hash_otp(context.id, otp):
        db.commit()
        raise ValueError("Invalid OTP")

    context.verified_at = now
    context.otp_hash = None
    db.commit()
    db.refresh(context)
    return context
