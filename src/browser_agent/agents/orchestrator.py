"""
Agent Orchestrator

Main coordination layer for the 4-agent browser automation hierarchy.
Integrates with Claude Agent SDK for agent lifecycle management.
"""

import os
from typing import Optional, Any
from pathlib import Path

try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        query,
    )
except ImportError:
    # SDK not installed - will be installed via dependencies
    ClaudeAgentOptions = None
    ClaudeSDKClient = None
    query = None

from .definitions import get_all_agent_definitions
from ..llm import LLMProvider, create_provider_from_env


class AgentOrchestrator:
    """
    Orchestrates the 4-agent hierarchy for browser automation.

    Uses Claude Agent SDK to manage:
    - Planner agent (sonnet): Task decomposition
    - DOM Analyzer agent (haiku): Page structure analysis
    - Executor agent (sonnet): Browser interactions
    - Validator agent (haiku): Result verification

    Integrates with custom LLM provider abstraction for flexibility.
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        working_dir: Optional[Path | str] = None,
        max_turns: int = 15,
        max_budget_usd: float = 10.0,
    ):
        """
        Initialize the agent orchestrator.

        Args:
            llm_provider: Custom LLM provider (uses env if None)
            working_dir: Working directory for file operations
            max_turns: Maximum agent iterations before timeout (FR-030)
            max_budget_usd: Maximum spend limit in USD
        """
        if ClaudeAgentOptions is None:
            raise ImportError(
                "Claude Agent SDK not installed. "
                "Install with: uv add claude-agent-sdk"
            )

        self.llm_provider = llm_provider or create_provider_from_env()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.max_turns = max_turns
        self.max_budget_usd = max_budget_usd

        self._client: Optional[ClaudeSDKClient] = None
        self._options: Optional[ClaudeAgentOptions] = None

    def _create_sdk_options(self) -> ClaudeAgentOptions:
        """
        Create Claude Agent SDK options with browser automation tools.

        Returns:
            Configured ClaudeAgentOptions
        """
        # Get agent definitions
        agent_definitions = get_all_agent_definitions()

        # Build options
        options = ClaudeAgentOptions(
            # Agent definitions (FR-026)
            agents=agent_definitions,

            # Model selection
            model=os.getenv("PLANNER_MODEL", "claude-sonnet-4-20250514"),

            # Execution limits
            max_turns=self.max_turns,
            max_budget_usd=self.max_budget_usd,

            # Working directory
            cwd=self.working_dir,

            # System prompt for main agent
            system_prompt="""You are a Browser Automation Agent with hierarchical sub-agents.

Your capabilities:
- Navigate to websites and interact with pages
- Click elements, type text, scroll pages
- Extract information from pages
- Handle multi-step tasks autonomously
- Request confirmation for destructive actions

Your sub-agents:
- Planner: Decomposes tasks into steps
- DOM Analyzer: Understands page structure
- Executor: Performs browser actions
- Validator: Verifies results

Always:
- Show your actions in [ACTION] blocks
- Explain reasoning in [THOUGHT] blocks
- Report results in [RESULT] blocks
- Ask before deleting, sending, or purchasing
- Stop after 15 iterations if stuck
""",

            # Tools will be added in browser module
            tools=[],
            allowed_tools=[],
        )

        return options

    async def initialize(self) -> None:
        """Initialize the orchestrator and SDK client."""
        if self._options is None:
            self._options = self._create_sdk_options()

        # Initialize LLM provider
        await self.llm_provider.initialize()

    async def execute_task(
        self,
        task: str,
    ) -> list[Any]:
        """
        Execute a browser automation task and collect all results.

        Args:
            task: Natural language task description

        Returns:
            List of task execution messages
        """
        await self.initialize()

        results = []
        async for message in query(prompt=task, options=self._options):
            results.append(message)
        return results

    async def execute_task_stream(
        self,
        task: str,
    ):
        """
        Execute a browser automation task with streaming.

        Args:
            task: Natural language task description

        Yields:
            Task execution messages as they arrive
        """
        await self.initialize()

        async for message in query(prompt=task, options=self._options):
            yield message

    async def close(self) -> None:
        """Close the orchestrator and release resources."""
        if self._client:
            await self._client.close()
            self._client = None

        await self.llm_provider.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


def create_orchestrator(
    llm_provider: Optional[LLMProvider] = None,
    working_dir: Optional[Path | str] = None,
    max_turns: int = 15,
    max_budget_usd: float = 10.0,
) -> AgentOrchestrator:
    """
    Factory function to create an AgentOrchestrator.

    Args:
        llm_provider: Custom LLM provider (uses env if None)
        working_dir: Working directory for file operations
        max_turns: Maximum agent iterations (default: 15 per FR-030)
        max_budget_usd: Maximum spend limit

    Returns:
        Configured AgentOrchestrator instance

    Example:
        >>> orchestrator = create_orchestrator()
        >>> async with orchestrator:
        ...     async for msg in orchestrator.execute_task("Open google.com"):
        ...         print(msg)
    """
    return AgentOrchestrator(
        llm_provider=llm_provider,
        working_dir=working_dir,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
    )
