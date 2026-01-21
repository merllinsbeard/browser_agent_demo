"""
LLM Provider Abstraction

Supports multiple LLM providers through a unified interface:
- Anthropic Claude (native)
- OpenAI-compatible APIs (OpenRouter, local models, etc.)

Architecture follows FR-027 for provider abstraction and FR-025 for Claude Agent SDK integration.
"""

from .provider import LLMProvider, LLMConfig, ModelTier, Message, LLMResponse
from .anthropic_provider import AnthropicProvider
from .openai_compatible_provider import OpenAICompatibleProvider
from .factory import create_provider_from_env, create_provider

__all__ = [
    "LLMProvider",
    "LLMConfig",
    "ModelTier",
    "Message",
    "LLMResponse",
    "AnthropicProvider",
    "OpenAICompatibleProvider",
    "create_provider_from_env",
    "create_provider",
]
