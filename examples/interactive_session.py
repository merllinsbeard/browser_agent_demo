#!/usr/bin/env python
"""
Interactive Session Example

Demonstrates multi-turn conversation with context preservation.
The agent remembers previous interactions within the session.

Usage:
    python examples/interactive_session.py

Requirements:
    - ANTHROPIC_API_KEY environment variable set
    - Browser agent installed: pip install -e .
"""

import asyncio
from browser_agent.agents.orchestrator import create_orchestrator
from browser_agent.tui import get_console

try:
    from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock, ResultMessage
except ImportError:
    print("Error: Claude Agent SDK not installed.")
    print("Install with: uv add claude-agent-sdk")
    exit(1)


def display_message(message):
    """Simple message display."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                text = block.text.strip()
                if text:
                    print(text)
            elif isinstance(block, ToolUseBlock):
                print(f"[Tool: {block.name}]")

    elif isinstance(message, ResultMessage):
        if message.subtype == "success":
            print(f"[Success] {message.result}")
        elif message.subtype == "error":
            print(f"[Error] {message.error_message}")


async def main():
    """Run interactive session."""
    console = get_console()

    console.print("[bold]Browser Automation Agent - Interactive Session[/bold]")
    console.print("Context is preserved between commands.")
    console.print("Type 'quit' to exit.\n")

    orchestrator = create_orchestrator(
        headless=False,
        max_turns=15,
    )

    async with orchestrator:
        # Create persistent session
        async with await orchestrator.create_session() as session:
            while True:
                try:
                    # Get user input
                    task = console.input("[bold green]>[/bold green] ").strip()

                    if not task:
                        continue
                    if task.lower() in ("quit", "exit", "q"):
                        break

                    console.print()

                    # Execute with context from previous interactions
                    async for message in session.query(task):
                        display_message(message)

                    console.print()

                except KeyboardInterrupt:
                    console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
                    continue

    console.print("[dim]Goodbye![/dim]")


if __name__ == "__main__":
    asyncio.run(main())
