"""OpenLedger configuration via environment variables."""

from enum import Enum
from pydantic_settings import BaseSettings


class OCREngine(str, Enum):
    TESSERACT = "tesseract"
    SONNET_VISION = "sonnet-vision"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/openledger"
    database_url_sync: str = "postgresql://user:pass@localhost:5432/openledger"

    # Auth
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # AI
    anthropic_api_key: str = ""
    sonnet_model: str = "claude-sonnet-4-20250514"

    # OCR
    ocr_engine: OCREngine = OCREngine.TESSERACT

    # Accounting defaults
    accounting_basis: str = "accrual"
    default_fiscal_year_start: int = 1

    # App
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Startup guard: refuse to start with the default secret key in non-debug mode
if not settings.debug and settings.secret_key in ("change-me-in-production", "dev-secret-change-in-production"):
    raise RuntimeError(
        "CRITICAL: SECRET_KEY is still set to the default value. "
        "Set a strong random SECRET_KEY environment variable before running in production."
    )
