"""
Anthropic Claude LLM Provider

Native implementation for Anthropic's Claude API.
Uses the Anthropic Python SDK for optimal integration.
"""

from typing import List, Any, Optional, AsyncIterator
from anthropic import AsyncAnthropic, AsyncStream
from anthropic.types import Message as AnthropicMessage

from .provider import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    Message,
    ModelTier,
)


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude API provider.

    Provides native integration with Anthropic's Claude models
    using the official Anthropic Python SDK.
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[AsyncAnthropic] = None

    async def initialize(self) -> None:
        """Initialize the Anthropic async client."""
        if self._client is None:
            self._client = AsyncAnthropic(
                api_key=self.config.api_key,
                base_url=self.config.base_url,  # Can override for proxy
                timeout=self.config.timeout,
            )

    async def complete(
        self,
        messages: List[Message],
        tier: Optional[ModelTier] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a completion using Anthropic's API.

        Args:
            messages: List of chat messages
            tier: Model tier to use (sonnet/haiku/opus)
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            LLMResponse with generated content
        """
        await self.initialize()

        model = self.get_model_for_tier(tier)

        # Convert messages to Anthropic format
        # Anthropic requires messages to alternate user/assistant
        # System messages should be passed separately
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                anthropic_messages.append(
                    {"role": msg.role, "content": msg.content}
                )

        # Prepare parameters
        params = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        if system_message:
            params["system"] = system_message

        # Make the API call
        response: AnthropicMessage = await self._client.messages.create(**params)

        # Extract the content
        content = response.content[0].text if response.content else ""

        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            stop_reason=response.stop_reason,
        )

    async def stream_complete(
        self,
        messages: List[Message],
        tier: Optional[ModelTier] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a completion using Anthropic's API.

        Yields chunks of text as they arrive.

        Args:
            messages: List of chat messages
            tier: Model tier to use
            **kwargs: Additional parameters

        Yields:
            Text chunks as they arrive
        """
        await self.initialize()

        model = self.get_model_for_tier(tier)

        # Convert messages
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                anthropic_messages.append(
                    {"role": msg.role, "content": msg.content}
                )

        # Prepare parameters
        params = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        if system_message:
            params["system"] = system_message

        # Stream the response
        stream: AsyncStream = await self._client.messages.create(**params, stream=True)

        async for event in stream:
            if event.type == "content_block_delta":
                yield event.delta.text
            elif event.type == "message_stop":
                break

    async def close(self) -> None:
        """Close the Anthropic client."""
        if self._client:
            await self._client.close()
            self._client = None
