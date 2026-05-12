from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

AUTHORIZATION_HEADER = "Authorization"
X_USER_ID_HEADER = "X-User-Id"
X_ROLE_HEADER = "X-Role"
DEFAULT_USER_ID = "guest_user"
GUEST_TOKEN_PREFIX = "guest:"

DbHeader = Annotated[str | None, Header(alias=AUTHORIZATION_HEADER)]
UserHeader = Annotated[str | None, Header(alias=X_USER_ID_HEADER)]
RoleHeader = Annotated[str | None, Header(alias=X_ROLE_HEADER)]


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _decode_hs256_subject(token: str) -> str | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            return None

        signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
        expected_signature = hmac.new(
            jwt_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_signature = _b64url_decode(parts[2])
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        payload = json.loads(_b64url_decode(parts[1]))
    except (ValueError, json.JSONDecodeError):
        return None

    expires_at = payload.get("exp")
    if isinstance(expires_at, (int, float)) and expires_at < time.time():
        return None
    if payload.get("type") not in {None, "access"}:
        return None

    subject = payload.get("sub") or payload.get("user_id")
    return str(subject) if subject else None


def get_active_user_id(
    authorization: DbHeader = None,
    x_user_id: UserHeader = None,
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        user_id = _decode_hs256_subject(authorization.split(" ", 1)[1].strip())
        if user_id:
            return user_id

    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    return DEFAULT_USER_ID


def get_current_user_id(
    authorization: DbHeader = None,
    x_user_id: UserHeader = None,
) -> str:
    user_id = get_active_user_id(authorization=authorization, x_user_id=x_user_id)
    if user_id != DEFAULT_USER_ID:
        return user_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "success": False,
            "message": "Authenticated user is required.",
            "data": None,
            "error": {"code": "UNAUTHORIZED", "message": "Authenticated user is required.", "details": []},
        },
    )


def get_current_role(
    authorization: DbHeader = None,
    x_role: RoleHeader = None,
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        try:
            payload = json.loads(_b64url_decode(authorization.split(" ", 1)[1].strip().split(".")[1]))
            role = str(payload.get("role") or "").strip().lower()
            if role == "vendor":
                return "employee"
            if role:
                return role
        except (ValueError, json.JSONDecodeError, IndexError):
            pass

    return (x_role or "").strip().lower()


UserId = Annotated[str, Depends(get_active_user_id)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
RoleId = Annotated[str, Depends(get_current_role)]
