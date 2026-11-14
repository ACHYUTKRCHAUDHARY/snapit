"""Supabase JWT authentication primitives."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status

from snappe.config import Settings, get_settings


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity extracted from a verified Supabase access token."""

    user_id: str
    role: str
    business_id: str | None = None
    email: str | None = None


def decode_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    """Verify and decode a Supabase JWT via symmetric HS256 or asymmetric RS256."""
    payload: dict[str, Any]
    if settings.supabase_jwt_public_key:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_public_key,
            algorithms=["RS256"],
            options={"require": ["exp"]},
        )
    elif settings.supabase_jwt_secret:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
    else:
        raise ValueError("Neither SUPABASE_JWT_SECRET nor SUPABASE_JWT_PUBLIC_KEY is configured")

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("JWT subject is missing")
    role = payload.get("role", "authenticated")
    if not isinstance(role, str):
        raise ValueError("JWT role is invalid")

    business_id = payload.get("business_id")
    if not isinstance(business_id, str):
        app_metadata = payload.get("app_metadata")
        if isinstance(app_metadata, dict):
            b_id = app_metadata.get("business_id")
            business_id = str(b_id) if b_id is not None else None
        else:
            business_id = None

    email = payload.get("email")
    if not isinstance(email, str):
        email = None

    return AuthenticatedUser(
        user_id=user_id,
        role=role,
        business_id=business_id,
        email=email,
    )


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


def require_role(
    allowed_roles: Sequence[str],
) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """Dependency factory checking that user possesses one of the allowed roles."""

    def role_checker(
        user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    ) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized for this resource",
            )
        return user

    return role_checker
