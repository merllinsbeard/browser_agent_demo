<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR - Claude Agent SDK integration details added

Added/Modified sections:
- Model Tiering (V): SDK model parameters ("sonnet", "haiku"), AgentDefinition reference
- Architecture Constraints: Sub-Agent Definition via AgentDefinition, @tool decorator pattern
- Technology Stack: Claude Agent SDK + OpenAI-compatible abstraction for OpenRouter/local models
- SDK Knowledge Source: /agent-sdk-dev:new-sdk-app skill for up-to-date SDK patterns

Unchanged:
- 7 Core Principles structure preserved
- Control Flow Requirements unchanged
- Governance rules unchanged

Templates requiring updates:
- .specify/templates/plan-template.md: ✅ OK (generic constitution reference)
- .specify/templates/spec-template.md: ✅ OK (no constitution refs)
- .specify/templates/tasks-template.md: ✅ OK (no constitution refs)
- .specify/templates/agent-file-template.md: ✅ OK (no constitution refs)

Deferred items: None
-->

# Browser Automation Agent Constitution

## Core Principles

### I. Zero Hardcoding

The agent MUST determine its own actions dynamically based on page analysis.

**NON-NEGOTIABLE RULES:**
- MUST NOT contain pre-written action sequences for specific tasks
- MUST NOT use hardcoded CSS/XPath selectors (e.g., `a[data-qa='vacancy']`)
- MUST NOT include hints about specific URLs, paths, or element text
- MUST discover page structure and interaction targets at runtime

**Rationale:** This is the core differentiator from traditional automation scripts.
The agent demonstrates intelligence by reasoning about unfamiliar interfaces.

### II. Autonomy First

The agent MUST operate independently until task completion or explicit user input is required.

**NON-NEGOTIABLE RULES:**
- MUST determine next action based on current page state and task goal
- MUST NOT require user confirmation for routine navigation/interaction
- MUST request user input ONLY when: information is missing, clarification needed,
  or destructive action requires confirmation (see Security Layer)
- MUST provide task completion report with actions taken

**Rationale:** Test assignment explicitly requires autonomy without constant participation.

### III. Context Efficiency

The agent MUST minimize token usage through intelligent page representation.

**NON-NEGOTIABLE RULES:**
- MUST use Accessibility Tree (`page.accessibility.snapshot()`) as primary representation
- MUST NOT send raw DOM to LLM context (150K+ tokens per page)
- MAY use Vision (screenshots) as fallback for spatial/visual elements only
- MUST achieve minimum 10x token reduction vs raw DOM
- MUST keep only latest snapshot in context (no history accumulation)

**Rationale:** Token limits and cost optimization are production requirements.
AxTree provides semantic structure that maps directly to LLM reasoning.

### IV. Security Layer

The agent MUST confirm potentially destructive actions with the user.

**NON-NEGOTIABLE RULES:**
- MUST request confirmation before: payment/checkout, deletion, sending messages
- MUST clearly describe the action and its consequences
- MUST NOT proceed without explicit user approval for destructive operations
- MUST log all destructive action requests and user responses

**Rationale:** Advanced pattern requirement from test assignment. Prevents
unintended financial transactions, data loss, or unauthorized communications.

### V. Model Tiering

The agent MUST use appropriate model tiers to optimize cost without sacrificing quality.

**NON-NEGOTIABLE RULES:**
- Planner Agent: MUST use Claude Sonnet (SDK `model: "sonnet"`) for complex reasoning, task decomposition
- Sub-agents (DOM Analyzer, Executor, Validator): MUST use Claude Haiku (SDK `model: "haiku"`) for volume ops
- Sub-agents defined via `AgentDefinition` with explicit model tier specification
- Target: 60-70% cost reduction through tiering
- MUST NOT use expensive models for repetitive/mechanical operations

**Rationale:** Production viability requires cost optimization.
Planner handles complexity; executors handle volume.
Claude Agent SDK provides native model selection via AgentDefinition.

### VI. Visible Execution

The agent MUST operate with full visibility for debugging and demonstration.

**NON-NEGOTIABLE RULES:**
- MUST launch browser with `headless=False` (visible window)
- MUST display tool calls and their arguments in terminal/UI
- MUST show agent reasoning/thoughts before actions
- MUST NOT operate in hidden/headless mode

**Rationale:** Test assignment requires visible browser. Debugging and demo
recording require transparency of agent decision-making process.

### VII. Persistent Sessions

The agent MUST support user-authenticated sessions without automating login.

**NON-NEGOTIABLE RULES:**
- MUST use `launch_persistent_context` with `user_data_dir`
- MUST allow user to login manually before agent operation
- MUST NOT automate login/password entry or MFA flows
- MUST preserve session state between agent invocations

**Rationale:** Security requirement - credentials never touch agent code.
Practical requirement - many sites have anti-bot login protection.

## Architecture Constraints

**Agent Pattern: 4-Agent Hierarchy (REQUIRED)**
```
User Request → Planner (Sonnet) → [DOM Analyzer | Executor | Validator] (Haiku) → Playwright
```

- Planner: Task decomposition, strategy, re-planning on failure
- DOM Analyzer: AxTree parsing, element detection, vision fusion
- Executor: Browser actions (click, type, navigate)
- Validator: Pre-execution checks, state verification, error detection

**Sub-Agent Definition (Claude Agent SDK):**
Sub-agents MUST be defined via `AgentDefinition` with fields:
- `description`: Agent purpose for orchestrator
- `prompt`: System prompt with specialized instructions
- `tools`: List of available tools (subset of 7 workflow tools)
- `model`: Tier specification ("sonnet" | "haiku" | "inherit")

**Page Representation Stack:**
1. Primary: Accessibility Tree via `page.accessibility.snapshot()`
2. Fallback: Screenshots for visual-only content (dropdowns, overlays)
3. Prohibited: Raw DOM parsing

**Technology Stack:**
- Browser Automation: Playwright (NOT Puppeteer, NOT Selenium)
- AI SDK: Claude Agent SDK for orchestration (NOT raw Anthropic API)
- LLM Abstraction: OpenAI-compatible API layer for provider flexibility (OpenRouter, local models)
- Language: Python 3.11+

**SDK Knowledge Source:**
- Use `/agent-sdk-dev:new-sdk-app` skill for up-to-date Claude Agent SDK patterns and documentation
- This skill provides current API signatures, AgentDefinition structure, @tool decorator usage
- Always consult this skill before implementing SDK-related features

**Tool Design: Minimal Workflow-Oriented Set (7 tools max)**

Tools implemented via `@tool` decorator pattern for native SDK integration:

| Tool | Purpose |
|------|---------|
| `navigate_to_url` | Go to URL |
| `take_screenshot` | Capture visible/full page |
| `click_element` | Click by natural language description |
| `input_text` | Type into field by description |
| `select_option` | Select from dropdown |
| `scroll` | Scroll page up/down |
| `wait_for` | Wait for condition |

Prohibited: Exposing 80+ Playwright APIs as individual tools.
Prohibited: Using MCP servers for browser tools (native @tool preferred for AxTree control).

## Control Flow Requirements

**ReAct Loop Structure:**
```
Observation → Thought → Action → (repeat until complete or max iterations)
```

**Iteration Limits:**
- MAX_ITERATIONS: 10-15 per task (prevent infinite loops)
- Confidence threshold: early exit when high confidence achieved

**Retry Strategy:**
- Exponential backoff: 1s → 2s → 4s
- Max retries per action: 3

**Error Classification:**

| Category | Examples | Strategy |
|----------|----------|----------|
| Retriable | Network timeout, element loading, stale element | Retry with backoff |
| Non-retriable | 404, auth failure, invalid credentials | Fail fast, report |
| Recoverable | Popup appeared, unexpected page change | Re-observe, adapt |
| Terminal | CAPTCHA wall, account blocked | Alert user, stop |

**Memory Module:**
- Retain multi-step context for task continuity
- Clear on task completion or explicit reset

## Governance

**Constitution Authority:**
This constitution supersedes all other practices. When conflict exists between
feature specs, implementation plans, or code patterns and this constitution,
the constitution prevails.

**Amendment Process:**
1. Document the reason for change
2. Obtain approval from project lead
3. Create migration plan for affected code
4. Update version according to semantic versioning:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle or material expansion
   - PATCH: Clarification, wording, non-semantic changes

**Compliance Verification:**
- All PRs MUST pass constitution compliance check
- Code review checklist includes:
  - [ ] No hardcoded selectors or action sequences
  - [ ] Proper model tier usage
  - [ ] Security layer for destructive actions
  - [ ] AxTree as primary page representation
  - [ ] Visible execution mode

**Complexity Justification:**
Any deviation from minimal architecture MUST answer:
"Why is the simpler approach insufficient?"

**Version**: 1.1.0 | **Ratified**: 2026-01-21 | **Last Amended**: 2026-01-21
