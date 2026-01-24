"""
LLM Provider Factory

Factory function for creating LLM provider instances based on configuration.
Simplifies provider instantiation and configuration management.
"""

import os
from typing import Optional
from dotenv import load_dotenv

from .provider import LLMConfig, LLMProvider, ModelTier
from .anthropic_provider import AnthropicProvider
from .openai_compatible_provider import OpenAICompatibleProvider

# Load environment variables (override shell env with .env values)
load_dotenv(override=True)


def create_provider_from_env() -> LLMProvider:
    """
    Create an LLM provider instance from environment variables.

    Reads configuration from .env file:
    - ANTHROPIC_API_KEY: Anthropic API key (for AnthropicProvider)
    - OPENAI_API_BASE + OPENAI_API_KEY: OpenAI-compatible endpoint (for OpenAICompatibleProvider)
    - PLANNER_MODEL, DOM_ANALYZER_MODEL, etc.: Model tier mappings

    Returns:
        Configured LLM provider instance

    Example:
        >>> provider = create_provider_from_env()
        >>> response = await provider.complete(messages)
    """
    # Check for OpenAI-compatible provider first
    base_url = os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY")

    if base_url and api_key:
        # Use OpenAI-compatible provider
        config = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            provider_type="openai-compatible",
            model=os.getenv("PLANNER_MODEL", "claude-sonnet-4-20250514"),
            tier_models={
                ModelTier.SONNET: os.getenv("PLANNER_MODEL", "claude-sonnet-4-20250514"),
                ModelTier.HAIKU: os.getenv("DOM_ANALYZER_MODEL", "claude-haiku-4-20250514"),
                ModelTier.OPUS: os.getenv("VALIDATOR_MODEL", "claude-opus-4-20250514"),
            },
        )
        return OpenAICompatibleProvider(config)

    # Fall back to Anthropic provider
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "No LLM provider configured. Set either:\n"
            "  - ANTHROPIC_API_KEY for Anthropic Claude\n"
            "  - OPENAI_API_BASE + OPENAI_API_KEY for OpenAI-compatible provider"
        )

    config = LLMConfig(
        api_key=api_key,
        base_url=os.getenv("ANTHROPIC_BASE_URL"),  # Optional, for proxy
        provider_type="anthropic",
        model=os.getenv("PLANNER_MODEL", "claude-sonnet-4-20250514"),
        tier_models={
            ModelTier.SONNET: os.getenv("PLANNER_MODEL", "claude-sonnet-4-20250514"),
            ModelTier.HAIKU: os.getenv("DOM_ANALYZER_MODEL", "claude-haiku-4-20250514"),
            ModelTier.OPUS: os.getenv("VALIDATOR_MODEL", "claude-opus-4-20250514"),
        },
    )

    return AnthropicProvider(config)


def create_provider(
    provider_type: str = "anthropic",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
    tier_models: Optional[dict[ModelTier, str]] = None,
    **kwargs,
) -> LLMProvider:
    """
    Create an LLM provider with explicit configuration.

    Args:
        provider_type: "anthropic" or "openai-compatible"
        api_key: API key for the provider
        base_url: Base URL (optional, for proxy or OpenAI-compatible endpoint)
        model: Default model name
        tier_models: Mapping of ModelTier to model names
        **kwargs: Additional LLMConfig parameters

    Returns:
        Configured LLM provider instance

    Example:
        >>> provider = create_provider(
        ...     provider_type="anthropic",
        ...     api_key="sk-ant-...",
        ...     model="claude-sonnet-4-20250514"
        ... )
    """
    if tier_models is None:
        tier_models = {
            ModelTier.SONNET: model,
            ModelTier.HAIKU: "claude-haiku-4-20250514",
            ModelTier.OPUS: "claude-opus-4-20250514",
        }

    config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        tier_models=tier_models,
        provider_type=provider_type,
        **kwargs,
    )

    if provider_type == "openai-compatible":
        return OpenAICompatibleProvider(config)
    else:
        return AnthropicProvider(config)
