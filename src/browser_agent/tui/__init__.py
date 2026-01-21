"""
Rich TUI Interface Module

Provides terminal user interface components for the browser automation agent.
Uses the Rich library for formatted, colorful output.

Components:
- AgentConsole: Main console wrapper with themed output
- TUIConfig: Configuration for colors and display options
- Block display functions for THOUGHT/ACTION/RESULT output
"""

from browser_agent.tui.console import (
    AgentConsole,
    BlockType,
    TUIConfig,
    create_console,
    get_console,
)

__all__ = [
    "AgentConsole",
    "BlockType",
    "TUIConfig",
    "create_console",
    "get_console",
]
