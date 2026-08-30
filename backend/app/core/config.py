from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="Cartel", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")
    docs_enabled: bool = Field(default=True, alias="DOCS_ENABLED")
    cors_allowed_origins: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")
    auth_required: bool = Field(default=False, alias="AUTH_REQUIRED")
    auth_tokens: str = Field(default="", alias="AUTH_TOKENS")
    rate_limit_requests: int = Field(default=120, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    checkout_observation_provider_mode: Literal["registry", "unavailable"] = Field(
        default="unavailable",
        alias="CHECKOUT_OBSERVATION_PROVIDER_MODE",
    )
    checkout_capture_adapter_mode: Literal["unavailable", "blinkit"] = Field(
        default="unavailable",
        alias="CHECKOUT_CAPTURE_ADAPTER_MODE",
    )
    planning_max_cart_items: int = Field(default=20, alias="PLANNING_MAX_CART_ITEMS")
    planning_max_candidates_per_item: int = Field(
        default=20,
        alias="PLANNING_MAX_CANDIDATES_PER_ITEM",
    )
    planning_max_combinations: int = Field(
        default=10000,
        alias="PLANNING_MAX_COMBINATIONS",
    )
    planning_max_supplied_plans: int = Field(
        default=100,
        alias="PLANNING_MAX_SUPPLIED_PLANS",
    )
    planning_retailer_identity_map: str = Field(default="", alias="PLANNING_RETAILER_IDENTITY_MAP")
    planning_checkout_group_map: str = Field(default="", alias="PLANNING_CHECKOUT_GROUP_MAP")
    planning_inconvenience_penalty_units: int | None = Field(
        default=None, alias="PLANNING_INCONVENIENCE_PENALTY_UNITS"
    )
    planning_retailer_preference_priority: int | None = Field(
        default=None, alias="PLANNING_RETAILER_PREFERENCE_PRIORITY"
    )
    planning_feasibility: str | None = Field(default=None, alias="PLANNING_FEASIBILITY")
    planning_feasibility_evidence: str = Field(default="", alias="PLANNING_FEASIBILITY_EVIDENCE")
    optimization_policy_version: str = Field(default="policy-v1", alias="OPTIMIZATION_POLICY_VERSION")
    scraper_timeout_seconds: float = Field(
        default=15.0,
        alias="SCRAPER_TIMEOUT_SECONDS",
    )
    scraper_max_retries: int = Field(default=3, alias="SCRAPER_MAX_RETRIES")
    scraper_retry_backoff_seconds: float = Field(
        default=1.0,
        alias="SCRAPER_RETRY_BACKOFF_SECONDS",
    )
    scraper_user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        alias="SCRAPER_USER_AGENT",
    )
    data_dir: Path = Field(default=Path("../data"), alias="DATA_DIR")
    blinkit_delivery_location_name: str = Field(
        default="New Delhi",
        alias="BLINKIT_DELIVERY_LOCATION_NAME",
    )
    blinkit_delivery_latitude: float = Field(
        default=28.6139,
        alias="BLINKIT_DELIVERY_LATITUDE",
    )
    blinkit_delivery_longitude: float = Field(
        default=77.2090,
        alias="BLINKIT_DELIVERY_LONGITUDE",
    )
    blinkit_geolocation_accuracy: float = Field(
        default=50.0,
        alias="BLINKIT_GEOLOCATION_ACCURACY",
    )
    blinkit_session_state_path: Path = Field(
        default=Path("../data/sessions/blinkit/browser_state.json"),
        alias="BLINKIT_SESSION_STATE_PATH",
    )
    blinkit_browser_executable_path: Path | None = Field(
        default=None,
        alias="BLINKIT_BROWSER_EXECUTABLE_PATH",
    )

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="cartel", alias="POSTGRES_DB")
    postgres_user: str = Field(default="cartel", alias="POSTGRES_USER")
    postgres_password: str = Field(default="cartel", alias="POSTGRES_PASSWORD")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    @field_validator(
        "app_name",
        "app_version",
        "api_v1_prefix",
        "log_level",
        "scraper_user_agent",
        "blinkit_delivery_location_name",
        "postgres_host",
        "postgres_db",
        "postgres_user",
        "postgres_password",
        "redis_url",
        "optimization_policy_version",
        mode="before",
    )
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("configuration value must not be blank")
        return value.strip()

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value == "/":
            raise ValueError("API_V1_PREFIX must be a non-root absolute path")
        return value.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("LOG_LEVEL is unsupported")
        return normalized

    @field_validator("postgres_port")
    @classmethod
    def validate_postgres_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("POSTGRES_PORT must be between 1 and 65535")
        return value

    @field_validator("scraper_timeout_seconds", "scraper_retry_backoff_seconds")
    @classmethod
    def validate_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("scraper timing values must be positive")
        return value

    @field_validator("scraper_max_retries")
    @classmethod
    def validate_retries(cls, value: int) -> int:
        if value < 0:
            raise ValueError("SCRAPER_MAX_RETRIES must not be negative")
        return value

    @field_validator("rate_limit_requests", "rate_limit_window_seconds")
    @classmethod
    def validate_rate_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("rate limit values must be positive")
        return value

    @property
    def configured_auth_tokens(self) -> dict[str, str]:
        tokens: dict[str, str] = {}
        for entry in self.auth_tokens.split(","):
            if not entry.strip():
                continue
            if "=" not in entry:
                raise ValueError("AUTH_TOKENS entries must use user_id=token format")
            user_id, token = (part.strip() for part in entry.split("=", 1))
            if not user_id or not token:
                raise ValueError("AUTH_TOKENS entries must contain user_id and token")
            tokens[token] = user_id
        return tokens

    @field_validator(
        "planning_max_cart_items",
        "planning_max_candidates_per_item",
        "planning_max_combinations",
        "planning_max_supplied_plans",
    )
    @classmethod
    def validate_planning_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("planning limits must be positive")
        return value

    @field_validator("planning_feasibility")
    @classmethod
    def validate_optional_feasibility(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("PLANNING_FEASIBILITY must not be blank when provided")
        return value.strip() if value is not None else None

    @property
    def configured_planning_feasibility_evidence(self) -> tuple[str, ...]:
        return tuple(item.strip() for item in self.planning_feasibility_evidence.split(",") if item.strip())

    @field_validator("blinkit_delivery_latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("BLINKIT_DELIVERY_LATITUDE is invalid")
        return value

    @field_validator("blinkit_delivery_longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("BLINKIT_DELIVERY_LONGITUDE is invalid")
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
            raise ValueError("REDIS_URL must be a valid redis:// or rediss:// URL")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("REDIS_URL port must be between 1 and 65535")
        return value

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> "Settings":
        if self.auth_required and not self.configured_auth_tokens:
            raise ValueError("AUTH_TOKENS must be configured when AUTH_REQUIRED is true")
        if self.app_env == "production":
            if "postgres_password" not in self.model_fields_set or self.postgres_password == "cartel":
                raise ValueError("POSTGRES_PASSWORD must be explicitly configured in production")
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
            if self.docs_enabled:
                raise ValueError("DOCS_ENABLED must be false in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins(self) -> tuple[str, ...]:
        return tuple(
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        )

    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def cleaned_data_dir(self) -> Path:
        return self.data_dir / "cleaned"

    @property
    def sessions_data_dir(self) -> Path:
        return self.data_dir / "sessions"

    @field_validator("data_dir", mode="after")
    @classmethod
    def resolve_data_dir(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return (BACKEND_ROOT / value).resolve()

    @field_validator("blinkit_session_state_path", mode="after")
    @classmethod
    def resolve_blinkit_session_state_path(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return (BACKEND_ROOT / value).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
