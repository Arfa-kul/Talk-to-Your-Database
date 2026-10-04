"""Application configuration loaded from environment variables / .env file."""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    anthropic_api_key: str = ""
    vanna_model: str = "claude-3-5-sonnet-20241022"

    # Database
    db_type: str = "sqlite"  # "sqlite" | "postgres"
    sqlite_db_path: str = "./data/chinook.db"

    # Postgres (only used when db_type == "postgres")
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "chinook"
    postgres_user: str = "postgres"
    postgres_password: str = ""

    # ChromaDB
    chroma_path: str = "./data/chroma_store"

    # Safety
    query_timeout_seconds: int = 30
    max_rows: int = 1000

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def db_url(self) -> str:
        if self.db_type == "postgres":
            return (
                f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        # SQLite – use the read-only URI flag for safety
        db_path = Path(self.sqlite_db_path).resolve()
        return f"sqlite:///file:{db_path}?mode=ro&uri=true"

    @property
    def db_url_writable(self) -> str:
        """Used only during DB bootstrap (download + initial setup)."""
        if self.db_type == "postgres":
            return self.db_url.replace("+psycopg2", "+psycopg2")
        db_path = Path(self.sqlite_db_path).resolve()
        return f"sqlite:///{db_path}"


settings = Settings()
