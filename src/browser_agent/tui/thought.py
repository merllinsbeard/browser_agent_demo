"""
THOUGHT block display for agent reasoning.

Provides enhanced formatting for displaying agent thoughts and reasoning
in the terminal with blue styling per FR-003.
"""

from typing import Optional

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from .console import AgentConsole, get_console


def format_thought_content(
    content: str,
    as_markdown: bool = False,
) -> Text | Markdown:
    """
    Format thought content for display.

    Args:
        content: The thought content to format
        as_markdown: Whether to render as markdown

    Returns:
        Formatted Rich renderable
    """
    if as_markdown:
        return Markdown(content)
    return Text(content)


def print_thought(
    content: str,
    *,
    title: Optional[str] = None,
    step: Optional[int] = None,
    total_steps: Optional[int] = None,
    as_markdown: bool = False,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print a THOUGHT block displaying agent reasoning.

    Args:
        content: The reasoning content to display
        title: Custom title (overrides default "[THOUGHT]")
        step: Current step number in reasoning chain
        total_steps: Total steps in reasoning chain
        as_markdown: Render content as markdown
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    # Build title with optional step indicator
    block_title = title
    if step is not None:
        if total_steps is not None:
            block_title = f"[THOUGHT {step}/{total_steps}]"
        else:
            block_title = f"[THOUGHT {step}]"

    # Format content
    formatted = format_thought_content(content, as_markdown=as_markdown)

    # Create panel with thought styling
    timestamp = console._get_timestamp()
    full_title = block_title or "[THOUGHT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        formatted,
        title=full_title,
        title_align="left",
        border_style=console.config.color_thought,
        padding=(0, 1),
    )
    console.console.print(panel)


def print_reasoning_chain(
    steps: list[str],
    *,
    title: Optional[str] = None,
    as_markdown: bool = False,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print a chain of reasoning steps as sequential THOUGHT blocks.

    Args:
        steps: List of reasoning steps to display
        title: Optional title prefix for steps
        as_markdown: Render content as markdown
        console: Console to use (defaults to global console)
    """
    total = len(steps)
    for i, step_content in enumerate(steps, 1):
        step_title = title if title else None
        print_thought(
            step_content,
            title=step_title,
            step=i,
            total_steps=total,
            as_markdown=as_markdown,
            console=console,
        )


def print_analysis(
    observation: str,
    reasoning: str,
    conclusion: str,
    *,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print structured analysis thought with observation, reasoning, and conclusion.

    This follows the common agent reasoning pattern of:
    1. Observing the current state
    2. Reasoning about what to do
    3. Concluding with next action

    Args:
        observation: What the agent observes about current state
        reasoning: The agent's reasoning process
        conclusion: The agent's conclusion or next action decision
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    # Build structured content
    content = Text()
    content.append("📋 Observation\n", style="bold")
    content.append(f"{observation}\n\n")
    content.append("💭 Reasoning\n", style="bold")
    content.append(f"{reasoning}\n\n")
    content.append("✅ Conclusion\n", style="bold")
    content.append(conclusion)

    timestamp = console._get_timestamp()
    full_title = "[THOUGHT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_thought,
        padding=(0, 1),
    )
    console.console.print(panel)
