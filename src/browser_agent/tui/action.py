"""
ACTION block display for browser interactions.

Provides enhanced formatting for displaying browser actions
in the terminal with green styling per FR-004.
"""

from typing import Any, Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .console import AgentConsole, get_console


def format_action_params(params: dict[str, Any]) -> Table:
    """
    Format action parameters as a Rich table.

    Args:
        params: Dictionary of parameter names to values

    Returns:
        Rich Table renderable
    """
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Param", style="bold")
    table.add_column("Value")

    for key, value in params.items():
        # Truncate long values
        str_value = str(value)
        if len(str_value) > 100:
            str_value = str_value[:97] + "..."
        table.add_row(key, str_value)

    return table


def print_action(
    action_name: str,
    *,
    params: Optional[dict[str, Any]] = None,
    description: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print an ACTION block displaying a browser action.

    Args:
        action_name: Name of the action being performed (e.g., "click", "navigate")
        params: Action parameters to display
        description: Human-readable description of the action
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    # Build content
    content = Text()

    # Add action name prominently
    content.append("⚡ ", style="bold")
    content.append(action_name, style="bold green")
    content.append("\n")

    # Add description if provided
    if description:
        content.append(f"\n{description}\n")

    # Build title with timestamp
    timestamp = console._get_timestamp()
    full_title = "[ACTION]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_action,
        padding=(0, 1),
    )
    console.console.print(panel)

    # Print params table separately if present (for cleaner layout)
    if params:
        params_table = format_action_params(params)
        console.console.print(params_table)


def print_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print a tool call action block (common format for browser automation).

    Args:
        tool_name: Name of the tool being called
        arguments: Tool arguments
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    # Build content with tool call format
    content = Text()
    content.append("🔧 Tool: ", style="bold")
    content.append(tool_name, style="bold green")
    content.append("\n")

    # Add arguments
    if arguments:
        content.append("\nArguments:\n", style="bold")
        for key, value in arguments.items():
            str_value = str(value)
            if len(str_value) > 80:
                str_value = str_value[:77] + "..."
            content.append(f"  {key}: ", style="dim")
            content.append(f"{str_value}\n")

    timestamp = console._get_timestamp()
    full_title = "[ACTION]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_action,
        padding=(0, 1),
    )
    console.console.print(panel)


def print_navigation(
    url: str,
    *,
    action: str = "navigate",
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print a navigation action block.

    Args:
        url: Target URL
        action: Navigation action type (navigate, back, forward, reload)
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    action_icons = {
        "navigate": "🌐",
        "back": "⬅️",
        "forward": "➡️",
        "reload": "🔄",
    }
    icon = action_icons.get(action, "🌐")

    content = Text()
    content.append(f"{icon} ", style="bold")
    content.append(action.capitalize(), style="bold green")
    content.append("\n\n")
    content.append("URL: ", style="dim")
    content.append(url, style="underline")

    timestamp = console._get_timestamp()
    full_title = "[ACTION]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_action,
        padding=(0, 1),
    )
    console.console.print(panel)


def print_interaction(
    element_description: str,
    interaction_type: str,
    *,
    value: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print an element interaction action block.

    Args:
        element_description: Natural language description of the element
        interaction_type: Type of interaction (click, type, scroll, etc.)
        value: Value for the interaction (e.g., text to type)
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    interaction_icons = {
        "click": "👆",
        "type": "⌨️",
        "scroll": "📜",
        "hover": "🎯",
        "select": "☑️",
    }
    icon = interaction_icons.get(interaction_type, "⚡")

    content = Text()
    content.append(f"{icon} ", style="bold")
    content.append(interaction_type.capitalize(), style="bold green")
    content.append("\n\n")
    content.append("Element: ", style="dim")
    content.append(f'"{element_description}"')

    if value is not None:
        content.append("\n")
        content.append("Value: ", style="dim")
        content.append(f'"{value}"')

    timestamp = console._get_timestamp()
    full_title = "[ACTION]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_action,
        padding=(0, 1),
    )
    console.console.print(panel)
