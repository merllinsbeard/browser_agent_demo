"""
Wait Tools

Implements FR-010: Wait for page load and custom conditions.
Provides tools for waiting on page states, elements, and custom conditions.
"""

from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import tool, ToolResult


@tool(
    name="wait_for_load",
    description="Wait for the page to reach a specific load state. Use after navigation or actions that trigger page changes.",
    parameters={
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "description": "Load state to wait for",
                "enum": ["load", "domcontentloaded", "networkidle"],
                "default": "load",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum wait time in milliseconds",
                "default": 30000,
            },
        },
    },
)
async def wait_for_load(
    page: Page,
    state: str = "load",
    timeout: int = 30000,
) -> ToolResult:
    """
    Wait for page load state.

    Args:
        page: Playwright Page instance
        state: Load state to wait for
        timeout: Maximum wait time in ms

    Returns:
        ToolResult indicating success or timeout
    """
    try:
        await page.wait_for_load_state(state, timeout=timeout)
        return ToolResult(
            success=True,
            data={
                "state": state,
                "url": page.url,
                "title": await page.title(),
            },
        )
    except PlaywrightTimeout:
        return ToolResult(
            success=False,
            error=f"Timeout waiting for {state} state after {timeout}ms",
            metadata={"state": state, "timeout": timeout},
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to wait for load state: {e!s}",
        )


@tool(
    name="wait_for_selector",
    description="Wait for an element matching the selector to appear in the page. Useful for waiting on dynamic content.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector to wait for",
            },
            "state": {
                "type": "string",
                "description": "Element state to wait for",
                "enum": ["attached", "detached", "visible", "hidden"],
                "default": "visible",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum wait time in milliseconds",
                "default": 30000,
            },
        },
        "required": ["selector"],
    },
)
async def wait_for_selector(
    page: Page,
    selector: str,
    state: str = "visible",
    timeout: int = 30000,
) -> ToolResult:
    """
    Wait for an element to reach a specific state.

    Args:
        page: Playwright Page instance
        selector: CSS selector
        state: Element state to wait for
        timeout: Maximum wait time in ms

    Returns:
        ToolResult with element info if found
    """
    try:
        locator = page.locator(selector)
        await locator.wait_for(state=state, timeout=timeout)

        # Get element info if visible/attached
        if state in ("visible", "attached"):
            count = await locator.count()
            return ToolResult(
                success=True,
                data={
                    "selector": selector,
                    "state": state,
                    "count": count,
                },
            )
        else:
            return ToolResult(
                success=True,
                data={
                    "selector": selector,
                    "state": state,
                },
            )

    except PlaywrightTimeout:
        return ToolResult(
            success=False,
            error=f"Timeout waiting for '{selector}' to be {state} after {timeout}ms",
            metadata={"selector": selector, "state": state, "timeout": timeout},
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to wait for selector: {e!s}",
        )


@tool(
    name="wait_for_text",
    description="Wait for specific text to appear on the page. Searches the entire page by default.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to wait for (exact or partial match)",
            },
            "selector": {
                "type": "string",
                "description": "Optional selector to scope the search",
            },
            "exact": {
                "type": "boolean",
                "description": "Whether to match exact text (default: false for partial match)",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum wait time in milliseconds",
                "default": 30000,
            },
        },
        "required": ["text"],
    },
)
async def wait_for_text(
    page: Page,
    text: str,
    selector: Optional[str] = None,
    exact: bool = False,
    timeout: int = 30000,
) -> ToolResult:
    """
    Wait for text to appear on the page.

    Args:
        page: Playwright Page instance
        text: Text to wait for
        selector: Optional selector to scope search
        exact: Whether to match exact text
        timeout: Maximum wait time in ms

    Returns:
        ToolResult indicating if text was found
    """
    try:
        if selector:
            locator = page.locator(selector).get_by_text(text, exact=exact)
        else:
            locator = page.get_by_text(text, exact=exact)

        await locator.first.wait_for(state="visible", timeout=timeout)

        return ToolResult(
            success=True,
            data={
                "text": text,
                "found": True,
                "count": await locator.count(),
            },
            metadata={"selector": selector, "exact": exact},
        )

    except PlaywrightTimeout:
        return ToolResult(
            success=False,
            error=f"Timeout waiting for text '{text}' after {timeout}ms",
            metadata={"text": text, "timeout": timeout},
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to wait for text: {e!s}",
        )


@tool(
    name="wait_for_url",
    description="Wait for the page URL to match a pattern. Useful after navigation or form submissions.",
    parameters={
        "type": "object",
        "properties": {
            "url_pattern": {
                "type": "string",
                "description": "URL pattern to match (can be substring or regex)",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum wait time in milliseconds",
                "default": 30000,
            },
        },
        "required": ["url_pattern"],
    },
)
async def wait_for_url(
    page: Page,
    url_pattern: str,
    timeout: int = 30000,
) -> ToolResult:
    """
    Wait for URL to match a pattern.

    Args:
        page: Playwright Page instance
        url_pattern: URL pattern (substring or regex)
        timeout: Maximum wait time in ms

    Returns:
        ToolResult with current URL
    """
    try:
        await page.wait_for_url(f"**/*{url_pattern}*", timeout=timeout)
        return ToolResult(
            success=True,
            data={
                "url": page.url,
                "pattern_matched": url_pattern,
            },
        )
    except PlaywrightTimeout:
        return ToolResult(
            success=False,
            error=f"Timeout waiting for URL matching '{url_pattern}' after {timeout}ms",
            metadata={
                "pattern": url_pattern,
                "current_url": page.url,
                "timeout": timeout,
            },
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to wait for URL: {e!s}",
        )


@tool(
    name="sleep",
    description="Pause execution for a specified duration. Use sparingly - prefer wait_for_* tools when possible.",
    parameters={
        "type": "object",
        "properties": {
            "milliseconds": {
                "type": "integer",
                "description": "Duration to sleep in milliseconds",
                "minimum": 0,
                "maximum": 30000,
            },
        },
        "required": ["milliseconds"],
    },
)
async def sleep(
    page: Page,
    milliseconds: int,
) -> ToolResult:
    """
    Sleep for a specified duration.

    Args:
        page: Playwright Page instance (required for tool signature)
        milliseconds: Duration to sleep

    Returns:
        ToolResult indicating completion
    """
    import asyncio

    # Cap at 30 seconds
    milliseconds = min(milliseconds, 30000)

    await asyncio.sleep(milliseconds / 1000)

    return ToolResult(
        success=True,
        data={"slept_ms": milliseconds},
    )
