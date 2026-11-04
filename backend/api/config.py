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

    # Background jobs. A crashed analysis is retried up to max_job_retries times after the first
    # try. A job stuck in `processing` longer than stale_job_minutes (worker died) is recovered;
    # keep that above analysis_timeout_seconds so a live job is never taken away.
    max_job_retries: int = 3
    analysis_timeout_seconds: int = 120
    stale_job_minutes: int = 5
    worker_poll_seconds: float = 1.0
