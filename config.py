from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Merchant Growth & Shopping Agent"
    debug: bool = False
    database_url: str = "mysql+pymysql://user:password@localhost/merchant_agent"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    llm_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
