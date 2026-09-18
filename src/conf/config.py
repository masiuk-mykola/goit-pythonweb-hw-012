"""Application settings loaded from environment variables and the ``.env`` file."""

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration.

    Every attribute can be overridden with an environment variable of the same
    name. Values without defaults (database URL, JWT secret, Cloudinary
    credentials, sender address) are required.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DB_URL: str

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRATION_SECONDS: int = 7 * 24 * 3600
    EMAIL_TOKEN_EXPIRATION_SECONDS: int = 7 * 24 * 3600
    RESET_TOKEN_EXPIRATION_SECONDS: int = 3600

    REDIS_URL: str = "redis://localhost:6379/0"
    USER_CACHE_TTL_SECONDS: int = 900

    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: EmailStr
    MAIL_FROM_NAME: str = "Phonebook API"
    MAIL_PORT: int = 1025
    MAIL_SERVER: str = "localhost"
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = False
    MAIL_USE_CREDENTIALS: bool = False
    MAIL_VALIDATE_CERTS: bool = False

    CLD_NAME: str
    CLD_API_KEY: str
    CLD_API_SECRET: str

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    APP_BASE_URL: str = "http://localhost:8000"


config = Settings()
