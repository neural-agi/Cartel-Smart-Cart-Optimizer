from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="cartel", alias="POSTGRES_DB")
    postgres_user: str = Field(default="cartel", alias="POSTGRES_USER")
    postgres_password: str = Field(default="cartel", alias="POSTGRES_PASSWORD")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

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
