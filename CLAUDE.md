# Browser Agent - Claude AI Instructions

This document contains project-specific instructions for Claude AI agents working on the browser automation codebase.

## Project Overview

The browser automation agent uses Playwright to interact with web pages, with special support for **iframe interactions**. Modern sites often embed content in iframes (search widgets, ads, payment forms), which requires special handling.

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
# Iframe Configuration (to be added to .env.example per T036)
IFRAME_TIMEOUT_MS=10000       # Timeout per frame attempt (FR-020)
IFRAME_WAIT_MS=5000           # Wait for dynamic iframes (FR-026)
```

### Default Values

- **Frame Depth Limit**: 3 levels (hardcoded, FR-008)
- **Timeout Per Frame**: 10000ms (10s, FR-020)
- **Dynamic Frame Wait**: 5000ms (5s, FR-026)
- **Frame Polling Interval**: 500ms (FR-026)

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

## Testing

### Unit Tests

Located in `tests/unit/test_frame_tools.py`:
- `TestRetryChainStateMachine` - RetryChain state machine tests (T029)
- `TestStructuredErrorResponse` - Error response format tests (T030)
- Frame content and switching tests (T027, T028)

### Integration Tests

Located in `tests/integration/test_iframes.py`:
- `test_search_in_iframe` - Iframe search flow (T009)
- `test_click_iframe_interception` - Click interception handling (T016)

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Frame tools only
uv run pytest tests/unit/test_frame_tools.py -v

# Integration tests
uv run pytest tests/integration/test_iframes.py -v
```

## Feature Reference

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

## Implementation Status

**Completed** (Phase 6 - User Story 4):
- ✅ T001-T034: All implementation tasks complete
- ✅ RetryChain state machine
- ✅ Structured error responses
- ✅ Configurable timeouts
- ✅ Frame metadata tracking

**In Progress** (Phase 7 - Polish):
- ⏳ T035: Update CLAUDE.md (this file)
- ⏳ T036: Add iframe configuration to .env.example
- ⏳ T037-T039: Validation and testing

## See Also

- `specs/002-iframe-interaction-fixes/spec.md` - Feature specification
- `specs/002-iframe-interaction-fixes/plan.md` - Implementation plan
- `specs/002-iframe-interaction-fixes/tasks.md` - Task checklist
- `README.md` - Project documentation
