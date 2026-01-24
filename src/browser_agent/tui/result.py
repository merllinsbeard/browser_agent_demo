"""
RESULT block display for action outcomes.

Provides enhanced formatting for displaying action results
in the terminal with yellow styling per FR-005.
"""

from typing import Any, Optional

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .console import AgentConsole, get_console


def print_result(
    content: str,
    *,
    success: bool = True,
    title: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print a RESULT block displaying an action outcome.

    Args:
        content: The result content to display
        success: Whether the action was successful
        title: Custom title (overrides default "[RESULT]")
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    # Build content with status indicator
    text = Text()
    status_icon = "✓" if success else "✗"
    status_style = "green" if success else "red"
    text.append(f"{status_icon} ", style=f"bold {status_style}")
    text.append(content)

    timestamp = console._get_timestamp()
    full_title = title or "[RESULT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        text,
        title=full_title,
        title_align="left",
        border_style=console.config.color_result,
        padding=(0, 1),
    )
    console.console.print(panel)


def print_error(
    error_message: str,
    *,
    error_type: Optional[str] = None,
    suggestion: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print an error result block.

    Args:
        error_message: The error message
        error_type: Type/category of error
        suggestion: Suggestion for resolution
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    content = Text()
    content.append("❌ Error", style="bold red")
    if error_type:
        content.append(f" ({error_type})", style="dim red")
    content.append("\n\n")
    content.append(error_message)

    if suggestion:
        content.append("\n\n")
        content.append("💡 ", style="bold")
        content.append(suggestion, style="italic")

    timestamp = console._get_timestamp()
    full_title = "[RESULT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style="red",
        padding=(0, 1),
    )
    console.console.print(panel)


def print_data_result(
    data: dict[str, Any],
    *,
    title: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print a result containing structured data.

    Args:
        data: Dictionary of data to display
        title: Custom title
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    # Create table for data
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Field", style="dim")
    table.add_column("Value")

    for key, value in data.items():
        str_value = str(value)
        if len(str_value) > 100:
            str_value = str_value[:97] + "..."
        table.add_row(key, str_value)

    timestamp = console._get_timestamp()
    full_title = title or "[RESULT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        table,
        title=full_title,
        title_align="left",
        border_style=console.config.color_result,
        padding=(0, 1),
    )
    console.console.print(panel)


def print_extracted_text(
    text: str,
    *,
    source: Optional[str] = None,
    truncate: int = 500,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print extracted text content from a page.

    Args:
        text: The extracted text
        source: Source description (e.g., element, page title)
        truncate: Max characters to display (0 for no truncation)
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    content = Text()
    content.append("📄 Extracted Text", style="bold")
    if source:
        content.append(f" from {source}", style="dim")
    content.append("\n\n")

    display_text = text
    if truncate > 0 and len(text) > truncate:
        display_text = text[:truncate] + f"... ({len(text) - truncate} more chars)"

    content.append(display_text)

    timestamp = console._get_timestamp()
    full_title = "[RESULT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_result,
        padding=(0, 1),
    )
    console.console.print(panel)


def print_page_info(
    url: str,
    title: str,
    *,
    status: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print page information result.

    Args:
        url: Current page URL
        title: Page title
        status: Page load status
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    content = Text()
    content.append("🌐 Page Info\n\n", style="bold")
    content.append("Title: ", style="dim")
    content.append(f"{title}\n")
    content.append("URL: ", style="dim")
    content.append(url, style="underline")

    if status:
        content.append("\n")
        content.append("Status: ", style="dim")
        content.append(status)

    timestamp = console._get_timestamp()
    full_title = "[RESULT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_result,
        padding=(0, 1),
    )
    console.console.print(panel)


def print_code_result(
    code: str,
    *,
    language: str = "text",
    description: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print code or structured output result with syntax highlighting.

    Args:
        code: The code/structured content
        language: Language for syntax highlighting
        description: Description of the code content
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    # Build content
    elements = []
    if description:
        desc_text = Text()
        desc_text.append(f"{description}\n\n")
        elements.append(desc_text)

    # Add syntax-highlighted code
    syntax = Syntax(code, language, theme="monokai", line_numbers=False)
    elements.append(syntax)

    from rich.console import Group

    content = Group(*elements)

    timestamp = console._get_timestamp()
    full_title = "[RESULT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_result,
        padding=(0, 1),
    )
    console.console.print(panel)


def print_subagent_result(
    subagent_name: str,
    result_content: str,
    *,
    success: bool = True,
    model: Optional[str] = None,
    duration_ms: Optional[int] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print a subagent task result block.

    Displays when a subagent (planner, executor, dom_analyzer, validator)
    returns its result from a Task tool delegation.

    Args:
        subagent_name: Name of the subagent that returned the result
        result_content: The result content from the subagent
        success: Whether the subagent task succeeded
        model: Model tier used (sonnet/haiku/opus)
        duration_ms: Execution time in milliseconds
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    # Agent-specific icons
    agent_icons = {
        "planner": "📋",
        "dom_analyzer": "🔍",
        "executor": "⚡",
        "validator": "✅",
    }
    icon = agent_icons.get(subagent_name, "🤖")
    status_icon = "✓" if success else "✗"
    status_style = "green" if success else "red"

    content = Text()
    content.append(f"{icon} ", style="bold")
    content.append(subagent_name, style="bold magenta")
    content.append(f" {status_icon}", style=f"bold {status_style}")
    if model:
        content.append(f" ({model})", style="dim italic")
    if duration_ms is not None:
        content.append(f" [{duration_ms}ms]", style="dim")
    content.append("\n\n")

    # Result content (truncate if long)
    result_display = result_content
    if len(result_display) > 500:
        result_display = result_display[:497] + "..."
    content.append(result_display)

    timestamp = console._get_timestamp()
    full_title = "[SUBAGENT RESULT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style="magenta" if success else "red",
        padding=(0, 1),
    )
    console.console.print(panel)


def print_completion(
    summary: str,
    *,
    actions_count: Optional[int] = None,
    duration: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> None:
    """
    Print task completion result.

    Args:
        summary: Summary of what was accomplished
        actions_count: Number of actions performed
        duration: Task duration string
        console: Console to use (defaults to global console)
    """
    console = console or get_console()

    content = Text()
    content.append("✅ Task Complete\n\n", style="bold green")
    content.append(summary)

    if actions_count is not None or duration is not None:
        content.append("\n\n")
        if actions_count is not None:
            content.append("Actions: ", style="dim")
            content.append(f"{actions_count}\n")
        if duration is not None:
            content.append("Duration: ", style="dim")
            content.append(duration)

    timestamp = console._get_timestamp()
    full_title = "[RESULT]"
    if timestamp:
        full_title = f"{timestamp} {full_title}"

    panel = Panel(
        content,
        title=full_title,
        title_align="left",
        border_style=console.config.color_result,
        padding=(0, 1),
    )
    console.console.print(panel)
