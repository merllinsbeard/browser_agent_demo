#!/usr/bin/env python
"""
Multi-Step Task Example

Demonstrates complex browser automation with task decomposition.
The planner agent breaks down the task and coordinates execution.

Usage:
    python examples/multi_step_task.py

Requirements:
    - ANTHROPIC_API_KEY environment variable set
    - Browser agent installed: pip install -e .
"""

import asyncio
from browser_agent.agents.orchestrator import create_orchestrator
from browser_agent.tui import (
    print_thought,
    print_tool_call,
    print_result,
    print_error,
    print_subagent_delegation,
)

try:
    from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock, ResultMessage
except ImportError:
    print("Error: Claude Agent SDK not installed.")
    print("Install with: uv add claude-agent-sdk")
    exit(1)


def display_message(message, verbose: bool = True):
    """Display SDK message with formatting."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                text = block.text.strip()
                if text:
                    if "<thought>" in text.lower() or "[thought]" in text.lower():
                        print_thought(text)
                    else:
                        print(text)
            elif isinstance(block, ToolUseBlock):
                if block.name == "Task":
                    # Subagent delegation
                    print_subagent_delegation(
                        subagent_name=block.input.get("subagent_type", "unknown"),
                        task_description=block.input.get("prompt", ""),
                        model=block.input.get("model"),
                    )
                elif verbose:
                    print_tool_call(block.name, block.input)

    elif isinstance(message, ResultMessage):
        if message.subtype == "success":
            print_result(str(message.result), success=True)
        elif message.subtype == "error":
            print_error(str(message.error_message), error_type="ExecutionError")


async def main():
    """Run multi-step task with planning."""
    # Create orchestrator
    orchestrator = create_orchestrator(
        headless=False,
        max_turns=20,  # Allow more iterations for complex tasks
    )

    # Complex task that requires planning and multiple steps
    task = """
    Navigate to Wikipedia (https://www.wikipedia.org), search for "Python programming language",
    and tell me when the language was first released and who designed it.
    """

    print(f"Task: {task.strip()}\n")
    print("=" * 60)

    # Execute with detailed output
    async with orchestrator:
        async for message in orchestrator.execute_task_stream(task):
            display_message(message)


if __name__ == "__main__":
    asyncio.run(main())
