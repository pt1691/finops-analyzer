"""Configuration management with Pydantic Settings."""

from enum import Enum
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIProvider(str, Enum):
    """Supported AI providers for sentiment analysis."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="FINOPS_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AI Configuration
    ai_provider: AIProvider = Field(default=AIProvider.OPENAI, description="AI provider for sentiment analysis")
    openai_api_key: SecretStr | None = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    anthropic_api_key: SecretStr | None = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-haiku-20240307", description="Anthropic model to use")

    # News API
    newsapi_key: SecretStr | None = Field(default=None, description="NewsAPI.org API key (optional)")

    # Analysis Configuration
    analysis_period_days: int = Field(default=30, description="Default analysis period in days")
    sentiment_news_count: int = Field(default=5, description="Number of news articles to analyze per stock")

    # Cache Configuration
    cache_enabled: bool = Field(default=True, description="Enable caching of API responses")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds (1 hour default)")
    cache_dir: Path = Field(default=Path.home() / ".finops-analyzer" / "cache", description="Cache directory")

    def get_active_api_key(self) -> SecretStr | None:
        """Get the API key for the active AI provider."""
        if self.ai_provider == AIProvider.OPENAI:
            return self.openai_api_key
        return self.anthropic_api_key

    def get_active_model(self) -> str:
        """Get the model name for the active AI provider."""
        if self.ai_provider == AIProvider.OPENAI:
            return self.openai_model
        return self.anthropic_model


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
