"""
Browser Interaction Tools

Implements user interaction tools for the browser automation agent:
- FR-007: Click with natural language element description
- FR-008: Type text into fields
- FR-009: Scroll the page
- FR-004, FR-010: Element search across all frames (iframes)
"""

import logging
from typing import Literal, Optional, Union
from playwright.async_api import Page, Frame, Locator

from .base import tool, ToolResult
from .frame_models import FrameContext, FrameLocatorResult
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

    logger.debug(
        f"Searching for '{description}' across {len(prioritized_frames)} accessible frames "
        f"(total: {len(page.frames)})"
    )

    # Search each frame in priority order
    searched_frames = []
    for frame_context in prioritized_frames:
        frame = page.frames[frame_context.index]
        searched_frames.append(frame_context.index)

        logger.debug(
            f"Searching frame {frame_context.index} "
            f"(name: {frame_context.name}, aria_label: {frame_context.aria_label})"
        )

        try:
            locator, error = await _find_element_by_description(
                frame, description, role
            )

            if locator is not None:
                logger.debug(
                    f"Element '{description}' found in frame {frame_context.index}"
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
    logger.debug(
        f"Element '{description}' not found in any frame "
        f"(searched frames: {searched_frames})"
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
    description="Click on an element described in natural language. Uses accessibility tree and multiple strategies to find the element.",
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
) -> ToolResult:
    """
    Click on an element by natural language description.

    Args:
        page: Playwright Page instance
        element_description: Description of element to click
        role: Optional ARIA role filter
        double_click: Whether to double-click
        right_click: Whether to right-click

    Returns:
        ToolResult indicating success or failure
    """
    try:
        locator, error = await _find_element_by_description(
            page, element_description, role
        )

        if locator is None:
            return ToolResult(
                success=False,
                error=error,
                metadata={"description": element_description, "role": role},
            )

        # Ensure element is visible and clickable
        await locator.wait_for(state="visible", timeout=5000)

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

        return ToolResult(
            success=True,
            data={
                "action": click_type,
                "element": element_description,
                "tag": tag_name,
                "text": element_text,
            },
            metadata={
                "description": element_description,
                "role": role,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Click failed: {e!s}",
            metadata={"description": element_description},
        )


@tool(
    name="type_text",
    description="Type text into an input field described in natural language. Optionally clears the field first.",
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
) -> ToolResult:
    """
    Type text into an input field.

    Args:
        page: Playwright Page instance
        element_description: Description of the input field
        text: Text to type
        clear_first: Whether to clear field first
        press_enter: Whether to press Enter after

    Returns:
        ToolResult indicating success or failure
    """
    try:
        locator, error = await _find_element_by_description(
            page, element_description, role="textbox"
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

        # Ensure element is visible and editable
        await locator.wait_for(state="visible", timeout=5000)

        # Clear field if requested
        if clear_first:
            await locator.clear()

        # Type text
        await locator.fill(text)

        # Press Enter if requested
        if press_enter:
            await locator.press("Enter")

        return ToolResult(
            success=True,
            data={
                "action": "typed",
                "element": element_description,
                "text": text if len(text) <= 50 else text[:47] + "...",
                "pressed_enter": press_enter,
            },
            metadata={
                "description": element_description,
                "full_text_length": len(text),
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Type failed: {e!s}",
            metadata={"description": element_description},
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

        return ToolResult(
            success=True,
            data={
                "action": action,
                "scroll_from": initial_scroll,
                "scroll_to": final_scroll,
            },
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

        return ToolResult(
            success=True,
            data={
                "action": "hovered",
                "element": element_description,
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

        return ToolResult(
            success=True,
            data={
                "action": "selected",
                "element": element_description,
                "option": option,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Select failed: {e!s}",
            metadata={"description": element_description, "option": option},
        )
