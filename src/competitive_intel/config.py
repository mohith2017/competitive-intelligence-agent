from __future__ import annotations

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import CATEGORIES, Category

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic



load_dotenv()

Provider = Literal["anthropic", "openai"]


class Settings(BaseSettings):
    """Runtime configuration, populated from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True
    )

    tavily_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    logfire_token: str | None = None
    logfire_console: bool = False

    provider: Provider = Field(
        default="anthropic",
        validation_alias=AliasChoices("CI_MODEL_PROVIDER", "provider"),
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-5",
        validation_alias=AliasChoices("CI_ANTHROPIC_MODEL", "anthropic_model"),
    )
    openai_model: str = Field(
        default="gpt-5.5",
        validation_alias=AliasChoices("CI_OPENAI_MODEL", "openai_model"),
    )
    temperature: float = 0.0

    default_recency_window: str = "month"
    results_per_query: int = 5
    extract_top_n: int = 3
    top_k_per_category: int = 4
    passage_char_cap: int = 1200
    rrf_k: int = 60
    min_fused_score: float = 0.02
    max_retrieval_workers: int = 8

    @property
    def default_categories(self) -> list[Category]:
        return list(CATEGORIES)

    def resolve_provider(self) -> Provider:
        """Pick a provider that actually has a key, preferring the configured one."""
        if self.provider == "anthropic" and self.anthropic_api_key:
            return "anthropic"
        if self.provider == "openai" and self.openai_api_key:
            return "openai"
        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        raise RuntimeError(
            "No model provider key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    def model_name(self, provider: Provider) -> str:
        return self.anthropic_model if provider == "anthropic" else self.openai_model


@lru_cache
def get_settings() -> Settings:
    return Settings()


def build_model(settings: Settings | None = None, provider: Provider | None = None):
    """Construct a LangChain chat model (Claude primary, OpenAI fallback)."""
    settings = settings or get_settings()
    provider = provider or settings.resolve_provider()

    if provider == "anthropic":
        return ChatAnthropic(
            model=settings.anthropic_model,
            temperature=settings.temperature,
            api_key=settings.anthropic_api_key,
            timeout=60,
            max_retries=2,
        )


    return ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.temperature,
        api_key=settings.openai_api_key,
        timeout=60,
        max_retries=2,
    )
