"""Application configuration."""

import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "MonAmogus"
    debug: bool = True
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://monamogus_user:monamogus_password@localhost:5432/monamogus_db",
    )


settings = Settings()