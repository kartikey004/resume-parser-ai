import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    OPENAI_API_KEY: str = ""
    UPLOADS_DIR: str = "/app/uploads" # Directory for storing uploads

    class Config:
        env_file = ".env"

settings = Settings()

