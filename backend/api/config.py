from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env, located by absolute path so it loads regardless of the working directory.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "vendra"
    upload_dir: str = "uploads"
    max_upload_mb: int = 50
    environment: str = "dev"
