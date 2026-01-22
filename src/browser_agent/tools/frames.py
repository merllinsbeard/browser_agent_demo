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

import logging

from playwright.async_api import Page, Frame

from .base import tool, ToolResult
from .frame_models import FrameContext

logger = logging.getLogger(__name__)


@tool(
    name="list_frames",
    description="List all frames on the page with their attributes (name, src, aria-label, title, accessibility status). Use this to discover iframe contexts before targeting elements.",
    parameters={
        "type": "object",
        "properties": {
            "include_inaccessible": {
                "type": "boolean",
                "description": "Include cross-origin iframes that cannot be accessed (marked with accessible: false)",
                "default": True,
            },
        },
        "required": [],
    },
)
async def list_frames(
    page: Page,
    include_inaccessible: bool = True,
) -> ToolResult:
    """
    List all frames on the page including main frame and iframes.

    Returns frame metadata for context-aware element targeting.

    Args:
        page: Playwright Page instance
        include_inaccessible: Include cross-origin iframes (default: true)

    Returns:
        ToolResult with frames array, total_count, and accessible_count

    Examples:
        >>> result = await list_frames(page)
        >>> frames = result.data["frames"]
        >>> for frame in frames:
        ...     print(f"Frame {frame['index']}: {frame['name']}")

    Requirements: FR-001, FR-002, FR-021
    """
    try:
        frames = []
        accessible_count = 0

        # Iterate through all frames (main frame is always at index 0)
        for index, frame in enumerate(page.frames):
            # Get frame element attributes (for iframes)
            frame_context = await _extract_frame_context(frame, index, page)

            # Check accessibility
            frame_context.accessible = await _check_frame_accessible(frame)

            if frame_context.accessible:
                accessible_count += 1

            # Filter out inaccessible if requested
            if not frame_context.accessible and not include_inaccessible:
                continue

            frames.append(frame_context.model_dump())

        return ToolResult(
            success=True,
            data={
                "frames": frames,
                "total_count": len(page.frames),
                "accessible_count": accessible_count,
            },
        )

    except Exception as e:
        logger.error(f"Error listing frames: {e}")
        return ToolResult(
            success=False,
            error=f"Failed to list frames: {str(e)}",
        )


async def _extract_frame_context(frame: Frame, index: int, page: Page) -> FrameContext:
    """
    Extract FrameContext from Playwright Frame.

    Args:
        frame: Playwright Frame instance
        index: Frame index in page.frames
        page: Playwright Page instance

    Returns:
        FrameContext with frame metadata
    """
    # Get basic frame properties
    name = frame.name
    src = frame.url if frame.url else None

    # For iframes, try to get element attributes
    aria_label = None
    title = None
    parent_index = None

    if frame.parent_frame is not None:  # This is an iframe (not main frame)
        try:
            # Try to get the frame element
            # Note: This may fail for cross-origin iframes
            frame_element = await frame.query_selector("iframe") if frame != page.main_frame else None

            if frame_element:
                aria_label = await frame_element.get_attribute("aria-label")
                title = await frame_element.get_attribute("title")

                # Get parent frame index
                if frame.parent_frame:
                    parent_index = page.frames.index(frame.parent_frame) if frame.parent_frame in page.frames else None

        except Exception as e:
            # Cross-origin iframe - cannot access element attributes
            logger.debug(f"Could not extract iframe element attributes: {e}")

    return FrameContext(
        name=name,
        index=index,
        src=src,
        aria_label=aria_label,
        title=title,
        accessible=True,  # Will be updated by _check_frame_accessible
        parent_index=parent_index,
    )


async def _check_frame_accessible(frame: Frame) -> bool:
    """
    Check if frame content is accessible (same-origin).

    Args:
        frame: Playwright Frame instance

    Returns:
        True if frame is accessible, False for cross-origin
    """
    try:
        # Try to access frame title - will fail for cross-origin
        _ = frame.title
        return True
    except Exception as e:
        # Cross-origin frame
        logger.debug(f"Frame {frame.name} is not accessible: {e}")
        return False


# Additional frame tools will be implemented in later tasks:
# - switch_to_frame: Change active frame context (T028)
# - get_frame_content: Extract frame content explicitly (T027)
# - _prioritize_frames(): Semantic-first frame search order (T005)
# - _wait_for_dynamic_iframes(): Dynamic iframe polling (T006)
