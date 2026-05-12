from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth.middleware.auth_guard import get_current_user
from auth.models.user import OtpPurpose, User, to_public_role
from auth.schemas.user_schema import (
    APIResponse,
    AuthResponse,
    EmployeeCreateRequest,
    EmployeeOut,
    EmployeeUpdateRequest,
    ForgotInitiateRequest,
    ForgotInitiateResponse,
    ForgotVerifyRequest,
    ForgotVerifyResponse,
    LoginRequest,
    LogoutRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    SignupInitiateRequest,
    SignupInitiateResponse,
    SignupVerifyRequest,
    UpdateProfileRequest,
    UserOut,
)
from auth.services.auth_service import (
    authenticate_by_identifier,
    create_employee_account,
    create_pending_user,
    delete_employee_account,
    get_employee_by_id,
    list_employees,
    mark_user_verified,
    update_employee_account,
    update_current_user,
)
from auth.services.identifier_service import normalize_identifier
from auth.services.otp_context_service import create_or_refresh_context, verify_context_otp
from auth.services.password_reset_service import consume_reset_token, create_reset_token
from auth.services.session_service import create_session, refresh_session, revoke_session
from auth.services.twilio_service import send_otp_sms

router = APIRouter()
public_router = APIRouter()
admin_workspace_router = APIRouter()

OTP_SENT_MESSAGE = "OTP sent successfully."


def _error(status_code: int, code: str, message: str, field_errors: list[dict] | None = None):
    raise HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "message": message,
            "error": {
                "code": code,
                "message": message,
                "details": field_errors or [],
            },
        },
    )


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=to_public_role(user.role),
    )


def _employee_out(user: User) -> EmployeeOut:
    profile = user.employee_profile
    return EmployeeOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=to_public_role(user.role),
        employeeCode=profile.employee_code if profile else "",
        designation=profile.designation if profile else None,
        department=profile.department if profile else None,
        managerId=profile.manager_id if profile else None,
        workLocation=profile.work_location if profile else None,
        isActive=bool(profile.is_active if profile else user.is_active),
    )


def _token_payload(access_token: str, refresh_token: str) -> dict:
    return {
        "tokens": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 15 * 60,
            "refresh_expires_in": 7 * 24 * 60 * 60,
        }
    }


def _auth_api_response(message: str, access_token: str, refresh_token: str, user: User) -> APIResponse:
    payload = _token_payload(access_token, refresh_token)
    payload["user"] = _user_out(user).model_dump()
    return APIResponse(success=True, message=message, data=payload)


def _require_admin(current_user: User) -> User:
    if to_public_role(current_user.role) != "admin":
        _error(403, "FORBIDDEN", "Admin access required.")
    return current_user


@router.post(
    "/signup/initiate",
    response_model=SignupInitiateResponse,
    responses={
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"},
    },
)
def signup_initiate(payload: SignupInitiateRequest, db: Annotated[Session, Depends(get_db)]):
    """Signup initiate.

    Creates/updates a pending user, creates an OTP context, and sends OTP via SMS.
    """

    try:
        user = create_pending_user(db, payload)
    except ValueError as exc:
        message = str(exc)
        field_errors = []
        code = "VALIDATION_ERROR"
        if "Email already exists" in message:
            code = "EMAIL_ALREADY_EXISTS"
            field_errors.append({"field": "email", "message": message})
        if "Phone already exists" in message:
            code = "PHONE_ALREADY_EXISTS"
            field_errors.append({"field": "phone", "message": message})
        if "Password is too long" in message:
            code = "PASSWORD_TOO_LONG"
            field_errors.append({"field": "password", "message": message})
        _error(400, code, message, field_errors)

    result = create_or_refresh_context(
        db,
        purpose=OtpPurpose.SIGNUP,
        user=user,
        email=user.email,
        phone=user.phone,
    )

    sms = send_otp_sms(user.phone or "", result.otp, expiry_minutes=int(result.otp_expiry_seconds / 60))
    if sms.get("status") != "sent":
        _error(500, "OTP_DELIVERY_FAILED", sms.get("error") or "Failed to send OTP")

    return SignupInitiateResponse(
        context_id=result.context_id,
        message=OTP_SENT_MESSAGE,
        otp_expiry_seconds=result.otp_expiry_seconds,
    )


@router.post("/register", response_model=APIResponse)
def register(payload: SignupInitiateRequest, db: Annotated[Session, Depends(get_db)]):
    response = signup_initiate(payload, db)
    return APIResponse(
        success=True,
        message=response.message,
        data={
            "context_id": response.context_id,
            "otp_expiry_seconds": response.otp_expiry_seconds,
        },
    )


@router.post(
    "/signup/verify-otp",
    response_model=AuthResponse,
    responses={
        400: {"description": "Bad request"},
        429: {"description": "Too many attempts"},
    },
)
def signup_verify(payload: SignupVerifyRequest, db: Annotated[Session, Depends(get_db)]):
    """Signup verify.

    Verifies OTP for the context and returns an authenticated token pair.
    """

    try:
        context = verify_context_otp(db, payload.context_id, payload.otp)
    except PermissionError as exc:
        _error(429, "OTP_RATE_LIMITED", str(exc))
    except ValueError as exc:
        message = str(exc)
        code = "OTP_EXPIRED" if "expired" in message.lower() else "INVALID_OTP"
        _error(400, code, message)

    if context.purpose != OtpPurpose.SIGNUP:
        _error(400, "INVALID_CONTEXT", "Invalid context")

    user = db.query(User).filter(User.id == context.user_id).first()
    if not user:
        _error(400, "USER_NOT_FOUND", "User not found")

    mark_user_verified(db, user)
    access, refresh = create_session(db, user)

    return AuthResponse(access_token=access, refresh_token=refresh, user=_user_out(user))


@router.post("/verify-otp", response_model=APIResponse)
def verify_otp(payload: SignupVerifyRequest, db: Annotated[Session, Depends(get_db)]):
    response = signup_verify(payload, db)
    user = db.query(User).filter(User.id == response.user.id).first()
    return _auth_api_response(
        "Account verified successfully.",
        response.access_token,
        response.refresh_token,
        user,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    },
)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    """Login.

    Accepts email or phone as identifier.
    """

    user = authenticate_by_identifier(db, payload.identifier, payload.password)

    if not user:
        _error(401, "INVALID_CREDENTIALS", "Invalid identifier or password.")

    if not user.is_verified:
        _error(403, "ACCOUNT_NOT_VERIFIED", "OTP verification required.")

    access, refresh = create_session(db, user)
    return AuthResponse(access_token=access, refresh_token=refresh, user=_user_out(user))


def login_unified(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    response = login(payload, db)
    user = db.query(User).filter(User.id == response.user.id).first()
    return _auth_api_response("Login successful.", response.access_token, response.refresh_token, user)


@router.post(
    "/password/forgot/initiate",
    response_model=ForgotInitiateResponse,
    responses={
        500: {"description": "Internal server error"},
    },
)
def forgot_initiate(payload: ForgotInitiateRequest, db: Annotated[Session, Depends(get_db)]):
    """Forgot password initiate.

    Sends OTP to the user's phone if user exists, but never leaks user existence.
    """

    kind, ident = normalize_identifier(payload.identifier)

    query = db.query(User)
    user = query.filter(User.email == ident).first() if kind == "email" else query.filter(User.phone == ident).first()

    if not user:
        return ForgotInitiateResponse(context_id="", message=OTP_SENT_MESSAGE, otp_expiry_seconds=300)

    result = create_or_refresh_context(
        db,
        purpose=OtpPurpose.PASSWORD_FORGOT,
        user=user,
        email=user.email,
        phone=user.phone,
    )

    sms = send_otp_sms(user.phone or "", result.otp, expiry_minutes=int(result.otp_expiry_seconds / 60))
    if sms.get("status") != "sent":
        _error(500, "OTP_DELIVERY_FAILED", sms.get("error") or "Failed to send OTP")

    return ForgotInitiateResponse(
        context_id=result.context_id,
        message=OTP_SENT_MESSAGE,
        otp_expiry_seconds=result.otp_expiry_seconds,
    )


@router.post("/password/forgot", response_model=APIResponse)
def forgot_password(payload: ForgotInitiateRequest, db: Annotated[Session, Depends(get_db)]):
    response = forgot_initiate(payload, db)
    return APIResponse(
        success=True,
        message=response.message,
        data={
            "context_id": response.context_id,
            "otp_expiry_seconds": response.otp_expiry_seconds,
        },
    )


@router.post(
    "/password/forgot/verify-otp",
    response_model=ForgotVerifyResponse,
    responses={
        400: {"description": "Bad request"},
        429: {"description": "Too many attempts"},
    },
)
def forgot_verify(payload: ForgotVerifyRequest, db: Annotated[Session, Depends(get_db)]):
    """Forgot password verify OTP.

    Verifies OTP for the context and returns a reset token.
    """

    try:
        context = verify_context_otp(db, payload.context_id, payload.otp)
    except PermissionError as exc:
        _error(429, "OTP_RATE_LIMITED", str(exc))
    except ValueError as exc:
        message = str(exc)
        code = "OTP_EXPIRED" if "expired" in message.lower() else "INVALID_OTP"
        _error(400, code, message)

    if context.purpose != OtpPurpose.PASSWORD_FORGOT:
        _error(400, "INVALID_CONTEXT", "Invalid context")

    user = db.query(User).filter(User.id == context.user_id).first()
    if not user:
        _error(400, "USER_NOT_FOUND", "User not found")

    reset_token, expiry_seconds = create_reset_token(db, user)
    return ForgotVerifyResponse(reset_token=reset_token, reset_token_expiry_seconds=expiry_seconds)


@router.post("/password/verify-otp", response_model=APIResponse)
def forgot_password_verify(payload: ForgotVerifyRequest, db: Annotated[Session, Depends(get_db)]):
    response = forgot_verify(payload, db)
    return APIResponse(
        success=True,
        message="OTP verified successfully.",
        data={
            "reset_token": response.reset_token,
            "reset_token_expiry_seconds": response.reset_token_expiry_seconds,
        },
    )


@router.post(
    "/password/reset",
    response_model=APIResponse,
    responses={
        400: {"description": "Bad request"},
    },
)
def password_reset(payload: PasswordResetRequest, db: Annotated[Session, Depends(get_db)]):
    """Password reset.

    Consumes a reset token and updates the password.
    """

    from auth.utils.password import hash_password

    user = consume_reset_token(db, payload.reset_token)
    if not user:
        _error(400, "INVALID_RESET_TOKEN", "Invalid or expired reset token")

    try:
        user.password_hash = hash_password(payload.new_password)
    except ValueError as exc:
        _error(400, "PASSWORD_TOO_LONG", str(exc), [{"field": "new_password", "message": str(exc)}])

    db.commit()

    return APIResponse(success=True, message="Password reset successful")


@router.post(
    "/token/refresh",
    response_model=AuthResponse,
    responses={
        401: {"description": "Unauthorized"},
    },
)
def token_refresh(payload: RefreshTokenRequest, db: Annotated[Session, Depends(get_db)]):
    """Refresh token rotation."""

    try:
        access, refresh, user = refresh_session(db, payload.refresh_token)
    except ValueError as exc:
        _error(401, "INVALID_REFRESH_TOKEN", str(exc))

    return AuthResponse(access_token=access, refresh_token=refresh, user=_user_out(user))


@router.post("/refresh", response_model=APIResponse)
def refresh(payload: RefreshTokenRequest, db: Annotated[Session, Depends(get_db)]):
    response = token_refresh(payload, db)
    user = db.query(User).filter(User.id == response.user.id).first()
    return _auth_api_response("Token refreshed.", response.access_token, response.refresh_token, user)


@router.post(
    "/logout",
    response_model=APIResponse,
)
def logout(payload: LogoutRequest, db: Annotated[Session, Depends(get_db)]):
    """Logout (session revocation)."""

    revoke_session(db, payload.refresh_token)
    return APIResponse(success=True, message="Logged out")


@router.get(
    "/me",
    response_model=UserOut,
    responses={
        401: {"description": "Unauthorized"},
    },
)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    """Return current user session (fast app boot dependency)."""

    return _user_out(current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        updated_user = update_current_user(db, current_user, payload)
    except ValueError as exc:
        message = str(exc)
        field_name = "email" if "Email" in message else "phone"
        _error(400, "VALIDATION_ERROR", message, [{"field": field_name, "message": message}])

    return _user_out(updated_user)


@router.get("/session", response_model=APIResponse, include_in_schema=False)
def me_session(current_user: Annotated[User, Depends(get_current_user)]):
    return APIResponse(
        success=True,
        message="Current user",
        data={"user": _user_out(current_user).model_dump()},
    )


@public_router.post("/register", response_model=APIResponse)
def public_register(payload: SignupInitiateRequest, db: Annotated[Session, Depends(get_db)]):
    return register(payload, db)


@public_router.post("/verify-otp", response_model=APIResponse)
def public_verify_otp(payload: SignupVerifyRequest, db: Annotated[Session, Depends(get_db)]):
    return verify_otp(payload, db)


@public_router.post("/login", response_model=APIResponse)
def public_login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    return login_unified(payload, db)


@public_router.post("/password/forgot", response_model=APIResponse)
def public_forgot_password(payload: ForgotInitiateRequest, db: Annotated[Session, Depends(get_db)]):
    return forgot_password(payload, db)


@public_router.post("/password/verify-otp", response_model=APIResponse)
def public_forgot_password_verify(payload: ForgotVerifyRequest, db: Annotated[Session, Depends(get_db)]):
    return forgot_password_verify(payload, db)


@public_router.post("/password/reset", response_model=APIResponse)
def public_password_reset(payload: PasswordResetRequest, db: Annotated[Session, Depends(get_db)]):
    return password_reset(payload, db)


@public_router.post("/refresh", response_model=APIResponse)
def public_refresh(payload: RefreshTokenRequest, db: Annotated[Session, Depends(get_db)]):
    return refresh(payload, db)


@public_router.post("/logout", response_model=APIResponse)
def public_logout(payload: LogoutRequest, db: Annotated[Session, Depends(get_db)]):
    return logout(payload, db)


@public_router.get("/me", response_model=APIResponse)
def public_me(current_user: Annotated[User, Depends(get_current_user)]):
    return me_session(current_user)


@public_router.patch("/me", response_model=APIResponse)
def public_update_me(
    payload: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    updated_user = update_me(payload, current_user, db)
    return APIResponse(
        success=True,
        message="Profile updated successfully.",
        data={"user": updated_user.model_dump()},
    )


@public_router.get("/admin/employees", response_model=APIResponse)
@admin_workspace_router.get("/admin/employees", response_model=APIResponse)
def public_list_employees(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_admin(current_user)
    employees = [_employee_out(employee).model_dump() for employee in list_employees(db)]
    return APIResponse(success=True, message="Employees fetched successfully.", data={"employees": employees})


@public_router.post("/admin/employees", response_model=APIResponse)
@admin_workspace_router.post("/admin/employees", response_model=APIResponse)
def public_create_employee(
    payload: EmployeeCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_admin(current_user)
    try:
        employee = create_employee_account(db, payload)
    except ValueError as exc:
        message = str(exc)
        if "Password is too long" in message:
            field_name = "password"
        else:
            field_name = "email" if "Email" in message else "phone"
        _error(400, "VALIDATION_ERROR", message, [{"field": field_name, "message": message}])
    return APIResponse(
        success=True,
        message="Employee created successfully.",
        data={"employee": _employee_out(employee).model_dump()},
    )


@public_router.put("/admin/employees/{employee_id}", response_model=APIResponse)
@admin_workspace_router.put("/admin/employees/{employee_id}", response_model=APIResponse)
def public_update_employee(
    employee_id: str,
    payload: EmployeeUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_admin(current_user)
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        _error(404, "NOT_FOUND", "Employee account not found.")
    try:
        employee = update_employee_account(db, employee, payload)
    except ValueError as exc:
        message = str(exc)
        if "Password is too long" in message:
            field_name = "password"
        else:
            field_name = "email" if "Email" in message else "phone"
        _error(400, "VALIDATION_ERROR", message, [{"field": field_name, "message": message}])
    return APIResponse(
        success=True,
        message="Employee updated successfully.",
        data={"employee": _employee_out(employee).model_dump()},
    )


@public_router.delete("/admin/employees/{employee_id}", response_model=APIResponse)
@admin_workspace_router.delete("/admin/employees/{employee_id}", response_model=APIResponse)
def public_delete_employee(
    employee_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    _require_admin(current_user)
    employee = get_employee_by_id(db, employee_id)
    if not employee:
        _error(404, "NOT_FOUND", "Employee account not found.")
    employee = delete_employee_account(db, employee)
    return APIResponse(
        success=True,
        message="Employee removed successfully.",
        data={"employee": _employee_out(employee).model_dump()},
    )
