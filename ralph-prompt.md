# Ralph Loop Iteration

You are running as part of an autonomous development loop. Each iteration: read context, pick ONE task, implement, verify, commit, update progress.

---

## 1. Session Start Protocol (READ FIRST)

Read these files in order (skip if not found):

1. `CLAUDE.md` or `AGENTS.md` — project-specific instructions
2. `README.md`, `CONTRIBUTING.md` — project context
3. Determine current feature from git branch: `git branch --show-current`
   - Branch format: `XXX-feature-name` (e.g., `001-feature`)
   - Specs location: `specs/<branch-name>/`
4. `specs/<branch-name>/tasks.md` — task checklist (source of truth)
5. `progress.txt` — log of completed work from previous iterations

---

## 2. Task Tracking (CRITICAL)

### 2.1 Find the Task List

```bash
# 1. Get current branch name
BRANCH=$(git branch --show-current)
# Example: 001-user-auth

# 2. Task file location
specs/${BRANCH}/tasks.md
# Example: specs/001-user-auth/tasks.md
```

### 2.2 Task Format in tasks.md

```markdown
## Phase 1: Setup

- [x] T001 Initialize project structure ← COMPLETED (skip)
- [ ] T002 Add configuration file

## Phase 2: Core Features

- [ ] T003 [P] Implement main feature
- [ ] T004 [P] Add error handling
- [ ] T005 Write tests for core module (depends on T003)
```

**Legend:**

- `[ ]` = pending (DO THIS)
- `[x]` = completed (SKIP)
- `[P]` = can run in parallel
- `[US1]` = belongs to User Story 1
- `(depends on T004)` = dependency

### 2.3 How to Choose Next Task

```
1. Open specs/<branch>/tasks.md
2. Scan from top to bottom
3. Find FIRST task with `- [ ]` (unchecked)
4. Check if it has dependencies:
   - "(depends on T004)" → T004 must be [x] first
   - If dependency not done → skip to next [ ] task
5. Selected task = first [ ] with all dependencies [x]
```

**Priority order within phases:**

- Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3+ (User Stories by P1, P2, P3) → Final (Polish)

### 2.4 Mark Task Complete (AFTER implementation + verification)

**Step 1:** Edit `specs/<branch>/tasks.md`:

```markdown
# BEFORE

- [ ] T003 Implement main feature

# AFTER

- [x] T003 Implement main feature
```

**Step 2:** Append to `progress.txt`:

```
=== 2026-01-20 21:45 | Iteration 3 ===
Task: T003 Implement main feature
Branch: 001-feature
Files changed:
  - src/feature.ts (created)
  - src/index.ts (modified)
Decisions: Used existing utility pattern from src/utils
Status: DONE
Next: T004 (error handling)
```

### 2.5 Two Files, Two Purposes

| File           | Purpose                    | Update When                          |
| -------------- | -------------------------- | ------------------------------------ |
| `tasks.md`     | **Checklist** — what to do | Change `[ ]` → `[x]` after task done |
| `progress.txt` | **Log** — what was done    | Append entry after each iteration    |

**tasks.md** = source of truth for remaining work
**progress.txt** = history for context between iterations

**If no tasks.md exists:** Look for tasks in spec.md user stories or plan.md.

---

## 3. Implement

- **Read project docs first**: Check CLAUDE.md, README.md, CONTRIBUTING.md for conventions
- **Follow existing patterns**: Match code style, naming, structure of the project
- **Small steps**: One logical change per iteration
- **Run existing checks**: If project has tests/lint/build — use them before committing

---

## 4. Verify

Run project's feedback loops before committing. Detect what exists:

```
# Look for these files and run appropriate commands:
# - package.json    → npm test / npm run lint / npm run build
# - Makefile        → make test / make lint / make check
# - pyproject.toml  → pytest / ruff / mypy
# - Cargo.toml      → cargo test / cargo clippy
# - go.mod          → go test ./...
# - .github/workflows/ → see what CI runs and replicate locally
```

**DO NOT commit if checks fail.** Fix issues first.

---

## 5. Commit & Update Progress

Follow section 2.4 for updating tasks.md and progress.txt, then:

### Git commit

```bash
git add .
git commit -m "feat(module): description

- What was done
- Why

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**DO NOT push to remote** — human will review.

---

## 6. Completion Signal

When ALL tasks in `specs/<branch-name>/tasks.md` are marked `- [x]`:

```
<promise>COMPLETE</promise>
```

This signals the loop to stop.

---

## Rules Summary

| Rule                   | Description                              |
| ---------------------- | ---------------------------------------- |
| ONE task per iteration | Don't combine multiple tasks             |
| Follow project style   | Match existing patterns and conventions  |
| All checks must pass   | No commit with failing tests/lint/build  |
| Update both files      | tasks.md (checkbox) + progress.txt (log) |
| No push                | Human reviews before push                |
| Quality over speed     | Small, correct steps                     |
| Document blockers      | If stuck, write to progress.txt          |
