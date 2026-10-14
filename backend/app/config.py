from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = (BACKEND_DIR / "issues.db").as_posix()


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"
    APP_NAME: str = "Accessibility Issue Tracker API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
