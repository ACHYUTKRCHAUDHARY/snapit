from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from pydantic import SecretStr
from starlette.requests import Request

from snappe.adapters.auth import (
    AuthenticatedUser,
    decode_access_token,
    get_current_user,
    require_role,
)
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


def test_decode_access_token_rs256_asymmetric_key() -> None:
    # Generate private and public RSA keys
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    settings = Settings(
        _env_file=None,
        supabase_jwt_public_key=public_pem,
    )

    token = jwt.encode(
        {
            "sub": "user-rsa-1",
            "role": "admin",
            "business_id": "biz-multi-tenant-1",
            "email": "admin@example.com",
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        private_pem,
        algorithm="RS256",
    )

    user = decode_access_token(token, settings)
    assert user.user_id == "user-rsa-1"
    assert user.role == "admin"
    assert user.business_id == "biz-multi-tenant-1"
    assert user.email == "admin@example.com"


def test_decode_access_token_app_metadata_business_id() -> None:
    settings = Settings(
        _env_file=None,
        supabase_jwt_secret=SecretStr("test-secret-that-is-long-enough"),
    )
    token = jwt.encode(
        {
            "sub": "user-meta",
            "role": "operator",
            "app_metadata": {"business_id": "biz-999"},
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "test-secret-that-is-long-enough",
        algorithm="HS256",
    )
    user = decode_access_token(token, settings)
    assert user.business_id == "biz-999"


def test_require_role_dependency() -> None:
    checker = require_role(["owner", "admin"])
    valid_user = AuthenticatedUser(user_id="u1", role="admin")
    invalid_user = AuthenticatedUser(user_id="u2", role="viewer")

    assert checker(valid_user) == valid_user

    with pytest.raises(HTTPException, match="Role 'viewer' is not authorized") as exc:
        checker(invalid_user)
    assert exc.value.status_code == 403
