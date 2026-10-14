import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Integrations (Groq, SendGrid) read their keys from os.environ directly
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from the environment / .env.

    DATABASE_URL and SECRET_KEY are required: a missing value makes the app
    fail at startup instead of silently running with an insecure fallback.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str
    SQLALCHEMY_ECHO: bool = False

    # Security
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Comma-separated list of origins allowed to call the API with credentials
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # External APIs (optional: features degrade gracefully when unset)
    GROQ_API_KEY: str = ""
    SENDGRID_API_KEY: str = ""

    # Audio digest: off unless switched on AND GOOGLE_APPLICATION_CREDENTIALS
    # points at a service-account file. Voices are Google Cloud WaveNet names.
    PODCAST_ENABLED: bool = False
    PODCAST_LANGUAGE_CODE: str = "de-DE"
    PODCAST_VOICE_HOST: str = "de-DE-Wavenet-B"
    PODCAST_VOICE_GUEST: str = "de-DE-Wavenet-A"
    PODCAST_SPEAKING_RATE: float = 1.05
    PODCAST_MAX_BYTES: int = 8 * 1024 * 1024

    # App
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    @field_validator("SECRET_KEY")
    @classmethod
    def reject_placeholder_secret(cls, v: str) -> str:
        if v.lower().startswith(("your-", "changeme")):
            raise ValueError("SECRET_KEY still contains a placeholder value")
        return v

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """Detect production via explicit ENVIRONMENT or Railway auto-set vars."""
        return (
            self.ENVIRONMENT == "production"
            or bool(os.getenv("RAILWAY_ENVIRONMENT"))
            or bool(os.getenv("RAILWAY_ENVIRONMENT_NAME"))
            or bool(os.getenv("RAILWAY_PROJECT_ID"))
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
