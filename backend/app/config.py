from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_postgres_url(url: str) -> str:
    """Ensure the URL uses the asyncpg driver.

    Managed providers (Railway, Render, Heroku, Neon, Supabase) expose the
    DATABASE_URL as plain `postgresql://...` for compatibility with sync
    clients. Our app stack is fully async, so SQLAlchemy needs
    `postgresql+asyncpg://...`. We transparently upgrade the scheme so any
    upstream URL Just Works without the operator having to remember.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


# Sentinel values that must never reach production.
_FORBIDDEN_SECRETS: frozenset[str] = frozenset({
    "change-me",
    "dev-secret-key-change-in-production",
    "dev-jwt-secret-change-in-production",
})
# Any secret starting with one of these prefixes is rejected in prod.
_FORBIDDEN_SECRET_PREFIXES: tuple[str, ...] = (
    "dev-only-",
    "dev-",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = "change-me"
    app_name: str = "Kuwait WhatsApp Growth Engine"
    app_version: str = "0.1.0"
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # Database
    database_url: str = "postgresql+asyncpg://kwgrowth:kwgrowth_dev@localhost:5432/kwgrowth"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    @field_validator("database_url")
    @classmethod
    def _ensure_asyncpg_driver(cls, v: str) -> str:
        return _normalize_postgres_url(v)

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # WhatsApp
    whatsapp_provider: Literal["cloud_api", "twilio"] = "cloud_api"
    whatsapp_cloud_api_token: str = ""
    whatsapp_cloud_api_phone_number_id: str = ""
    whatsapp_cloud_api_business_account_id: str = ""
    whatsapp_verify_token: str = "change-me"

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""

    # Tap Payments
    tap_secret_key: str = ""
    tap_publishable_key: str = ""
    tap_webhook_secret: str = ""

    # S3 Storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "kwgrowth"
    s3_region: str = "us-east-1"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Sentry
    sentry_dsn: str = ""

    # AI
    anthropic_api_key: str = ""
    anthropic_api_url: str = "https://api.anthropic.com/v1"

    # App domain (used in email templates, widget embed codes, payment callbacks)
    app_domain: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    # ── Security validation ───────────────────────────────────────────────────
    # Runs after fields are populated. In staging/production, refuses to start
    # if any critical secret is still a known-dev placeholder or is empty.
    @model_validator(mode="after")
    def _validate_secrets_for_non_dev(self) -> "Settings":
        if self.app_env == "development":
            return self

        required: dict[str, str] = {
            "APP_SECRET_KEY": self.app_secret_key,
            "JWT_SECRET_KEY": self.jwt_secret_key,
            "WHATSAPP_VERIFY_TOKEN": self.whatsapp_verify_token,
        }
        problems: list[str] = []
        for name, value in required.items():
            if not value:
                problems.append(f"{name} is empty")
                continue
            if value in _FORBIDDEN_SECRETS:
                problems.append(f"{name} is a known dev placeholder ({value!r})")
                continue
            if value.startswith(_FORBIDDEN_SECRET_PREFIXES):
                problems.append(f"{name} uses a dev-only prefix ({value!r})")
                continue
            if len(value) < 32:
                problems.append(
                    f"{name} is too short ({len(value)} chars); require at least 32"
                )

        # Tap and Sentry are not strictly required at boot, but flag in prod
        # if payments are expected to work.
        if self.app_env == "production":
            if self.tap_secret_key and self.tap_secret_key.startswith("sk_test_"):
                problems.append(
                    "TAP_SECRET_KEY is a Tap test key (sk_test_*); "
                    "production must use a live key (sk_live_*)"
                )
            if self.tap_secret_key and not self.tap_webhook_secret:
                problems.append(
                    "TAP_WEBHOOK_SECRET is required when TAP_SECRET_KEY is set"
                )

        if self.app_debug and self.app_env == "production":
            problems.append("APP_DEBUG must be false in production")

        if problems:
            joined = "\n  - ".join(problems)
            raise ValueError(
                f"Refusing to start in {self.app_env!r} with insecure config:\n"
                f"  - {joined}\n"
                f"Populate secrets via your secret manager before deploying."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
