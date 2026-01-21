"""
Live action progress indicators.

Provides spinner and progress display for ongoing browser actions
to show the user that work is in progress.
"""

from contextlib import contextmanager
from typing import Generator, Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .console import AgentConsole, get_console


@contextmanager
def action_spinner(
    message: str,
    *,
    spinner: str = "dots",
    console: Optional[AgentConsole] = None,
) -> Generator[None, None, None]:
    """
    Context manager that shows a spinner while an action is in progress.

    Args:
        message: Message to display next to spinner
        spinner: Spinner style (dots, line, arc, etc.)
        console: Console to use (defaults to global console)

    Usage:
        with action_spinner("Navigating to page..."):
            await page.goto(url)
    """
    console = console or get_console()

    with console.console.status(
        f"[{console.config.color_action}]{message}[/]",
        spinner=spinner,
    ):
        yield


@contextmanager
def progress_indicator(
    action_name: str,
    *,
    detail: Optional[str] = None,
    console: Optional[AgentConsole] = None,
) -> Generator["ActionProgress", None, None]:
    """
    Context manager for live action progress with updatable status.

    Args:
        action_name: Name of the action being performed
        detail: Optional initial detail text
        console: Console to use (defaults to global console)

    Yields:
        ActionProgress instance for updating status

    Usage:
        with progress_indicator("Processing page") as progress:
            progress.update("Extracting elements...")
            # do work
            progress.update("Analyzing structure...")
            # more work
    """
    console = console or get_console()
    progress = ActionProgress(action_name, detail, console)

    with Live(progress._render(), console=console.console, refresh_per_second=10) as live:
        progress._live = live
        yield progress


class ActionProgress:
    """
    Live progress indicator for browser actions.

    Provides methods to update the progress status in real-time.
    """

    def __init__(
        self,
        action_name: str,
        detail: Optional[str] = None,
        console: Optional[AgentConsole] = None,
    ):
        """
        Initialize action progress.

        Args:
            action_name: Name of the action
            detail: Initial detail text
            console: Console to use
        """
        self.action_name = action_name
        self.detail = detail or ""
        self.console = console or get_console()
        self._live: Optional[Live] = None

    def _render(self) -> Panel:
        """Render the current progress state."""
        content = Text()
        content.append("⏳ ", style="bold")
        content.append(self.action_name, style=f"bold {self.console.config.color_action}")
        if self.detail:
            content.append(f"\n\n{self.detail}", style="dim")

        return Panel(
            content,
            title="[ACTION IN PROGRESS]",
            title_align="left",
            border_style=self.console.config.color_action,
            padding=(0, 1),
        )

    def update(self, detail: str) -> None:
        """
        Update the progress detail text.

        Args:
            detail: New detail text to display
        """
        self.detail = detail
        if self._live:
            self._live.update(self._render())


def create_task_progress(
    console: Optional[AgentConsole] = None,
) -> Progress:
    """
    Create a Rich Progress instance for tracking task steps.

    Returns a configured Progress object that can be used to track
    multiple task steps with elapsed time.

    Args:
        console: Console to use (defaults to global console)

    Returns:
        Configured Rich Progress instance
    """
    console = console or get_console()

    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console.console,
    )


@contextmanager
def step_progress(
    steps: list[str],
    *,
    console: Optional[AgentConsole] = None,
) -> Generator["StepTracker", None, None]:
    """
    Context manager for tracking progress through a series of steps.

    Args:
        steps: List of step descriptions
        console: Console to use (defaults to global console)

    Yields:
        StepTracker for advancing through steps

    Usage:
        with step_progress(["Navigate", "Extract", "Analyze"]) as tracker:
            tracker.advance()  # Complete "Navigate"
            tracker.advance()  # Complete "Extract"
            tracker.advance()  # Complete "Analyze"
    """
    console = console or get_console()
    tracker = StepTracker(steps, console)

    with tracker._progress:
        yield tracker


class StepTracker:
    """
    Tracks progress through a series of steps.

    Displays a progress bar with step descriptions and timing.
    """

    def __init__(
        self,
        steps: list[str],
        console: Optional[AgentConsole] = None,
    ):
        """
        Initialize step tracker.

        Args:
            steps: List of step descriptions
            console: Console to use
        """
        self.steps = steps
        self.console = console or get_console()
        self.current_step = 0

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self.console.console,
        )
        self._task_id = self._progress.add_task(
            steps[0] if steps else "Working...",
            total=len(steps),
        )

    def advance(self, description: Optional[str] = None) -> None:
        """
        Advance to the next step.

        Args:
            description: Optional description override for next step
        """
        self.current_step += 1
        self._progress.advance(self._task_id)

        if self.current_step < len(self.steps):
            next_desc = description or self.steps[self.current_step]
            self._progress.update(self._task_id, description=next_desc)

    def set_description(self, description: str) -> None:
        """
        Update the current step description.

        Args:
            description: New description text
        """
        self._progress.update(self._task_id, description=description)
