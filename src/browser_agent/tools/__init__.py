"""
Browser Automation Tools

Collection of tools for browser interaction:
- Navigation (FR-006)
- Click (FR-007)
- Type (FR-008)
- Scroll (FR-009)
- Wait (FR-010)
- Frame Management (002-iframe-interaction-fixes)
"""

from .navigation import (
    navigate,
    navigate_tool,
    get_current_url,
    go_back,
    go_forward,
    reload_page,
)
from .accessibility import (
    get_accessibility_tree,
    find_interactive_elements,
    get_page_text,
)
from .screenshot import (
    screenshot,
    save_screenshot,
    get_viewport_info,
)
from .wait import (
    wait_for_load,
    wait_for_selector,
    wait_for_text,
    wait_for_url,
    sleep,
)
from .interactions import (
    click,
    type_text,
    scroll,
    hover,
    select_option,
)
from .frames import (
    list_frames,
    get_frame_content,
    switch_to_frame,
)
from .base import ToolResult, tool, get_tool, get_all_tools, get_tool_schemas

__all__ = [
    # Navigation
    "navigate",
    "navigate_tool",
    "get_current_url",
    "go_back",
    "go_forward",
    "reload_page",
    # Accessibility
    "get_accessibility_tree",
    "find_interactive_elements",
    "get_page_text",
    # Screenshot
    "screenshot",
    "save_screenshot",
    "get_viewport_info",
    # Wait
    "wait_for_load",
    "wait_for_selector",
    "wait_for_text",
    "wait_for_url",
    "sleep",
    # Interactions (FR-007, FR-008, FR-009)
    "click",
    "type_text",
    "scroll",
    "hover",
    "select_option",
    # Frames (002-iframe-interaction-fixes)
    "list_frames",
    "get_frame_content",
    "switch_to_frame",
    # Base
    "ToolResult",
    "tool",
    "get_tool",
    "get_all_tools",
    "get_tool_schemas",
]
