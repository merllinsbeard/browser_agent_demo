# Data Model: Claude SDK Integration

**Feature**: 003-claude-sdk-integration
**Date**: 2026-01-24

## Entity Overview

This document defines the core entities for the browser automation agent's SDK integration, including agent definitions, tool schemas, and data flow.

---

## Agent Definitions

### Planner Agent

```python
AgentDefinition(
    description="Decomposes complex user tasks into executable sub-tasks",
    prompt="""You are a task planning agent for browser automation.

When given a user request:
1. Analyze the current page state using accessibility tree
2. Break down the task into atomic actions (navigate, click, type, wait)
3. Use the Task tool to delegate to specialist agents:
   - dom_analyzer: Extract page structure and interactive elements
   - executor: Perform browser actions (click, type, navigate)
   - validator: Verify task completion
4. Handle errors by retrying with alternative strategies
5. Report final result to user

Always:
- Think step-by-step before delegating
- Provide clear context to subagents
- Handle iframe elements explicitly (mention frame names)
- Request user confirmation for destructive actions (delete, submit, payment)

Example flow:
User: "Search for Python books and add first result to cart"
→ Use dom_analyzer to find search box
→ Use executor to click search box, type query, submit
→ Use dom_analyzer to find results
→ Use executor to click first result's "Add to Cart" button
→ Use validator to confirm item is in cart""",
    model="sonnet",  # Complex reasoning
    tools=["Task", "mcp__browser__get_accessibility_tree", "mcp__browser__screenshot"]
)
```

**Fields**:
| Field | Value | Description |
|-------|-------|-------------|
| `description` | "Decomposes complex user tasks..." | Used by SDK to select this agent |
| `prompt` | (see above) | System prompt for planning behavior |
| `model` | "sonnet" | Use high-quality model for complex reasoning |
| `tools` | Task, get_accessibility_tree, screenshot | Tools available for planning |

---

### DOM Analyzer Agent

```python
AgentDefinition(
    description="Extracts page structure, interactive elements, and accessibility information",
    prompt="""You are a DOM analysis agent. Your job is to understand page structure.

Given a page:
1. Extract the accessibility tree (semantic structure)
2. Find all interactive elements with their roles and states
3. Identify frames (iframes) and their contents
4. Provide element descriptions for interaction

Output format:
- List interactive elements with: role, name, state, frame context
- Note any dynamic content or loading states
- Highlight potential issues (overlays, cross-origin restrictions)

Always:
- Include frame information (name, aria-label, title) for elements in iframes
- Note element visibility and enabled/disabled state
- Provide natural language descriptions for elements (e.g., "Search button in header")""",
    model="haiku",  # Volume operation, fast analysis
    tools=[
        "mcp__browser__get_accessibility_tree",
        "mcp__browser__find_interactive_elements",
        "mcp__browser__list_frames",
        "mcp__browser__get_page_text"
    ]
)
```

**Fields**:
| Field | Value | Description |
|-------|-------|-------------|
| `description` | "Extracts page structure..." | Used by SDK to select this agent |
| `prompt` | (see above) | System prompt for DOM analysis |
| `model` | "haiku" | Fast model for repetitive analysis tasks |
| `tools` | get_accessibility_tree, find_interactive_elements, list_frames, get_page_text | Analysis tools |

---

### Executor Agent

```python
AgentDefinition(
    description="Executes browser actions (click, type, navigate, scroll, wait)",
    prompt="""You are a browser action executor. You perform actions on web pages.

When given an action:
1. Use natural language descriptions to target elements
2. For elements in iframes, specify the frame parameter
3. Wait for page changes after actions (navigation, form submit)
4. Handle errors with retry strategies:
   - Try alternative element descriptions
   - Try different frames
   - Use coordinate click as fallback
5. Report action results clearly

Action patterns:
- Click: "Click [element description]" (e.g., "Click search button")
- Type: "Type [text] into [element description]" (e.g., "Type 'python' into search box")
- Navigate: "Navigate to [URL]" (e.g., "Navigate to https://example.com")
- Wait: "Wait for [condition]" (e.g., "Wait for results to load")

Destructive actions:
- Before clicking delete/submit/payment buttons, request confirmation
- Never type into password fields (block and request manual input)
- Confirm with user before sensitive operations""",
    model="sonnet",  # Complex decision-making for interactions
    tools=[
        "mcp__browser__click",
        "mcp__browser__type_text",
        "mcp__browser__navigate",
        "mcp__browser__scroll",
        "mcp__browser__wait_for_load",
        "mcp__browser__wait_for_selector",
        "mcp__browser__wait_for_text",
        "mcp__browser__hover",
        "mcp__browser__select_option",
        "mcp__browser__switch_to_frame",
        "mcp__browser__screenshot"
    ]
)
```

**Fields**:
| Field | Value | Description |
|-------|-------|-------------|
| `description` | "Executes browser actions..." | Used by SDK to select this agent |
| `prompt` | (see above) | System prompt for execution behavior |
| `model` | "sonnet" | Complex reasoning for interaction decisions |
| `tools` | click, type_text, navigate, scroll, wait, hover, select_option, switch_to_frame, screenshot | Action tools |

---

### Validator Agent

```python
AgentDefinition(
    description="Validates task completion and verifies expected outcomes",
    prompt="""You are a result validator. You verify that tasks completed successfully.

When given validation criteria:
1. Check current page state (URL, title, content)
2. Verify expected elements are present/absent
3. Confirm page state matches expected outcome
4. Report success or failure with reasoning

Validation patterns:
- Page loaded: Check URL and title match expected
- Element clicked: Verify element state changed (button disabled, new content)
- Text entered: Confirm text appears in field
- Navigation successful: Check URL changed
- Task complete: Summarize what was achieved

Always:
- Be specific about what you're checking
- Provide evidence (screenshot, element state, URL)
- Note any discrepancies or partial success
- Suggest next steps if validation fails""",
    model="haiku",  # Lightweight verification checks
    tools=[
        "mcp__browser__get_accessibility_tree",
        "mcp__browser__get_page_text",
        "mcp__browser__screenshot",
        "mcp__browser__is_element_visible",
        "mcp__browser__wait_for_selector"
    ]
)
```

**Fields**:
| Field | Value | Description |
|-------|-------|-------------|
| `description` | "Validates task completion..." | Used by SDK to select this agent |
| `prompt` | (see above) | System prompt for validation behavior |
| `model` | "haiku" | Fast model for verification tasks |
| `tools` | get_accessibility_tree, get_page_text, screenshot, is_element_visible, wait_for_selector | Verification tools |

---

## Tool Schema

### Tool Categories

| Category | Tools | Purpose |
|----------|-------|---------|
| **Navigation** | navigate, go_back, go_forward, reload | Page navigation |
| **Interactions** | click, type_text, scroll, hover, select_option | Element interaction |
| **Frames** | list_frames, get_frame_content, switch_to_frame | Iframe handling |
| **Wait** | wait_for_load, wait_for_selector, wait_for_text, wait_for_url, sleep | Timing control |
| **Accessibility** | get_accessibility_tree, find_interactive_elements, get_page_text | Page analysis |
| **Screenshot** | screenshot, save_screenshot, get_viewport_info | Visual capture |

### Tool Input/Output Contract

**Standard Input Format**:
```python
{
    "element_description": str,  # Natural language description
    "frame": str | None,         # Optional frame selector
    "timeout_ms": int | None,    # Optional timeout
    # ... tool-specific parameters
}
```

**Standard Output Format**:
```python
{
    "success": bool,
    "data": Any,                 # Result data
    "error": str | None,         # Error message if failed
    "metadata": dict             # Timing, retries, frame context
}
```

### Security Integration

All tools with `security_check=True` (click, type_text) include:

```python
# Pre-execution flow:
1. DestructiveActionDetector.check_action()
2. If blocked: return error
3. If requires_confirmation: UserConfirmation.confirm_action()
4. If confirmed: execute tool
5. Return ToolResult
```

---

## Data Flow

### Request Flow

```
User Input → ClaudeSDKClient.query()
           ↓
       Planner Agent (Sonnet)
           ↓
    [Task tool calls to subagents]
           ↓
    +---- DOM Analyzer (Haiku) → Accessibility Tree
    +---- Executor (Sonnet) → Browser Tools → Playwright
    +---- Validator (Haiku) → Verification
           ↓
       Result to User
```

### Message Types

```python
# User Message
{"type": "user", "content": "Search for books"}

# Assistant Message with Tool Use
{"type": "assistant", "content": [
    {"type": "tool_use", "id": "123", "name": "Task", "input": {...}}
]}

# Tool Result Message
{"type": "assistant", "content": [
    {"type": "tool_result", "tool_use_id": "123", "content": "Task completed"}
]}

# Result Message (final)
{"type": "system", "subtype": "success", "result": "Task completed successfully"}
```

---

## State Management

### Session State

```python
{
    "session_id": str,              # SDK session identifier
    "browser_state": {
        "page_url": str,
        "page_title": str,
        "current_frame": str | None
    },
    "task_state": {
        "original_prompt": str,
        "sub_tasks": list[dict],
        "current_step": int
    },
    "context_window": list[Message]  # Sliding window of recent messages
}
```

### Page State (for agent context)

```python
{
    "url": str,
    "title": str,
    "accessibility_tree": dict,     # Recursive tree structure
    "interactive_elements": list[dict],
    "frames": list[dict],           # Frame metadata
    "screenshot_b64": str | None    # Optional visual context
}
```

---

## Validation Rules

### Tool Input Validation

- `element_description`: Required, non-empty string
- `frame`: Optional string, must match existing frame
- `timeout_ms`: Optional integer, 1000-60000 range

### Security Validation

**Blocked Actions** (no confirmation):
- Password/MFA input (type: password, otp, verification code)

**Requires Confirmation**:
- Delete actions (delete, remove, erase, clear)
- Send actions (send, submit, post, publish, reply)
- Payment actions (pay, buy, purchase, checkout, order)

### Cross-Origin Frame Handling

```python
{
    "accessible": bool,             # Can we access this frame?
    "reason": str | None,           # Why inaccessible (e.g., "SOP restriction")
    "fallback": str | None          # Alternative strategy
}
```

---

## Error Handling

### Error Categories

| Category | Retry Strategy | Examples |
|----------|---------------|----------|
| **Retriable** | Exponential backoff | Element not found, timeout |
| **Recoverable** | Re-analyze and adapt | Unexpected modal, overlay |
| **Non-retriable** | Fail fast | 404, auth failure |
| **Terminal** | Alert user | CAPTCHA, account blocked |

### Error Response Format

```python
{
    "success": False,
    "error": str,
    "metadata": {
        "retry_chain": {
            "strategies": list[str],
            "attempts": list[dict],
            "exhausted": bool
        }
    }
}
```

---

## Key Relationships

```
AgentDefinition → tools → ToolRegistry (existing)
     ↓
   prompt → LLM (Sonnet/Haiku)
     ↓
   Task tool → SubAgentDefinition
     ↓
   Tool execution → Playwright → PageState → Result
```
