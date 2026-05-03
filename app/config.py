"""Application configuration placeholders."""

from pydantic import BaseModel


class Settings(BaseModel):
    """Runtime settings for the application."""

    app_name: str = "MonAmogus"
    debug: bool = True


settings = Settings()
