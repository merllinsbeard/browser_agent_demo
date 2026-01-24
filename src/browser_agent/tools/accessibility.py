"""
Accessibility Tree Tools

Implements FR-011: Accessibility Tree extraction for page analysis.
The accessibility tree provides a semantic view of the page structure
that is easier for AI agents to understand than raw DOM.

Implements FR-005, FR-008, FR-006: Recursive iframe traversal with frame metadata.
"""

import logging
from typing import Any, Optional
from playwright.async_api import Frame, Page

from .base import tool, ToolResult

logger = logging.getLogger(__name__)

# Constants for frame traversal (FR-008)
MAX_IFRAME_DEPTH = 3  # Maximum depth for recursive iframe traversal


async def _is_frame_accessible(frame: Frame) -> bool:
    """
    Check if a frame is accessible (same-origin).

    Args:
        frame: Playwright Frame object

    Returns:
        True if frame is accessible, False if cross-origin
    """
    try:
        # Try to access frame's title - will fail for cross-origin frames
        _ = frame.name
        # Try accessing the frame's page context
        await frame.evaluate("() => true")
        return True
    except Exception:
        return False


def _get_frame_label(frame: Frame, frame_index: int) -> str:
    """
    Get a human-readable label for a frame.

    Args:
        frame: Playwright Frame object
        frame_index: Index of the frame in page.frames

    Returns:
        Human-readable frame label
    """
    # Try frame name first
    if frame.name:
        return frame.name

    # Fallback to frame index or URL
    if frame.url and frame.url != "about:blank":
        # Extract filename from URL
        url_parts = frame.url.split("/")
        return url_parts[-1] if url_parts[-1] else f"frame-{frame_index}"

    return f"frame-{frame_index}"


async def _get_frame_metadata(frame: Frame, frame_index: int, frame_path: list[str]) -> dict[str, Any]:
    """
    Extract metadata for a frame (FR-006).

    Args:
        frame: Playwright Frame object
        frame_index: Index of the frame in page.frames
        frame_path: List of frame names representing the path to this frame

    Returns:
        Dictionary with frame metadata
    """
    metadata = {
        "frame_name": _get_frame_label(frame, frame_index),
        "frame_index": frame_index,
        "frame_path": " > ".join(frame_path),
    }

    # Add additional attributes if available
    if frame.name:
        metadata["frame_name_attr"] = frame.name

    # Try to get frame element attributes (async)
    try:
        frame_element = await frame.frame_element()
        if frame_element:
            aria_label = await frame_element.get_attribute("aria-label")
            if aria_label:
                metadata["aria_label"] = aria_label

            title = await frame_element.get_attribute("title")
            if title:
                metadata["title"] = title
    except Exception:
        pass  # Frame element might not be accessible

    if frame.url and frame.url != "about:blank":
        metadata["src"] = frame.url

    return metadata


async def _extract_dom_structure(frame: Frame, max_depth: int = 10, root_selector: str | None = None) -> dict[str, Any]:
    """
    Extract DOM structure from a frame using query selectors.

    This is a workaround for the deprecated page.accessibility.snapshot() API.
    We extract the semantic structure by querying for common element types.

    Args:
        frame: Playwright Frame object
        max_depth: Maximum depth to traverse
        root_selector: Optional CSS selector to scope extraction (e.g., '#modal')

    Returns:
        Dictionary representing the accessibility tree structure
    """
    try:
        # Extract basic page structure
        structure = await frame.evaluate("""(rootSelector) => {
            function buildAccessibilityTree(node, depth = 0) {
                if (depth > 10) return null;

                // Get role based on tag name and attributes
                let role = node.tagName?.toLowerCase() || 'text';
                if (node.role) {
                    role = node.role;
                } else if (node.tagName === 'BUTTON' || node.type === 'submit' || node.type === 'button') {
                    role = 'button';
                } else if (node.tagName === 'A') {
                    role = 'link';
                } else if (node.tagName === 'INPUT' || node.tagName === 'TEXTAREA') {
                    role = node.type || 'textbox';
                } else if (node.tagName === 'SELECT') {
                    role = 'combobox';
                } else if (node.tagName === 'H1' || node.tagName === 'H2' || node.tagName === 'H3') {
                    role = 'heading';
                } else if (node.tagName === 'LI') {
                    role = 'listitem';
                } else if (node.tagName === 'UL' || node.tagName === 'OL') {
                    role = 'list';
                }

                // Get accessible name
                let name = '';
                if (node.getAttribute('aria-label')) {
                    name = node.getAttribute('aria-label');
                } else if (node.getAttribute('aria-labelledby')) {
                    name = node.getAttribute('aria-labelledby');
                } else if (node.placeholder) {
                    name = node.placeholder;
                } else if (node.alt) {
                    name = node.alt;
                } else if (node.tagName === 'INPUT' && node.type === 'submit') {
                    name = node.value || 'Submit';
                } else if (node.textContent) {
                    // Get text content, truncate if too long
                    const text = node.textContent.trim();
                    name = text.length > 50 ? text.substring(0, 50) + '...' : text;
                }

                // Get value for inputs
                const value = node.value || '';

                // Get description
                const description = node.getAttribute('aria-describedby') || '';

                // Get states
                const disabled = node.disabled || false;
                const focused = document.activeElement === node;
                const checked = node.checked !== undefined ? node.checked : null;
                const selected = node.selected || false;
                const expanded = node.getAttribute('aria-expanded');

                // Build node
                const treeNode = {
                    role: role,
                    name: name,
                };

                if (value) treeNode.value = value;
                if (description) treeNode.description = description;
                if (disabled) treeNode.disabled = disabled;
                if (focused) treeNode.focused = focused;
                if (checked !== null) treeNode.checked = checked;
                if (selected) treeNode.selected = selected;
                if (expanded !== null) treeNode.expanded = expanded;

                // Process children (limit to reasonable number for performance)
                const children = [];
                const childNodes = node.childNodes || [];
                let childCount = 0;

                for (const child of childNodes) {
                    if (childCount >= 50) break; // Limit children per node

                    if (child.nodeType === 1) { // Element node
                        // Skip script, style, and other non-semantic elements
                        const tagName = child.tagName?.toUpperCase();
                        if (tagName && !['SCRIPT', 'STYLE', 'NOSCRIPT', 'HEAD', 'META'].includes(tagName)) {
                            // Only include elements with semantic value
                            if (child.tagName === 'BUTTON' || child.tagName === 'A' ||
                                child.tagName === 'INPUT' || child.tagName === 'TEXTAREA' ||
                                child.tagName === 'SELECT' || child.tagName === 'H1' ||
                                child.tagName === 'H2' || child.tagName === 'H3' ||
                                child.tagName === 'LI' || child.hasAttribute('role') ||
                                child.hasAttribute('aria-label') || child.textContent?.trim()) {
                                const childNode = buildAccessibilityTree(child, depth + 1);
                                if (childNode) children.push(childNode);
                                childCount++;
                            }
                        }
                    }
                }

                if (children.length > 0) {
                    treeNode.children = children;
                }

                return treeNode;
            }

            // Start from body or document element, or use root_selector if provided
            const root = rootSelector
                ? document.querySelector(rootSelector)
                : document.body || document.documentElement;
            if (!root) return null;

            const tree = buildAccessibilityTree(root);
            return tree;
        }""", root_selector)

        return structure or {}

    except Exception as e:
        logger.warning(f"Failed to extract DOM structure from frame: {e}")
        return {}


async def _traverse_frames_recursively(
    page_or_frame: Page | Frame,
    depth: int = 0,
    frame_path: list[str] | None = None,
    visited_frames: set[int] | None = None,
) -> list[dict[str, Any]]:
    """
    Recursively traverse frames and extract accessibility trees (FR-005, FR-008).

    Args:
        page_or_frame: Playwright Page or Frame object
        depth: Current traversal depth
        frame_path: List of frame names representing the path to current frame
        visited_frames: Set of visited frame IDs to prevent infinite loops

    Returns:
        List of accessibility tree nodes from all traversed frames
    """
    if visited_frames is None:
        visited_frames = set()
    if frame_path is None:
        frame_path = []

    # Get the frame object
    frame = page_or_frame if isinstance(page_or_frame, Frame) else page_or_frame.main_frame

    # Prevent infinite loops
    frame_id = id(frame)
    if frame_id in visited_frames:
        return []
    visited_frames.add(frame_id)

    results = []

    # Check depth limit (FR-008)
    if depth > MAX_IFRAME_DEPTH:
        logger.debug(f"Reached maximum iframe depth {MAX_IFRAME_DEPTH}, stopping traversal")
        return results

    # Check if frame is accessible (FR-027)
    if not await _is_frame_accessible(frame):
        logger.warning(f"Frame is not accessible (cross-origin): {frame.url or 'unknown'}")
        return results

    try:
        # Get frame index and label
        if isinstance(page_or_frame, Page):
            frame_index = 0
            current_path = ["main"]
        else:
            # Find this frame's index
            page = frame.page
            frame_index = page.frames.index(frame) if frame in page.frames else len(page.frames)
            label = _get_frame_label(frame, frame_index)
            current_path = frame_path + [label]

        # Extract accessibility tree from this frame
        tree = await _extract_dom_structure(frame, max_depth=10)

        if tree:
            # Add frame metadata to each element (FR-006)
            frame_metadata = await _get_frame_metadata(frame, frame_index, current_path)

            # Wrap tree in a structure that includes frame metadata
            frame_marker = {
                "role": "frame-marker",
                "name": f"--- [frame: {frame_metadata['frame_name']}, index: {frame_index}] ---",
                "frame_metadata": frame_metadata,
            }

            results.append(frame_marker)

            # Add the tree content
            if "children" not in tree:
                tree = {"role": "root", "children": [tree] if tree else []}

            # Add frame metadata to all elements in the tree
            def add_metadata_to_tree(node: dict[str, Any]) -> None:
                node["frame_name"] = frame_metadata["frame_name"]
                node["frame_index"] = frame_metadata["frame_index"]
                node["frame_path"] = frame_metadata["frame_path"]
                if "children" in node:
                    for child in node["children"]:
                        add_metadata_to_tree(child)

            add_metadata_to_tree(tree)

            if "children" in tree:
                results.extend(tree["children"])

        # Recursively process child frames (iframes within this frame)
        child_frames = frame.child_frames
        for child_frame in child_frames:
            child_results = await _traverse_frames_recursively(
                child_frame,
                depth + 1,
                current_path,
                visited_frames,
            )
            results.extend(child_results)

    except Exception as e:
        logger.error(f"Error traversing frame at depth {depth}: {e}")

    return results


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
    description="Get the accessibility tree of the current page. Returns a hierarchical structure of all accessible elements, including iframe contents recursively (up to depth 3).",
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
            "include_iframes": {
                "type": "boolean",
                "description": "Include iframe contents recursively (default: true)",
                "default": True,
            },
        },
    },
)
async def get_accessibility_tree(
    page: Page,
    root: Optional[str] = None,
    max_depth: int = 10,
    include_iframes: bool = True,
) -> ToolResult:
    """
    Get the accessibility tree of the page.

    Args:
        page: Playwright Page instance
        root: Optional CSS selector to scope the tree
        max_depth: Maximum depth to traverse
        include_iframes: Whether to include iframe contents recursively (FR-005)

    Returns:
        ToolResult with formatted accessibility tree
    """
    try:
        # Handle root element scoping
        if root:
            root_element = page.locator(root).first
            if not await root_element.count():
                return ToolResult(
                    success=False,
                    error=f"Root element not found: {root}",
                )
            # For root-scoped queries, only extract from main frame
            tree = await _extract_dom_structure(page.main_frame, max_depth=max_depth, root_selector=root)
            if not tree:
                return ToolResult(
                    success=True,
                    data={
                        "tree": "Empty accessibility tree",
                        "interactive_count": 0,
                    },
                    metadata={"root": root, "include_iframes": False},
                )

            # Format tree as human-readable text
            formatted_lines = _format_tree_node(tree, max_depth=max_depth)
            formatted_tree = "\n".join(formatted_lines)

            # Extract interactive elements
            interactive = _extract_interactive_elements(tree)

            return ToolResult(
                success=True,
                data={
                    "tree": formatted_tree,
                    "raw": tree,
                    "interactive_elements": interactive,
                    "interactive_count": len(interactive),
                },
                metadata={"root": root, "max_depth": max_depth, "include_iframes": False},
            )

        # Use recursive frame traversal (FR-005, FR-008)
        if include_iframes:
            all_nodes = await _traverse_frames_recursively(page)
        else:
            # Only extract from main frame
            tree = await _extract_dom_structure(page.main_frame, max_depth=max_depth, root_selector=None)
            all_nodes = [tree] if tree else []

        if not all_nodes:
            return ToolResult(
                success=True,
                data={
                    "tree": "Empty accessibility tree",
                    "interactive_count": 0,
                },
                metadata={"root": root or "document", "include_iframes": include_iframes},
            )

        # Build tree structure from all nodes
        merged_tree = {"role": "root", "children": all_nodes}

        # Format tree as human-readable text
        formatted_lines = _format_tree_node(merged_tree, max_depth=max_depth)
        formatted_tree = "\n".join(formatted_lines)

        # Extract interactive elements
        interactive = _extract_interactive_elements(merged_tree)

        return ToolResult(
            success=True,
            data={
                "tree": formatted_tree,
                "raw": merged_tree,
                "interactive_elements": interactive,
                "interactive_count": len(interactive),
            },
            metadata={
                "root": root or "document",
                "max_depth": max_depth,
                "include_iframes": include_iframes,
            },
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to get accessibility tree: {e!s}",
        )


@tool(
    name="find_interactive_elements",
    description="Find all interactive elements on the page (buttons, links, inputs, etc.), including iframe contents. Returns a list with their roles, names, and states.",
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
            "include_iframes": {
                "type": "boolean",
                "description": "Include elements from iframes (default: true)",
                "default": True,
            },
        },
    },
)
async def find_interactive_elements(
    page: Page,
    filter_role: Optional[str] = None,
    filter_name: Optional[str] = None,
    include_iframes: bool = True,
) -> ToolResult:
    """
    Find interactive elements on the page.

    Args:
        page: Playwright Page instance
        filter_role: Optional role filter
        filter_name: Optional name filter (case-insensitive)
        include_iframes: Whether to include iframe contents (FR-007)

    Returns:
        ToolResult with list of interactive elements
    """
    try:
        # Use recursive frame traversal for iframe support (FR-007)
        if include_iframes:
            all_nodes = await _traverse_frames_recursively(page)
            merged_tree = {"role": "root", "children": all_nodes}
        else:
            # Only extract from main frame
            tree = await _extract_dom_structure(page.main_frame)
            merged_tree = tree if tree else {"role": "root", "children": []}

        if not merged_tree or not merged_tree.get("children"):
            return ToolResult(
                success=True,
                data={"elements": [], "count": 0},
            )

        # Extract interactive elements
        elements = _extract_interactive_elements(merged_tree)

        # Apply filters
        if filter_role:
            elements = [e for e in elements if e["role"] == filter_role.lower()]

        if filter_name:
            filter_lower = filter_name.lower()
            elements = [
                e for e in elements
                if e.get("name") and filter_lower in e["name"].lower()
            ]

        # Format for readability with frame context
        formatted = []
        frame_counts = {"main": 0}

        for elem in elements:
            desc_parts = [elem["role"]]
            if elem.get("name"):
                desc_parts.append(f'"{elem["name"]}"')
            if elem.get("disabled"):
                desc_parts.append("(disabled)")

            # Add frame context to description
            frame_name = elem.get("frame_name", "main")
            if frame_name != "main":
                desc_parts.append(f"[in frame: {frame_name}]")
                frame_counts[frame_name] = frame_counts.get(frame_name, 0) + 1
            else:
                frame_counts["main"] += 1

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
                "include_iframes": include_iframes,
                "frame_counts": frame_counts,
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
