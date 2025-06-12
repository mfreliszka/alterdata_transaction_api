"""Configuration settings for the Transaction API application."""

from typing import Any

from pydantic import PostgresDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    SECRET_KEY: str = "c52374c72780ff0720fe2311eb4313b57a67ec321f40eaf47f86c221fb586e59" # change in production
    API_TOKEN: str = "e905476521695f4bf485befac69345556c3d9aaa59098d5f8d7369a0614e6b18"  # Simple token for demo, change in production
    TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REQUIRE_AUTH: bool = False

    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Transaction API"

    # Database settings
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Customize SQLAlchemy database URL for PostgreSQL
    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v: str | None) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user="postgres",
            password="postgres",
            host="db",
            path="/transaction_db",
        )

    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v: str) -> str:
        if v == "c52374c72780ff0720fe2311eb4313b57a67ec321f40eaf47f86c221fb586e59":
            print("WARNING: Using default SECRET_KEY. Change in production!")
        return v

    # CORS settings
    CORS_ORIGINS: list[str] = ["*"]

    # Logging settings
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
