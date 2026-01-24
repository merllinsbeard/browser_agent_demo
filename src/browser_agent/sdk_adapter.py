"""
SDK Adapter Layer

Adapts existing browser automation tools for Claude Agent SDK compatibility.
This module provides:
- tool_result_to_sdk_format(): Convert ToolResult to SDK response format
- adapt_tool_for_sdk(): Wrap existing @tool decorated functions
- create_browser_server(): Create MCP server with all 23 browser tools
"""

from typing import Any, Callable, Optional
from playwright.async_api import Page

from claude_agent_sdk import tool as sdk_tool, create_sdk_mcp_server

from browser_agent.tools.base import get_all_tools, ToolResult


def tool_result_to_sdk_format(result: ToolResult) -> dict[str, Any]:
    """
    Convert existing ToolResult to SDK response format.

    Args:
        result: ToolResult from existing tool execution

    Returns:
        SDK-compatible response dict with content blocks and is_error flag
    """
    if result.success:
        # Format data as readable text
        if result.data is None:
            text = "Operation completed successfully"
        elif isinstance(result.data, dict):
            # Pretty format dict data
            import json
            text = json.dumps(result.data, indent=2, default=str)
        elif isinstance(result.data, (list, tuple)):
            import json
            text = json.dumps(result.data, indent=2, default=str)
        else:
            text = str(result.data)

        return {
            "content": [{"type": "text", "text": text}],
            "is_error": False
        }
    else:
        error_msg = result.error or "Unknown error occurred"
        # Include retry chain info if available (check both data and metadata)
        retry_info = None
        if result.data and isinstance(result.data, dict) and "retry_chain" in result.data:
            retry_info = result.data["retry_chain"]
        elif result.metadata and "retry_chain" in result.metadata:
            retry_info = result.metadata["retry_chain"]

        if retry_info and retry_info.get("exhausted"):
            attempts = retry_info.get("attempts", [])
            error_msg += f"\n\nRetry chain exhausted after {len(attempts)} attempts:"
            for attempt in attempts:
                error_msg += f"\n  - {attempt.get('strategy')}: {attempt.get('error', 'unknown')}"

        return {
            "content": [{"type": "text", "text": error_msg}],
            "is_error": True
        }


def _convert_json_schema_to_sdk_params(json_schema: dict[str, Any]) -> dict[str, type]:
    """
    Convert JSON Schema parameters to SDK type hints.

    The SDK @tool decorator expects {param_name: type} but existing tools
    use JSON Schema format. This function performs the conversion.

    Args:
        json_schema: JSON Schema parameters dict

    Returns:
        Dict mapping parameter names to Python types
    """
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    properties = json_schema.get("properties", {})
    sdk_params = {}

    for param_name, param_schema in properties.items():
        param_type = param_schema.get("type", "string")
        sdk_params[param_name] = type_map.get(param_type, str)

    return sdk_params


def adapt_tool_for_sdk(
    tool_name: str,
    tool_info: dict[str, Any],
    page_getter: Callable[[], Page]
) -> Callable:
    """
    Adapt existing @tool decorated function for SDK compatibility.

    Creates a new async function that:
    1. Receives args dict from SDK
    2. Gets the current page via page_getter
    3. Calls the original tool function
    4. Converts ToolResult to SDK format

    Args:
        tool_name: Name of the tool (e.g., "click")
        tool_info: Tool metadata from registry (description, parameters, function)
        page_getter: Callable that returns the current Page object

    Returns:
        SDK-compatible async function decorated with @sdk_tool
    """
    description = tool_info.get("description", f"Browser tool: {tool_name}")
    json_schema = tool_info.get("parameters", {})
    original_func = tool_info["function"]

    # Convert JSON Schema to SDK parameter format
    sdk_params = _convert_json_schema_to_sdk_params(json_schema)

    # Create adapted async function
    async def adapted_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Adapted tool wrapper that bridges existing tools to SDK format."""
        page = page_getter()

        if page is None:
            return {
                "content": [{"type": "text", "text": "Error: Browser page not available"}],
                "is_error": True
            }

        try:
            # Call original tool with page as first argument
            result = await original_func(page, **args)

            # Ensure result is ToolResult
            if not isinstance(result, ToolResult):
                result = ToolResult(success=True, data=result)

            return tool_result_to_sdk_format(result)

        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Tool execution error: {str(e)}"}],
                "is_error": True
            }

    # Apply SDK @tool decorator
    decorated = sdk_tool(tool_name, description, sdk_params)(adapted_tool)

    return decorated


def create_browser_server(
    page_getter: Callable[[], Optional[Page]],
    server_name: str = "browser",
    server_version: str = "1.0.0"
):
    """
    Create MCP server with all 23 browser automation tools.

    This creates an in-process SDK MCP server that wraps all existing
    browser tools, making them available to Claude via the SDK.

    Tool naming convention: mcp__<server_name>__<tool_name>
    Example: mcp__browser__click, mcp__browser__navigate

    Args:
        page_getter: Callable that returns the current Page object (or None)
        server_name: Name for the MCP server (default: "browser")
        server_version: Version string (default: "1.0.0")

    Returns:
        SDK MCP server configuration to use with ClaudeAgentOptions

    Example:
        >>> def get_page():
        ...     return browser_controller.current_page
        >>> server = create_browser_server(get_page)
        >>> options = ClaudeAgentOptions(
        ...     mcp_servers={"browser": server},
        ...     allowed_tools=get_allowed_tools()
        ... )
    """
    all_tools = get_all_tools()
    adapted_tools = []

    for tool_name, tool_info in all_tools.items():
        adapted = adapt_tool_for_sdk(tool_name, tool_info, page_getter)
        adapted_tools.append(adapted)

    return create_sdk_mcp_server(
        name=server_name,
        version=server_version,
        tools=adapted_tools
    )


def get_allowed_tools(server_name: str = "browser") -> list[str]:
    """
    Get list of allowed tool names for ClaudeAgentOptions.

    Returns tool names in the SDK format: mcp__<server_name>__<tool_name>

    Args:
        server_name: Name of the MCP server (default: "browser")

    Returns:
        List of tool names like ["mcp__browser__click", "mcp__browser__navigate", ...]
    """
    all_tools = get_all_tools()
    return [f"mcp__{server_name}__{name}" for name in all_tools.keys()]


# Tool count for validation
EXPECTED_TOOL_COUNT = 23
