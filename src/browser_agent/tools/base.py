"""
Base Tool Infrastructure

Provides the foundation for browser automation tools:
- Tool decorator for registration
- ToolResult for standardized responses
- Tool registry for discovery
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from functools import wraps


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


def tool(
    name: str,
    description: str,
    parameters: Optional[dict[str, Any]] = None,
):
    """
    Decorator to register a function as a browser automation tool.

    Args:
        name: Tool identifier (e.g., "navigate")
        description: Human-readable description of what the tool does
        parameters: JSON Schema for tool parameters

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
    """

    def decorator(func: Callable) -> Callable:
        # Store tool metadata
        _TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or {},
            "function": func,
        }

        @wraps(func)
        async def wrapper(*args, **kwargs):
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
