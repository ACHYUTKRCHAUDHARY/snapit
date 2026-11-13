from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from starlette.requests import Request

from snappe.adapters.auth import decode_access_token, get_current_user
from snappe.config import Settings


def test_decode_access_token_returns_verified_identity() -> None:
    settings = Settings(
        _env_file=None,
        supabase_jwt_secret=SecretStr("test-secret-that-is-long-enough"),
    )
    token = jwt.encode(
        {
            "sub": "user-1",
            "role": "authenticated",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "test-secret-that-is-long-enough",
        algorithm="HS256",
    )

    assert decode_access_token(token, settings).user_id == "user-1"


def test_decode_access_token_rejects_missing_secret() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(ValueError, match="SUPABASE_JWT_SECRET"):
        decode_access_token("token", settings)


def test_decode_access_token_rejects_missing_subject() -> None:
    settings = Settings(
        _env_file=None,
        supabase_jwt_secret=SecretStr("test-secret-that-is-long-enough"),
    )
    token = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(minutes=5)},
        "test-secret-that-is-long-enough",
        algorithm="HS256",
    )

    with pytest.raises(ValueError, match="subject"):
        decode_access_token(token, settings)


def test_decode_access_token_rejects_invalid_role() -> None:
    settings = Settings(
        _env_file=None,
        supabase_jwt_secret=SecretStr("test-secret-that-is-long-enough"),
    )
    token = jwt.encode(
        {
            "sub": "user-1",
            "role": 123,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "test-secret-that-is-long-enough",
        algorithm="HS256",
    )

    with pytest.raises(ValueError, match="role"):
        decode_access_token(token, settings)


def test_current_user_requires_bearer_token() -> None:
    request = Request({"type": "http", "headers": []})

    with pytest.raises(HTTPException, match="Bearer token required"):
        get_current_user(request, Settings(_env_file=None))


def test_current_user_rejects_invalid_bearer_token() -> None:
    request = Request(
        {
            "type": "http",
            "headers": [(b"authorization", b"Bearer invalid")],
        }
    )

    with pytest.raises(HTTPException, match="Invalid access token"):
        get_current_user(request, Settings(_env_file=None))
