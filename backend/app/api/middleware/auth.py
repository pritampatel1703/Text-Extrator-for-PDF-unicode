"""
JWT Authentication middleware.
Validates Bearer tokens and extracts user info.
"""

from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.db.database import get_db
from app.models import User

# HTTP Bearer token scheme
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Extract and validate the current user from the JWT token.
    Returns None if no token is provided (for optional auth).
    """
    if not credentials:
        return None

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise AuthenticationError()

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError()

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("User not found or disabled.")

    return user


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authentication — raises 401 if no valid token."""
    if not user:
        raise AuthenticationError()
    return user


async def require_admin(
    user: User = Depends(require_auth),
) -> User:
    """Require admin role — raises 403 if not admin."""
    if user.role != "admin":
        raise AuthorizationError()
    return user
