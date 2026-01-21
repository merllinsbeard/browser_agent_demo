"""
Rich TUI Interface Module

Provides terminal user interface components for the browser automation agent.
Uses the Rich library for formatted, colorful output.

Components:
- AgentConsole: Main console wrapper with themed output
- TUIConfig: Configuration for colors and display options
- Block display functions for THOUGHT/ACTION/RESULT output
- Thought module: Enhanced formatting for agent reasoning (FR-003)
"""

from browser_agent.tui.console import (
    AgentConsole,
    BlockType,
    TUIConfig,
    create_console,
    get_console,
)
from browser_agent.tui.thought import (
    format_thought_content,
    print_analysis,
    print_reasoning_chain,
    print_thought,
)
from browser_agent.tui.action import (
    format_action_params,
    print_action,
    print_interaction,
    print_navigation,
    print_tool_call,
)

__all__ = [
    # Console infrastructure
    "AgentConsole",
    "BlockType",
    "TUIConfig",
    "create_console",
    "get_console",
    # Thought block functions (FR-003)
    "format_thought_content",
    "print_analysis",
    "print_reasoning_chain",
    "print_thought",
    # Action block functions (FR-004)
    "format_action_params",
    "print_action",
    "print_interaction",
    "print_navigation",
    "print_tool_call",
]
