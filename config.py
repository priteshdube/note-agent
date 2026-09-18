from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    transcription_provider: str = "groq"
    notegen_provider: str = "groq"
    groq_api_key: str
    gemini_api_key: str
    notion_token: str
    notion_root_page_id: str
    api_key: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()