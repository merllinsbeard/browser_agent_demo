# Implementation Plan: Claude SDK Integration

**Branch**: `003-claude-sdk-integration` | **Date**: 2026-01-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-claude-sdk-integration/spec.md`

## Summary

Integrate Claude Agent SDK as the sole orchestration framework for the browser automation agent, replacing the custom ReActPlanner approach. The implementation will register all 23 existing tools with the SDK, implement a tool dispatcher for execution, create a page state builder for agent context, and provide a CLI entry point. The LLMProvider abstraction will be adapted to support Claude SDK's tool calling format while preserving OpenAI-compatible API support per FR-027 from spec 001.

**Key Changes:**
- Remove: ReActPlanner class and custom ReAct loop (~300 lines)
- Adapt: LLMProvider to SDK-compatible format (preserve OpenAI support)
- Add: Tool dispatcher, page state builder, main.py CLI (~240 lines new)
- Preserve: All 23 tools, security system, iframe capabilities

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Claude Agent SDK (anthropic-agent-sdk), Playwright (playwright), Rich (terminal UI)
**Storage**: N/A (browser session persistence via user_data_dir only)
**Testing**: pytest (existing test suite: 80 passing)
**Target Platform**: CLI application on macOS/Linux/Windows
**Project Type**: Single project (src/browser_agent)
**Performance Goals**:
- Tool execution: <500ms average (excluding browser operations)
- Page state extraction: <2s for accessibility tree
- Agent loop iteration: <5s per action
- Model cost reduction: 60-70% through tiering (Sonnet for planning, Haiku for execution)
**Constraints**:
- Must maintain existing test coverage (80 passing tests)
- Must not break existing iframe capabilities (FR-001 through FR-027)
- Must preserve security confirmation flow (FR-019 through FR-022)
- Token efficiency: 10x reduction vs raw DOM (Constitution Principle III)
**Scale/Scope**:
- 23 tools to integrate with SDK
- 4-agent hierarchy: Planner (Sonnet), DOM Analyzer (Haiku), Executor (Sonnet), Validator (Haiku)
- Single-threaded execution (no concurrent browser instances)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Zero Hardcoding | ✅ PASS | Existing tools use natural language descriptions; no hardcoded selectors |
| II. Autonomy First | ✅ PASS | Agent operates independently; confirmation only for destructive actions (security system) |
| III. Context Efficiency | ✅ PASS | Uses Accessibility Tree as primary representation (existing get_accessibility_tree tool) |
| IV. Security Layer | ✅ PASS | DestructiveActionDetector + UserConfirmation integrated via @tool decorator |
| V. Model Tiering | ⚠️ IMPLEMENT | Need to define AgentDefinition with model tiers (Sonnet/Haiku) - Phase 0 research |
| VI. Visible Execution | ✅ PASS | Existing BrowserController launches visible browser; TUI displays tool calls |
| VII. Persistent Sessions | ✅ PASS | Existing SessionManager supports user_data_dir for manual login |

**Gate Result**: ✅ PASS (with Phase 0 research required for Model Tiering implementation details)

### Architecture Constraints Compliance

| Constraint | Status | Implementation Notes |
|------------|--------|---------------------|
| 4-Agent Hierarchy | ⚠️ IMPLEMENT | Planner exists (ReActPlanner to be removed); DOM Analyzer, Executor, Validator need SDK AgentDefinition |
| Sub-Agent Definition (SDK) | ⚠️ RESEARCH | Need to define AgentDefinition structure for each agent type - Phase 0 |
| Page Representation Stack | ✅ PASS | AxTree via get_accessibility_tree, screenshots via screenshot tool |
| Technology Stack | ✅ PASS | Playwright ✅, Claude Agent SDK to be added ✅, OpenAI-compatible abstraction to be adapted ✅ |
| Tool Design (@tool) | ✅ PASS | All 23 tools use @tool decorator pattern already |
| ReAct Loop Structure | ⚠️ REPLACE | Custom ReActPlanner loop → SDK-managed loop |
| SDK Knowledge Source | ⚠️ RESEARCH | Need to consult `/agent-sdk-dev:new-sdk-app` skill for current SDK patterns |

**Action Items for Phase 0 Research:**
1. Claude Agent SDK AgentDefinition structure and model tier specification
2. SDK tool registration pattern for existing @tool decorated functions
3. SDK-managed ReAct loop vs custom loop differences
4. LLMProvider adaptation strategy for SDK tool calling format

## Project Structure

### Documentation (this feature)

```text
specs/003-claude-sdk-integration/
├── spec.md              # Feature specification (already complete)
├── plan.md              # This file
├── research.md          # Phase 0 output (SDK patterns, AgentDefinition structure)
├── data-model.md        # Phase 1 output (agent definitions, tool schemas)
├── quickstart.md        # Phase 1 output (developer onboarding)
├── contracts/           # Phase 1 output (tool schemas for SDK registration)
│   ├── tools.json       # All 23 tools in SDK-compatible format
│   └── agent-definitions.json  # 4 agent definitions with model tiers
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/browser_agent/
├── agents/
│   ├── planner.py              # REMOVE: ReActPlanner class (~150 lines)
│   ├── orchestrator.py         # MODIFY: Implement SDK integration
│   ├── definitions.py          # MODIFY: Update AgentDefinition with model tiers
│   ├── dom_analyzer.py         # KEEP: Sub-agent implementation
│   ├── executor.py             # KEEP: Sub-agent implementation
│   └── validator.py            # KEEP: Sub-agent implementation
├── tools/
│   ├── base.py                 # MODIFY: Add SDK tool adapter
│   ├── interactions.py         # KEEP: click, type_text, scroll, hover, select_option
│   ├── navigation.py           # KEEP: navigate, go_back, go_forward, reload
│   ├── accessibility.py        # KEEP: get_accessibility_tree, find_interactive_elements, get_page_text
│   ├── frames.py               # KEEP: list_frames, get_frame_content, switch_to_frame
│   ├── wait.py                 # KEEP: wait_for_load, wait_for_selector, wait_for_text, wait_for_url, sleep
│   └── screenshot.py           # KEEP: screenshot, save_screenshot, get_viewport_info
├── security/
│   ├── detector.py             # KEEP: DestructiveActionDetector
│   └── confirmation.py         # KEEP: UserConfirmation
├── browser/
│   ├── controller.py           # KEEP: BrowserController
│   └── session.py              # KEEP: SessionManager
├── llm/
│   ├── provider.py             # MODIFY: Adapt to SDK tool calling format
│   ├── anthropic_provider.py   # MODIFY: SDK-native implementation
│   ├── openai_compatible_provider.py  # KEEP: OpenAI-compatible support
│   └── factory.py              # MODIFY: Return SDK-compatible provider
├── tui/
│   └── display.py              # KEEP: Rich terminal UI
├── __init__.py
└── main.py                     # ADD: CLI entry point (~100 lines)
```

**Structure Decision**: Single project structure (Option 1) - CLI tool with core library in src/browser_agent. No backend/frontend separation needed.

## Complexity Tracking

> No constitution violations requiring justification. All checks pass with Phase 0 research items identified.

## Phase 0: Research & Unknowns Resolution

### Research Tasks

1. **Claude Agent SDK - AgentDefinition Structure**
   - **Question**: How do I define agents with model tiers (Sonnet vs Haiku) in Claude Agent SDK?
   - **Source**: `/agent-sdk-dev:new-sdk-app` skill
   - **Output**: AgentDefinition pattern for 4-agent hierarchy

2. **Claude Agent SDK - Tool Registration**
   - **Question**: How do I register existing @tool decorated functions with the SDK?
   - **Source**: `/agent-sdk-dev:new-sdk-app` skill
   - **Output**: Tool adapter pattern for get_all_tools() → SDK registration

3. **Claude Agent SDK - Managed ReAct Loop**
   - **Question**: How does SDK handle the ReAct loop vs custom implementation?
   - **Source**: `/agent-sdk-dev:new-sdk-app` skill
   - **Output**: Loop management strategy, when to use SDK vs custom

4. **LLMProvider - Tool Calling Format**
   - **Question**: What format does Claude Agent SDK expect for tool calls?
   - **Source**: SDK documentation
   - **Output**: Adapter to convert ToolResult → SDK response format

5. **SDK Orchestration Pattern**
   - **Question**: How do I orchestrate 4 agents (Planner → DOM Analyzer/Executor/Validator) in SDK?
   - **Source**: `/agent-sdk-dev:new-sdk-app` skill
   - **Output**: Orchestration flow, agent coordination pattern

### Unknowns from Technical Context

| Unknown | Research Task | Decision Point |
|---------|--------------|----------------|
| AgentDefinition model tier syntax | Task 1 | Phase 1: data-model.md |
| Tool registration API | Task 2 | Phase 1: contracts/tools.json |
| SDK ReAct loop hooks | Task 3 | Phase 1: orchestrator.py implementation |
| Tool call response format | Task 4 | Phase 1: base.py adapter |
| Agent orchestration API | Task 5 | Phase 1: orchestrator.py flow |

### Research Execution

**Phase 0 Status**: ✅ COMPLETE

All research questions resolved. See `research.md` for detailed findings:

1. ✅ **AgentDefinition Structure**: Use `model` field for tiering (sonnet/haiku)
2. ✅ **Tool Registration**: Use `create_sdk_mcp_server()` with adapter layer
3. ✅ **ReAct Loop**: SDK handles automatically via `ClaudeSDKClient`
4. ✅ **Tool Calling Format**: MCP format with `content` + `is_error` fields
5. ✅ **Orchestration**: Use Task tool for subagent delegation

---

## Phase 1: Design & Contracts

### Data Model

**Status**: ✅ COMPLETE - See `data-model.md`

Created comprehensive data model with:
- 4 AgentDefinitions (Planner, DOM Analyzer, Executor, Validator)
- Tool schema contracts for all 23 tools
- Message types and data flow
- State management structures
- Error handling patterns

### API Contracts

**Status**: ✅ COMPLETE - See `contracts/`

Generated contract files:
- `contracts/tools.json` - All 23 tools with input/output schemas
- `contracts/agent-definitions.json` - 4 agent definitions with model tiers

### Agent Context Update

**Status**: ✅ COMPLETE

Updated `CLAUDE.md` with:
- Language: Python 3.11+
- Framework: Claude Agent SDK, Playwright, Rich
- Project type: Single project (src/browser_agent)
- Database: N/A (user_data_dir persistence)

---

## Quickstart Guide

**Status**: ✅ COMPLETE - See `quickstart.md`

Created developer onboarding guide with:
- Installation instructions
- Configuration setup
- Running the agent examples
- Troubleshooting tips
- Architecture overview diagram
