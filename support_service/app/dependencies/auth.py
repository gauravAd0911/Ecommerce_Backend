from __future__ import annotations

import os
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()


def _extract_token(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return access_token


def _decode_token(authorization: str | None) -> dict | None:
    if not authorization:
        return None

    token = authorization
    if authorization.lower().startswith("bearer "):
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
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
):
    token = _extract_token(authorization, access_token)
    payload = _decode_token(token)
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
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
):
    actor = get_optional_actor(authorization, access_token)
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
