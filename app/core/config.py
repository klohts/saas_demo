import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    app_env: str = "production"
    app_api_key: str | None = None
    x_api_key: str | None = None
    secret_key: str | None = None
    debug: bool = False
    base_url: str | None = None
    allowed_origins: str | None = None
    ai_provider: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_api_key: str | None = None
    gmail_oauth_client_json: str | None = None
    email_sender_override: str | None = None
    database_url: str | None = None
    render_api_key: str | None = None
    render_service_id: str | None = None
    slack_webhook: str | None = None
    app_url: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()
