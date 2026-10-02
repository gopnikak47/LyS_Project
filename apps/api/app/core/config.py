"""Cấu hình ứng dụng đọc từ biến môi trường (xem `.env.example`)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_INSECURE_DEFAULTS = {"change-me", "change-me-too", "change-me-to-a-long-random-string"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Chung ---
    app_name: str = "LyS Survey"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_json: bool = True
    public_base_url: str = "http://localhost:8080"

    # --- Bảo mật ---
    secret_key: SecretStr = SecretStr("change-me")
    hash_salt: SecretStr = SecretStr("change-me-too")
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_ttl_days: int = Field(default=14, ge=1, le=90)
    bcrypt_rounds: int = Field(default=12, ge=12, le=16)
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    # Cookie Secure: mặc định bật ở production (HTTPS); dev chạy http://localhost nên tắt.
    cookie_secure: bool | None = None
    login_max_attempts: int = Field(default=5, ge=1)
    login_lock_minutes: int = Field(default=15, ge=1)
    login_rate_per_minute: int = Field(default=10, ge=1)
    register_rate_per_hour: int = Field(default=20, ge=1)
    invite_ttl_days: int = Field(default=7, ge=1)
    reset_token_ttl_minutes: int = Field(default=60, ge=5)

    # --- PostgreSQL ---
    postgres_db: str = "lys"
    postgres_user: str = "lys"
    postgres_password: SecretStr = SecretStr("lys_dev_password")
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = ""
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Email ---
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "LyS Survey <no-reply@lys.local>"
    smtp_use_tls: bool = False

    # --- Lưu tệp ---
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: str = "./var/storage"

    # NLP mặc định đòi artifact thật; rules chỉ dùng demo, không tuyên bố F1 production.
    nlp_backend: Literal["phobert", "rules"] = "phobert"
    nlp_model_path: str = ""
    nlp_topic_model: str = ""
    nlp_batch_size: int = Field(default=64, ge=1, le=256)
    upload_scanner_host: str = ""
    upload_scanner_port: int = 3310

    # --- Health-check ---
    health_check_timeout_seconds: float = Field(default=2.0, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        # Cho phép khai báo "a,b,c" trong .env thay vì JSON.
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _finalize(self) -> Settings:
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:"
                f"{self.postgres_password.get_secret_value()}@"
                f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        if self.is_production:
            # Không cho chạy production với bí mật mặc định.
            for name in ("secret_key", "hash_salt"):
                secret: SecretStr = getattr(self, name)
                raw = secret.get_secret_value()
                if raw in _INSECURE_DEFAULTS or len(raw) < 32:
                    msg = f"{name.upper()} phải được đặt giá trị ngẫu nhiên ≥ 32 ký tự ở production"
                    raise ValueError(msg)
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def secure_cookies(self) -> bool:
        return self.is_production if self.cookie_secure is None else self.cookie_secure


@lru_cache
def get_settings() -> Settings:
    return Settings()
