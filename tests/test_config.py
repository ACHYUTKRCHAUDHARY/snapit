import pytest
from pydantic import ValidationError

from snappe.config import Settings


def test_development_settings_use_local_database() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///./snappe.db"
    assert settings.retention_days == 210


def test_production_settings_require_supabase_dependencies() -> None:
    with pytest.raises(ValidationError, match="SUPABASE_URL"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="sqlite:///./snappe.db",
        )
