import uuid
from pydantic import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""    # The OpenAI API key
    DRY_RUN: bool = True        # If true, don't send to the OpenAI API
    SYSTEM_PROMPT: str = ""     # the system role prompt part to prime GPT in the right direction.
    SESSION_UUID: uuid.UUID = uuid.uuid4()  # the "End-user ID" field for the OpenAI API

    class Config:
        env_file = '.env'       # in the docker container, if the .env file is present, take it.
                                # overwrite the .env settings via real ENV variables of course.
