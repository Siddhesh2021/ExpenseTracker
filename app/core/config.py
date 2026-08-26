from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret: str = ""
    database_url: str = "mysql+pymysql://expensebot:password@localhost:3306/expensebot"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_api_version: str = "v21.0"
    default_currency: str = "INR"
    default_timezone: str = "Asia/Kolkata"
    conversation_state_ttl_minutes: int = 30
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
