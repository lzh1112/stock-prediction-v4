from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 应用 ---
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-change-in-production"
    PROJECT_NAME: str = "多模态新闻驱动型股价预测系统"

    # --- 数据库 (原型: SQLite) ---
    DATABASE_PATH: str = "data/stock_pred.db"

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite+aiosqlite:///{self.DATABASE_PATH}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return f"sqlite:///{self.DATABASE_PATH}"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- LLM ---
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL_NAME: str = "gpt-4o-mini"
    LOCAL_LLM_PATH: str = "models/qwen2.5-7b-instruct-int4"
    LLM_TIMEOUT: int = 30
    LLM_MAX_RETRIES: int = 3

    # --- 数据源 ---
    TUSHARE_TOKEN: str = ""

    # --- 日志 ---
    LOG_LEVEL: str = "DEBUG"

    # --- 限流 ---
    RATE_LIMIT_PER_MINUTE: int = 60


settings = Settings()
