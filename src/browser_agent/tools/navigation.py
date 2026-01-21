"""
Navigation Tools

Implements FR-006: Page navigation capabilities.
"""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import tool, ToolResult


@tool(
    name="navigate",
    description="Navigate to a URL. Opens the specified web page in the browser.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to navigate to (e.g., 'https://example.com')",
            },
            "wait_until": {
                "type": "string",
                "description": "When to consider navigation successful",
                "enum": ["load", "domcontentloaded", "networkidle", "commit"],
                "default": "load",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum wait time in milliseconds",
                "default": 30000,
            },
        },
        "required": ["url"],
    },
)
async def navigate_tool(
    page: Page,
    url: str,
    wait_until: str = "load",
    timeout: int = 30000,
) -> ToolResult:
    """
    Navigate to a URL.

    Args:
        page: Playwright Page instance
        url: URL to navigate to
        wait_until: Navigation completion condition
        timeout: Maximum wait time in ms

    Returns:
        ToolResult with navigation status
    """
    try:
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://", "file://")):
            url = f"https://{url}"

        response = await page.goto(
            url,
            wait_until=wait_until,
            timeout=timeout,
        )

        # Check response status
        status = response.status if response else None
        ok = response.ok if response else False

        return ToolResult(
            success=ok or status is None,  # Allow for about:blank, etc.
            data={
                "url": page.url,
                "title": await page.title(),
                "status": status,
            },
            metadata={
                "wait_until": wait_until,
                "final_url": page.url,  # May differ if redirected
            },
        )

    except PlaywrightTimeout:
        return ToolResult(
            success=False,
            error=f"Navigation timeout after {timeout}ms",
            metadata={"url": url, "timeout": timeout},
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Navigation failed: {e!s}",
            metadata={"url": url},
        )


async def navigate(
    page: Page,
    url: str,
    wait_until: str = "load",
    timeout: int = 30000,
) -> ToolResult:
    """
    Navigate to a URL (convenience function).

    This is a direct function call without the tool decorator overhead.

    Args:
        page: Playwright Page instance
        url: URL to navigate to
        wait_until: Navigation completion condition
        timeout: Maximum wait time in ms

    Returns:
        ToolResult with navigation status
    """
    return await navigate_tool(page, url, wait_until, timeout)


async def get_current_url(page: Page) -> str:
    """
    Get the current page URL.

    Args:
        page: Playwright Page instance

    Returns:
        Current URL string
    """
    return page.url


@tool(
    name="go_back",
    description="Navigate back to the previous page in browser history.",
    parameters={
        "type": "object",
        "properties": {
            "timeout": {
                "type": "integer",
                "description": "Maximum wait time in milliseconds",
                "default": 30000,
            },
        },
    },
)
async def go_back(page: Page, timeout: int = 30000) -> ToolResult:
    """
    Navigate back in browser history.

    Args:
        page: Playwright Page instance
        timeout: Maximum wait time in ms

    Returns:
        ToolResult with navigation status
    """
    try:
        await page.go_back(timeout=timeout)
        return ToolResult(
            success=True,
            data={
                "url": page.url,
                "title": await page.title(),
            },
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to go back: {e!s}",
        )


@tool(
    name="go_forward",
    description="Navigate forward in browser history.",
    parameters={
        "type": "object",
        "properties": {
            "timeout": {
                "type": "integer",
                "description": "Maximum wait time in milliseconds",
                "default": 30000,
            },
        },
    },
)
async def go_forward(page: Page, timeout: int = 30000) -> ToolResult:
    """
    Navigate forward in browser history.

    Args:
        page: Playwright Page instance
        timeout: Maximum wait time in ms

    Returns:
        ToolResult with navigation status
    """
    try:
        await page.go_forward(timeout=timeout)
        return ToolResult(
            success=True,
            data={
                "url": page.url,
                "title": await page.title(),
            },
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to go forward: {e!s}",
        )


@tool(
    name="reload",
    description="Reload the current page.",
    parameters={
        "type": "object",
        "properties": {
            "timeout": {
                "type": "integer",
                "description": "Maximum wait time in milliseconds",
                "default": 30000,
            },
        },
    },
)
async def reload_page(page: Page, timeout: int = 30000) -> ToolResult:
    """
    Reload the current page.

    Args:
        page: Playwright Page instance
        timeout: Maximum wait time in ms

    Returns:
        ToolResult with reload status
    """
    try:
        await page.reload(timeout=timeout)
        return ToolResult(
            success=True,
            data={
                "url": page.url,
                "title": await page.title(),
            },
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to reload: {e!s}",
        )
