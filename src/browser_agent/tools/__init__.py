"""
Browser Automation Tools

Collection of tools for browser interaction:
- Navigation (FR-006)
- Click (FR-007)
- Type (FR-008)
- Scroll (FR-009)
- Wait (FR-010)
"""

from .navigation import (
    navigate,
    navigate_tool,
    get_current_url,
    go_back,
    go_forward,
    reload_page,
)
from .base import ToolResult, tool, get_tool, get_all_tools, get_tool_schemas

__all__ = [
    "navigate",
    "navigate_tool",
    "get_current_url",
    "go_back",
    "go_forward",
    "reload_page",
    "ToolResult",
    "tool",
    "get_tool",
    "get_all_tools",
    "get_tool_schemas",
]
