"""
Executor Sub-Agent

Browser interaction executor using the sonnet model tier.
Performs precise browser actions based on planner instructions.
Handles element interactions, navigation, and form operations.

Following FR-007 (click), FR-008 (type), FR-009 (scroll), FR-010 (wait).
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Awaitable
from datetime import datetime

from ..tui import print_action, print_result, print_error, action_spinner
from ..tools import ToolResult


@dataclass
class ExecutionResult:
    """
    Result of a single action execution.

    Tracks the action performed, its result, and any side effects.
    """

    action: str
    tool_name: str
    arguments: dict[str, Any]
    success: bool
    result_data: Any = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    side_effects: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionContext:
    """
    Context for action execution.

    Provides state information needed for intelligent execution.
    """

    current_url: str
    page_title: str
    previous_action: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class BrowserExecutor:
    """
    Executor sub-agent for browser interactions.

    Uses the sonnet model tier for precise, reliable execution.
    Handles the actual browser operations with error recovery
    and intelligent retry logic.
    """

    def __init__(
        self,
        execute_tool: Callable[[str, dict[str, Any]], Awaitable[ToolResult]],
        verbose: bool = True,
    ):
        """
        Initialize the executor.

        Args:
            execute_tool: Async function to execute browser tools
            verbose: Whether to print progress
        """
        self.execute_tool = execute_tool
        self.verbose = verbose
        self.history: list[ExecutionResult] = []

    async def execute(
        self,
        action: str,
        tool_name: str,
        arguments: dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """
        Execute a browser action.

        Args:
            action: Human-readable action description
            tool_name: Tool to execute
            arguments: Tool arguments
            context: Execution context

        Returns:
            ExecutionResult with outcome
        """
        context = context or ExecutionContext(current_url="unknown", page_title="unknown")

        if self.verbose:
            print_action(action, params=arguments)

        start_time = datetime.now()

        try:
            # Execute with retry logic
            result = await self._execute_with_retry(
                tool_name, arguments, context
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            execution_result = ExecutionResult(
                action=action,
                tool_name=tool_name,
                arguments=arguments,
                success=result.success,
                result_data=result.data,
                error=result.error,
                duration_ms=duration_ms,
                side_effects=self._detect_side_effects(result),
            )

            self.history.append(execution_result)

            if self.verbose:
                if result.success:
                    data_str = str(result.data)[:150] if result.data else "OK"
                    print_result(
                        f"{action}\n{data_str}",
                        success=True,
                        title="[EXECUTION SUCCESS]",
                    )
                else:
                    print_error(
                        f"{action} failed: {result.error}",
                        error_type="ExecutionError",
                    )

            return execution_result

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            execution_result = ExecutionResult(
                action=action,
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

            self.history.append(execution_result)

            if self.verbose:
                print_error(f"{action}: {e}", error_type="Exception")

            return execution_result

    async def _execute_with_retry(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """
        Execute tool with retry logic for transient failures.

        Args:
            tool_name: Tool to execute
            arguments: Tool arguments
            context: Execution context

        Returns:
            ToolResult from execution
        """
        last_error = None

        for attempt in range(context.max_retries):
            if attempt > 0 and self.verbose:
                with action_spinner(f"Retry {attempt}/{context.max_retries}..."):
                    result = await self.execute_tool(tool_name, arguments)
            else:
                with action_spinner(f"Executing {tool_name}..."):
                    result = await self.execute_tool(tool_name, arguments)

            if result.success:
                return result

            last_error = result.error

            # Check if error is retryable
            if not self._is_retryable_error(result.error):
                break

        # Return last result (failure)
        return ToolResult(success=False, error=last_error)

    def _is_retryable_error(self, error: Optional[str]) -> bool:
        """Check if an error is worth retrying."""
        if not error:
            return False

        error_lower = error.lower()
        retryable_patterns = [
            "timeout",
            "network",
            "connection",
            "loading",
            "not visible",
            "not stable",
            "detached",
        ]
        return any(pattern in error_lower for pattern in retryable_patterns)

    def _detect_side_effects(self, result: ToolResult) -> list[str]:
        """Detect potential side effects from action result."""
        side_effects = []

        if result.data:
            data = result.data if isinstance(result.data, dict) else {}

            # URL change
            if "url" in data:
                side_effects.append(f"URL changed to {data['url']}")

            # Form submission
            if data.get("pressed_enter"):
                side_effects.append("Form may have been submitted")

            # Scroll position changed
            if "scroll_to" in data:
                side_effects.append("Page scrolled")

        return side_effects

    async def click(
        self,
        element_description: str,
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """
        Click an element by natural language description.

        Args:
            element_description: Description of element to click
            context: Execution context

        Returns:
            ExecutionResult
        """
        return await self.execute(
            action=f'Click "{element_description}"',
            tool_name="click",
            arguments={"element_description": element_description},
            context=context,
        )

    async def type_text(
        self,
        element_description: str,
        text: str,
        press_enter: bool = False,
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """
        Type text into a field.

        Args:
            element_description: Description of input field
            text: Text to type
            press_enter: Whether to press Enter after
            context: Execution context

        Returns:
            ExecutionResult
        """
        return await self.execute(
            action=f'Type "{text}" into "{element_description}"',
            tool_name="type_text",
            arguments={
                "element_description": element_description,
                "text": text,
                "press_enter": press_enter,
            },
            context=context,
        )

    async def navigate(
        self,
        url: str,
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            context: Execution context

        Returns:
            ExecutionResult
        """
        return await self.execute(
            action=f"Navigate to {url}",
            tool_name="navigate",
            arguments={"url": url},
            context=context,
        )

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 500,
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """
        Scroll the page.

        Args:
            direction: Scroll direction (up, down, left, right)
            amount: Pixels to scroll
            context: Execution context

        Returns:
            ExecutionResult
        """
        return await self.execute(
            action=f"Scroll {direction} by {amount}px",
            tool_name="scroll",
            arguments={"direction": direction, "amount": amount},
            context=context,
        )

    async def wait_for_load(
        self,
        state: str = "load",
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionResult:
        """
        Wait for page to reach load state.

        Args:
            state: Load state to wait for
            context: Execution context

        Returns:
            ExecutionResult
        """
        return await self.execute(
            action=f"Wait for page {state}",
            tool_name="wait_for_load",
            arguments={"state": state},
            context=context,
        )

    def get_history(self, limit: int = 10) -> list[ExecutionResult]:
        """Get recent execution history."""
        return self.history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        if not self.history:
            return {"total": 0, "success": 0, "failure": 0, "success_rate": 0}

        total = len(self.history)
        success = sum(1 for r in self.history if r.success)
        failure = total - success

        return {
            "total": total,
            "success": success,
            "failure": failure,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration_ms": sum(
                r.duration_ms for r in self.history if r.duration_ms
            ) / total,
        }


def create_executor(
    execute_tool: Callable[[str, dict[str, Any]], Awaitable[ToolResult]],
    verbose: bool = True,
) -> BrowserExecutor:
    """
    Factory function to create a browser executor.

    Args:
        execute_tool: Async function to execute browser tools
        verbose: Whether to print progress

    Returns:
        Configured BrowserExecutor instance
    """
    return BrowserExecutor(execute_tool=execute_tool, verbose=verbose)
