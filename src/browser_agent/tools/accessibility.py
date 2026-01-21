"""
Accessibility Tree Tools

Implements FR-011: Accessibility Tree extraction for page analysis.
The accessibility tree provides a semantic view of the page structure
that is easier for AI agents to understand than raw DOM.
"""

from typing import Any, Optional
from playwright.async_api import Page

from .base import tool, ToolResult


def _format_tree_node(
    node: dict[str, Any],
    indent: int = 0,
    max_depth: int = 10,
) -> list[str]:
    """
    Format an accessibility tree node as human-readable lines.

    Args:
        node: Accessibility tree node
        indent: Current indentation level
        max_depth: Maximum depth to traverse

    Returns:
        List of formatted lines
    """
    if indent > max_depth:
        return ["  " * indent + "..."]

    lines = []

    # Build node description
    role = node.get("role", "unknown")
    name = node.get("name", "")
    value = node.get("value", "")
    description = node.get("description", "")

    # Build concise representation
    parts = [role]
    if name:
        parts.append(f'"{name}"')
    if value:
        parts.append(f"value={value}")
    if description:
        parts.append(f"desc={description}")

    # Add state flags
    states = []
    if node.get("disabled"):
        states.append("disabled")
    if node.get("focused"):
        states.append("focused")
    if node.get("checked") is not None:
        states.append(f"checked={node['checked']}")
    if node.get("selected"):
        states.append("selected")
    if node.get("expanded") is not None:
        states.append(f"expanded={node['expanded']}")

    if states:
        parts.append(f"[{', '.join(states)}]")

    lines.append("  " * indent + " ".join(parts))

    # Process children
    children = node.get("children", [])
    for child in children:
        lines.extend(_format_tree_node(child, indent + 1, max_depth))

    return lines


def _extract_interactive_elements(
    node: dict[str, Any],
    path: str = "",
) -> list[dict[str, Any]]:
    """
    Extract interactive elements from accessibility tree.

    Args:
        node: Accessibility tree node
        path: Current path in tree

    Returns:
        List of interactive elements with their properties
    """
    interactive_roles = {
        "button",
        "link",
        "textbox",
        "checkbox",
        "radio",
        "combobox",
        "listbox",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "option",
        "slider",
        "spinbutton",
        "switch",
        "tab",
        "searchbox",
    }

    elements = []
    role = node.get("role", "")
    name = node.get("name", "")

    # Build path for this node
    current_path = f"{path}/{role}" if path else role
    if name:
        current_path += f'["{name}"]'

    # Check if this is an interactive element
    if role in interactive_roles:
        elements.append({
            "role": role,
            "name": name,
            "value": node.get("value"),
            "description": node.get("description"),
            "disabled": node.get("disabled", False),
            "focused": node.get("focused", False),
            "checked": node.get("checked"),
            "expanded": node.get("expanded"),
            "path": current_path,
        })

    # Process children
    children = node.get("children", [])
    for i, child in enumerate(children):
        child_path = f"{current_path}[{i}]"
        elements.extend(_extract_interactive_elements(child, child_path))

    return elements


@tool(
    name="get_accessibility_tree",
    description="Get the accessibility tree of the current page. Returns a hierarchical structure of all accessible elements, useful for understanding page layout and finding interactive elements.",
    parameters={
        "type": "object",
        "properties": {
            "root": {
                "type": "string",
                "description": "Optional selector to scope the tree to a specific element",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth to traverse (default: 10)",
                "default": 10,
            },
        },
    },
)
async def get_accessibility_tree(
    page: Page,
    root: Optional[str] = None,
    max_depth: int = 10,
) -> ToolResult:
    """
    Get the accessibility tree of the page.

    Args:
        page: Playwright Page instance
        root: Optional CSS selector to scope the tree
        max_depth: Maximum depth to traverse

    Returns:
        ToolResult with formatted accessibility tree
    """
    try:
        # Get root element if specified
        root_element = None
        if root:
            root_element = page.locator(root).first
            if not await root_element.count():
                return ToolResult(
                    success=False,
                    error=f"Root element not found: {root}",
                )

        # Get accessibility snapshot
        snapshot = await page.accessibility.snapshot(
            interesting_only=True,
            root=root_element,
        )

        if not snapshot:
            return ToolResult(
                success=True,
                data={
                    "tree": "Empty accessibility tree",
                    "interactive_count": 0,
                },
                metadata={"root": root or "document"},
            )

        # Format tree as human-readable text
        formatted_lines = _format_tree_node(snapshot, max_depth=max_depth)
        formatted_tree = "\n".join(formatted_lines)

        # Extract interactive elements
        interactive = _extract_interactive_elements(snapshot)

        return ToolResult(
            success=True,
            data={
                "tree": formatted_tree,
                "raw": snapshot,
                "interactive_elements": interactive,
                "interactive_count": len(interactive),
            },
            metadata={
                "root": root or "document",
                "max_depth": max_depth,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to get accessibility tree: {e!s}",
        )


@tool(
    name="find_interactive_elements",
    description="Find all interactive elements on the page (buttons, links, inputs, etc.). Returns a list with their roles, names, and states.",
    parameters={
        "type": "object",
        "properties": {
            "filter_role": {
                "type": "string",
                "description": "Filter by specific role (e.g., 'button', 'link', 'textbox')",
            },
            "filter_name": {
                "type": "string",
                "description": "Filter by name containing this text (case-insensitive)",
            },
        },
    },
)
async def find_interactive_elements(
    page: Page,
    filter_role: Optional[str] = None,
    filter_name: Optional[str] = None,
) -> ToolResult:
    """
    Find interactive elements on the page.

    Args:
        page: Playwright Page instance
        filter_role: Optional role filter
        filter_name: Optional name filter (case-insensitive)

    Returns:
        ToolResult with list of interactive elements
    """
    try:
        snapshot = await page.accessibility.snapshot(interesting_only=True)

        if not snapshot:
            return ToolResult(
                success=True,
                data={"elements": [], "count": 0},
            )

        # Extract interactive elements
        elements = _extract_interactive_elements(snapshot)

        # Apply filters
        if filter_role:
            elements = [e for e in elements if e["role"] == filter_role.lower()]

        if filter_name:
            filter_lower = filter_name.lower()
            elements = [
                e for e in elements
                if e.get("name") and filter_lower in e["name"].lower()
            ]

        # Format for readability
        formatted = []
        for elem in elements:
            desc_parts = [elem["role"]]
            if elem.get("name"):
                desc_parts.append(f'"{elem["name"]}"')
            if elem.get("disabled"):
                desc_parts.append("(disabled)")
            formatted.append({
                "description": " ".join(desc_parts),
                **elem,
            })

        return ToolResult(
            success=True,
            data={
                "elements": formatted,
                "count": len(formatted),
            },
            metadata={
                "filter_role": filter_role,
                "filter_name": filter_name,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to find interactive elements: {e!s}",
        )


@tool(
    name="get_page_text",
    description="Extract all visible text content from the page. Useful for reading page content and understanding context.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "Optional CSS selector to scope text extraction",
            },
        },
    },
)
async def get_page_text(
    page: Page,
    selector: Optional[str] = None,
) -> ToolResult:
    """
    Extract visible text from the page.

    Args:
        page: Playwright Page instance
        selector: Optional selector to scope extraction

    Returns:
        ToolResult with page text content
    """
    try:
        if selector:
            element = page.locator(selector)
            if not await element.count():
                return ToolResult(
                    success=False,
                    error=f"Element not found: {selector}",
                )
            text = await element.inner_text()
        else:
            text = await page.locator("body").inner_text()

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        clean_text = "\n".join(lines)

        return ToolResult(
            success=True,
            data={
                "text": clean_text,
                "length": len(clean_text),
                "line_count": len(lines),
            },
            metadata={"selector": selector or "body"},
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to extract text: {e!s}",
        )
