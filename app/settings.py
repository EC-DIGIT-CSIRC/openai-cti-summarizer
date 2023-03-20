from pydantic import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = None # To check if supplied
    DRY_RUN: bool = True

    class Config:
        env_file = '.env'
