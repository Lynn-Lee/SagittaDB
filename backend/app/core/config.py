"""
应用配置 — 通过 Pydantic Settings 从环境变量读取，类型安全。
所有配置项均有默认值，便于开发环境零配置启动。
"""
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── 应用基础 ─────────────────────────────────────────────
    APP_ENV: Literal["development", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ─── 数据库 ───────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://archery:archery123@localhost:5432/archery"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://archery:archery123@localhost:5432/archery"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # ─── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"

    # ─── 安全 ─────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_RANDOM_32_CHARS"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── 多租户预留（企业版固定为 1）─────────────────────────
    TENANT_ID: int = 1

    # ─── CORS ─────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost", "http://localhost:5173", "http://localhost:3000"]

    # ─── 可观测中心 ────────────────────────────────────────────
    PROMETHEUS_URL: str = "http://localhost:9090"
    ALERTMANAGER_URL: str = "http://localhost:9093"
    GRAFANA_URL: str = "http://localhost:3000"
    GRAFANA_CLIENT_ID: str = "archery"
    GRAFANA_CLIENT_SECRET: str = ""

    # ─── AI 能力（可选）──────────────────────────────────────
    AI_PROVIDER: Literal["openai", "anthropic", "none"] = "none"
    AI_API_KEY: str = ""

    # ─── goInception（可选增强）──────────────────────────────
    ENABLE_GOINCEPTION: bool = False
    GO_INCEPTION_HOST: str = ""
    GO_INCEPTION_PORT: int = 4000

    # ─── LDAP（可选）─────────────────────────────────────────
    LDAP_ENABLED: bool = False
    LDAP_SERVER_URI: str = ""
    LDAP_BIND_DN: str = ""
    LDAP_BIND_PASSWORD: str = ""
    LDAP_USER_DN_TEMPLATE: str = ""

    # ─── OIDC（可选）─────────────────────────────────────────
    OIDC_ENABLED: bool = False
    OIDC_OP_AUTHORIZATION_ENDPOINT: str = ""
    OIDC_OP_TOKEN_ENDPOINT: str = ""
    OIDC_OP_JWKS_ENDPOINT: str = ""
    OIDC_RP_CLIENT_ID: str = ""
    OIDC_RP_CLIENT_SECRET: str = ""

    # ─── 对象存储 ─────────────────────────────────────────────
    STORAGE_TYPE: Literal["local", "s3", "oss", "azure"] = "local"
    STORAGE_LOCAL_PATH: str = "/app/downloads"

    # ─── 通知 ─────────────────────────────────────────────────
    DINGTALK_WEBHOOK: str = ""
    FEISHU_WEBHOOK: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if v == "CHANGE_ME_IN_PRODUCTION_USE_RANDOM_32_CHARS":
            import warnings
            warnings.warn("SECRET_KEY 使用默认值，请在生产环境中替换！", stacklevel=2)
        return v

    @property
    def celery_broker_url(self) -> str:
        return self.REDIS_URL

    @property
    def celery_result_backend(self) -> str:
        return self.REDIS_URL


# 全局单例
settings = Settings()
