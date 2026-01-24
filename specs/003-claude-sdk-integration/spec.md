# Feature Specification: Claude SDK Integration

**Feature Branch**: `003-claude-sdk-integration`
**Created**: 2026-01-24
**Status**: Draft
**Input**: User description: "Feature: Implement browser agent using Claude SDK exclusively..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simple Browser Automation (Priority: P1)

A user wants to automate a simple web task (e.g., "search for a product and add to cart") by providing natural language instructions. The system should understand the task, control the browser to complete it, and report the results.

**Why this priority**: This is the core value proposition - users want to give natural language instructions and have the browser agent complete web tasks. Without this, the system provides no user value.

**Independent Test**: Can be fully tested by running `python main.py "search for Python books and add the first result to cart"` and verifying the browser completes the task autonomously.

**Acceptance Scenarios**:

1. **Given** the user provides a natural language task, **When** the system starts, **Then** the browser launches and executes the requested task without manual intervention
2. **Given** the browser encounters an iframe (e.g., search widget), **When** the agent needs to interact with elements inside, **Then** the system automatically searches across all frames and finds the target elements
3. **Given** the task involves clicking a "Delete" button, **When** the agent attempts the action, **Then** the system detects the destructive action and prompts the user for confirmation before proceeding
4. **Given** the task completes successfully, **When** the agent finishes, **Then** the system reports the outcome with a summary of actions taken

---

### User Story 2 - Complex Multi-Step Tasks with Planning (Priority: P2)

A user wants to automate a complex task that requires multiple steps (e.g., "log into the site, navigate to settings, change preferences, and logout"). The system should break down the task into steps, execute them in sequence, and handle errors gracefully.

**Why this priority**: Complex tasks are a common use case but depend on the basic automation working first. This extends the value from simple one-shot tasks to sophisticated workflows.

**Independent Test**: Can be fully tested by running `python main.py "log into example.com with username user@example.com and change the timezone to UTC"` and verifying the agent navigates through multiple pages and completes all steps.

**Acceptance Scenarios**:

1. **Given** a multi-step task, **When** the planner agent analyzes it, **Then** the system breaks it into atomic sub-tasks with clear dependencies
2. **Given** a sub-task fails (e.g., element not found), **When** the error occurs, **Then** the executor agent attempts recovery strategies (retry, alternative selectors, coordinate click) before failing
3. **Given** all sub-tasks complete, **When** the validator agent reviews results, **Then** the system confirms the desired outcome was achieved (e.g., preferences actually changed)

---

### User Story 3 - Resilient Error Handling and Recovery (Priority: P3)

A user wants the system to handle common web automation failures gracefully (cross-origin iframes, dynamic content loading, overlays blocking clicks). When failures occur, the system should automatically retry with alternative strategies rather than failing immediately.

**Why this priority**: Error resilience improves reliability and user trust, but it's an enhancement to the core functionality. The system can work without it, just with lower success rates.

**Independent Test**: Can be tested by running tasks on sites known to have problematic elements (e.g., overlays, cross-origin iframes) and verifying the agent successfully completes tasks despite these obstacles.

**Acceptance Scenarios**:

1. **Given** an element is inside a cross-origin iframe, **When** the agent tries to interact, **Then** the system detects the Same-Origin Policy restriction, logs a warning, and continues searching in accessible frames
2. **Given** an iframe loads dynamically after page load, **When** the agent searches for elements, **Then** the system waits for frames to appear (up to timeout) before attempting interaction
3. **Given** a standard click is blocked by an invisible overlay, **When** the click fails, **Then** the system automatically falls back to coordinate-based clicking using the element's bounding box

---

### User Story 4 - Security Confirmation for Destructive Actions (Priority: P2)

A user wants the system to detect potentially dangerous actions (deleting data, submitting forms, making payments) and request confirmation before executing them. This prevents accidental damage from misinterpreted instructions.

**Why this priority**: Safety is critical for a system that controls a browser autonomously. Without confirmation, a misinterpreted instruction could delete user data or make unwanted purchases.

**Independent Test**: Can be tested by running `python main.py "delete my account"` and verifying the system blocks or requests confirmation rather than executing immediately.

**Acceptance Scenarios**:

1. **Given** the agent attempts to click a "Delete account" button, **When** the security detector identifies the action, **Then** the system displays a confirmation prompt and waits for user approval
2. **Given** the agent attempts to type into a password field, **When** the security detector identifies the input type, **Then** the system blocks the action and requests the user perform it manually
3. **Given** the user denies confirmation, **When** the rejection occurs, **Then** the system cancels the action and returns an error without executing
4. **Given** the user confirms the action, **When** approval is received, **Then** the system proceeds with the destructive operation

---

### Edge Cases

- What happens when the browser crashes or becomes unresponsive during task execution?
- How does the system handle CAPTCHA challenges that require human intervention?
- What happens when a website's structure changes mid-task (e.g., single-page app navigation)?
- How does the system handle rate limiting or IP blocking from aggressive automation?
- What happens when the user interrupts the task with Ctrl+C?
- How does the system handle network timeouts or slow page loads?
- What happens when the LLM provider API key is invalid or quota exceeded?
- How does the system handle tasks that require authentication credentials not provided by the user?
- What happens when multiple browser instances are needed concurrently?
- How does the system handle iframes with identical aria-labels or titles?

## Requirements *(mandatory)*

### Functional Requirements

#### Core Integration
- **FR-001**: System MUST provide a main CLI entry point that accepts natural language task descriptions and executes them
- **FR-002**: System MUST use the Claude Agent SDK as the sole orchestration framework for agent coordination
- **FR-003**: System MUST populate the AgentOrchestrator with all 23 registered tools from the tool registry (wait_for_load, wait_for_selector, wait_for_text, wait_for_url, sleep, navigate, go_back, go_forward, reload, get_accessibility_tree, find_interactive_elements, get_page_text, list_frames, get_frame_content, switch_to_frame, click, type_text, scroll, hover, select_option, screenshot, save_screenshot, get_viewport_info)
- **FR-004**: System MUST implement a tool dispatcher that executes tool functions and returns results to the SDK agent loop
- **FR-005**: System MUST provide page state (URL, title, text content, accessibility tree) to agents for decision-making

#### Agent Coordination
- **FR-006**: System MUST implement the 4-agent hierarchy: Planner (Sonnet), DOM Analyzer (Haiku), Executor (Sonnet), Validator (Haiku)
- **FR-007**: The Planner agent MUST decompose user tasks into atomic sub-tasks with clear dependencies
- **FR-008**: The DOM Analyzer agent MUST extract interactive elements and page structure for the Executor
- **FR-009**: The Executor agent MUST execute browser tools (click, type_text, navigate) based on Planner instructions
- **FR-010**: The Validator agent MUST verify task completion by checking expected outcomes

#### Tool Execution
- **FR-011**: System MUST execute tools asynchronously and await results before continuing the agent loop
- **FR-012**: System MUST convert ToolResult responses to SDK-compatible result format
- **FR-013**: System MUST handle tool errors gracefully and report them to the LLM for recovery attempts
- **FR-014**: System MUST integrate security confirmation prompts into the tool execution flow

#### Browser Automation
- **FR-015**: System MUST maintain existing iframe interaction capabilities (FR-001 through FR-027 from Feature 002)
- **FR-016**: System MUST maintain the retry chain mechanism for click and type_text tools
- **FR-017**: System MUST search across all frames (main + iframes) when frame parameter is not specified
- **FR-018**: System MUST provide frame context (name, index, src, accessibility) in tool results

#### Security
- **FR-019**: System MUST maintain the DestructiveActionDetector for classifying dangerous actions
- **FR-020**: System MUST block password and MFA input actions entirely
- **FR-021**: System MUST request user confirmation for delete, send/submit, and payment actions
- **FR-022**: System MUST display blocked action messages with clear explanations

#### Code Cleanup
- **FR-023**: System MUST remove the ReActPlanner class and related custom ReAct loop implementation
- **FR-024**: System MUST adapt the LLMProvider abstraction to return Claude SDK-compatible tool call format (preserving OpenAI-compatible API support per FR-027 from spec 001)
- **FR-025**: System MUST implement working AgentOrchestrator with Claude SDK, registering all tools and implementing the execute_tool callback
- **FR-026**: System MUST update CLAUDE.md to document the SDK-based architecture only

#### Error Handling
- **FR-027**: System MUST provide structured error responses when tools fail after all retry strategies
- **FR-028**: [REMOVED - Too broad, requires separate specification] Browser crash recovery is out of scope for this feature
- **FR-029**: System MUST request manual user intervention for CAPTCHAs and other human-only challenges
- **FR-030**: System MUST implement graceful shutdown on user interrupt (Ctrl+C)

### Key Entities

- **Task**: A user-provided natural language description of a web automation goal (e.g., "search for books")
- **Sub-Task**: An atomic action derived from a task by the Planner (e.g., "click search box", "type query", "press enter")
- **Tool**: A browser automation function registered in the tool registry (e.g., click, type_text, navigate)
- **Frame Context**: Metadata about an iframe (name, index, URL, accessibility status)
- **Security Check**: Result from DestructiveActionDetector indicating action type and confirmation requirements
- **Page State**: Snapshot of current browser context (URL, title, content, accessibility tree)
- **Agent Result**: Outcome from an agent (Planner, DOM Analyzer, Executor, Validator) containing data or errors

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can run a simple web automation task (e.g., search and navigate) by executing a single command with natural language input, completing the task autonomously
- **SC-002**: The system gracefully handles cross-origin iframe restrictions by detecting Same-Origin Policy limitations, logging warnings, and continuing with accessible frames in 100% of cases (interaction with cross-origin content is technically impossible)
- **SC-003**: 100% of password/MFA input attempts are blocked with clear user-facing messages
- **SC-004**: 100% of delete/send/payment actions trigger confirmation prompts before execution
- **SC-005**: The system recovers from transient failures (element not found, overlay blocking) without user intervention in 80% of cases
- **SC-006**: All 23 registered tools are accessible and functional through the SDK agent loop
- **SC-007**: Task completion time for a typical 3-step workflow is under 60 seconds (excluding page load times)
- **SC-008**: Code reduction: Remove at least 300 lines of unused/orphaned code (ReActPlanner, custom ReAct loop); adapt LLMProvider to SDK format (preserving OpenAI-compatible support)
- **SC-009**: Zero references to ReActPlanner remain in the active codebase; LLMProvider is adapted to Claude SDK format (preserved for OpenAI-compatible API support per spec 001 FR-027)
- **SC-010**: End-to-end integration test passes demonstrating a complete task from natural language to browser execution

## Technical Context *(for reference only)*

> **NOTE**: This section documents existing technical details for reference during planning. Implementation details should NOT appear in the above requirements.

### Existing Components (To Be Integrated)

The following components are fully implemented and must be preserved during SDK integration:

**Tools (23 total)**:
- Wait (5): wait_for_load, wait_for_selector, wait_for_text, wait_for_url, sleep
- Navigation (4): navigate, go_back, go_forward, reload
- Accessibility (3): get_accessibility_tree, find_interactive_elements, get_page_text
- Frames (3): list_frames, get_frame_content, switch_to_frame
- Interactions (5): click, type_text, scroll, hover, select_option
- Screenshot (3): screenshot, save_screenshot, get_viewport_info

**Security System**: DestructiveActionDetector classifies actions (DELETE, SEND, PAYMENT, PASSWORD, MFA), UserConfirmation provides Rich terminal UI for confirmations, integration via security_check flag in @tool decorator wrapper (runs before tool execution, blocks dangerous actions, prompts for confirmation)

**Iframe Capabilities**: Frame enumeration, cross-origin detection, retry chains, frame prioritization, recursive accessibility tree traversal

### Components To Modify/Remove

**Remove:**
- ReActPlanner class (`src/browser_agent/agents/planner.py`) - custom ReAct loop not needed with SDK
- Custom ReAct loop implementation in agents

**Adapt (not remove - preserves FR-027 from spec 001):**
- LLMProvider abstraction - adapt to return Claude SDK-compatible tool call format while preserving OpenAI-compatible API support

### Integration Strategy

Use Claude Agent SDK as the orchestration layer:
1. Register all 21 tools with the SDK
2. Implement tool dispatcher that calls registered tool functions
3. Implement page state builder for agent context
4. Wire up security confirmation in tool execution flow
5. Create main.py CLI entry point

Estimated new code: ~240 lines of "glue code"

## Dependencies

- Claude Agent SDK must be installed and configured
- ANTHROPIC_API_KEY environment variable must be set
- Existing Feature 002 (iframe interactions) must remain functional
- Existing Feature 003 (security system) must remain functional

## Assumptions

- Users have Python 3.11+ and uv package manager installed
- Users will provide necessary credentials (e.g., login passwords) when prompted
- Default browser will be Chromium (via Playwright)
- Single-threaded execution is sufficient (no concurrent browser instances needed initially)
- Claude API is available and responsive
- Users want CLI interface first; web UI is out of scope for this feature

## Open Questions

None - the feature requirements are clear based on existing architectural analysis.
