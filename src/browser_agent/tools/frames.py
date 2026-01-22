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


async def _wait_for_dynamic_iframes(
    page: Page,
    timeout_ms: int = 5000,
    poll_interval_ms: int = 500,
    expected_count: int | None = None,
) -> list[Frame]:
    """
    Wait for dynamic iframes to load with polling (FR-026).

    Some sites load iframes dynamically after initial page load.
    This function polls for new frames until timeout or expected count reached.

    Args:
        page: Playwright Page instance
        timeout_ms: Maximum time to wait in milliseconds (default: 5000)
        poll_interval_ms: Time between polls in milliseconds (default: 500)
        expected_count: Optional expected frame count (returns when reached)

    Returns:
        List of frames found after waiting

    Examples:
        >>> # Wait up to 5s for iframes to load
        >>> frames = await _wait_for_dynamic_iframes(page)
        >>>
        >>> # Wait for specific frame count
        >>> frames = await _wait_for_dynamic_iframes(page, expected_count=3)
    """
    import asyncio

    start_time = asyncio.get_event_loop().time()
    initial_count = len(page.frames)

    logger.debug(f"Waiting for dynamic iframes. Initial count: {initial_count}")

    while True:
        current_time = asyncio.get_event_loop().time()
        elapsed_ms = int((current_time - start_time) * 1000)

        # Check timeout
        if elapsed_ms >= timeout_ms:
            logger.debug(f"Timeout waiting for iframes. Found {len(page.frames)} frames.")
            return page.frames

        # Check if expected count reached
        if expected_count is not None and len(page.frames) >= expected_count:
            logger.debug(f"Expected frame count {expected_count} reached.")
            return page.frames

        # Wait for poll interval
        await asyncio.sleep(poll_interval_ms / 1000)


def _prioritize_frames(
    frames: list[FrameContext],
    include_inaccessible: bool = True,
) -> list[FrameContext]:
    """
    Prioritize frames in semantic-first search order (FR-025).

    Args:
        frames: List of FrameContext objects to prioritize
        include_inaccessible: Include cross-origin iframes (default: true)

    Returns:
        Prioritized list of frames:
        1. Main frame (index 0) - always first
        2. Frames with semantic labels (aria-label, title, or name)
        3. Remaining frames by index

    Priority order within semantic frames:
    - aria-label (highest priority for accessibility)
    - title
    - name

    Examples:
        >>> frames = [FrameContext(index=0), FrameContext(index=1, aria_label="Search")]
        >>> prioritized = _prioritize_frames(frames)
        >>> assert prioritized[0].index == 0  # Main frame first
        >>> assert prioritized[1].aria_label == "Search"  # Semantic frame next
    """
    # Filter out inaccessible frames if requested
    accessible_frames = [f for f in frames if f.accessible or include_inaccessible]

    # Separate main frame from iframes
    main_frame = None
    iframes = []

    for frame in accessible_frames:
        if frame.index == 0:
            main_frame = frame
        else:
            iframes.append(frame)

    # Prioritize iframes by semantic labels
    def get_semantic_priority(frame: FrameContext) -> tuple[int, int]:
        """
        Return priority tuple (semantic_score, index).

        Lower score = higher priority.
        - aria-label: score 0 (highest)
        - title: score 1
        - name: score 2
        - No semantic label: score 3
        """
        if frame.aria_label:
            return (0, frame.index)
        elif frame.title:
            return (1, frame.index)
        elif frame.name:
            return (2, frame.index)
        else:
            return (3, frame.index)

    # Sort iframes by semantic priority
    sorted_iframes = sorted(iframes, key=get_semantic_priority)

    # Combine: main frame first, then sorted iframes
    if main_frame:
        return [main_frame] + sorted_iframes
    else:
        return sorted_iframes
