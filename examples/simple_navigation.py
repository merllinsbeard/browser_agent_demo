#!/usr/bin/env python
"""
Simple Navigation Example

Demonstrates basic browser automation: navigate to a website and interact
with elements using natural language descriptions.

Usage:
    python examples/simple_navigation.py

Requirements:
    - ANTHROPIC_API_KEY environment variable set
    - Browser agent installed: pip install -e .
"""

import asyncio
from browser_agent.agents.orchestrator import create_orchestrator


async def main():
    """Run simple navigation task."""
    # Create orchestrator with visible browser (headless=False)
    orchestrator = create_orchestrator(
        headless=False,  # Show browser window
        max_turns=10,    # Limit iterations
    )

    # Task description in natural language
    task = "Navigate to https://example.com and tell me the page title"

    print(f"Task: {task}\n")

    # Execute task with streaming output
    async with orchestrator:
        async for message in orchestrator.execute_task_stream(task):
            # Simple output - main.py has better formatting
            print(message)


if __name__ == "__main__":
    asyncio.run(main())
