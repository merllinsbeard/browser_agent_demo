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
    )
except ImportError:
    # SDK not installed - will be installed via dependencies
    ClaudeAgentOptions = None
    ClaudeSDKClient = None

from .definitions import get_all_agent_definitions
from ..browser.controller import BrowserController, BrowserConfig
from ..sdk_adapter import create_browser_server, get_allowed_tools


class AgentOrchestrator:
    """
    Orchestrates the 4-agent hierarchy for browser automation.

    Uses Claude Agent SDK to manage:
    - Planner agent (sonnet): Task decomposition
    - DOM Analyzer agent (haiku): Page structure analysis
    - Executor agent (sonnet): Browser interactions
    - Validator agent (haiku): Result verification

    Integrates browser tools via MCP server for full automation capability.
    """

    def __init__(
        self,
        browser: Optional[BrowserController] = None,
        browser_config: Optional[BrowserConfig] = None,
        working_dir: Optional[Path | str] = None,
        max_turns: int = 15,
        max_budget_usd: float = 10.0,
        headless: bool = False,
    ):
        """
        Initialize the agent orchestrator.

        Args:
            browser: Existing BrowserController (creates one if None)
            browser_config: Browser configuration (uses env if None)
            working_dir: Working directory for file operations
            max_turns: Maximum agent iterations before timeout (FR-030)
            max_budget_usd: Maximum spend limit in USD
            headless: Run browser in headless mode (default: False for visible)
        """
        if ClaudeAgentOptions is None:
            raise ImportError(
                "Claude Agent SDK not installed. "
                "Install with: uv add claude-agent-sdk"
            )

        # Browser configuration
        if browser is not None:
            self._browser = browser
            self._owns_browser = False
        else:
            # Create browser config with headless override
            if browser_config is None:
                browser_config = BrowserConfig.from_env()
            browser_config.headless = headless
            self._browser = BrowserController(browser_config)
            self._owns_browser = True

        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.max_turns = max_turns
        self.max_budget_usd = max_budget_usd

        self._client: Optional[ClaudeSDKClient] = None
        self._options: Optional[ClaudeAgentOptions] = None
        self._browser_server = None

    def _create_sdk_options(self) -> ClaudeAgentOptions:
        """
        Create Claude Agent SDK options with browser automation tools.

        Returns:
            Configured ClaudeAgentOptions
        """
        # Get agent definitions
        agent_definitions = get_all_agent_definitions()

        # Create browser MCP server with page getter
        def page_getter():
            return self._browser.current_page

        self._browser_server = create_browser_server(page_getter)

        # Get list of allowed browser tools
        browser_tools = get_allowed_tools()

        # Build options
        options = ClaudeAgentOptions(
            # Agent definitions (FR-026)
            agents=agent_definitions,

            # MCP servers with browser tools
            mcp_servers={"browser": self._browser_server},

            # Allowed tools: all browser tools + Task for agent delegation
            allowed_tools=["Task"] + browser_tools,

            # Model selection
            model=os.getenv("PLANNER_MODEL", "sonnet"),

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
- Extract information from pages (accessibility tree, text content)
- Handle iframes and dynamic content
- Handle multi-step tasks autonomously
- Request confirmation for destructive actions (delete, send, pay)

Your sub-agents (use Task tool to delegate):
- planner: Decomposes complex tasks into steps
- dom_analyzer: Understands page structure and finds elements
- executor: Performs browser actions (click, type, navigate)
- validator: Verifies task completion

Browser tools available (via mcp__browser__*):
- navigate, go_back, go_forward, reload
- click, type_text, scroll, hover, select_option
- list_frames, switch_to_frame, get_frame_content
- wait_for_load, wait_for_selector, wait_for_text
- get_accessibility_tree, find_interactive_elements, get_page_text
- screenshot, save_screenshot

Always:
- Start by navigating to the target URL
- Use natural language descriptions to target elements
- For iframe elements, specify the frame parameter
- Wait for page loads after navigation
- Report results clearly
- Ask before destructive actions (delete, send, purchase)
""",
        )

        return options

    async def initialize(self) -> None:
        """Initialize the orchestrator, browser, and SDK client."""
        # Initialize browser first
        if not self._browser.is_initialized:
            await self._browser.initialize()

        # Create SDK options (includes browser server)
        if self._options is None:
            self._options = self._create_sdk_options()

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
        async with ClaudeSDKClient(options=self._options) as client:
            await client.query(task)
            async for message in client.receive_response():
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

        async with ClaudeSDKClient(options=self._options) as client:
            await client.query(task)
            async for message in client.receive_response():
                yield message

    async def create_session(self) -> "ConversationSession":
        """
        Create a persistent conversation session for multi-turn interactions.

        The session maintains context between queries, allowing follow-up
        questions that reference previous interactions.

        Returns:
            ConversationSession instance

        Example:
            >>> async with await orchestrator.create_session() as session:
            ...     async for msg in session.query("Navigate to example.com"):
            ...         print(msg)
            ...     async for msg in session.query("Click the first link"):
            ...         print(msg)  # Knows we're on example.com
        """
        await self.initialize()
        return ConversationSession(self._options)

    async def close(self) -> None:
        """Close the orchestrator and release resources."""
        # Close browser if we own it
        if self._owns_browser and self._browser:
            await self._browser.close()

    async def __aenter__(self) -> "AgentOrchestrator":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


class ConversationSession:
    """
    Persistent conversation session for multi-turn browser automation.

    Maintains context between queries, allowing follow-up commands
    that reference previous interactions and browser state.
    """

    def __init__(self, options: ClaudeAgentOptions):
        """
        Initialize conversation session.

        Args:
            options: ClaudeAgentOptions with browser MCP server
        """
        self._options = options
        self._client: Optional[ClaudeSDKClient] = None

    async def __aenter__(self) -> "ConversationSession":
        """Start the conversation session."""
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End the conversation session."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    async def query(self, prompt: str):
        """
        Send a query and stream responses.

        Context from previous queries in this session is preserved.

        Args:
            prompt: Natural language task or follow-up question

        Yields:
            SDK messages as they arrive
        """
        if not self._client:
            raise RuntimeError("Session not started. Use 'async with' context manager.")

        await self._client.query(prompt)
        async for message in self._client.receive_response():
            yield message

    async def interrupt(self):
        """Interrupt the current operation."""
        if self._client:
            await self._client.interrupt()


def create_orchestrator(
    browser: Optional[BrowserController] = None,
    browser_config: Optional[BrowserConfig] = None,
    working_dir: Optional[Path | str] = None,
    max_turns: int = 15,
    max_budget_usd: float = 10.0,
    headless: bool = False,
) -> AgentOrchestrator:
    """
    Factory function to create an AgentOrchestrator.

    Args:
        browser: Existing BrowserController (creates one if None)
        browser_config: Browser configuration (uses env if None)
        working_dir: Working directory for file operations
        max_turns: Maximum agent iterations (default: 15 per FR-030)
        max_budget_usd: Maximum spend limit
        headless: Run browser in headless mode (default: False)

    Returns:
        Configured AgentOrchestrator instance

    Example:
        >>> orchestrator = create_orchestrator()
        >>> async with orchestrator:
        ...     async for msg in orchestrator.execute_task_stream("Open google.com"):
        ...         print(msg)
    """
    return AgentOrchestrator(
        browser=browser,
        browser_config=browser_config,
        working_dir=working_dir,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        headless=headless,
    )
