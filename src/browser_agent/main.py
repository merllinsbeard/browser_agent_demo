"""
Browser Agent CLI Entry Point

Provides the command-line interface for running browser automation tasks
using the Claude Agent SDK.

Usage:
    python -m browser_agent.main "Your task description"
    python -m browser_agent.main "Your task" --verbose --headless
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SDK imports
try:
    from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock, ResultMessage
except ImportError:
    print("Error: Claude Agent SDK not installed.")
    print("Install with: uv add claude-agent-sdk")
    sys.exit(1)

from browser_agent.agents.orchestrator import create_orchestrator
from browser_agent.tui import (
    print_thought,
    print_tool_call,
    print_result,
    print_error,
    print_subagent_delegation,
    print_subagent_result,
    get_console,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Browser automation agent powered by Claude SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m browser_agent.main "Search for Python books on Amazon"
    python -m browser_agent.main "Fill the contact form" --start-url https://example.com
    python -m browser_agent.main "Run tests" --headless --verbose
        """,
    )

    parser.add_argument(
        "task",
        nargs="?",
        help="Natural language task description",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output including all tool calls",
    )

    parser.add_argument(
        "--model", "-m",
        choices=["sonnet", "haiku", "opus"],
        default="sonnet",
        help="Model to use for planning (default: sonnet)",
    )

    parser.add_argument(
        "--start-url", "-u",
        type=str,
        default=None,
        help="Initial URL to navigate to before running task",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (for CI/CD)",
    )

    parser.add_argument(
        "--max-turns",
        type=int,
        default=15,
        help="Maximum agent iterations (default: 15)",
    )

    parser.add_argument(
        "--max-budget",
        type=float,
        default=10.0,
        help="Maximum spend in USD (default: 10.0)",
    )

    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume from a previous session ID",
    )

    parser.add_argument(
        "--dev",
        action="store_true",
        help="Development mode with debug output",
    )

    return parser.parse_args()


async def run_task(
    task: str,
    start_url: Optional[str] = None,
    headless: bool = False,
    verbose: bool = False,
    max_turns: int = 15,
    max_budget: float = 10.0,
) -> bool:
    """
    Run a browser automation task.

    Args:
        task: Natural language task description
        start_url: Optional URL to navigate to first
        headless: Run browser in headless mode
        verbose: Show detailed output
        max_turns: Maximum agent iterations
        max_budget: Maximum spend in USD

    Returns:
        True if task completed successfully, False otherwise
    """
    console = get_console()

    # Create orchestrator
    orchestrator = create_orchestrator(
        headless=headless,
        max_turns=max_turns,
        max_budget_usd=max_budget,
    )

    try:
        async with orchestrator:
            # Navigate to start URL if provided
            if start_url:
                console.print(f"[dim]Navigating to {start_url}...[/dim]")
                page = orchestrator._browser.current_page
                if page:
                    await page.goto(start_url)

            # Execute task with streaming
            console.print(f"[bold]Task:[/bold] {task}\n")

            async for message in orchestrator.execute_task_stream(task):
                _display_message(message, verbose)

            return True

    except KeyboardInterrupt:
        console.print("\n[yellow]Task interrupted by user[/yellow]")
        return False
    except Exception as e:
        print_error(str(e), error_type="TaskError")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def _display_message(message, verbose: bool) -> None:
    """
    Display an SDK message to the console.

    Args:
        message: Message from SDK (AssistantMessage, ResultMessage, etc.)
        verbose: Show detailed output
    """
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                # Display text output
                text = block.text.strip()
                if text:
                    # Check for thought markers
                    if "<thought>" in text.lower() or "[thought]" in text.lower():
                        print_thought(text)
                    else:
                        print(text)

            elif isinstance(block, ToolUseBlock):
                # Check if this is a subagent delegation (Task tool)
                if block.name == "Task":
                    _display_subagent_delegation(block.input, verbose)
                elif verbose:
                    print_tool_call(block.name, block.input)

    elif isinstance(message, ResultMessage):
        # Final result
        if message.subtype == "success":
            print_result(str(message.result), success=True)
        elif message.subtype == "error":
            print_error(str(message.error_message), error_type="ExecutionError")
        elif message.subtype == "subagent_result":
            # Subagent result from Task tool
            _display_subagent_result_message(message, verbose)
        else:
            # Other result types
            if verbose:
                print(f"[{message.subtype}] {message}")

    elif verbose:
        # Unknown message type
        print(f"[dim]{type(message).__name__}: {message}[/dim]")


def _display_subagent_delegation(task_input: dict, verbose: bool) -> None:
    """
    Display subagent delegation from Task tool call.

    Args:
        task_input: Task tool input dict with subagent_type, prompt, etc.
        verbose: Show detailed output
    """
    subagent_name = task_input.get("subagent_type", "unknown")
    task_description = task_input.get("prompt", task_input.get("description", ""))
    model = task_input.get("model")

    # Always show subagent delegation for visibility
    print_subagent_delegation(
        subagent_name=subagent_name,
        task_description=task_description,
        model=model,
    )


def _display_subagent_result_message(message, verbose: bool) -> None:
    """
    Display result from a subagent Task tool call.

    Args:
        message: ResultMessage with subagent_result subtype
        verbose: Show detailed output
    """
    # Extract subagent info from result metadata if available
    result_data = message.result if hasattr(message, 'result') else {}
    if isinstance(result_data, dict):
        subagent_name = result_data.get("subagent", "unknown")
        content = result_data.get("content", str(result_data))
        success = result_data.get("success", True)
        model = result_data.get("model")
        duration_ms = result_data.get("duration_ms")
    else:
        subagent_name = "unknown"
        content = str(result_data)
        success = True
        model = None
        duration_ms = None

    print_subagent_result(
        subagent_name=subagent_name,
        result_content=content,
        success=success,
        model=model,
        duration_ms=duration_ms,
    )


async def run_interactive_session(
    start_url: Optional[str] = None,
    headless: bool = False,
    verbose: bool = False,
    max_turns: int = 15,
    max_budget: float = 10.0,
) -> None:
    """
    Run an interactive multi-turn conversation session.

    Maintains context between queries, allowing follow-up commands
    that reference previous interactions.

    Args:
        start_url: Optional URL to navigate to first
        headless: Run browser in headless mode
        verbose: Show detailed output
        max_turns: Maximum agent iterations per query
        max_budget: Maximum spend in USD for the session
    """
    console = get_console()

    console.print("[bold]Browser Automation Agent[/bold] (Multi-turn Session)")
    console.print("Enter tasks to automate. Context is preserved between commands.")
    console.print("Commands: 'quit' to exit, 'new' to start fresh session\n")

    orchestrator = create_orchestrator(
        headless=headless,
        max_turns=max_turns,
        max_budget_usd=max_budget,
    )

    try:
        async with orchestrator:
            # Navigate to start URL if provided
            if start_url:
                console.print(f"[dim]Navigating to {start_url}...[/dim]")
                page = orchestrator._browser.current_page
                if page:
                    await page.goto(start_url)
                    console.print(f"[dim]Ready at {start_url}[/dim]\n")

            # Create persistent conversation session
            async with await orchestrator.create_session() as session:
                while True:
                    try:
                        task = console.input("[bold green]>[/bold green] ").strip()
                        if not task:
                            continue
                        if task.lower() in ("quit", "exit", "q"):
                            break
                        if task.lower() == "new":
                            console.print("[dim]Starting new session...[/dim]\n")
                            # Exit current session, will create new one
                            break

                        console.print()  # Spacing before output

                        async for message in session.query(task):
                            _display_message(message, verbose)

                        console.print()  # Spacing after output

                    except KeyboardInterrupt:
                        console.print("\n[yellow]Interrupted. Type 'quit' to exit or continue with a new task.[/yellow]")
                        continue

    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")
    except Exception as e:
        print_error(str(e), error_type="SessionError")
        if verbose:
            import traceback
            traceback.print_exc()


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging for dev mode
    if args.dev:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        os.environ.setdefault("LOG_LEVEL", "DEBUG")

    # Interactive mode if no task provided
    if not args.task:
        asyncio.run(run_interactive_session(
            start_url=args.start_url,
            headless=args.headless,
            verbose=args.verbose,
            max_turns=args.max_turns,
            max_budget=args.max_budget,
        ))
        return 0

    # Single task mode
    success = asyncio.run(run_task(
        task=args.task,
        start_url=args.start_url,
        headless=args.headless,
        verbose=args.verbose,
        max_turns=args.max_turns,
        max_budget=args.max_budget,
    ))

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
