"""
Planner Agent with ReAct Loop

Implements the core reasoning-action cycle for browser automation.
The planner coordinates task execution through:
1. THOUGHT: Reason about current state and next action
2. ACTION: Execute browser tool
3. OBSERVATION: Process result and update state
4. Repeat until task complete or max iterations

Following FR-014 (natural language tasks) and FR-015 (action sequence determination).
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Awaitable
from datetime import datetime

from ..tui import (
    print_thought,
    print_tool_call,
    print_result,
    print_error,
    action_spinner,
    get_console,
)
from ..tools import get_all_tools, get_tool_schemas, ToolResult


@dataclass
class PlannerState:
    """
    Current state of the planner's execution.

    Tracks task progress, history, and context for the ReAct loop.
    """

    task: str
    iteration: int = 0
    max_iterations: int = 15
    history: list[dict[str, Any]] = field(default_factory=list)
    completed: bool = False
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_thought(self, thought: str) -> None:
        """Record a thought step."""
        self.history.append({
            "type": "thought",
            "content": thought,
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
        })

    def add_action(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Record an action step."""
        self.history.append({
            "type": "action",
            "tool": tool_name,
            "arguments": arguments,
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
        })

    def add_observation(self, result: ToolResult) -> None:
        """Record an observation from tool execution."""
        self.history.append({
            "type": "observation",
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
        })

    def get_context_window(self, window_size: int = 5) -> list[dict[str, Any]]:
        """
        Get recent history for context window (FR-018).

        Args:
            window_size: Number of recent entries to include

        Returns:
            Recent history entries
        """
        return self.history[-window_size * 3:]  # 3 entries per iteration


@dataclass
class PlannerConfig:
    """Configuration for the Planner agent."""

    max_iterations: int = 15  # FR-030
    thinking_enabled: bool = True
    verbose: bool = True


class ReActPlanner:
    """
    Planner agent implementing the ReAct loop pattern.

    The planner coordinates browser automation through a cycle of:
    - Thought: LLM reasons about current state and plans action
    - Action: Tool is selected and executed
    - Observation: Result is processed and state updated

    Uses the TUI system for displaying progress to the user.
    """

    def __init__(
        self,
        llm_complete: Callable[[str, list[dict]], Awaitable[dict[str, Any]]],
        config: Optional[PlannerConfig] = None,
    ):
        """
        Initialize the ReAct planner.

        Args:
            llm_complete: Async function to call LLM for completions.
                         Signature: (prompt, tools) -> response
            config: Planner configuration
        """
        self.llm_complete = llm_complete
        self.config = config or PlannerConfig()
        self.console = get_console()

        # Get available tools
        self._tools = get_all_tools()
        self._tool_schemas = get_tool_schemas()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the planner."""
        return """You are a Browser Automation Agent implementing a ReAct loop.

For each step, you MUST:
1. THINK: Analyze the current state and decide what to do next
2. ACT: Call exactly ONE tool to perform an action
3. OBSERVE: Wait for the result before continuing

Output format:
- First, provide your reasoning in a <thought> block
- Then, call a single tool with the appropriate arguments
- Wait for the observation before the next iteration

Key principles:
- Always analyze the page state before acting
- Use natural language descriptions for elements
- Request confirmation for destructive actions (delete, send, purchase)
- Adapt if the page changes unexpectedly
- Report task completion or inability to complete

Available interaction patterns:
- Navigate: Use 'navigate' to go to URLs
- Click: Use 'click' with natural language element description
- Type: Use 'type_text' to enter text in fields
- Scroll: Use 'scroll' to navigate the page
- Wait: Use wait tools for dynamic content
- Read: Use accessibility tools to understand page structure

Stop when:
- Task is completed successfully
- You need user confirmation
- You've hit max iterations
- An unrecoverable error occurs"""

    def _build_user_prompt(self, state: PlannerState, page_state: dict) -> str:
        """
        Build the user prompt for current iteration.

        Args:
            state: Current planner state
            page_state: Current browser page state

        Returns:
            Formatted prompt for LLM
        """
        prompt_parts = [
            f"## Task\n{state.task}",
            f"\n## Iteration\n{state.iteration + 1} of {state.max_iterations}",
            f"\n## Current Page State\nURL: {page_state.get('url', 'unknown')}",
            f"Title: {page_state.get('title', 'unknown')}",
        ]

        # Add page content summary if available
        if page_state.get("text_summary"):
            prompt_parts.append(f"\n## Page Summary\n{page_state['text_summary'][:1000]}")

        # Add interactive elements if available
        if page_state.get("interactive_elements"):
            elements = page_state["interactive_elements"][:20]  # Limit for context
            element_list = "\n".join([
                f"- {e.get('role', 'element')}: {e.get('name', 'unnamed')}"
                for e in elements
            ])
            prompt_parts.append(f"\n## Interactive Elements\n{element_list}")

        # Add recent history for context
        context = state.get_context_window()
        if context:
            history_text = []
            for entry in context:
                if entry["type"] == "thought":
                    history_text.append(f"[Thought] {entry['content'][:200]}")
                elif entry["type"] == "action":
                    history_text.append(f"[Action] {entry['tool']}({entry['arguments']})")
                elif entry["type"] == "observation":
                    status = "✓" if entry["success"] else "✗"
                    history_text.append(f"[Observation] {status} {entry.get('data', entry.get('error', ''))}")

            prompt_parts.append("\n## Recent History\n" + "\n".join(history_text[-6:]))

        prompt_parts.append("\n## Instructions\nAnalyze the current state and decide your next action. Provide your reasoning in <thought> tags, then call the appropriate tool.")

        return "\n".join(prompt_parts)

    async def execute(
        self,
        task: str,
        page: Any,  # Playwright Page
        get_page_state: Callable[[], Awaitable[dict]],
        execute_tool: Callable[[str, dict], Awaitable[ToolResult]],
    ) -> PlannerState:
        """
        Execute the ReAct loop for a task.

        Args:
            task: Natural language task description
            page: Playwright page instance
            get_page_state: Async function to get current page state
            execute_tool: Async function to execute a tool

        Returns:
            Final PlannerState with execution history
        """
        state = PlannerState(
            task=task,
            max_iterations=self.config.max_iterations,
            start_time=datetime.now(),
        )

        if self.config.verbose:
            print_thought(
                f"Starting task: {task}\nMax iterations: {state.max_iterations}",
                title="[PLANNER INIT]",
            )

        while state.iteration < state.max_iterations and not state.completed:
            state.iteration += 1

            try:
                # Get current page state
                page_state = await get_page_state()

                # Build prompts
                system_prompt = self._build_system_prompt()
                user_prompt = self._build_user_prompt(state, page_state)

                # Get LLM response with tool schemas
                with action_spinner("Thinking..."):
                    response = await self.llm_complete(
                        f"{system_prompt}\n\n{user_prompt}",
                        self._tool_schemas,
                    )

                # Process response
                await self._process_response(response, state, execute_tool)

            except Exception as e:
                state.error = str(e)
                if self.config.verbose:
                    print_error(
                        f"Iteration {state.iteration} failed: {e}",
                        error_type="PlannerError",
                    )
                # Continue trying unless it's critical
                if "CRITICAL" in str(e).upper():
                    break

        state.end_time = datetime.now()

        # Final status
        if self.config.verbose:
            if state.completed:
                print_result(
                    f"Task completed in {state.iteration} iterations",
                    success=True,
                )
            elif state.iteration >= state.max_iterations:
                print_error(
                    f"Max iterations ({state.max_iterations}) reached",
                    error_type="IterationLimit",
                    suggestion="Task may be too complex. Consider breaking it down.",
                )

        return state

    async def _process_response(
        self,
        response: dict[str, Any],
        state: PlannerState,
        execute_tool: Callable[[str, dict], Awaitable[ToolResult]],
    ) -> None:
        """
        Process LLM response and execute any tool calls.

        Args:
            response: LLM response with content and tool calls
            state: Current planner state
            execute_tool: Function to execute tools
        """
        # Extract thought from response
        content = response.get("content", "")
        if isinstance(content, list):
            # Handle Claude-style content blocks
            for block in content:
                if block.get("type") == "text":
                    thought = block.get("text", "")
                    if thought:
                        state.add_thought(thought)
                        if self.config.verbose:
                            # Check for <thought> tags
                            if "<thought>" in thought:
                                start = thought.find("<thought>") + 9
                                end = thought.find("</thought>")
                                if end > start:
                                    thought = thought[start:end].strip()
                            print_thought(thought, step=state.iteration)
        elif isinstance(content, str) and content:
            state.add_thought(content)
            if self.config.verbose:
                print_thought(content, step=state.iteration)

        # Check for tool use
        tool_use = response.get("tool_use") or response.get("tool_calls", [])
        if not tool_use:
            # No tool call - check if task is complete
            if any(word in content.lower() for word in ["complete", "done", "finished", "success"]):
                state.completed = True
            return

        # Handle tool calls
        if isinstance(tool_use, list):
            for tool_call in tool_use:
                await self._execute_tool_call(tool_call, state, execute_tool)
        else:
            await self._execute_tool_call(tool_use, state, execute_tool)

    async def _execute_tool_call(
        self,
        tool_call: dict[str, Any],
        state: PlannerState,
        execute_tool: Callable[[str, dict], Awaitable[ToolResult]],
    ) -> None:
        """
        Execute a single tool call.

        Args:
            tool_call: Tool call specification
            state: Current planner state
            execute_tool: Function to execute tools
        """
        tool_name = tool_call.get("name") or tool_call.get("function", {}).get("name")
        arguments = tool_call.get("input") or tool_call.get("arguments", {})

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        if not tool_name:
            return

        # Record action
        state.add_action(tool_name, arguments)

        if self.config.verbose:
            print_tool_call(tool_name, arguments)

        # Execute tool
        with action_spinner(f"Executing {tool_name}..."):
            result = await execute_tool(tool_name, arguments)

        # Record observation
        state.add_observation(result)

        if self.config.verbose:
            if result.success:
                data_str = str(result.data)[:200] if result.data else "OK"
                print_result(data_str, success=True)
            else:
                print_error(result.error or "Unknown error", error_type="ToolError")


def create_planner(
    llm_complete: Callable[[str, list[dict]], Awaitable[dict[str, Any]]],
    max_iterations: int = 15,
    verbose: bool = True,
) -> ReActPlanner:
    """
    Factory function to create a ReAct planner.

    Args:
        llm_complete: Async function for LLM completions
        max_iterations: Maximum iterations before timeout
        verbose: Whether to print progress to console

    Returns:
        Configured ReActPlanner instance
    """
    config = PlannerConfig(
        max_iterations=max_iterations,
        verbose=verbose,
    )
    return ReActPlanner(llm_complete, config)
