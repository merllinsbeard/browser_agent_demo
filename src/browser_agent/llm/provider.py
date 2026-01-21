"""
Base LLM Provider Interface and Configuration

Defines the abstraction layer for LLM providers following FR-027.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pydantic import BaseModel


class ModelTier(str, Enum):
    """
    Model tier classification for agent hierarchy (FR-026).

    Tiers determine which model to use for different agent types:
    - sonnet: High-quality reasoning for Planner and Executor agents
    - haiku: Fast, lightweight for DOM Analyzer and Validator agents
    - opus: Maximum quality (if needed for complex tasks)
    """

    SONNET = "sonnet"
    HAIKU = "haiku"
    OPUS = "opus"


@dataclass
class LLMConfig:
    """
    Configuration for LLM provider connection.

    Supports both Anthropic native and OpenAI-compatible APIs.
    """

    # API configuration
    api_key: str
    base_url: Optional[str] = None  # None for Anthropic native, URL for OpenAI-compatible
    model: str = "claude-sonnet-4-20250514"

    # Model tier mapping (FR-026)
    tier_models: Dict[ModelTier, str] = field(default_factory=lambda: {
        ModelTier.SONNET: "claude-sonnet-4-20250514",
        ModelTier.HAIKU: "claude-haiku-4-20250514",
        ModelTier.OPUS: "claude-opus-4-20250514",
    })

    # Request parameters
    max_tokens: int = 8192
    temperature: float = 0.7
    timeout: int = 60

    # Provider type
    provider_type: str = "anthropic"  # "anthropic" or "openai-compatible"

    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Get the model name for a given tier."""
        return self.tier_models.get(tier, self.model)


class Message(BaseModel):
    """Chat message representation."""

    role: str  # "user", "assistant", "system"
    content: str


class LLMResponse(BaseModel):
    """Response from LLM provider."""

    content: str
    model: str
    usage: Dict[str, int] = {}
    stop_reason: Optional[str] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Implements FR-027: OpenAI-compatible API abstraction.
    All providers must implement this interface.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider client."""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tier: Optional[ModelTier] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a completion for the given messages.

        Args:
            messages: List of chat messages
            tier: Model tier to use (overrides config.model)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated content and metadata
        """
        pass

    @abstractmethod
    async def stream_complete(
        self,
        messages: List[Message],
        tier: Optional[ModelTier] = None,
        **kwargs: Any,
    ):
        """
        Stream a completion for the given messages.

        Args:
            messages: List of chat messages
            tier: Model tier to use
            **kwargs: Additional provider-specific parameters

        Yields:
            Chunks of the response as they arrive
        """
        pass

    def get_model_for_tier(self, tier: Optional[ModelTier]) -> str:
        """Get the appropriate model for the given tier."""
        if tier is None:
            return self.config.model
        return self.config.get_model_for_tier(tier)

    async def close(self) -> None:
        """Close the provider connection."""
        if self._client:
            await self._client.close()
            self._client = None
