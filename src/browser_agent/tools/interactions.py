"""
Browser Interaction Tools

Implements user interaction tools for the browser automation agent:
- FR-007: Click with natural language element description
- FR-008: Type text into fields
- FR-009: Scroll the page
- FR-004, FR-010: Element search across all frames (iframes)
- FR-015, FR-017: Click retry chain with coordinate_click fallback
- FR-019: Structured error response with all attempts
- FR-020: Configurable timeout_per_frame_ms
"""

import logging
import time
from typing import Literal, Optional, Union
from playwright.async_api import Page, Frame, Locator, TimeoutError as PlaywrightTimeoutError

from .base import tool, ToolResult
from .frame_models import FrameContext, FrameLocatorResult, RetryChain
from .frames import (
    _prioritize_frames,
    _extract_frame_context,
    _check_frame_accessible,
)

logger = logging.getLogger(__name__)


async def _find_element_by_description(
    page_or_frame: Union[Page, Frame],
    description: str,
    role: Optional[str] = None,
) -> tuple[Optional[Locator], Optional[str]]:
    """
    Find an element using natural language description.

    Uses accessibility tree matching to find elements based on their
    accessible name, role, or text content.

    Args:
        page_or_frame: Playwright Page or Frame instance (supports iframe search)
        description: Natural language description of the element
        role: Optional ARIA role to filter by

    Returns:
        Tuple of (locator, error_message)
    """
    description_lower = description.lower()

    # Strategy 1: Try getByRole with name if role is specified
    if role:
        try:
            locator = page_or_frame.get_by_role(role, name=description)
            if await locator.count() > 0:
                return locator.first, None
        except Exception:
            pass

    # Strategy 2: Try common roles with exact name
    common_roles = ["button", "link", "textbox", "checkbox", "radio", "combobox"]
    for r in common_roles:
        try:
            locator = page_or_frame.get_by_role(r, name=description)
            if await locator.count() > 0:
                return locator.first, None
        except Exception:
            pass

    # Strategy 3: Try getByText for text content match
    try:
        locator = page_or_frame.get_by_text(description, exact=False)
        if await locator.count() > 0:
            return locator.first, None
    except Exception:
        pass

    # Strategy 4: Try getByLabel for form fields
    try:
        locator = page_or_frame.get_by_label(description)
        if await locator.count() > 0:
            return locator.first, None
    except Exception:
        pass

    # Strategy 5: Try getByPlaceholder for inputs
    try:
        locator = page_or_frame.get_by_placeholder(description)
        if await locator.count() > 0:
            return locator.first, None
    except Exception:
        pass

    # Strategy 6: Try getByTitle
    try:
        locator = page_or_frame.get_by_title(description)
        if await locator.count() > 0:
            return locator.first, None
    except Exception:
        pass

    # Strategy 7: Try getByAltText for images
    try:
        locator = page_or_frame.get_by_alt_text(description)
        if await locator.count() > 0:
            return locator.first, None
    except Exception:
        pass

    # Strategy 8: Partial text matching in accessibility snapshot (using modern aria_snapshot)
    try:
        yaml_snapshot = await page_or_frame.locator("body").aria_snapshot()
        if yaml_snapshot:
            matching_names = _find_matching_names_from_yaml(yaml_snapshot, description_lower)
            for name in matching_names:
                for r in common_roles:
                    try:
                        locator = page_or_frame.get_by_role(r, name=name)
                        if await locator.count() > 0:
                            return locator.first, None
                    except Exception:
                        pass
    except Exception:
        pass

    return None, f"Could not find element matching: '{description}'"


def _find_matching_names_from_yaml(
    yaml_str: str,
    search_term: str,
) -> list[str]:
    """
    Find accessible names in aria_snapshot YAML that match search term.

    The aria_snapshot() returns YAML like:
        - heading "todos"
        - textbox "What needs to be done?"
        - button "Submit"

    Args:
        yaml_str: YAML string from aria_snapshot()
        search_term: Lowercase search term

    Returns:
        List of matching names
    """
    import re

    found = []
    for line in yaml_str.strip().split('\n'):
        # Extract name from YAML line: - role "name"
        match = re.search(r'"([^"]+)"', line)
        if match:
            name = match.group(1)
            if name and search_term in name.lower():
                found.append(name)

    return found


async def _get_main_frame_context(page: Page) -> dict:
    """
    Get the context dictionary for the main frame.

    Used by interaction tools to include frame_context in ToolResult.data
    when operating on the main frame (FR-011).

    Args:
        page: Playwright Page instance

    Returns:
        Dictionary representation of the main frame's FrameContext
    """
    main_frame = page.main_frame
    return FrameContext(
        name=main_frame.name or "main",
        index=0,
        src=main_frame.url,
        aria_label=None,
        title=None,
        accessible=True,
        parent_index=None,
    ).model_dump()


def _build_retry_strategies(
    page: Page,
    element_description: str,
    role: Optional[str] = None,
    explicit_frame: Optional[str] = None,
) -> list[str]:
    """Build the list of retry strategies for click/type_text operations.

    Constructs an ordered list of strategies to try:
    1. If explicit frame specified: only that frame
    2. If no explicit frame: main_frame -> prioritized iframes -> coordinate_click

    Implements FR-015: Multi-strategy retry chain for element interaction.

    Args:
        page: Playwright Page instance
        element_description: Description of element to interact with
        role: Optional ARIA role filter
        explicit_frame: Optional specific frame name/aria-label

    Returns:
        List of strategy names to try in order
    """
    if explicit_frame:
        # Only try the specified frame
        return [f"frame:{explicit_frame}"]

    # Build prioritized frame list
    strategies = ["main_frame"]

    # Add prioritized iframes by semantic labels
    frame_contexts = []
    for index, frame in enumerate(page.frames):
        if index == 0:  # Skip main frame
            continue
        ctx = FrameContext(
            name=frame.name,
            index=index,
            src=frame.url,
            aria_label=None,  # Will be populated if needed
            title=None,
            accessible=True,  # Assume accessible, will be checked during attempt
            parent_index=None,
        )
        frame_contexts.append(ctx)

    prioritized = _prioritize_frames(frame_contexts, include_inaccessible=False)

    # Add iframe strategies in priority order
    for frame_ctx in prioritized:
        label = frame_ctx.aria_label or frame_ctx.title or frame_ctx.name
        if label:
            strategies.append(f"iframe:{label}")
        else:
            strategies.append(f"iframe:{frame_ctx.index}")

    # Coordinate click is final fallback
    strategies.append("coordinate_click")

    return strategies


async def _try_click_in_frame(
    page: Page,
    frame: Union[Page, Frame],
    element_description: str,
    role: Optional[str],
    double_click: bool,
    right_click: bool,
    timeout_ms: int,
) -> tuple[bool, Optional[str], Optional[dict], int]:
    """Attempt a click operation in a specific frame.

    Args:
        page: Playwright Page instance
        frame: Frame to search in
        element_description: Element description
        role: Optional ARIA role filter
        double_click: Whether to double-click
        right_click: Whether to right-click
        timeout_ms: Timeout in milliseconds

    Returns:
        Tuple of (success, error_message, result_data, duration_ms)
    """
    start_time = time.time()

    try:
        locator, error = await _find_element_by_description(
            frame, element_description, role
        )

        if locator is None:
            duration_ms = int((time.time() - start_time) * 1000)
            return False, error, None, duration_ms

        # Ensure element is visible and clickable
        await locator.wait_for(state="visible", timeout=timeout_ms)

        # Get element info before clicking
        tag_name = await locator.evaluate("el => el.tagName")
        element_text = await locator.text_content() or ""
        if len(element_text) > 50:
            element_text = element_text[:47] + "..."

        # Perform click
        if double_click:
            await locator.dblclick()
            click_type = "double-clicked"
        elif right_click:
            await locator.click(button="right")
            click_type = "right-clicked"
        else:
            await locator.click()
            click_type = "clicked"

        duration_ms = int((time.time() - start_time) * 1000)

        result_data = {
            "action": click_type,
            "element": element_description,
            "tag": tag_name,
            "text": element_text,
        }

        return True, None, result_data, duration_ms

    except PlaywrightTimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)
        return False, "Timeout waiting for element", None, duration_ms

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return False, str(e), None, duration_ms


async def _try_type_in_frame(
    page: Page,
    frame: Union[Page, Frame],
    element_description: str,
    text: str,
    clear_first: bool,
    press_enter: bool,
    timeout_ms: int,
) -> tuple[bool, Optional[str], Optional[dict], int]:
    """Attempt a type_text operation in a specific frame.

    Args:
        page: Playwright Page instance
        frame: Frame to search in
        element_description: Element description
        text: Text to type
        clear_first: Whether to clear field first
        press_enter: Whether to press Enter after
        timeout_ms: Timeout in milliseconds

    Returns:
        Tuple of (success, error_message, result_data, duration_ms)
    """
    start_time = time.time()

    try:
        # Try to find textbox first
        locator, error = await _find_element_by_description(
            frame, element_description, role="textbox"
        )

        if locator is None:
            # Try without role restriction
            locator, error = await _find_element_by_description(
                frame, element_description
            )

        if locator is None:
            duration_ms = int((time.time() - start_time) * 1000)
            return False, error, None, duration_ms

        # Ensure element is visible and editable
        await locator.wait_for(state="visible", timeout=timeout_ms)

        # Clear field if requested
        if clear_first:
            await locator.clear()

        # Type text
        await locator.fill(text)

        # Press Enter if requested
        if press_enter:
            await locator.press("Enter")

        duration_ms = int((time.time() - start_time) * 1000)

        result_data = {
            "action": "typed",
            "element": element_description,
            "text": text if len(text) <= 50 else text[:47] + "...",
            "text_entered": text,
            "pressed_enter": press_enter,
        }

        return True, None, result_data, duration_ms

    except PlaywrightTimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)
        return False, "Timeout waiting for element", None, duration_ms

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return False, str(e), None, duration_ms


async def _detect_iframe_interception(
    page: Page,
    locator: Locator,
) -> Optional[FrameContext]:
    """
    Detect if an element is being intercepted (blocked) by an iframe overlay.

    When a click times out, it may be because an iframe is positioned over
    the element, preventing normal click interaction. This function checks
    if any iframe on the page overlaps with the element's bounding box.

    Implements FR-018: iframe interception detection on TimeoutError.

    Args:
        page: Playwright Page instance
        locator: Locator for the element that failed to click

    Returns:
        FrameContext of the overlapping iframe if found, None otherwise
    """
    try:
        # Get element's bounding box center coordinates
        box = await locator.bounding_box()
        if not box:
            # Element has no bounding box (hidden or display: none)
            return None

        # Calculate center of the element
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2

        # Check each iframe to see if it overlaps the element
        for idx, frame in enumerate(page.frames):
            if idx == 0:  # Skip main frame
                continue

            try:
                # Get frame's element (the iframe tag in the parent page)
                frame_element = await frame.frame_element()
                if frame_element is None:
                    continue

                # Get iframe's bounding box
                iframe_box = await frame_element.bounding_box()
                if not iframe_box:
                    continue

                # Check if element's center is within iframe's bounds
                if (
                    iframe_box["x"] <= center_x <= iframe_box["x"] + iframe_box["width"]
                    and iframe_box["y"] <= center_y <= iframe_box["y"] + iframe_box["height"]
                ):
                    # Element is being intercepted by this iframe
                    frame_context = await _extract_frame_context(frame, idx, page)

                    logger.warning(
                        f"[Frame Interception] Element click blocked by iframe at index {idx} "
                        f"(name: {frame_context.name or 'none'}, "
                        f"aria-label: {frame_context.aria_label or 'none'})"
                    )

                    return frame_context

            except Exception:
                # Skip frames that can't be accessed
                continue

        return None

    except Exception as e:
        logger.debug(f"Error detecting iframe interception: {e}")
        return None


async def _find_element_in_all_frames(
    page: Page,
    description: str,
    role: Optional[str] = None,
) -> FrameLocatorResult:
    """
    Find an element across all frames (main frame and iframes).

    Searches frames in priority order: main frame first, then iframes
    sorted by semantic labels (aria-label > title > name > none).

    Implements FR-004 (element search across frames) and FR-010 (iframe fallback).

    Args:
        page: Playwright Page instance
        description: Natural language description of the element
        role: Optional ARIA role to filter by

    Returns:
        FrameLocatorResult with:
        - found: True if element was found
        - frame_context: FrameContext of the frame containing the element
        - locator: Playwright Locator for the element
        - search_strategy: Strategy that found the element
        - locator_description: The description used to find the element

    Examples:
        >>> result = await _find_element_in_all_frames(page, "Search input")
        >>> if result.found:
        ...     await result.locator.fill("test query")
        ...     print(f"Found in frame {result.frame_context.index}")
    """
    # Build frame contexts for all frames
    frame_contexts: list[FrameContext] = []
    for index, frame in enumerate(page.frames):
        frame_context = await _extract_frame_context(frame, index, page)
        frame_context.accessible = await _check_frame_accessible(frame)
        frame_contexts.append(frame_context)

    # Prioritize frames for search order
    prioritized_frames = _prioritize_frames(frame_contexts, include_inaccessible=False)

    # FR-016: Log frame context switch - beginning cross-frame search
    logger.info(
        f"[Frame Search] Searching for '{description}' across {len(prioritized_frames)} "
        f"accessible frames (total: {len(page.frames)})"
    )

    # Search each frame in priority order
    searched_frames = []
    previous_frame_index = None
    for frame_context in prioritized_frames:
        frame = page.frames[frame_context.index]
        searched_frames.append(frame_context.index)

        # FR-016: Log frame context switch when moving to a new frame
        if previous_frame_index is not None:
            logger.info(
                f"[Frame Switch] Switching from frame {previous_frame_index} "
                f"to frame {frame_context.index}"
            )

        frame_label = frame_context.aria_label or frame_context.title or frame_context.name
        logger.info(
            f"[Frame Search] Searching frame {frame_context.index} "
            f"(label: {frame_label or 'none'})"
        )
        previous_frame_index = frame_context.index

        try:
            locator, error = await _find_element_by_description(
                frame, description, role
            )

            if locator is not None:
                # FR-016: Log frame context when element is found
                frame_label = frame_context.aria_label or frame_context.title or frame_context.name
                if frame_context.index == 0:
                    logger.info(
                        f"[Frame Search] Element '{description}' found in main frame"
                    )
                else:
                    logger.info(
                        f"[Frame Search] Element '{description}' found in iframe {frame_context.index} "
                        f"(label: {frame_label or 'none'}, src: {frame_context.src or 'none'})"
                    )
                return FrameLocatorResult(
                    found=True,
                    frame_context=frame_context,
                    locator=locator,
                    locator_description=description,
                    search_strategy="prioritized_frame_search",
                    confidence_score=1.0 if frame_context.index == 0 else 0.9,
                )
        except Exception as e:
            logger.debug(
                f"Error searching frame {frame_context.index}: {e}"
            )
            continue

    # Element not found in any frame
    # FR-016: Log search completion with all frames searched
    logger.info(
        f"[Frame Search] Element '{description}' not found in any frame "
        f"(searched {len(searched_frames)} frames: {searched_frames})"
    )
    return FrameLocatorResult(
        found=False,
        frame_context=None,
        locator=None,
        locator_description=description,
        search_strategy="prioritized_frame_search",
        confidence_score=0.0,
    )


@tool(
    name="click",
    description="Click on an element described in natural language. Automatically searches across all frames (main page and iframes). Uses accessibility tree and multiple strategies to find the element.",
    parameters={
        "type": "object",
        "properties": {
            "element_description": {
                "type": "string",
                "description": "Natural language description of the element to click (e.g., 'Submit button', 'Login link', 'Search field')",
            },
            "role": {
                "type": "string",
                "description": "Optional ARIA role to filter by (e.g., 'button', 'link', 'textbox')",
            },
            "double_click": {
                "type": "boolean",
                "description": "Whether to double-click (default: false)",
            },
            "right_click": {
                "type": "boolean",
                "description": "Whether to right-click (default: false)",
            },
            "frame": {
                "type": "string",
                "description": "Optional frame name/aria-label to search in. If not specified, searches all frames automatically.",
            },
            "timeout_per_frame_ms": {
                "type": "integer",
                "description": "Timeout for each frame attempt in milliseconds (default: 10000)",
            },
        },
        "required": ["element_description"],
    },
)
async def click(
    page: Page,
    element_description: str,
    role: Optional[str] = None,
    double_click: bool = False,
    right_click: bool = False,
    frame: Optional[str] = None,
    timeout_per_frame_ms: int = 10000,
) -> ToolResult:
    """
    Click on an element with automatic iframe search and retry chain.

    Implements FR-013: click supports frame parameter and auto-search.
    Implements FR-011: Returns frame_context in ToolResult.data.
    Implements FR-015, FR-017: Multi-strategy retry chain with coordinate_click fallback.
    Implements FR-019: Structured error response with all attempts.
    Implements FR-020: Configurable timeout_per_frame_ms.

    Args:
        page: Playwright Page instance
        element_description: Description of element to click
        role: Optional ARIA role filter
        double_click: Whether to double-click
        right_click: Whether to right-click
        frame: Optional frame name/aria-label to search in
        timeout_per_frame_ms: Timeout for each frame attempt (default 10000)

    Returns:
        ToolResult indicating success or failure with frame_context and retry info
    """
    # Build retry strategies
    strategies = _build_retry_strategies(page, element_description, role, frame)

    # Create RetryChain with FR-020 configurable timeout
    retry_chain = RetryChain(
        strategies=strategies,
        max_attempts=len(strategies),
        timeout_per_frame_ms=timeout_per_frame_ms,
    )

    logger.info(
        f"[Retry Chain] Starting click for '{element_description}' "
        f"with {len(strategies)} strategies: {strategies}"
    )

    # Try each strategy in sequence
    while not retry_chain.is_exhausted:
        strategy = retry_chain.current_strategy
        start_time = time.time()

        logger.info(f"[Retry Chain] Attempting strategy {retry_chain.current_index + 1}/{len(strategies)}: {strategy}")

        try:
            # Parse strategy and execute appropriate click method
            if strategy == "main_frame":
                success, error, result_data, duration_ms = await _try_click_in_frame(
                    page,
                    page.main_frame,
                    element_description,
                    role,
                    double_click,
                    right_click,
                    retry_chain.timeout_per_frame_ms,
                )

                # Get main frame context
                frame_ctx = await _get_main_frame_context(page)

                if success:
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=True,
                        duration_ms=duration_ms,
                        error=None,
                        frame_context=FrameContext(**frame_ctx),
                    )
                    result_data["frame_context"] = frame_ctx
                    result_data["retry_chain"] = retry_chain.to_error_dict()

                    logger.info(f"[Retry Chain] Strategy '{strategy}' succeeded in {duration_ms}ms")

                    return ToolResult(
                        success=True,
                        data=result_data,
                        metadata={
                            "description": element_description,
                            "role": role,
                            "frame": frame,
                        },
                    )
                else:
                    # Record failed attempt
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=False,
                        duration_ms=duration_ms,
                        error=error,
                        frame_context=FrameContext(**frame_ctx),
                    )
                    logger.warning(f"[Retry Chain] Strategy '{strategy}' failed: {error}")
                    retry_chain.advance()
                    continue

            elif strategy.startswith("iframe:"):
                # Extract frame identifier
                frame_id = strategy[len("iframe:"):]
                target_frame = None
                frame_ctx = None

                # Find frame by name, aria-label, title, or index
                for idx, f in enumerate(page.frames):
                    ctx = await _extract_frame_context(f, idx, page)
                    if (
                        f.name == frame_id
                        or ctx.aria_label == frame_id
                        or ctx.title == frame_id
                        or str(idx) == frame_id
                    ):
                        target_frame = f
                        frame_ctx = ctx
                        break

                if target_frame is None:
                    duration_ms = int((time.time() - start_time) * 1000)
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=False,
                        duration_ms=duration_ms,
                        error=f"Frame '{frame_id}' not found",
                        frame_context=None,
                    )
                    logger.warning(f"[Retry Chain] Strategy '{strategy}' failed: Frame not found")
                    retry_chain.advance()
                    continue

                # Try clicking in the iframe
                success, error, result_data, duration_ms = await _try_click_in_frame(
                    page,
                    target_frame,
                    element_description,
                    role,
                    double_click,
                    right_click,
                    retry_chain.timeout_per_frame_ms,
                )

                if success:
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=True,
                        duration_ms=duration_ms,
                        error=None,
                        frame_context=frame_ctx,
                    )
                    result_data["frame_context"] = frame_ctx.model_dump()
                    result_data["retry_chain"] = retry_chain.to_error_dict()

                    logger.info(f"[Retry Chain] Strategy '{strategy}' succeeded in {duration_ms}ms")

                    return ToolResult(
                        success=True,
                        data=result_data,
                        metadata={
                            "description": element_description,
                            "role": role,
                            "frame": frame,
                        },
                    )
                else:
                    # Record failed attempt
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=False,
                        duration_ms=duration_ms,
                        error=error,
                        frame_context=frame_ctx,
                    )
                    logger.warning(f"[Retry Chain] Strategy '{strategy}' failed: {error}")
                    retry_chain.advance()
                    continue

            elif strategy == "coordinate_click":
                # Coordinate click fallback - need to find element first
                locator = None
                frame_ctx = None

                # Try to find element in any frame for coordinate calculation
                for idx, f in enumerate(page.frames):
                    loc, err = await _find_element_by_description(f, element_description, role)
                    if loc is not None:
                        locator = loc
                        frame_ctx = await _extract_frame_context(f, idx, page)
                        break

                if locator is None:
                    duration_ms = int((time.time() - start_time) * 1000)
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=False,
                        duration_ms=duration_ms,
                        error="Could not find element for coordinate click",
                        frame_context=None,
                    )
                    logger.warning(f"[Retry Chain] Strategy '{strategy}' failed: Element not found")
                    retry_chain.advance()
                    continue

                # Try coordinate click
                coord_result = await coordinate_click(page, locator)
                duration_ms = int((time.time() - start_time) * 1000)

                if coord_result.success:
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=True,
                        duration_ms=duration_ms,
                        error=None,
                        frame_context=frame_ctx,
                    )

                    logger.info(f"[Retry Chain] Strategy '{strategy}' succeeded in {duration_ms}ms")

                    # Get main frame context if none available
                    if frame_ctx is None:
                        frame_ctx = FrameContext(**(await _get_main_frame_context(page)))

                    return ToolResult(
                        success=True,
                        data={
                            "action": "coordinate-clicked",
                            "element": element_description,
                            "method": "retry_chain",
                            "click_type": "coordinate-clicked",
                            "frame_context": frame_ctx.model_dump(),
                            "coordinates": {
                                "x": coord_result.data.get("center_x"),
                                "y": coord_result.data.get("center_y"),
                            },
                            "bounding_box": coord_result.data.get("bounding_box"),
                            "retry_chain": retry_chain.to_error_dict(),
                        },
                        metadata={
                            "description": element_description,
                            "role": role,
                            "frame": frame,
                        },
                    )
                else:
                    # Record failed attempt
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=False,
                        duration_ms=duration_ms,
                        error=coord_result.error,
                        frame_context=frame_ctx,
                    )
                    logger.warning(f"[Retry Chain] Strategy '{strategy}' failed: {coord_result.error}")
                    retry_chain.advance()
                    continue

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            retry_chain.add_attempt(
                strategy=strategy,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
                frame_context=None,
            )
            logger.warning(f"[Retry Chain] Strategy '{strategy}' raised exception: {e}")
            retry_chain.advance()
            continue

    # All strategies exhausted - return structured error (FR-019)
    logger.error(f"[Retry Chain] All {len(strategies)} strategies exhausted for '{element_description}'")

    return ToolResult(
        success=False,
        error=f"Click failed after {len(strategies)} attempts",
        data={
            "retry_chain": retry_chain.to_error_dict(),
            "element_description": element_description,
        },
        metadata={
            "description": element_description,
            "role": role,
            "frame": frame,
        },
    )


@tool(
    name="type_text",
    description="Type text into an input field described in natural language. Automatically searches across all frames (main page and iframes). Optionally clears the field first.",
    parameters={
        "type": "object",
        "properties": {
            "element_description": {
                "type": "string",
                "description": "Natural language description of the input field (e.g., 'Search box', 'Email field', 'Username input')",
            },
            "text": {
                "type": "string",
                "description": "Text to type into the field",
            },
            "clear_first": {
                "type": "boolean",
                "description": "Whether to clear the field before typing (default: true)",
            },
            "press_enter": {
                "type": "boolean",
                "description": "Whether to press Enter after typing (default: false)",
            },
            "frame": {
                "type": "string",
                "description": "Optional frame name/aria-label to search in. If not specified, searches all frames automatically.",
            },
            "timeout_per_frame_ms": {
                "type": "integer",
                "description": "Timeout for each frame attempt in milliseconds (default: 10000)",
            },
        },
        "required": ["element_description", "text"],
    },
)
async def type_text(
    page: Page,
    element_description: str,
    text: str,
    clear_first: bool = True,
    press_enter: bool = False,
    frame: Optional[str] = None,
    timeout_per_frame_ms: int = 10000,
) -> ToolResult:
    """
    Type text into an input field with automatic iframe search and retry chain.

    Implements FR-014: type_text supports frame parameter and auto-search.
    Implements FR-011: Returns frame_context in ToolResult.data.
    Implements FR-015, FR-017: Multi-strategy retry chain for element interaction.
    Implements FR-019: Structured error response with all attempts.
    Implements FR-020: Configurable timeout_per_frame_ms.

    Args:
        page: Playwright Page instance
        element_description: Description of the input field
        text: Text to type
        clear_first: Whether to clear field first
        press_enter: Whether to press Enter after
        frame: Optional frame name/aria-label to search in
        timeout_per_frame_ms: Timeout for each frame attempt (default 10000)

    Returns:
        ToolResult indicating success or failure with frame_context and retry info
    """
    # Build retry strategies (note: type_text doesn't use coordinate_click fallback)
    strategies = _build_retry_strategies(page, element_description, None, frame)
    # Remove coordinate_click from strategies for type_text
    strategies = [s for s in strategies if not s.startswith("coordinate")]

    # Create RetryChain with FR-020 configurable timeout
    retry_chain = RetryChain(
        strategies=strategies,
        max_attempts=len(strategies),
        timeout_per_frame_ms=timeout_per_frame_ms,
    )

    logger.info(
        f"[Retry Chain] Starting type_text for '{element_description}' "
        f"with {len(strategies)} strategies: {strategies}"
    )

    # Try each strategy in sequence
    while not retry_chain.is_exhausted:
        strategy = retry_chain.current_strategy
        start_time = time.time()

        logger.info(f"[Retry Chain] Attempting strategy {retry_chain.current_index + 1}/{len(strategies)}: {strategy}")

        try:
            # Parse strategy and execute appropriate type_text method
            if strategy == "main_frame":
                success, error, result_data, duration_ms = await _try_type_in_frame(
                    page,
                    page.main_frame,
                    element_description,
                    text,
                    clear_first,
                    press_enter,
                    retry_chain.timeout_per_frame_ms,
                )

                # Get main frame context
                frame_ctx = await _get_main_frame_context(page)

                if success:
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=True,
                        duration_ms=duration_ms,
                        error=None,
                        frame_context=FrameContext(**frame_ctx),
                    )
                    result_data["frame_context"] = frame_ctx
                    result_data["retry_chain"] = retry_chain.to_error_dict()

                    logger.info(f"[Retry Chain] Strategy '{strategy}' succeeded in {duration_ms}ms")

                    return ToolResult(
                        success=True,
                        data=result_data,
                        metadata={
                            "description": element_description,
                            "full_text_length": len(text),
                            "frame": frame,
                        },
                    )
                else:
                    # Record failed attempt
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=False,
                        duration_ms=duration_ms,
                        error=error,
                        frame_context=FrameContext(**frame_ctx),
                    )
                    logger.warning(f"[Retry Chain] Strategy '{strategy}' failed: {error}")
                    retry_chain.advance()
                    continue

            elif strategy.startswith("iframe:"):
                # Extract frame identifier
                frame_id = strategy[len("iframe:"):]
                target_frame = None
                frame_ctx = None

                # Find frame by name, aria-label, title, or index
                for idx, f in enumerate(page.frames):
                    ctx = await _extract_frame_context(f, idx, page)
                    if (
                        f.name == frame_id
                        or ctx.aria_label == frame_id
                        or ctx.title == frame_id
                        or str(idx) == frame_id
                    ):
                        target_frame = f
                        frame_ctx = ctx
                        break

                if target_frame is None:
                    duration_ms = int((time.time() - start_time) * 1000)
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=False,
                        duration_ms=duration_ms,
                        error=f"Frame '{frame_id}' not found",
                        frame_context=None,
                    )
                    logger.warning(f"[Retry Chain] Strategy '{strategy}' failed: Frame not found")
                    retry_chain.advance()
                    continue

                # Try typing in the iframe
                success, error, result_data, duration_ms = await _try_type_in_frame(
                    page,
                    target_frame,
                    element_description,
                    text,
                    clear_first,
                    press_enter,
                    retry_chain.timeout_per_frame_ms,
                )

                if success:
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=True,
                        duration_ms=duration_ms,
                        error=None,
                        frame_context=frame_ctx,
                    )
                    result_data["frame_context"] = frame_ctx.model_dump()
                    result_data["retry_chain"] = retry_chain.to_error_dict()

                    logger.info(f"[Retry Chain] Strategy '{strategy}' succeeded in {duration_ms}ms")

                    return ToolResult(
                        success=True,
                        data=result_data,
                        metadata={
                            "description": element_description,
                            "full_text_length": len(text),
                            "frame": frame,
                        },
                    )
                else:
                    # Record failed attempt
                    retry_chain.add_attempt(
                        strategy=strategy,
                        success=False,
                        duration_ms=duration_ms,
                        error=error,
                        frame_context=frame_ctx,
                    )
                    logger.warning(f"[Retry Chain] Strategy '{strategy}' failed: {error}")
                    retry_chain.advance()
                    continue

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            retry_chain.add_attempt(
                strategy=strategy,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
                frame_context=None,
            )
            logger.warning(f"[Retry Chain] Strategy '{strategy}' raised exception: {e}")
            retry_chain.advance()
            continue

    # All strategies exhausted - return structured error (FR-019)
    logger.error(f"[Retry Chain] All {len(strategies)} strategies exhausted for '{element_description}'")

    return ToolResult(
        success=False,
        error=f"Type text failed after {len(strategies)} attempts",
        data={
            "retry_chain": retry_chain.to_error_dict(),
            "element_description": element_description,
        },
        metadata={
            "description": element_description,
            "frame": frame,
        },
    )


@tool(
    name="scroll",
    description="Scroll the page or a specific element. Can scroll by direction, to an element, or to specific coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["up", "down", "left", "right"],
                "description": "Direction to scroll",
            },
            "amount": {
                "type": "integer",
                "description": "Pixels to scroll (default: 500)",
            },
            "to_element": {
                "type": "string",
                "description": "Natural language description of element to scroll to",
            },
            "to_top": {
                "type": "boolean",
                "description": "Scroll to top of page",
            },
            "to_bottom": {
                "type": "boolean",
                "description": "Scroll to bottom of page",
            },
        },
    },
)
async def scroll(
    page: Page,
    direction: Optional[Literal["up", "down", "left", "right"]] = None,
    amount: int = 500,
    to_element: Optional[str] = None,
    to_top: bool = False,
    to_bottom: bool = False,
) -> ToolResult:
    """
    Scroll the page.

    Args:
        page: Playwright Page instance
        direction: Scroll direction
        amount: Pixels to scroll
        to_element: Element to scroll to
        to_top: Scroll to page top
        to_bottom: Scroll to page bottom

    Returns:
        ToolResult indicating success or failure
    """
    try:
        # Get initial scroll position
        initial_scroll = await page.evaluate(
            "() => ({ x: window.scrollX, y: window.scrollY })"
        )

        # Frame context for element-based scrolling (FR-011)
        element_frame_context = None

        if to_top:
            await page.evaluate("window.scrollTo(0, 0)")
            action = "scrolled to top"

        elif to_bottom:
            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            action = "scrolled to bottom"

        elif to_element:
            locator, error = await _find_element_by_description(page, to_element)
            if locator is None:
                return ToolResult(
                    success=False,
                    error=error,
                    metadata={"to_element": to_element},
                )
            await locator.scroll_into_view_if_needed()
            action = f"scrolled to element: {to_element}"
            # Get main frame context for FR-011 compliance (element scroll)
            element_frame_context = await _get_main_frame_context(page)

        elif direction:
            dx = 0
            dy = 0
            if direction == "up":
                dy = -amount
            elif direction == "down":
                dy = amount
            elif direction == "left":
                dx = -amount
            elif direction == "right":
                dx = amount

            await page.evaluate(f"window.scrollBy({dx}, {dy})")
            action = f"scrolled {direction} by {amount}px"

        else:
            # Default: scroll down
            await page.evaluate(f"window.scrollBy(0, {amount})")
            action = f"scrolled down by {amount}px"

        # Get final scroll position
        final_scroll = await page.evaluate(
            "() => ({ x: window.scrollX, y: window.scrollY })"
        )

        # Build result data with optional frame_context (FR-011)
        result_data = {
            "action": action,
            "scroll_from": initial_scroll,
            "scroll_to": final_scroll,
        }
        if element_frame_context is not None:
            result_data["frame_context"] = element_frame_context

        return ToolResult(
            success=True,
            data=result_data,
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Scroll failed: {e!s}",
        )


@tool(
    name="hover",
    description="Hover over an element to reveal tooltips or dropdown menus.",
    parameters={
        "type": "object",
        "properties": {
            "element_description": {
                "type": "string",
                "description": "Natural language description of the element to hover over",
            },
        },
        "required": ["element_description"],
    },
)
async def hover(
    page: Page,
    element_description: str,
) -> ToolResult:
    """
    Hover over an element.

    Args:
        page: Playwright Page instance
        element_description: Description of element to hover

    Returns:
        ToolResult indicating success or failure
    """
    try:
        locator, error = await _find_element_by_description(
            page, element_description
        )

        if locator is None:
            return ToolResult(
                success=False,
                error=error,
                metadata={"description": element_description},
            )

        await locator.wait_for(state="visible", timeout=5000)
        await locator.hover()

        # Get main frame context for FR-011 compliance
        frame_context = await _get_main_frame_context(page)

        return ToolResult(
            success=True,
            data={
                "action": "hovered",
                "element": element_description,
                "frame_context": frame_context,  # FR-011: Include frame context
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Hover failed: {e!s}",
            metadata={"description": element_description},
        )


@tool(
    name="select_option",
    description="Select an option from a dropdown or select element.",
    parameters={
        "type": "object",
        "properties": {
            "element_description": {
                "type": "string",
                "description": "Natural language description of the select/dropdown",
            },
            "option": {
                "type": "string",
                "description": "Option to select (by visible text)",
            },
        },
        "required": ["element_description", "option"],
    },
)
async def select_option(
    page: Page,
    element_description: str,
    option: str,
) -> ToolResult:
    """
    Select an option from a dropdown.

    Args:
        page: Playwright Page instance
        element_description: Description of the select element
        option: Option text to select

    Returns:
        ToolResult indicating success or failure
    """
    try:
        locator, error = await _find_element_by_description(
            page, element_description, role="combobox"
        )

        if locator is None:
            # Try without role restriction
            locator, error = await _find_element_by_description(
                page, element_description
            )

        if locator is None:
            return ToolResult(
                success=False,
                error=error,
                metadata={"description": element_description},
            )

        await locator.wait_for(state="visible", timeout=5000)
        await locator.select_option(label=option)

        # Get main frame context for FR-011 compliance
        frame_context = await _get_main_frame_context(page)

        return ToolResult(
            success=True,
            data={
                "action": "selected",
                "element": element_description,
                "option": option,
                "frame_context": frame_context,  # FR-011: Include frame context
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Select failed: {e!s}",
            metadata={"description": element_description, "option": option},
        )


async def coordinate_click(
    page: Page,
    locator: Locator,
    frame: Optional[Frame] = None,
) -> ToolResult:
    """
    Click at the center coordinates of an element using page.mouse.click.

    This is a fallback click method (FR-024) used when standard click() fails
    due to iframe overlays or other interception issues. It calculates the
    center point of the element's bounding box and performs a raw mouse click.

    Args:
        page: Playwright Page instance
        locator: Playwright Locator for the target element
        frame: Optional Frame if the element is inside an iframe

    Returns:
        ToolResult with:
        - success: True if click succeeded
        - data.method: "coordinate_click"
        - data.center_x: X coordinate of click
        - data.center_y: Y coordinate of click
        - error: Message if click failed (e.g., hidden element)

    Examples:
        >>> button = page.locator("#submit-btn")
        >>> result = await coordinate_click(page, button)
        >>> if result.success:
        ...     print(f"Clicked at ({result.data['center_x']}, {result.data['center_y']})")
    """
    try:
        # First check if element has a bounding box (fails fast for hidden elements)
        bounding_box = await locator.bounding_box()

        if bounding_box is None:
            return ToolResult(
                success=False,
                error="Element has no bounding box (may be hidden or not rendered)",
                metadata={"method": "coordinate_click"},
            )

        # Scroll element into view if needed (handles elements outside viewport)
        await locator.scroll_into_view_if_needed()

        # Get updated bounding box after scrolling (position may have changed)
        bounding_box = await locator.bounding_box()

        if bounding_box is None:
            return ToolResult(
                success=False,
                error="Element has no bounding box after scrolling",
                metadata={"method": "coordinate_click"},
            )

        # Calculate center coordinates
        center_x = bounding_box["x"] + bounding_box["width"] / 2
        center_y = bounding_box["y"] + bounding_box["height"] / 2

        # Perform click at coordinates using page.mouse.click
        # Note: If in iframe, coordinates are relative to iframe's position in page
        await page.mouse.click(center_x, center_y)

        logger.info(
            f"[Coordinate Click] Clicked at ({center_x:.1f}, {center_y:.1f}) "
            f"(element box: {bounding_box['width']:.0f}x{bounding_box['height']:.0f})"
        )

        return ToolResult(
            success=True,
            data={
                "method": "coordinate_click",
                "center_x": center_x,
                "center_y": center_y,
                "bounding_box": bounding_box,
            },
            metadata={
                "frame": frame.name if frame else None,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Coordinate click failed: {e!s}",
            metadata={"method": "coordinate_click"},
        )
