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

    # For iframes, try to get element attributes from the PARENT page
    aria_label = None
    title = None
    parent_index = None

    if frame.parent_frame is not None:  # This is an iframe (not main frame)
        parent_frame = frame.parent_frame

        try:
            # Find the iframe element in the parent frame by name or src
            frame_element = None

            # Try finding by name attribute first
            if name:
                frame_element = await parent_frame.query_selector(f'iframe[name="{name}"]')

            # If not found by name, try by src
            if not frame_element and src:
                frame_element = await parent_frame.query_selector(f'iframe[src="{src}"]')

            # If still not found, try all iframes and match by frame reference
            if not frame_element:
                iframe_elements = await parent_frame.query_selector_all("iframe")
                for iframe_el in iframe_elements:
                    try:
                        content_frame = await iframe_el.content_frame()
                        if content_frame == frame:
                            frame_element = iframe_el
                            break
                    except Exception:
                        continue

            if frame_element:
                aria_label = await frame_element.get_attribute("aria-label")
                title = await frame_element.get_attribute("title")

            # Get parent frame index
            parent_index = page.frames.index(parent_frame) if parent_frame in page.frames else None

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


def is_cross_origin_frame(frame: Frame) -> bool:
    """
    Detect if frame is cross-origin with warning logging (FR-027).

    Args:
        frame: Playwright Frame instance

    Returns:
        True if frame is cross-origin (inaccessible), False if same-origin

    Examples:
        >>> if is_cross_origin_frame(frame):
        ...     logger.warning(f"Skipping cross-origin iframe: {frame.name}")
    """
    try:
        # Try to access frame properties - will fail for cross-origin
        _ = frame.url
        _ = frame.title
        return False  # Same-origin
    except Exception as e:
        # Cross-origin frame detected
        logger.warning(
            f"Cross-origin iframe detected (name: {frame.name}, url: {getattr(frame, 'url', 'unknown')}): {e}. "
            f"Frame content is inaccessible due to same-origin policy. Skipping."
        )
        return True


async def skip_cross_origin_frames_gracefully(frames: list[Frame]) -> list[Frame]:
    """
    Filter out cross-origin frames with warning logging (FR-027).

    Args:
        frames: List of Playwright Frame objects

    Returns:
        List of accessible (same-origin) frames only

    Examples:
        >>> accessible_frames = await skip_cross_origin_frames_gracefully(page.frames)
        >>> logger.info(f"Found {len(accessible_frames)} accessible frames")
    """
    accessible_frames = []
    skipped_count = 0

    for frame in frames:
        if is_cross_origin_frame(frame):
            skipped_count += 1
            continue

        accessible_frames.append(frame)

    if skipped_count > 0:
        logger.info(
            f"Skipped {skipped_count} cross-origin iframe(s) due to same-origin policy restrictions. "
            f"Proceeding with {len(accessible_frames)} accessible frame(s)."
        )

    return accessible_frames


@tool(
    name="get_frame_content",
    description="Extract content from a specific frame (main frame or iframe). Use this to explicitly get text or HTML content from a frame by its name, aria-label, title, or index.",
    parameters={
        "type": "object",
        "properties": {
            "frame_selector": {
                "type": "string",
                "description": 'Frame selector: "main" or "0" for main frame, frame name (e.g., "search-frame"), aria-label (e.g., "Yandex Search"), title, or index (e.g., "1", "2")',
            },
            "content_type": {
                "type": "string",
                "enum": ["text", "html", "both"],
                "description": "Type of content to extract: 'text' for visible text, 'html' for HTML source, 'both' for both",
                "default": "text",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum content length to return (default: 10000). Content will be truncated if longer.",
                "default": 10000,
            },
        },
        "required": ["frame_selector"],
    },
)
async def get_frame_content(
    page: Page,
    frame_selector: str,
    content_type: str = "text",
    max_length: int = 10000,
) -> ToolResult:
    """
    Extract content from a specific frame (FR-023).

    Allows explicit extraction of iframe content (text, HTML, or both).
    Supports multiple frame selector types (name, aria-label, title, index).

    Args:
        page: Playwright Page instance
        frame_selector: Frame identifier ("main", name, aria-label, title, or index)
        content_type: Type of content ("text", "html", or "both")
        max_length: Maximum content length (default: 10000)

    Returns:
        ToolResult with frame_context and content data

    Examples:
        >>> # Get text content from iframe by name
        >>> result = await get_frame_content(page, "search-frame", "text")
        >>>
        >>> # Get HTML content from main frame
        >>> result = await get_frame_content(page, "main", "html")

    Requirements: FR-023
    """
    try:
        # Find the target frame
        frame = await _find_frame_by_selector(page, frame_selector)
        if frame is None:
            available = await _get_available_frame_names(page)
            return ToolResult(
                success=False,
                error=f"Frame '{frame_selector}' not found. Available frames: {', '.join(available)}",
            )

        # Check cross-origin accessibility
        if is_cross_origin_frame(frame):
            return ToolResult(
                success=False,
                error=f"Frame '{frame_selector}' is cross-origin and cannot be accessed due to same-origin policy.",
            )

        # Extract content based on content_type
        data = {}
        text_content = None
        html_content = None

        if content_type in ("text", "both"):
            # Get visible text - try multiple methods for reliability
            try:
                # Method 1: inner_text on body
                text_content = await frame.inner_text("body")
                if not text_content:
                    # Method 2: evaluate JavaScript to get body text
                    text_content = await frame.evaluate("() => document.body ? document.body.innerText : ''")
                if not text_content:
                    # Method 3: textContent as fallback
                    text_content = await frame.evaluate("() => document.body ? document.body.textContent : ''")
            except Exception:
                # If all methods fail, try evaluate as last resort
                try:
                    text_content = await frame.evaluate("() => document.body ? document.body.textContent : ''")
                except Exception:
                    text_content = ""

            if text_content and len(text_content) > max_length:
                text_content = text_content[:max_length] + "... (truncated)"

        if content_type in ("html", "both"):
            # Get HTML source
            try:
                html_content = await frame.inner_html("body")
                if not html_content:
                    # Fallback to evaluate
                    html_content = await frame.evaluate("() => document.body ? document.body.innerHTML : ''")
            except Exception:
                try:
                    html_content = await frame.evaluate("() => document.body ? document.body.innerHTML : ''")
                except Exception:
                    html_content = ""

            if html_content and len(html_content) > max_length:
                html_content = html_content[:max_length] + "... (truncated)"

        # Build response data
        if content_type == "text":
            data["content"] = text_content
        elif content_type == "html":
            data["content"] = html_content
        else:  # both
            data["text"] = text_content
            data["html"] = html_content

        # Add frame context metadata
        frame_index = page.frames.index(frame)
        frame_context = await _extract_frame_context(frame, frame_index, page)
        data["frame_context"] = frame_context.model_dump()
        data["content_type"] = content_type
        data["length"] = len(text_content or html_content or "")

        return ToolResult(success=True, data=data)

    except Exception as e:
        logger.error(f"Error extracting frame content: {e}")
        return ToolResult(
            success=False,
            error=f"Failed to extract frame content: {str(e)}",
        )


async def _find_frame_by_selector(page: Page, frame_selector: str) -> Frame | None:
    """
    Find frame by selector (name, aria-label, title, or index).

    Args:
        page: Playwright Page instance
        frame_selector: Frame identifier

    Returns:
        Frame object or None if not found
    """
    # Main frame shortcuts
    if frame_selector in ("main", "0"):
        return page.main_frame

    # Try numeric index
    try:
        index = int(frame_selector)
        if 0 <= index < len(page.frames):
            return page.frames[index]
    except ValueError:
        pass

    # Search through frames for matching attributes
    for frame in page.frames:
        # Skip main frame (already handled)
        if frame == page.main_frame:
            continue

        # Try matching by name
        if frame.name == frame_selector:
            return frame

        # Try matching by aria-label or title (need to check iframe element)
        if frame.parent_frame:
            try:
                iframe_elements = await frame.parent_frame.query_selector_all("iframe")
                for iframe_el in iframe_elements:
                    try:
                        content_frame = await iframe_el.content_frame()
                        if content_frame == frame:
                            # Check aria-label
                            aria_label = await iframe_el.get_attribute("aria-label")
                            if aria_label == frame_selector:
                                return frame

                            # Check title
                            title = await iframe_el.get_attribute("title")
                            if title == frame_selector:
                                return frame
                    except Exception:
                        continue
            except Exception:
                continue

    return None


async def _get_available_frame_names(page: Page) -> list[str]:
    """
    Get list of available frame identifiers for error messages.

    Args:
        page: Playwright Page instance

    Returns:
        List of frame identifiers
    """
    names = ["main", "0"]

    for index, frame in enumerate(page.frames):
        if frame == page.main_frame:
            continue

        # Add name
        if frame.name:
            names.append(frame.name)

        # Add aria-label and title from iframe element
        if frame.parent_frame:
            try:
                iframe_elements = await frame.parent_frame.query_selector_all("iframe")
                for iframe_el in iframe_elements:
                    try:
                        content_frame = await iframe_el.content_frame()
                        if content_frame == frame:
                            aria_label = await iframe_el.get_attribute("aria-label")
                            if aria_label:
                                names.append(aria_label)

                            title = await iframe_el.get_attribute("title")
                            if title:
                                names.append(title)
                            break
                    except Exception:
                        continue
            except Exception:
                continue

        # Add index
        names.append(str(index))

    return list(set(names))  # Remove duplicates


@tool(
    name="switch_to_frame",
    description="Switch to a specific frame context for explicit targeting. Returns frame information including frame_selector for use with click/type_text frame parameter.",
    parameters={
        "type": "object",
        "properties": {
            "frame_selector": {
                "type": "string",
                "description": 'Frame selector: "main" or "0" for main frame, frame name (e.g., "search-frame"), aria-label (e.g., "Yandex Search"), title, or index (e.g., "1", "2")',
            },
        },
        "required": ["frame_selector"],
    },
)
async def switch_to_frame(
    page: Page,
    frame_selector: str,
) -> ToolResult:
    """
    Switch to a specific frame context for explicit frame targeting (FR-022).

    Allows user to explicitly set frame context for subsequent operations.
    Returns frame_selector recommendation for use with click/type_text frame parameter.

    Args:
        page: Playwright Page instance
        frame_selector: Frame identifier ("main", name, aria-label, title, or index)

    Returns:
        ToolResult with frame_context and frame_selector recommendation

    Examples:
        >>> # Switch to search iframe
        >>> result = await switch_to_frame(page, "search-frame")
        >>> frame_selector = result.data["frame_selector"]
        >>>
        >>> # Use frame_selector with click
        >>> await click(page, "Search button", frame=frame_selector)

    Requirements: FR-022
    """
    try:
        # Find the target frame
        frame = await _find_frame_by_selector(page, frame_selector)
        if frame is None:
            available = await _get_available_frame_names(page)
            return ToolResult(
                success=False,
                error=f"Frame '{frame_selector}' not found. Available frames: {', '.join(available)}",
            )

        # Check cross-origin accessibility
        if is_cross_origin_frame(frame):
            return ToolResult(
                success=False,
                error=f"Frame '{frame_selector}' is cross-origin and cannot be accessed due to same-origin policy.",
            )

        # Get frame context
        frame_index = page.frames.index(frame)
        frame_context = await _extract_frame_context(frame, frame_index, page)

        # Count interactive elements in target frame
        interactive_count = 0
        try:
            # Try to count interactive elements
            buttons = await frame.query_selector_all("button")
            inputs = await frame.query_selector_all("input")
            links = await frame.query_selector_all("a")
            interactive_count = len(buttons) + len(inputs) + len(links)
        except Exception:
            interactive_count = 0

        # Determine best frame_selector for use with click/type_text
        # Priority: aria-label > title > name > index (matches semantic priority)
        recommended_selector = None
        if frame_context.aria_label:
            recommended_selector = frame_context.aria_label
        elif frame_context.title:
            recommended_selector = frame_context.title
        elif frame_context.name:
            recommended_selector = frame_context.name
        else:
            recommended_selector = str(frame_context.index)

        data = {
            "frame_context": frame_context.model_dump(),
            "frame_selector": recommended_selector,
            "interactive_element_count": interactive_count,
            "message": f"Switched to frame '{frame_selector}'. Use frame='{recommended_selector}' for click/type_text operations.",
        }

        return ToolResult(success=True, data=data)

    except Exception as e:
        logger.error(f"Error switching to frame: {e}")
        return ToolResult(
            success=False,
            error=f"Failed to switch to frame: {str(e)}",
        )


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
