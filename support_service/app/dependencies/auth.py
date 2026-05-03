from __future__ import annotations

import os
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status


def _decode_token(authorization: str | None) -> dict | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    secret = os.getenv("JWT_SECRET")
    if not secret:
        return None

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None

    if payload.get("type") not in {None, "access"}:
        return None

    return payload


def get_optional_actor(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    payload = _decode_token(authorization)
    if not payload:
        return None

    role = str(payload.get("role") or "").lower()
    if role == "vendor":
        role = "employee"

    return {
        "user_id": str(payload.get("user_id") or ""),
        "role": role,
    }


def get_actor(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    actor = get_optional_actor(authorization)
    if not actor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return actor


def require_operational_actor(actor=Depends(get_actor)):
    if actor["role"] not in {"admin", "employee"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or employee access required")
    return actor


def require_admin_actor(actor=Depends(get_actor)):
    if actor["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return actor
