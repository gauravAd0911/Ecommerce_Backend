from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from auth.models.user import User
from auth.utils.jwt import verify_token

security = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    access_token: str | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    return access_token


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from the Authorization JWT token or access_token cookie."""

    token = _extract_token(credentials, access_token)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")

    return user


def require_role(required_role: str):
    """Dependency factory for role checks."""

    def decorator(user: User = Depends(get_current_user)) -> User:
        if user.role.value != required_role:
            raise HTTPException(status_code=403, detail=f"{required_role.title()} access required")
        return user

    return decorator
