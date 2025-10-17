from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv


class Settings(BaseSettings):
    PROJECT_NAME: str = "Survey Theme Agent"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ROOT_PATH: str = "/"

    # Environment
    DEBUG: bool = False
    IS_PROD: bool = False

    # LLM API Keys
    OPENAI_API_KEY: str
    GOOGLE_API_KEY: str

    # Langsmith Tracing
    LANGCHAIN_TRACING_V2: bool
    LANGCHAIN_ENDPOINT: str
    LANGCHAIN_API_KEY: str
    LANGCHAIN_PROJECT: str

    # Database Configuration
    DATABASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DB_SAVE: bool = False

    # LLM MODEL
    OPENAI_MODEL: str
    GEMINI_MODEL: str


    class Config:
        env_file = ".env"


@lru_cache
def get_settings():
    load_dotenv(override=True)
    return Settings()


settings = get_settings()

