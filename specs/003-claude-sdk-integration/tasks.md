# Tasks: Claude SDK Integration

**Input**: Design documents from `/specs/003-claude-sdk-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are NOT included in this task list - existing test suite (80 passing) will be updated after implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/browser_agent/` at repository root
- **Tests**: `tests/unit/`, `tests/integration/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install SDK dependencies and prepare project structure

- [x] T001 Install Claude Agent SDK Python package via uv (claude-agent-sdk@latest)
- [x] T002 [P] Verify Claude Code CLI installation (required by SDK)
- [x] T003 [P] Update pyproject.toml with SDK dependency and Python 3.11+ requirement
- [x] T004 Create .claude/settings.json for project-level SDK configuration

**Checkpoint**: SDK installed and configured - ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core SDK integration that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create SDK adapter layer in src/browser_agent/sdk_adapter.py
- [x] T006 [P] Implement adapt_tool_for_sdk() function to wrap existing @tool tools
- [x] T007 [P] Implement create_browser_server() to create MCP server with 23 adapted tools
- [x] T008 [P] Implement tool_result_to_sdk_format() converter in src/browser_agent/sdk_adapter.py
- [x] T009 Update src/browser_agent/agents/definitions.py with AgentDefinition model tiers (sonnet/haiku)
- [x] T010 [P] Implement planner agent definition with Task tool access in src/browser_agent/agents/definitions.py
- [x] T011 [P] Implement dom_analyzer agent definition in src/browser_agent/agents/definitions.py
- [x] T012 [P] Implement executor agent definition in src/browser_agent/agents/definitions.py
- [x] T013 [P] Implement validator agent definition in src/browser_agent/agents/definitions.py
- [x] T014 Implement ClaudeSDKClient wrapper in src/browser_agent/agents/orchestrator.py
- [x] T015 Remove src/browser_agent/agents/planner.py (ReActPlanner class - ~150 lines)
- [x] T016 [P] Adapt src/browser_agent/llm/provider.py for SDK tool calling format (N/A - SDK handles LLM directly)
- [x] T017 [P] Adapt src/browser_agent/llm/anthropic_provider.py for SDK native implementation (N/A - SDK handles LLM directly)
- [x] T018 [P] Update src/browser_agent/llm/factory.py to return SDK-compatible provider (N/A - SDK handles LLM directly)
- [x] T019 Create main CLI entry point in src/browser_agent/main.py (~100 lines)

**Checkpoint**: SDK integration foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Simple Browser Automation (Priority: P1) 🎯 MVP

**Goal**: Users can run simple web automation tasks (search, navigate, click) through natural language instructions, with the browser completing tasks autonomously

**Independent Test**: Run `python -m browser_agent.main "Search for Python books and add first result to cart"` and verify browser completes the task without manual intervention

### Implementation for User Story 1

- [x] T020 [P] [US1] Wire up browser_server in ClaudeAgentOptions.mcp_servers in src/browser_agent/agents/orchestrator.py
- [x] T021 [P] [US1] Configure allowed_tools with all 23 browser tools in src/browser_agent/agents/orchestrator.py
- [x] T022 [US1] Implement main query loop in src/browser_agent/main.py using ClaudeSDKClient
- [x] T023 [P] [US1] Add CLI argument parser in src/browser_agent/main.py (--verbose, --model, --start-url, --headless)
- [x] T024 [P] [US1] Implement message output handler for AssistantMessage in src/browser_agent/tui/display.py
- [x] T025 [US1] Integrate security confirmation flow in SDK tool execution path (src/browser_agent/sdk_adapter.py)
- [ ] T026 [US1] Test end-to-end simple task: navigate to example.com and click first button
- [ ] T027 [US1] Test iframe handling: navigate to page with search iframe and interact with element
- [x] T028 [US1] Verify 80 existing tests still pass after SDK integration (119 passed)

**Checkpoint**: User Story 1 complete - simple automation tasks work via natural language

---

## Phase 4: User Story 2 - Complex Multi-Step Tasks (Priority: P2)

**Goal**: Users can automate complex multi-step tasks that require planning, decomposition, and sequential execution with error handling

**Independent Test**: Run `python -m browser_agent.main "Log into example.com with user@example.com, navigate to settings, change timezone to UTC, and logout"` and verify agent navigates through multiple pages and completes all steps

### Implementation for User Story 2

- [x] T029 [P] [US2] Implement planner agent prompt in src/browser_agent/agents/definitions.py with task decomposition logic
- [x] T030 [P] [US2] Implement executor agent retry strategies in src/browser_agent/agents/definitions.py (alternative descriptions, frames, coordinate click)
- [x] T031 [US2] Implement Task tool orchestration flow in src/browser_agent/agents/orchestrator.py
- [x] T032 [P] [US2] Add multi-turn conversation support in src/browser_agent/main.py (ClaudeSDKClient session)
- [x] T033 [US2] Implement subagent result aggregation and reporting in src/browser_agent/tui/display.py
- [ ] T034 [US2] Test complex multi-step task with planner decomposition
- [ ] T035 [US2] Test error recovery when sub-task fails (element not found → retry)

**Checkpoint**: User Story 2 complete - complex multi-step tasks work with planning and recovery

---

## Phase 5: User Story 3 - Error Handling & Recovery (Priority: P3)

**Goal**: System handles common web automation failures gracefully (cross-origin iframes, dynamic content, overlays) with automatic retry strategies

**Independent Test**: Run tasks on sites with problematic elements (overlays, cross-origin iframes) and verify agent successfully completes tasks despite obstacles

### Implementation for User Story 3

- [x] T036 [P] [US3] Implement cross-origin frame graceful skip in src/browser_agent/tools/interactions.py
- [x] T037 [P] [US3] Implement dynamic iframe wait polling in src/browser_agent/tools/frames.py
- [x] T038 [US3] Implement coordinate click fallback for overlay blocking in src/browser_agent/tools/interactions.py
- [x] T039 [P] [US3] Add retry chain logging for debugging in src/browser_agent/tools/interactions.py
- [ ] T040 [US3] Test cross-origin iframe handling (should skip gracefully with warning)
- [ ] T041 [US3] Test dynamic iframe loading (should wait for frames before interaction)
- [ ] T042 [US3] Test overlay blocking (should fall back to coordinate click)

**Checkpoint**: User Story 3 complete - error resilience working across edge cases

---

## Phase 6: User Story 4 - Security Confirmation (Priority: P2)

**Goal**: System detects potentially dangerous actions (deletions, payments, form submissions) and requests confirmation before executing them

**Independent Test**: Run `python -m browser_agent.main "Delete my account"` and verify system blocks or requests confirmation rather than executing immediately

### Implementation for User Story 4

- [x] T043 [P] [US4] Verify DestructiveActionDetector integration with SDK tools in src/browser_agent/sdk_adapter.py
- [x] T044 [P] [US4] Verify UserConfirmation prompts work in SDK context in src/browser_agent/security/confirmation.py
- [ ] T045 [US4] Test password blocking: `python -m browser_agent.main "Type password into login form"`
- [ ] T046 [US4] Test delete confirmation: `python -m browser_agent.main "Click delete account button"`
- [ ] T047 [US4] Test payment confirmation: `python -m browser_agent.main "Click checkout button"`
- [ ] T048 [US4] Test confirmation denial: cancel confirmation and verify action is blocked

**Checkpoint**: User Story 4 complete - security layer protecting against destructive actions

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements across all user stories

- [x] T049 [P] Update CLAUDE.md with SDK-based architecture documentation
- [x] T050 [P] Remove ReActPlanner and LLMProvider references from documentation
- [x] T051 [P] Create examples/ directory with example usage scripts
- [x] T052 [P] Add logging configuration via LOG_LEVEL environment variable
- [x] T053 [P] Add --dev flag for development mode with auto-reload
- [x] T054 [P] Update README.md with SDK-based quickstart instructions
- [ ] T055 Run quickstart.md validation examples to ensure they work
- [x] T056 [P] Add type hints to all new SDK integration code
- [x] T057 [P] Add docstrings to all public functions in src/browser_agent/sdk_adapter.py
- [x] T058 Performance optimization: cache page state queries within agent loop
- [x] T059 Security audit: verify no hardcoded selectors or action sequences
- [ ] T060 Final end-to-end test: complete multi-step task with all 4 user story features

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in parallel after Foundational (if staffed)
  - Or sequentially in priority order (P1 → P2 → P4 → P3)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends US1 with planning, but independently testable
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Security layer, works with any story
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances all stories with error recovery

### Within Each User Story

- Core implementation before integration
- Integration before testing
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks (T001-T004) can run in parallel
- Most Foundational tasks (T006-T018) can run in parallel (different files)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Within each story, tasks marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all adapter implementations together (after T005 completes):
Task: "Implement adapt_tool_for_sdk() function"
Task: "Implement create_browser_server() function"
Task: "Implement tool_result_to_sdk_format() converter"

# Launch all agent definitions in parallel:
Task: "Implement planner agent definition"
Task: "Implement dom_analyzer agent definition"
Task: "Implement executor agent definition"
Task: "Implement validator agent definition"

# Launch all CLI setup tasks together:
Task: "Wire up browser_server in ClaudeAgentOptions"
Task: "Configure allowed_tools with all 23 browser tools"
Task: "Add CLI argument parser"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T019) - CRITICAL
3. Complete Phase 3: User Story 1 (T020-T028)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Demo simple automation: navigate, search, click

### Incremental Delivery

1. Complete Setup + Foundational → SDK foundation ready
2. Add User Story 1 → Test independently → MVP Demo (simple automation)
3. Add User Story 2 → Test independently → Demo (complex multi-step)
4. Add User Story 4 → Test independently → Demo (security confirmation)
5. Add User Story 3 → Test independently → Demo (error resilience)
6. Polish phase → Production ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (P1) - Core automation
   - Developer B: User Story 2 (P2) - Planning & recovery
   - Developer C: User Story 4 (P2) - Security layer
3. Stories complete and integrate independently
4. User Story 3 (P3) can be added by anyone as enhancement

---

## Summary

- **Total Tasks**: 60
- **Setup Phase**: 4 tasks
- **Foundational Phase**: 15 tasks (BLOCKS all stories)
- **User Story 1 (P1)**: 9 tasks - MVP (simple automation)
- **User Story 2 (P2)**: 7 tasks - Complex tasks with planning
- **User Story 3 (P3)**: 7 tasks - Error handling & recovery
- **User Story 4 (P2)**: 6 tasks - Security confirmation
- **Polish Phase**: 12 tasks - Cross-cutting improvements

**Parallel Opportunities**: 30+ tasks marked [P] across all phases

**Independent Test Criteria**: Each user story has specific test scenario that validates it works independently

**MVP Scope**: Phases 1-3 (Setup + Foundational + User Story 1) = 28 tasks for core automation capability

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- SDK handles ReAct loop automatically - no need to implement manually
- Security confirmation already integrated via @tool decorator - preserve this flow
- All 23 existing tools must remain functional - adapter layer only, no rewrites
