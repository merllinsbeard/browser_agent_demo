# Tasks: Iframe Interaction Fixes

**Input**: Design documents from `/specs/002-iframe-interaction-fixes/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Included per SC-007 requirement (>80% coverage for iframe scenarios)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Project type**: Single CLI tool
- **Source**: `src/browser_agent/`
- **Tests**: `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create shared data models and module structure

- [x] T001 Create Pydantic models (FrameContext, FrameLocatorResult, InteractionAttempt, RetryChain) in src/browser_agent/tools/frame_models.py
- [x] T002 [P] Create frames.py module skeleton with @tool decorator imports in src/browser_agent/tools/frames.py
- [x] T003 [P] Create test directory structure: tests/integration/test_iframes.py and tests/unit/test_frame_tools.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core frame utilities that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement list_frames tool that enumerates page.frames with attributes (name, src, aria-label, title, accessible) in src/browser_agent/tools/frames.py
- [x] T005 [P] Implement _prioritize_frames() utility for semantic-first frame search order (FR-025) in src/browser_agent/tools/frames.py
- [x] T006 [P] Implement _wait_for_dynamic_iframes() with 5s timeout and 500ms polling (FR-026) in src/browser_agent/tools/frames.py
- [x] T007 Implement cross-origin detection with warning logging and graceful skip (FR-027) in src/browser_agent/tools/frames.py
- [x] T008 Register frames.py tools in src/browser_agent/tools/__init__.py

**Checkpoint**: Foundation ready - frame enumeration, prioritization, and error handling complete

---

## Phase 3: User Story 1 - Iframe Search (Priority: P1) 🎯 MVP

**Goal**: Agent successfully enters search query on sites with iframe-embedded search widgets (Yandex/Dzen, Google)

**Independent Test**: Task "Open yandex.ru and search for weather" → Agent detects iframe, enters query, gets results

### Tests for User Story 1

- [x] T009 [P] [US1] Integration test for iframe search flow in tests/integration/test_iframes.py::test_search_in_iframe
- [x] T010 [P] [US1] Unit test for _find_element_in_all_frames in tests/unit/test_frame_tools.py::test_find_element_all_frames

### Implementation for User Story 1

- [x] T011 [US1] Add optional frame_selector parameter to _find_element_by_description() in src/browser_agent/tools/interactions.py
- [x] T012 [US1] Implement _find_element_in_all_frames() utility that searches main frame then iframes (FR-004, FR-010) in src/browser_agent/tools/interactions.py
- [x] T013 [US1] Enhance type_text tool with frame parameter and auto-search (FR-014) in src/browser_agent/tools/interactions.py
- [x] T014 [US1] Add frame_context to ToolResult.data for all successful interactions (FR-011) in src/browser_agent/tools/interactions.py
- [x] T015 [US1] Add frame context switch logging (FR-016) in src/browser_agent/tools/interactions.py

**Checkpoint**: User Story 1 complete - agent can find and type into iframe inputs

---

## Phase 4: User Story 2 - Click Interception (Priority: P2)

**Goal**: Agent detects when click is blocked by iframe overlay and retries in correct frame context

**Independent Test**: Task "Click on search bar on dzen.ru" → Agent detects interception, clicks inside iframe context

### Tests for User Story 2

- [x] T016 [P] [US2] Integration test for click interception handling in tests/integration/test_iframes.py::test_click_iframe_interception
- [x] T017 [P] [US2] Unit test for coordinate_click fallback in tests/unit/test_frame_tools.py::test_coordinate_click

### Implementation for User Story 2

- [x] T018 [US2] Implement coordinate_click() using bounding_box center and page.mouse.click (FR-024) in src/browser_agent/tools/interactions.py
- [x] T019 [US2] Enhance click tool with frame parameter and auto-search (FR-013) in src/browser_agent/tools/interactions.py
- [x] T020 [US2] Add iframe interception detection on TimeoutError (FR-018) in src/browser_agent/tools/interactions.py
- [x] T021 [US2] Implement click retry chain: main_frame → iframes → coordinate_click (FR-015, FR-017) in src/browser_agent/tools/interactions.py

**Checkpoint**: User Story 2 complete - agent handles click interception with fallback strategies

---

## Phase 5: User Story 3 - Accessibility Tree (Priority: P2)

**Goal**: get_accessibility_tree and find_interactive_elements include iframe contents with frame metadata

**Independent Test**: Call get_accessibility_tree on page with iframe → Result includes elements from all frames with metadata

### Tests for User Story 3

- [x] T022 [P] [US3] Unit test for recursive frame traversal in tests/unit/test_frame_tools.py::test_recursive_accessibility_tree
- [ ] T023 [P] [US3] Unit test for frame metadata markers in tests/unit/test_frame_tools.py::test_frame_metadata_format

### Implementation for User Story 3

- [ ] T024 [US3] Implement recursive frame traversal in get_accessibility_tree up to depth 3 (FR-005, FR-008) in src/browser_agent/tools/accessibility.py
- [ ] T025 [US3] Add frame context metadata markers to merged accessibility tree (FR-006) in src/browser_agent/tools/accessibility.py
- [ ] T026 [US3] Enhance find_interactive_elements to search all frames (FR-007) in src/browser_agent/tools/accessibility.py
- [ ] T027 [US3] Implement get_frame_content tool for explicit frame content extraction (FR-023) in src/browser_agent/tools/frames.py
- [ ] T028 [US3] Implement switch_to_frame tool for explicit context switching (FR-022) in src/browser_agent/tools/frames.py

**Checkpoint**: User Story 3 complete - accessibility tree includes all frame contents

---

## Phase 6: User Story 4 - Error Recovery (Priority: P3)

**Goal**: Smart retry logic with structured error reporting showing all attempts

**Independent Test**: Simulate failed click → Agent auto-retries via alternative strategies → Returns detailed error with all attempts

### Tests for User Story 4

- [ ] T029 [P] [US4] Unit test for RetryChain state machine in tests/unit/test_frame_tools.py::test_retry_chain_state_machine
- [ ] T030 [P] [US4] Unit test for structured error response in tests/unit/test_frame_tools.py::test_structured_error_response

### Implementation for User Story 4

- [ ] T031 [US4] Implement RetryChain state machine with strategy progression in src/browser_agent/tools/interactions.py
- [ ] T032 [US4] Add InteractionAttempt tracking to click and type_text tools in src/browser_agent/tools/interactions.py
- [ ] T033 [US4] Return structured error with attempts[] array on final failure (FR-019) in src/browser_agent/tools/interactions.py
- [ ] T034 [US4] Add configurable timeout_per_frame_ms parameter (FR-020, default 10000) in src/browser_agent/tools/interactions.py

**Checkpoint**: User Story 4 complete - full retry chain with detailed error reporting

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and final quality checks

- [ ] T035 [P] Update CLAUDE.md with new iframe tools documentation
- [ ] T036 [P] Add iframe configuration to .env.example (IFRAME_TIMEOUT_MS, IFRAME_WAIT_MS)
- [ ] T037 Validate all quickstart.md test scenarios pass
- [ ] T038 Run full test suite and verify >80% iframe coverage (SC-007)
- [ ] T039 Verify all existing tests still pass (SC-006 backward compatibility)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2 → P2 → P3)
  - US2 and US3 are both P2 and can run in parallel after US1
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Priority | Depends On | Can Parallel With |
|-------|----------|------------|-------------------|
| US1 (Iframe Search) | P1 | Foundational | None (MVP first) |
| US2 (Click Interception) | P2 | Foundational + US1 T012 (_find_element_in_all_frames) | US3 |
| US3 (Accessibility Tree) | P2 | Foundational | US2 |
| US4 (Error Recovery) | P3 | US1, US2 (uses retry chain) | None |

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Utilities before tools
- Core implementation before logging/metadata
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 can run in parallel (Setup)
- T005, T006 can run in parallel (Foundational)
- T009, T010 can run in parallel (US1 tests)
- T016, T017 can run in parallel (US2 tests)
- T022, T023 can run in parallel (US3 tests)
- T029, T030 can run in parallel (US4 tests)
- T035, T036 can run in parallel (Polish)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: T009 "Integration test for iframe search flow in tests/integration/test_iframes.py::test_search_in_iframe"
Task: T010 "Unit test for _find_element_in_all_frames in tests/unit/test_frame_tools.py::test_find_element_all_frames"

# Then implement sequentially (dependencies between tasks):
Task: T011 → T012 → T013 → T014 → T015
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T008)
3. Complete Phase 3: User Story 1 (T009-T015)
4. **STOP and VALIDATE**: Test "Open yandex.ru and search for weather in Moscow"
5. Deploy/demo if ready - iframe search works!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **MVP Ready!**
3. Add User Story 2 → Test independently → Click interception works
4. Add User Story 3 → Test independently → Full accessibility tree
5. Add User Story 4 → Test independently → Robust error handling
6. Polish phase → Production ready

### File Modification Summary

| File | Phase | Action |
|------|-------|--------|
| src/browser_agent/tools/frame_models.py | 1 | NEW |
| src/browser_agent/tools/frames.py | 2 | NEW |
| src/browser_agent/tools/__init__.py | 2 | MODIFY |
| src/browser_agent/tools/interactions.py | 3,4,6 | MODIFY |
| src/browser_agent/tools/accessibility.py | 5 | MODIFY |
| tests/integration/test_iframes.py | 3,4 | NEW |
| tests/unit/test_frame_tools.py | 3,4,5,6 | NEW |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Performance target: < 500ms overhead for frame scanning (per plan.md)
- Nested iframe depth limit: 3 (hardcoded per spec clarification)
