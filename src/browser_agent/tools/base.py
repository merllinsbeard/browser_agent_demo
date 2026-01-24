"""
Base Tool Infrastructure

Provides the foundation for browser automation tools:
- Tool decorator for registration
- ToolResult for standardized responses
- Tool registry for discovery
- Security integration for destructive actions
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """
    Standardized result from tool execution.

    Attributes:
        success: Whether the tool executed successfully
        data: Result data (varies by tool)
        error: Error message if failed
        metadata: Additional context (timing, screenshots, etc.)
    """

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.success:
            return f"Success: {self.data}"
        return f"Error: {self.error}"


# Tool registry for all registered tools
_TOOL_REGISTRY: dict[str, dict[str, Any]] = {}

# Global security components (lazy loaded)
_detector = None
_confirmation = None


def _get_security_components():
    """
    Lazy load security components to avoid circular imports.

    Returns:
        Tuple of (detector, confirmation) or (None, None) if not available
    """
    global _detector, _confirmation

    if _detector is None:
        try:
            from browser_agent.security.detector import create_detector
            from browser_agent.security.confirmation import create_confirmation
            _detector = create_detector()
            _confirmation = create_confirmation()
        except ImportError:
            logger.debug("Security module not available")
            _detector = False
            _confirmation = False

    if _detector is False:
        return None, None

    return _detector, _confirmation


def _extract_action_description(func_name: str, args: tuple, kwargs: dict) -> Optional[str]:
    """
    Extract action description from tool arguments for security checking.

    Args:
        func_name: Name of the tool function
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Action description or None
    """
    # Common parameter names that contain action description
    description_params = ["description", "text", "selector", "query"]

    # Check kwargs first
    for param in description_params:
        if param in kwargs and kwargs[param]:
            return str(kwargs[param])

    # For click and type_text, description is typically the first positional arg after page
    if func_name in ("click", "type_text") and len(args) > 1:
        return str(args[1])

    return None


def _extract_page_context(page: Any) -> dict[str, Any]:
    """
    Extract page context for security checking.

    Args:
        page: Playwright Page object

    Returns:
        Dictionary with url and title if available
    """
    context = {}

    if page is None:
        return context

    try:
        # Try to get URL and title
        if hasattr(page, "url"):
            context["url"] = page.url
        if hasattr(page, "title"):
            # title is async, skip for now
            context["title"] = ""
    except Exception as e:
        logger.debug(f"Could not extract page context: {e}")

    return context


def tool(
    name: str,
    description: str,
    parameters: Optional[dict[str, Any]] = None,
    security_check: bool = False,
):
    """
    Decorator to register a function as a browser automation tool.

    Args:
        name: Tool identifier (e.g., "navigate")
        description: Human-readable description of what the tool does
        parameters: JSON Schema for tool parameters
        security_check: Enable security checking for destructive actions (default: False)

    Example:
        >>> @tool(
        ...     name="navigate",
        ...     description="Navigate to a URL",
        ...     parameters={
        ...         "type": "object",
        ...         "properties": {
        ...             "url": {"type": "string", "description": "URL to navigate to"}
        ...         },
        ...         "required": ["url"]
        ...     }
        ... )
        ... async def navigate(page, url: str) -> ToolResult:
        ...     await page.goto(url)
        ...     return ToolResult(success=True, data={"url": page.url})

    Security Example:
        >>> @tool(
        ...     name="click",
        ...     description="Click an element on the page",
        ...     security_check=True,  # Enable security checking
        ... )
        ... async def click(page, description: str) -> ToolResult:
        ...     # Security check runs automatically before execution
        ...     ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Security check if enabled
            if security_check:
                detector, confirmation = _get_security_components()

                if detector and confirmation:
                    # Extract action description
                    action_desc = _extract_action_description(name, args, kwargs)

                    if action_desc:
                        # Extract page context (first arg is usually page)
                        page = args[0] if args else None
                        page_context = _extract_page_context(page)

                        # Check action with detector
                        security_result = detector.check_action(
                            action_description=action_desc,
                            element_context={},  # Could be populated later
                            page_context=page_context,
                        )

                        # Handle blocked actions
                        if security_result.is_blocked:
                            confirmation.show_blocked_action(
                                reason=security_result.message,
                                suggestion="Please perform this action manually",
                            )
                            return ToolResult(
                                success=False,
                                error=f"Action blocked by security policy: {security_result.message}",
                            )

                        # Handle actions requiring confirmation
                        if security_result.requires_confirmation:
                            result, user_response = confirmation.confirm_action(
                                action_description=action_desc,
                                action_type=security_result.action_type.value,
                                details=security_result.context,
                                prompt=security_result.confirmation_prompt,
                            )

                            if result.value != "confirmed":
                                return ToolResult(
                                    success=False,
                                    error=f"Action cancelled by user: {user_response or 'cancelled'}",
                                )

            # Execute the tool function
            try:
                result = await func(*args, **kwargs)
                if isinstance(result, ToolResult):
                    return result
                return ToolResult(success=True, data=result)
            except Exception as e:
                return ToolResult(success=False, error=str(e))

        # Attach metadata to function
        wrapper.tool_name = name
        wrapper.tool_description = description
        wrapper.tool_parameters = parameters
        wrapper.security_check = security_check

        # Store tool metadata in registry (with wrapper for security)
        _TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or {},
            "function": wrapper,  # Store wrapper to preserve security checks
            "security_check": security_check,
        }

        return wrapper

    return decorator


def get_tool(name: str) -> Optional[dict[str, Any]]:
    """Get a tool by name from the registry."""
    return _TOOL_REGISTRY.get(name)


def get_all_tools() -> dict[str, dict[str, Any]]:
    """Get all registered tools."""
    return _TOOL_REGISTRY.copy()


def get_tool_schemas() -> list[dict[str, Any]]:
    """
    Get tool schemas in a format suitable for LLM function calling.

    Returns list of tool definitions with name, description, and parameters.
    """
    return [
        {
            "name": info["name"],
            "description": info["description"],
            "input_schema": info["parameters"],
        }
        for info in _TOOL_REGISTRY.values()
    ]
