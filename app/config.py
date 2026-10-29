from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = "sqlite:///./mentor.db"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.hcnsec.cn/v1"
    llm_model: str = "DeepSeek-V4-Pro"
    app_env: str = "development"
    firebase_project_id: str | None = None
    firebase_service_account_json: str | None = None
    firebase_service_account_file: str | None = None
    firebase_api_key: str | None = None
    firebase_auth_domain: str | None = None
    firebase_storage_bucket: str | None = None
    firebase_messaging_sender_id: str | None = None
    firebase_app_id: str | None = None
    sandbox_mode: str = "docker"
    sandbox_image: str = "python:3.12-slim"
    sandbox_timeout_seconds: int = 5
    sandbox_memory: str = "128m"
    sandbox_cpus: str = "0.5"

    # Resolve .env from the project rather than from whichever directory
    # happens to be used to start Uvicorn.
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")


settings = Settings()
