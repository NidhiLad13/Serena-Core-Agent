# app/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str
    MONGODB_URI: str
    REDIS_URI: str
    
    # MongoDB Database name
    DEEPGRAM_API_KEY: str
    MONGODB_DB_NAME: str = "serena"

    class Config:
        env_file = ".env"

settings = Settings()