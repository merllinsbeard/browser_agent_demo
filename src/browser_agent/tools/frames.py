"""
Frame Tools

Implements iframe interaction and frame management capabilities.

Feature: 002-iframe-interaction-fixes

This module provides tools for:
- Listing and enumerating frames on a page
- Switching between frame contexts
- Extracting frame content
- Cross-origin frame detection and handling
"""

from playwright.async_api import Page, Frame  # noqa: F401 - Used in Phase 2 implementations

from .base import tool, ToolResult  # noqa: F401 - Used in Phase 2 implementations
from .frame_models import FrameContext, FrameLocatorResult  # noqa: F401 - Used in Phase 2 implementations


# Frame enumeration tools will be implemented in Phase 2 (T004-T008)
# - list_frames: Enumerate page.frames with attributes
# - switch_to_frame: Change active frame context
# - get_frame_content: Extract frame content explicitly


# NOTE: Tool implementations go here
# Tools are registered using the @tool decorator
# Example:
# @tool(
#     name="list_frames",
#     description="List all frames on the page including iframes",
#     parameters={...}
# )
# async def list_frames_tool(page: Page) -> ToolResult:
#     ...
