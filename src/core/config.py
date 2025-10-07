from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv_list(value: Optional[str], default: List[str]) -> List[str]:
    """Return a cleaned list parsed from a comma-separated string."""
    if not value:
        return default
    return [raw_item.strip() for raw_item in value.split(",") if raw_item.strip()]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_env: str = "dev"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    redis_url: str = "redis://localhost:6379/0"

    # Safety
    moderation_enabled: bool = True
    tool_allowlist_raw: Optional[str] = Field(default=None, alias="TOOL_ALLOWLIST")
    rate_limit_chat_per_min: int = 30
    rate_limit_tool_per_min: int = 10

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: Optional[str] = Field(default=None, alias="OPENAI_MODEL")

    # LangSmith (for tracing and observability)
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: Optional[str] = Field(default=None, alias="LANGSMITH_PROJECT")
    langsmith_tracing: bool = Field(default=True, alias="LANGSMITH_TRACING")
    langsmith_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        alias="LANGSMITH_ENDPOINT"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )

    @property
    def tool_allowlist(self) -> List[str]:
        """Parsed tool allowlist."""
        return _csv_list(self.tool_allowlist_raw, [])


settings = Settings()
