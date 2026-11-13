"""Supabase JWT authentication primitives."""

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status

from snappe.config import Settings, get_settings


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity extracted from a verified Supabase access token."""

    user_id: str
    role: str


def decode_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    """Verify and decode a Supabase JWT using the configured signing secret."""
    if settings.supabase_jwt_secret is None:
        raise ValueError("SUPABASE_JWT_SECRET is not configured")

    payload = jwt.decode(
        token,
        settings.supabase_jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        options={"require": ["exp"]},
    )
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("JWT subject is missing")
    role = payload.get("role", "authenticated")
    if not isinstance(role, str):
        raise ValueError("JWT role is invalid")
    return AuthenticatedUser(user_id=user_id, role=role)


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> AuthenticatedUser:
    """FastAPI dependency for routes requiring a verified bearer token."""
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_access_token(token, settings)
    except (ValueError, jwt.InvalidTokenError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
