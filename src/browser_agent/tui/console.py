"""
Rich TUI Console Setup

Provides the core console infrastructure for the browser automation agent.
Configured via environment variables for customizable appearance.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.theme import Theme


# Block types for agent output
BlockType = Literal["thought", "action", "result"]


@dataclass
class TUIConfig:
    """
    TUI configuration loaded from environment variables.

    Attributes:
        color_thought: Color for THOUGHT blocks (agent reasoning)
        color_action: Color for ACTION blocks (browser actions)
        color_result: Color for RESULT blocks (outcomes)
        show_timestamps: Whether to display timestamps
    """

    color_thought: str = "blue"
    color_action: str = "green"
    color_result: str = "yellow"
    show_timestamps: bool = True

    @classmethod
    def from_env(cls) -> "TUIConfig":
        """Load configuration from environment variables."""
        return cls(
            color_thought=os.getenv("COLOR_THOUGHT", "blue"),
            color_action=os.getenv("COLOR_ACTION", "green"),
            color_result=os.getenv("COLOR_RESULT", "yellow"),
            show_timestamps=os.getenv("SHOW_TIMESTAMPS", "true").lower() == "true",
        )


def create_theme(config: TUIConfig) -> Theme:
    """Create a Rich theme from TUI configuration."""
    return Theme(
        {
            "thought": Style(color=config.color_thought, bold=True),
            "thought.text": Style(color=config.color_thought),
            "action": Style(color=config.color_action, bold=True),
            "action.text": Style(color=config.color_action),
            "result": Style(color=config.color_result, bold=True),
            "result.text": Style(color=config.color_result),
            "timestamp": Style(dim=True),
            "label": Style(bold=True),
        }
    )


class AgentConsole:
    """
    Rich console wrapper for browser automation agent output.

    Provides formatted output for agent thoughts, actions, and results
    with consistent styling and optional timestamps.
    """

    def __init__(self, config: Optional[TUIConfig] = None):
        """
        Initialize the agent console.

        Args:
            config: TUI configuration. If None, loads from environment.
        """
        self.config = config or TUIConfig.from_env()
        self._theme = create_theme(self.config)
        self.console = Console(theme=self._theme)

    def _get_timestamp(self) -> str:
        """Get formatted timestamp if enabled."""
        if self.config.show_timestamps:
            return datetime.now().strftime("%H:%M:%S")
        return ""

    def _get_block_style(self, block_type: BlockType) -> tuple[str, str]:
        """Get the style and label for a block type."""
        styles = {
            "thought": (self.config.color_thought, "THOUGHT"),
            "action": (self.config.color_action, "ACTION"),
            "result": (self.config.color_result, "RESULT"),
        }
        return styles[block_type]

    def print_block(
        self,
        content: str,
        block_type: BlockType,
        title: Optional[str] = None,
    ) -> None:
        """
        Print a styled block to the console.

        Args:
            content: The text content to display
            block_type: Type of block (thought, action, result)
            title: Optional title to override default label
        """
        color, label = self._get_block_style(block_type)
        block_title = title or f"[{label}]"

        timestamp = self._get_timestamp()
        if timestamp:
            block_title = f"{timestamp} {block_title}"

        panel = Panel(
            content,
            title=block_title,
            title_align="left",
            border_style=color,
            padding=(0, 1),
        )
        self.console.print(panel)

    def print_thought(self, content: str, title: Optional[str] = None) -> None:
        """Print a THOUGHT block (agent reasoning)."""
        self.print_block(content, "thought", title)

    def print_action(self, content: str, title: Optional[str] = None) -> None:
        """Print an ACTION block (browser action)."""
        self.print_block(content, "action", title)

    def print_result(self, content: str, title: Optional[str] = None) -> None:
        """Print a RESULT block (outcome)."""
        self.print_block(content, "result", title)

    def print(self, *args, **kwargs) -> None:
        """Passthrough to underlying Rich console."""
        self.console.print(*args, **kwargs)

    def status(self, message: str):
        """Create a status context for progress indication."""
        return self.console.status(message)


# Global console instance
_console: Optional[AgentConsole] = None


def get_console() -> AgentConsole:
    """Get or create the global console instance."""
    global _console
    if _console is None:
        _console = AgentConsole()
    return _console


def create_console(config: Optional[TUIConfig] = None) -> AgentConsole:
    """
    Create a new console instance with optional configuration.

    Args:
        config: TUI configuration. If None, loads from environment.
    """
    return AgentConsole(config)
