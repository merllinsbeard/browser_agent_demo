"""
Screenshot Tools

Implements FR-012: Screenshot capture as fallback for visual analysis.
Screenshots provide visual context when accessibility tree is insufficient.
"""

import base64
from pathlib import Path
from typing import Optional, Literal
from datetime import datetime

from playwright.async_api import Page

from .base import tool, ToolResult


ScreenshotType = Literal["png", "jpeg"]


@tool(
    name="screenshot",
    description="Take a screenshot of the current page or a specific element. Returns base64-encoded image data. Use this when you need visual information that the accessibility tree doesn't provide.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "Optional CSS selector to screenshot a specific element",
            },
            "full_page": {
                "type": "boolean",
                "description": "Whether to capture the full scrollable page (default: false)",
                "default": False,
            },
            "type": {
                "type": "string",
                "description": "Image format: 'png' or 'jpeg' (default: 'png')",
                "enum": ["png", "jpeg"],
                "default": "png",
            },
            "quality": {
                "type": "integer",
                "description": "JPEG quality 0-100 (only for jpeg type)",
                "minimum": 0,
                "maximum": 100,
            },
        },
    },
)
async def screenshot(
    page: Page,
    selector: Optional[str] = None,
    full_page: bool = False,
    type: ScreenshotType = "png",
    quality: Optional[int] = None,
) -> ToolResult:
    """
    Take a screenshot of the page or element.

    Args:
        page: Playwright Page instance
        selector: Optional CSS selector for element screenshot
        full_page: Whether to capture full scrollable page
        type: Image format (png or jpeg)
        quality: JPEG quality (0-100)

    Returns:
        ToolResult with base64-encoded screenshot data
    """
    try:
        screenshot_options = {
            "type": type,
            "full_page": full_page and not selector,  # full_page only for page screenshots
        }

        if type == "jpeg" and quality is not None:
            screenshot_options["quality"] = quality

        if selector:
            # Screenshot specific element
            element = page.locator(selector)
            if not await element.count():
                return ToolResult(
                    success=False,
                    error=f"Element not found: {selector}",
                )
            screenshot_bytes = await element.screenshot(**screenshot_options)
        else:
            # Screenshot full page
            screenshot_bytes = await page.screenshot(**screenshot_options)

        # Encode as base64
        base64_data = base64.b64encode(screenshot_bytes).decode("utf-8")

        return ToolResult(
            success=True,
            data={
                "base64": base64_data,
                "mime_type": f"image/{type}",
                "size_bytes": len(screenshot_bytes),
            },
            metadata={
                "selector": selector,
                "full_page": full_page,
                "type": type,
                "url": page.url,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to take screenshot: {e!s}",
        )


@tool(
    name="save_screenshot",
    description="Take a screenshot and save it to a file. Useful for debugging or creating evidence of actions taken.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to save the screenshot (default: auto-generated in ./screenshots/)",
            },
            "selector": {
                "type": "string",
                "description": "Optional CSS selector to screenshot a specific element",
            },
            "full_page": {
                "type": "boolean",
                "description": "Whether to capture the full scrollable page",
                "default": False,
            },
        },
    },
)
async def save_screenshot(
    page: Page,
    path: Optional[str] = None,
    selector: Optional[str] = None,
    full_page: bool = False,
) -> ToolResult:
    """
    Take a screenshot and save to file.

    Args:
        page: Playwright Page instance
        path: File path (auto-generated if None)
        selector: Optional CSS selector
        full_page: Whether to capture full page

    Returns:
        ToolResult with file path
    """
    try:
        # Generate path if not provided
        if path is None:
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = str(screenshots_dir / f"screenshot_{timestamp}.png")

        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        if selector:
            element = page.locator(selector)
            if not await element.count():
                return ToolResult(
                    success=False,
                    error=f"Element not found: {selector}",
                )
            await element.screenshot(path=path)
        else:
            await page.screenshot(path=path, full_page=full_page)

        return ToolResult(
            success=True,
            data={
                "path": str(Path(path).absolute()),
                "url": page.url,
            },
            metadata={
                "selector": selector,
                "full_page": full_page,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to save screenshot: {e!s}",
        )


@tool(
    name="get_viewport_info",
    description="Get information about the current viewport size and scroll position.",
    parameters={
        "type": "object",
        "properties": {},
    },
)
async def get_viewport_info(page: Page) -> ToolResult:
    """
    Get viewport and scroll information.

    Args:
        page: Playwright Page instance

    Returns:
        ToolResult with viewport dimensions and scroll position
    """
    try:
        viewport_size = page.viewport_size
        scroll_position = await page.evaluate("""() => ({
            scrollX: window.scrollX,
            scrollY: window.scrollY,
            scrollWidth: document.documentElement.scrollWidth,
            scrollHeight: document.documentElement.scrollHeight,
            clientWidth: document.documentElement.clientWidth,
            clientHeight: document.documentElement.clientHeight,
        })""")

        return ToolResult(
            success=True,
            data={
                "viewport": viewport_size,
                "scroll": scroll_position,
                "can_scroll_down": (
                    scroll_position["scrollY"] + scroll_position["clientHeight"]
                    < scroll_position["scrollHeight"]
                ),
                "can_scroll_up": scroll_position["scrollY"] > 0,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to get viewport info: {e!s}",
        )
