# Browser Agent - Claude AI Instructions

This document contains project-specific instructions for Claude AI agents working on the browser automation codebase.

## Project Overview

The browser automation agent uses Playwright to interact with web pages, with special support for:
- **Claude Agent SDK integration** for AI-powered browser automation (Feature 003)
- **iframe interactions** with cross-frame element discovery (Feature 002)
- **Security and user confirmation** for destructive actions
- **Multi-agent architecture** powered by Claude Agent SDK

Modern sites often embed content in iframes (search widgets, ads, payment forms), which requires special handling. Additionally, certain actions like deletions, payments, or form submissions require explicit user confirmation for safety.

## Architecture Overview

### Component Structure

```
src/browser_agent/
├── agents/              # Agent orchestration (Claude SDK integration)
│   ├── orchestrator.py  # AgentOrchestrator with ClaudeSDKClient
│   └── definitions.py   # AgentDefinition configs (planner, executor, etc.)
├── browser/             # Playwright wrapper (BrowserController, SessionManager)
├── tools/               # Tool registry with @tool decorator pattern
├── sdk_adapter.py       # SDK adapter layer (MCP server, tool conversion)
├── main.py              # CLI entry point for browser automation
├── security/            # Destructive action detection and user confirmation
└── tui/                 # Rich terminal UI for agent output
```

### Claude Agent SDK Architecture

The agent uses Claude Agent SDK for AI-powered browser automation:

```python
# SDK adapter creates MCP server with 23 browser tools
from browser_agent.sdk_adapter import create_browser_server, get_allowed_tools

# Orchestrator wraps SDK with browser lifecycle
from browser_agent.agents.orchestrator import create_orchestrator

async with create_orchestrator(headless=True) as orchestrator:
    async for message in orchestrator.execute_task_stream(task):
        print(message)
```

**Key Components**:
- **sdk_adapter.py**: Adapts existing @tool functions for SDK compatibility
- **AgentOrchestrator**: Manages browser lifecycle and SDK client
- **MCP Server**: Exposes browser tools via Model Context Protocol
- **Agent Definitions**: Configures planner, executor, dom_analyzer, validator agents

### Tool Registry Pattern

All browser automation tools use the `@tool` decorator for registration:

```python
from .base import tool, ToolResult

@tool(
    name="click",
    description="Click an element on the page",
    parameters={...},
)
async def click(page: Page, description: str, ...) -> ToolResult:
    # Implementation
    return ToolResult(success=True, data={...})
```

**Security Integration**: Tools that perform destructive actions (click, type_text) automatically invoke the security module for action classification and user confirmation.

## Iframe Interaction System (Feature 002)

### Core Problem

Elements inside iframes are not directly accessible from the main page context. The agent must:
1. Detect iframes on the page
2. Search across all frame contexts for elements
3. Retry interactions with fallback strategies
4. Provide detailed error reporting

### Frame Tools Module (`src/browser_agent/tools/frames.py`)

#### 1. `list_frames(page, include_inaccessible=True)`

**Purpose**: Enumerate all frames on the page with metadata.

**Returns**:
```python
{
    "frames": [
        {
            "name": "main",
            "index": 0,
            "src": "https://example.com",
            "aria_label": None,
            "title": None,
            "accessible": True,
            "parent_index": None
        },
        {
            "name": "search-widget",
            "index": 1,
            "src": "https://search.example.com/widget",
            "aria_label": "Search",
            "title": "Search Widget",
            "accessible": True,
            "parent_index": 0
        }
    ],
    "total_count": 2,
    "accessible_count": 2
}
```

**Use When**: You need to understand the frame structure of a page before targeting elements.

**Frame Selection Priority** (FR-025):
1. Main frame (index 0) - always first
2. Frames with semantic labels (aria-label > title > name)
3. Remaining frames by index

#### 2. `get_frame_content(page, frame_selector, content_type="text", max_length=10000)`

**Purpose**: Extract content from a specific frame (main or iframe).

**Frame Selectors**:
- `"main"` or `"0"` - Main frame
- Frame name (e.g., `"search-frame"`)
- aria-label (e.g., `"Yandex Search"`)
- title attribute
- Numeric index (e.g., `"1"`, `"2"`)

**Example**:
```python
# Get text content from iframe by name
result = await get_frame_content(page, "search-frame", "text")

# Get HTML content from main frame
result = await get_frame_content(page, "main", "html")
```

**Returns**:
```python
{
    "content": "Visible text from frame...",
    "frame_context": {...},
    "content_type": "text",
    "length": 1234
}
```

#### 3. `switch_to_frame(page, frame_selector)`

**Purpose**: Explicitly switch to a frame context for subsequent operations.

**Returns**:
```python
{
    "frame_context": {...},
    "frame_selector": "search-frame",  # Recommended selector for click/type_text
    "interactive_element_count": 12,
    "message": "Switched to frame 'search-frame'. Use frame='search-frame' for click/type_text operations."
}
```

**Use When**: You want to explicitly set frame context before multiple operations.

### Interaction Tools with Iframe Support (`src/browser_agent/tools/interactions.py`)

#### 1. `click(page, description, role=None, double_click=False, right_click=False, frame=None, timeout_per_frame_ms=10000)`

**Auto-Retry Chain** (FR-015, FR-017):
1. Try main frame first
2. Try each iframe (prioritized by semantic labels)
3. Fallback to coordinate_click (bounding box center)

**Frame Parameter**:
- If `frame` is specified: only search that frame
- If `frame` is None: auto-retry across all frames

**Example**:
```python
# Auto-search across all frames
result = await click(page, "Search button")

# Explicit frame targeting
result = await click(page, "Search button", frame="search-frame")
```

**Success Response**:
```python
{
    "action": "clicked",
    "element": {"tag": "BUTTON", "text": "Search"},
    "frame_context": {
        "name": "search-frame",
        "index": 1,
        "src": "https://...",
        "accessible": True
    },
    "retry_chain": {
        "strategies": ["main_frame", "iframe:search-frame", "coordinate_click"],
        "attempts": [
            {
                "strategy": "main_frame",
                "success": False,
                "error": "Element not found",
                "duration_ms": 245
            },
            {
                "strategy": "iframe:search-frame",
                "success": True,
                "duration_ms": 512
            }
        ]
    }
}
```

**Failure Response** (FR-019):
```python
{
    "success": False,
    "error": "Failed to click after all retry strategies",
    "data": {
        "retry_chain": {
            "strategies": ["main_frame", "iframe:0", "iframe:1", "coordinate_click"],
            "attempts": [
                {"strategy": "main_frame", "success": False, "error": "...", "duration_ms": 123},
                {"strategy": "iframe:0", "success": False, "error": "...", "duration_ms": 456},
                ...
            ],
            "exhausted": True,
            "succeeded": False
        }
    }
}
```

#### 2. `type_text(page, text, description=None, clear_first=True, press_enter=False, frame=None, timeout_per_frame_ms=10000)`

**Same retry chain pattern as click**.

**Example**:
```python
# Auto-search across all frames
result = await type_text(page, "weather forecast", description="Search input")

# Explicit frame targeting
result = await type_text(page, "query", description="Search box", frame="search-widget")
```

#### 3. `coordinate_click(page, description)` (Internal Tool)

**Purpose**: Fallback strategy using bounding box center + `page.mouse.click`.

**Use When**: Element is found but standard click fails (e.g., intercepted by iframe overlay).

### Accessibility Tools with Frame Support (`src/browser_agent/tools/accessibility.py`)

#### `get_accessibility_tree(page, max_depth=10)`

**Frame Traversal** (FR-005, FR-008):
- Recursively traverses iframes up to depth 3
- Merges accessibility trees from all frames
- Adds frame metadata markers to each element

**Frame Metadata Markers** (FR-006):
```python
{
    "role": "textbox",
    "name": "Search",
    "frame_name": "search-widget",
    "frame_index": 1,
    "frame_path": "main > search-widget"
}
```

#### `find_interactive_elements(page)`

**Cross-Frame Search** (FR-007):
- Searches main frame + all iframes
- Returns elements with frame context
- Prioritizes semantically labeled frames

### Frame Models (`src/browser_agent/tools/frame_models.py`)

#### `FrameContext`

Represents a frame (main or iframe) with metadata:
```python
{
    "name": "search-frame",        # Frame name attribute
    "index": 1,                     # Position in page.frames
    "src": "https://...",           # Frame URL
    "aria_label": "Search",         # Semantic label
    "title": "Search Widget",       # Title attribute
    "accessible": True,             # False for cross-origin
    "parent_index": 0               # For nested iframes
}
```

#### `InteractionAttempt`

Records a single interaction attempt:
```python
{
    "strategy": "iframe:search-frame",
    "frame_context": {...},
    "success": True,
    "duration_ms": 512,
    "error": None
}
```

#### `RetryChain`

State machine for retry strategies:
```python
{
    "strategies": ["main_frame", "iframe:search-frame", "coordinate_click"],
    "current_index": 1,
    "max_attempts": 3,
    "attempts": [...],
    "timeout_per_frame_ms": 10000
}
```

**Properties**:
- `current_strategy` - Returns current strategy to try
- `is_exhausted` - True if all strategies attempted
- `has_succeeded` - True if any attempt succeeded

**Methods**:
- `advance()` - Move to next strategy
- `add_attempt()` - Record attempt result
- `to_error_dict()` - Convert to error response (FR-019)

## Security System (Feature 003)

### Overview

The security system protects against unintended destructive actions by:
1. **Detecting** potentially dangerous actions (deletions, payments, form submissions)
2. **Blocking** high-risk actions (password/MFA input)
3. **Requesting confirmation** for medium-risk actions

### DestructiveActionDetector (`src/browser_agent/security/detector.py`)

Classifies actions based on description and element context:

```python
from browser_agent.security.detector import DestructiveActionDetector

detector = DestructiveActionDetector()
security_check = detector.check_action(
    action_description="Delete account",
    element_context={"tag": "BUTTON", "text": "Delete"},
    page_context={"url": "https://example.com/settings"}
)

if security_check.requires_confirmation:
    # Ask user for confirmation
    pass
```

**Action Types**:
- `ActionType.SAFE` - No confirmation needed
- `ActionType.DELETE` - Delete/remove/clear actions
- `ActionType.SEND` - Submit/send/publish actions
- `ActionType.PAYMENT` - Pay/checkout/purchase actions
- `ActionType.PASSWORD` - **BLOCKED** - Password input
- `ActionType.MFA` - **BLOCKED** - MFA/OTP input

**Detection Patterns**:

| Category | Patterns (examples) |
|----------|---------------------|
| Delete | delete, remove, erase, clear, destroy, forget |
| Send | send, submit, post, publish, transfer, reply |
| Payment | pay, buy, purchase, checkout, order, subscribe |
| Password | password, passwd, passcode, secret (blocked) |
| MFA | otp, code, verification, authenticator (blocked) |

**SecurityCheck Response**:
```python
{
    "action_type": ActionType.DELETE,
    "requires_confirmation": True,
    "is_blocked": False,
    "confidence": 0.9,
    "matched_patterns": ["delete"],
    "confirmation_prompt": "This will delete an item. Continue?"
}
```

### UserConfirmation (`src/browser_agent/security/confirmation.py`)

Rich terminal UI for user confirmations:

```python
from browser_agent.security.confirmation import UserConfirmation

confirmation = UserConfirmation()

# Request confirmation for destructive action
result, user_response = confirmation.confirm_action(
    action_description="Delete account",
    action_type="DELETE",
    details={"url": "https://example.com/settings"},
    prompt="This action cannot be undone. Continue?"
)

if result == ConfirmationResult.CONFIRMED:
    # Proceed with action
    pass
```

**Confirmation Types**:
- `ConfirmationResult.CONFIRMED` - User approved the action
- `ConfirmationResult.DENIED` - User rejected the action
- `ConfirmationResult.CANCELLED` - User cancelled (Ctrl+C)

**Manual Input Request** (for CAPTCHA, login, etc.):
```python
success = confirmation.request_manual_input(
    message="Please complete the CAPTCHA",
    wait_message="Press Enter when done..."
)
```

**Blocked Action Display**:
```python
confirmation.show_blocked_action(
    reason="Password input is not allowed for security reasons",
    suggestion="Please enter passwords manually"
)
```

### Tool Integration

Security is integrated via the `@tool` decorator in `src/browser_agent/tools/base.py`:

```python
@tool(
    name="click",
    description="Click an element on the page",
    security_check=True,  # Enables security for this tool
)
async def click(page: Page, description: str, ...) -> ToolResult:
    # Security check runs automatically before tool execution
    # - Action classified by DestructiveActionDetector
    # - User confirmation requested if needed
    # - Blocked actions return error without executing
    ...
```

**Tools with Security Enabled**:
- `click` - Checks button/link text for destructive patterns
- `type_text` - Checks input description for password/MFA patterns

**Tools without Security** (safe operations):
- `navigate` - Navigation only
- `scroll` - View manipulation only
- `wait` - Passive waiting only

### Configuration

Environment variables (`.env`):
```bash
# Security settings
SECURITY_CONFIRMATION_ENABLED=true    # Enable user confirmations (default: true)
SECURITY_BLOCK_PASSWORD_INPUT=true    # Block password/MFA input (default: true)
SECURITY_CONFIDENCE_THRESHOLD=0.5     # Minimum confidence for confirmation
```

## Cross-Origin Frame Handling (FR-027)

**Same-Origin Policy**: Cross-origin iframes are inaccessible due to browser security.

**Detection**:
```python
def is_cross_origin_frame(frame: Frame) -> bool:
    try:
        _ = frame.url
        _ = frame.title
        return False  # Same-origin
    except Exception:
        return True   # Cross-origin
```

**Graceful Handling**:
- Log warning when cross-origin iframe detected
- Skip inaccessible frames in search
- Continue with accessible frames only
- `list_frames` shows all frames but marks `accessible: False`

**Example**:
```python
# Returns all frames, including cross-origin
result = await list_frames(page, include_inaccessible=True)

# Filter to only accessible frames
result = await list_frames(page, include_inaccessible=False)
```

## Dynamic Frame Loading (FR-026)

Some sites load iframes dynamically after initial page load.

**Helper**: `_wait_for_dynamic_iframes(page, timeout_ms=5000, poll_interval_ms=500)`

**Usage** (internal):
```python
# Wait for dynamically loaded iframes
frames = await _wait_for_dynamic_iframes(page, expected_count=3)
```

## Configuration

### Environment Variables (`.env`)

```bash
# LLM Provider
ANTHROPIC_API_KEY=sk-ant-...

### OpenRouter Configuration (Alternative)

To use OpenRouter instead of direct Anthropic API:

```bash
# In .env
ANTHROPIC_BASE_URL=https://openrouter.ai/api
ANTHROPIC_AUTH_TOKEN=sk-or-v1-your-openrouter-key
ANTHROPIC_API_KEY=  # Leave empty
```

OpenRouter provides Anthropic-compatible API endpoint for Claude Agent SDK.

**Model Selection**: OpenRouter maps model aliases automatically:
- `sonnet` → `anthropic/claude-3.5-sonnet` (or latest)
- `opus` → `anthropic/claude-3-opus` (or latest)
- `haiku` → `anthropic/claude-3-haiku` (or latest)

You can also specify full model names like `google/gemini-2-flash` or `meta-llama/llama-3.1-70b`.

# Model Selection
MODEL_SONNET=claude-sonnet-4-20250514      # High-quality reasoning
MODEL_HAIKU=claude-haiku-4-20250514        # Fast lightweight tasks
MODEL_OPUS=claude-opus-4-20250514          # Maximum quality

# Iframe Configuration
IFRAME_TIMEOUT_MS=10000       # Timeout per frame attempt (FR-020)
IFRAME_WAIT_MS=5000           # Wait for dynamic iframes (FR-026)

# Security Settings
SECURITY_CONFIRMATION_ENABLED=true    # Enable user confirmations
SECURITY_BLOCK_PASSWORD_INPUT=true    # Block password/MFA input
SECURITY_CONFIDENCE_THRESHOLD=0.5     # Minimum confidence for confirmation
```

### Default Values

- **Frame Depth Limit**: 3 levels (hardcoded, FR-008)
- **Timeout Per Frame**: 10000ms (10s, FR-020)
- **Dynamic Frame Wait**: 5000ms (5s, FR-026)
- **Frame Polling Interval**: 500ms (FR-026)
- **Security Confidence Threshold**: 0.5

## Best Practices

### 1. Frame Discovery

Before targeting elements, discover available frames:
```python
frames_result = await list_frames(page)
for frame in frames_result.data["frames"]:
    print(f"Frame {frame['index']}: {frame.get('aria_label') or frame.get('name')}")
```

### 2. Auto-Retry vs Explicit Targeting

**Use Auto-Retry** (default) when:
- You don't know which frame contains the element
- The site structure is unknown
- You want maximum reliability

```python
result = await click(page, "Submit button")
```

**Use Explicit Targeting** when:
- You know exactly which frame contains the element
- You want to avoid unnecessary searches
- Performance is critical

```python
result = await click(page, "Submit button", frame="payment-frame")
```

### 3. Error Debugging

When interactions fail, inspect the retry chain:
```python
if not result.success:
    retry_chain = result.data.get("retry_chain", {})
    for attempt in retry_chain.get("attempts", []):
        print(f"Strategy: {attempt['strategy']}")
        print(f"  Success: {attempt['success']}")
        print(f"  Duration: {attempt['duration_ms']}ms")
        if attempt.get("error"):
            print(f"  Error: {attempt['error']}")
```

### 4. Cross-Origin Detection

Always check `accessible` status:
```python
result = await list_frames(page)
for frame in result.data["frames"]:
    if not frame["accessible"]:
        logger.warning(f"Skipping cross-origin frame: {frame['name']}")
```

### 5. Frame Priority Order

When multiple iframes exist, search order is:
1. Main frame (index 0)
2. Frames with aria-label (e.g., `"Search"`, `"Payment"`)
3. Frames with title (e.g., `"Search Widget"`)
4. Frames with name (e.g., `"search-frame"`)
5. Remaining frames by index (e.g., `1`, `2`)

### 6. Security Best Practices

- **Always** enable security for production use
- **Never** disable password/MFA blocking for automated tasks
- **Review** confirmation prompts before approving
- **Test** destructive actions in a safe environment first

## Testing

### Unit Tests

Located in `tests/unit/`:
- `test_frame_tools.py` - RetryChain state machine (T029), error responses (T030), frame content (T027-T028)
- `test_security.py` - DestructiveActionDetector, UserConfirmation

### Integration Tests

Located in `tests/integration/`:
- `test_iframes.py` - Iframe search flow (T009), click interception (T016)
- `test_security_integration.py` - Security flow with click/type_text tools

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Frame tools only
uv run pytest tests/unit/test_frame_tools.py -v

# Security tests
uv run pytest tests/unit/test_security.py -v

# Integration tests
uv run pytest tests/integration/ -v

# With coverage
uv run pytest tests/ --cov=src/browser_agent --cov-report=html
```

## Feature Reference

### Iframe Interactions (Feature 002)
- **FR-001**: Frame enumeration with metadata
- **FR-002**: Cross-origin detection
- **FR-004**: Element search across all frames
- **FR-005**: Recursive iframe traversal in accessibility tree
- **FR-006**: Frame context metadata markers
- **FR-007**: Cross-frame interactive element search
- **FR-008**: Frame depth limiting (max 3 levels)
- **FR-010**: Element discovery in iframes
- **FR-011**: Frame context in ToolResult
- **FR-013**: Click tool frame parameter
- **FR-014**: Type text tool frame parameter
- **FR-015**: Click retry chain with fallback
- **FR-016**: Frame context switch logging
- **FR-017**: Coordinate click fallback
- **FR-018**: Iframe interception detection
- **FR-019**: Structured error response with attempts
- **FR-020**: Configurable timeout_per_frame_ms
- **FR-021**: list_frames tool
- **FR-022**: switch_to_frame tool
- **FR-023**: get_frame_content tool
- **FR-024**: coordinate_click implementation
- **FR-025**: Semantic frame prioritization
- **FR-026**: Dynamic iframe wait
- **FR-027**: Cross-origin graceful handling

### Security System (Feature 003)
- **FR-028**: DestructiveActionDetector for action classification
- **FR-029**: UserConfirmation with rich terminal UI
- **FR-030**: Tool registry integration via @tool decorator
- **FR-031**: Password/MFA input blocking
- **FR-032**: Delete action detection and confirmation
- **FR-033**: Send/submit action detection and confirmation
- **FR-034**: Payment action detection and confirmation

## Implementation Status

**Feature 002 - Iframe Interactions**: ✅ Complete
- ✅ T001-T034: All implementation tasks complete
- ✅ RetryChain state machine
- ✅ Structured error responses
- ✅ Configurable timeouts
- ✅ Frame metadata tracking
- ✅ Cross-origin graceful handling

**Feature 003 - Security System**: ✅ Complete
- ✅ DestructiveActionDetector implementation
- ✅ UserConfirmation with rich terminal UI
- ✅ Tool registry integration via @tool decorator
- ✅ Unit tests for detector and confirmation
- ✅ Integration tests for security flow

**Feature 004 - Claude SDK Integration**: 🚧 In Progress
- ✅ Phase 1 (Setup): SDK dependencies and configuration
- ✅ Phase 2 (Foundational): SDK adapter, agent definitions, orchestrator
- ✅ T025: Security checks integrated with SDK adapter
- ✅ T036-T039 (US3): Error handling (from iframe feature)
- ✅ T043-T044 (US4): Security integration verified
- 🕐 T026-T027, T040-T042, T045-T048: Manual E2E validation pending
- 🕐 Phase 7 (Polish): Documentation and cleanup tasks

**Project Cleanup** (Jan 2026): ✅ Complete
- ✅ Removed dead code (burger scripts, main.py placeholder)
- ✅ Cleaned git history of exposed API keys
- ✅ Updated .gitignore with security rules
- ✅ Removed non-existent Intelligent Button documentation

## See Also

- `specs/003-claude-sdk-integration/tasks.md` - SDK integration task checklist
- `specs/002-iframe-interaction-fixes/spec.md` - Iframe feature specification
- `specs/002-iframe-interaction-fixes/tasks.md` - Iframe task checklist
- `README.md` - Project documentation

## Active Technologies
- Python 3.11+ + Claude Agent SDK (anthropic-agent-sdk), Playwright (playwright), Rich (terminal UI) (003-claude-sdk-integration)
- N/A (browser session persistence via user_data_dir only) (003-claude-sdk-integration)

## Recent Changes
- 003-claude-sdk-integration: Added Python 3.11+ + Claude Agent SDK (anthropic-agent-sdk), Playwright (playwright), Rich (terminal UI)
