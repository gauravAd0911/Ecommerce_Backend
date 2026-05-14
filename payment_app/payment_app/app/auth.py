"""Authentication utilities for payment service."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import JWT_SECRET, JWT_ALGORITHM

security = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    """Extract JWT token from Authorization header."""
    if credentials and credentials.credentials:
        return credentials.credentials
    return None


def get_authenticated_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> int:
    """
    Extract and validate JWT token to get authenticated user_id.
    
    Raises HTTPException if token is missing, invalid, or expired.
    """
    token = _extract_token(credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please provide a valid JWT token.",
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id.",
        )

    return int(user_id)
