from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = "AI Automation Onboarding"
    ENV: str = "development"
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    DATABASE_URL: str = Field("sqlite+aiosqlite:///./data.db", env="DATABASE_URL")
    STRIPE_API_KEY: str = Field(..., env="STRIPE_API_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field("", env="STRIPE_WEBHOOK_SECRET")
    DOMAIN: str = Field("http://localhost:8000", env="DOMAIN")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    RATE_LIMIT: str = "200/hour"

    PRICE_STARTER_ID: str = Field("price_starter_test", env="PRICE_STARTER_ID")
    PRICE_PRO_ID: str = Field("price_pro_test", env="PRICE_PRO_ID")
    PRICE_AGENCY_ID: str = Field("price_agency_test", env="PRICE_AGENCY_ID")

    # THE13TH Integration
    THE13TH_URL: str = Field("https://the13th.onrender.com/api/events", env="THE13TH_URL")
    THE13TH_API_KEY: str = Field("dev-test-key", env="THE13TH_API_KEY")
    THE13TH_PROJECT_ID: str = Field("project_1234567890", env="THE13TH_PROJECT_ID")

    # ✅ Allow extra environment variables without breaking
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow"
    )

settings = Settings()
