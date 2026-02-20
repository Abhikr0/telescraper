import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str
    API_ID: Optional[int] = None
    API_HASH: Optional[str] = None
    SUPABASE_URL: str
    SUPABASE_KEY: str
    STORAGE_CHANNEL_ID: int
    ADMIN_IDS: str
    ENVIRONMENT: str = "local"

    @field_validator("STORAGE_CHANNEL_ID", mode="before")
    @classmethod
    def parse_storage_channel_id(cls, v):
        if isinstance(v, str) and "," in v:
            v = v.split(",")[0].strip()
        return v

    @field_validator("API_ID", mode="before")
    @classmethod
    def parse_api_id(cls, v):
        if v == "" or v is None:
            return None
        return int(v)

    @field_validator("API_HASH", mode="before")
    @classmethod
    def parse_api_hash(cls, v):
        if v == "" or v is None:
            return None
        return v

    @property
    def admin_list(self) -> list[int]:
        return [int(id_.strip()) for id_ in self.ADMIN_IDS.split(",") if id_.strip()]

    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

settings = Settings()
