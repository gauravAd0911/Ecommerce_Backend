from __future__ import annotations

from sqlalchemy.orm import Session

from auth.models.user import EmployeeProfile, Role, User
from auth.schemas.user_schema import (
    EmployeeCreateRequest,
    EmployeeUpdateRequest,
    SignupInitiateRequest,
    UpdateProfileRequest,
)
from auth.services.identifier_service import normalize_email, normalize_phone
from auth.utils.password import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_phone(db: Session, phone: str) -> User | None:
    return db.query(User).filter(User.phone == phone).first()


def create_pending_user(db: Session, payload: SignupInitiateRequest) -> User:
    """Create or update a pending (unverified) user for signup."""

    email = normalize_email(payload.email)
    phone = normalize_phone(payload.phone)

    existing = get_user_by_email(db, email)
    if existing and existing.is_verified:
        raise ValueError("Email already exists")

    existing_phone_user = get_user_by_phone(db, phone)
    if existing_phone_user and existing_phone_user.id != (existing.id if existing else None) and existing_phone_user.is_verified:
        raise ValueError("Phone already exists")

    user = existing or User(email=email)

    user.full_name = payload.full_name
    user.phone = phone
    user.password_hash = hash_password(payload.password)
    user.role = Role.CONSUMER
    user.is_active = True
    user.is_verified = False

    if not existing:
        db.add(user)

    db.commit()
    db.refresh(user)

    return user


def mark_user_verified(db: Session, user: User) -> None:
    user.is_verified = True
    db.commit()


def authenticate_by_identifier(db: Session, identifier: str, password: str) -> User | None:
    """Authenticate user by email or phone."""

    ident = identifier.strip()

    user = get_user_by_email(db, normalize_email(ident)) if "@" in ident else get_user_by_phone(db, normalize_phone(ident))
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def update_current_user(db: Session, user: User, payload: UpdateProfileRequest) -> User:
    email = normalize_email(payload.email)
    phone = normalize_phone(payload.phone)

    existing_email_user = get_user_by_email(db, email)
    if existing_email_user and existing_email_user.id != user.id:
        raise ValueError("Email already exists")

    existing_phone_user = get_user_by_phone(db, phone)
    if existing_phone_user and existing_phone_user.id != user.id:
        raise ValueError("Phone already exists")

    user.full_name = payload.full_name
    user.email = email
    user.phone = phone

    db.commit()
    db.refresh(user)
    return user


def _employee_code_sequence(db: Session) -> int:
    employee_count = db.query(EmployeeProfile).count()
    return employee_count + 1


def build_employee_code(db: Session) -> str:
    return f"EMP-{_employee_code_sequence(db):04d}"


def get_employee_by_id(db: Session, employee_id: str) -> User | None:
    return (
        db.query(User)
        .filter(User.id == employee_id)
        .filter(User.role == Role.VENDOR)
        .first()
    )


def list_employees(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.role == Role.VENDOR)
        .order_by(User.created_at.desc())
        .all()
    )


def create_employee_account(db: Session, payload: EmployeeCreateRequest) -> User:
    email = normalize_email(payload.email)
    phone = normalize_phone(payload.phone)

    if get_user_by_email(db, email):
        raise ValueError("Email already exists")
    if get_user_by_phone(db, phone):
        raise ValueError("Phone already exists")

    user = User(
        full_name=payload.full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(payload.password),
        role=Role.VENDOR,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    profile = EmployeeProfile(
        user_id=user.id,
        employee_code=build_employee_code(db),
        designation=payload.designation,
        department=payload.department,
        manager_id=payload.manager_id,
        work_location=payload.work_location,
        is_active=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def update_employee_account(db: Session, employee: User, payload: EmployeeUpdateRequest) -> User:
    if payload.email is not None:
        email = normalize_email(payload.email)
        existing_email_user = get_user_by_email(db, email)
        if existing_email_user and existing_email_user.id != employee.id:
            raise ValueError("Email already exists")
        employee.email = email

    if payload.phone is not None:
        phone = normalize_phone(payload.phone)
        existing_phone_user = get_user_by_phone(db, phone)
        if existing_phone_user and existing_phone_user.id != employee.id:
            raise ValueError("Phone already exists")
        employee.phone = phone

    if payload.full_name is not None:
        employee.full_name = payload.full_name

    if payload.password:
        employee.password_hash = hash_password(payload.password)

    profile = employee.employee_profile or EmployeeProfile(
        user_id=employee.id,
        employee_code=build_employee_code(db),
    )
    if employee.employee_profile is None:
        db.add(profile)

    if payload.designation is not None:
        profile.designation = payload.designation
    if payload.department is not None:
        profile.department = payload.department
    if payload.manager_id is not None:
        profile.manager_id = payload.manager_id
    if payload.work_location is not None:
        profile.work_location = payload.work_location
    if payload.is_active is not None:
        profile.is_active = payload.is_active
        employee.is_active = payload.is_active

    db.commit()
    db.refresh(employee)
    return employee


def delete_employee_account(db: Session, employee: User) -> User:
    employee.is_active = False
    if employee.employee_profile:
        employee.employee_profile.is_active = False
    db.commit()
    db.refresh(employee)
    return employee


