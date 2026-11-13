"""Validated application configuration."""

from functools import lru_cache

from pydantic import Field, PositiveInt, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./snappe.db"
    default_timezone: str = "Asia/Kolkata"
    retention_days: PositiveInt = Field(default=210, validation_alias="RETENTION_DAYS")
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_jwt_secret: SecretStr | None = None
    meta_app_id: str | None = None
    meta_app_secret: SecretStr | None = None
    meta_verify_token: SecretStr | None = None
    meta_phone_number_id: str | None = None
    meta_access_token: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    llm_provider: str = "gemini"
    llm_model: str | None = None

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        if self.app_env.lower() == "production":
            missing = []
            if not self.supabase_url:
                missing.append("SUPABASE_URL")
            if not self.supabase_service_role_key:
                missing.append("SUPABASE_SERVICE_ROLE_KEY")
            if not self.supabase_jwt_secret:
                missing.append("SUPABASE_JWT_SECRET")
            if not self.database_url.startswith(("postgresql://", "postgresql+")):
                missing.append("DATABASE_URL (PostgreSQL)")
            if missing:
                raise ValueError("Production configuration is incomplete: " + ", ".join(missing))
        return self

    @property
    def is_production(self) -> bool:
        """Return whether production safeguards should be enabled."""
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""
    return Settings()
