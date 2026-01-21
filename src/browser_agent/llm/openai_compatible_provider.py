"""
OpenAI-Compatible LLM Provider

Universal provider for any API that follows the OpenAI API format.
Supports OpenRouter, local models (Ollama, LM Studio), and other OpenAI-compatible services.

Implements FR-027: OpenAI-compatible API abstraction.
"""

from typing import List, Any, Optional, AsyncIterator
import httpx
from httpx import AsyncTimeoutException

from .provider import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    Message,
    ModelTier,
)


class OpenAICompatibleProvider(LLMProvider):
    """
    OpenAI-compatible API provider.

    Works with any API that follows the OpenAI chat completion format:
    - OpenRouter (https://openrouter.ai)
    - Local models (Ollama, LM Studio)
    - Other OpenAI-compatible services
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )

    async def complete(
        self,
        messages: List[Message],
        tier: Optional[ModelTier] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a completion using OpenAI-compatible API.

        Args:
            messages: List of chat messages
            tier: Model tier to use
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated content
        """
        await self.initialize()

        model = self.get_model_for_tier(tier)

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Prepare request payload
        payload = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract content from response
            content = data["choices"][0]["message"]["content"]

            return LLMResponse(
                content=content,
                model=data.get("model", model),
                usage={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                },
                stop_reason=data["choices"][0].get("finish_reason"),
            )

        except AsyncTimeoutException:
            raise TimeoutError(f"LLM request timed out after {self.config.timeout}s")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LLM API error: {e.response.status_code} - {e.response.text}")

    async def stream_complete(
        self,
        messages: List[Message],
        tier: Optional[ModelTier] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a completion using OpenAI-compatible API.

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
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Prepare request payload
        payload = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        if data_str == "[DONE]":
                            break

                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                yield content

                        except (json.JSONDecodeError, KeyError):
                            # Skip malformed SSE data
                            continue

        except AsyncTimeoutException:
            raise TimeoutError(f"LLM request timed out after {self.config.timeout}s")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LLM API error: {e.response.status_code} - {e.response.text}")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
