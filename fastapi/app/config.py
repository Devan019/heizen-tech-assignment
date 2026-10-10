from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "FastAPI MCP Gateway & Groq Agent"
    APP_VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = True

    # Groq LLM Configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-120b"
    GROQ_BASE_URL: Optional[str] = None
    GROQ_TEMPERATURE: float = 0.2
    GROQ_MAX_TOKENS: int = 4096
    MAX_TOOLS_PER_REQUEST: int = 20

    # Upstream MCP Server 1: Grafana
    GRAFANA_MCP_URL: str = "http://localhost:8000/mcp"
    GRAFANA_AUTH_TOKEN: str = "token"

    # Upstream MCP Server 2: Composio
    COMPOSIO_MCP_URL: str = "https://connect.composio.dev/mcp"
    COMPOSIO_API_KEY: str = "token"

    # Microsoft SQL Server Database Configuration
    SQL_SERVER_HOST: str = "DEVAN"
    SQL_SERVER_DATABASE: str = "wf"
    SQL_SERVER_DRIVER: str = "ODBC Driver 18 for SQL Server"
    SQL_SERVER_TRUSTED_CONNECTION: bool = True
    SQL_SERVER_USER: Optional[str] = None
    SQL_SERVER_PASSWORD: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
