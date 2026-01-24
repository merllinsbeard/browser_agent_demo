# Quickstart: Browser Agent with Claude SDK

**Feature**: 003-claude-sdk-integration
**Last Updated**: 2026-01-24

## Overview

This guide will get you up and running with the browser automation agent using Claude Agent SDK. The agent can perform web tasks through natural language instructions.

---

## Prerequisites

- Python 3.11+
- uv package manager
- ANTHROPIC_API_KEY from [Anthropic Console](https://console.anthropic.com/)
- Chrome/Chromium browser (for Playwright)

---

## Installation

```bash
# Clone repository
git clone <repo-url>
cd browser_agent_demo

# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

---

## Configuration

Create a `.env` file in the project root:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (with defaults shown)
MODEL_SONNET=claude-sonnet-4-20250514
MODEL_HAIKU=claude-haiku-4-20250514
IFRAME_TIMEOUT_MS=10000
IFRAME_WAIT_MS=5000
SECURITY_CONFIRMATION_ENABLED=true
```

---

## Running the Agent

### Basic Usage

```bash
# Simple task
uv run python -m browser_agent.main "Search for Python books on Amazon"

# Multi-step task
uv run python -m browser_agent.main "Navigate to example.com, click the login button, then wait for the modal"

# Complex task with planning
uv run python -m browser_agent.main "Find contact form on the site, fill it with test data, submit, and verify confirmation message"
```

### CLI Options

```bash
# Verbose mode (shows all tool calls)
uv run python -m browser_agent.main "Your task" --verbose

# Custom model
uv run python -m browser_agent.main "Your task" --model haiku

# Start with URL
uv run python -m browser_agent.main "Your task" --start-url https://example.com

# Headless mode (for CI/CD)
uv run python -m browser_agent.main "Your task" --headless

# Session persistence (resume from previous session)
uv run python -m browser_agent.main "Your task" --resume <session-id>
```

---

## Development Quickstart

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# With coverage
uv run pytest tests/ --cov=src/browser_agent --cov-report=html
```

### Development Mode

```bash
# Start development server with auto-reload
uv run python -m browser_agent.main --dev

# Enable debug logging
export LOG_LEVEL=DEBUG
uv run python -m browser_agent.main "Your task"
```

---

## Example Tasks

### Task 1: Search and Navigate

```bash
uv run python -m browser_agent.main "Go to google.com, search for 'browser automation', click the first result"
```

**What happens**:
1. Planner agent breaks down the task
2. Executor agent navigates to google.com
3. DOM Analyzer finds the search box
4. Executor types and submits
5. DOM Analyzer finds results
6. Executor clicks first result
7. Validator confirms page loaded

### Task 2: Form Filling

```bash
uv run python -m browser_agent.main "Navigate to example.com/contact, fill the form with name 'John Doe', email 'john@example.com', submit the form"
```

**What happens**:
1. Navigate to contact page
2. Find form fields (name, email)
3. Type values into each field
4. Click submit button
5. **Confirmation prompt appears** (destructive action)
6. User confirms → form submitted
7. Verify confirmation message

### Task 3: Iframe Interaction

```bash
uv run python -m browser_agent.main "On the checkout page, select 'Visa' from the payment method dropdown inside the payment frame"
```

**What happens**:
1. List frames to find payment iframe
2. Switch to payment frame
3. Find dropdown element
4. Select option
5. Verify selection

---

## Troubleshooting

### "Claude Code not found" Error

```bash
# Install Claude Code CLI
curl -fsSL https://claude.ai/install.sh | bash

# Or via Homebrew
brew install --cask claude-code
```

### Playwright Browser Not Found

```bash
# Install Chromium
uv run playwright install chromium

# Install all browsers (optional)
uv run playwright install
```

### API Key Issues

```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# Set key temporarily
export ANTHROPIC_API_KEY=sk-ant-...

# Or add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### Iframe Elements Not Found

```bash
# Enable verbose logging to see frame detection
uv run python -m browser_agent.main "Your task" --verbose

# Check iframe timeout (increase if needed)
export IFRAME_TIMEOUT_MS=20000
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User Task                             │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  ClaudeSDKClient                             │
│                  (Claude Agent SDK)                          │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
              ┌─────────────┴─────────────┐
              ↓                           ↓
    ┌─────────────────┐         ┌─────────────────┐
    │  Planner Agent  │         │  MCP Server     │
    │   (Sonnet)      │◄────────┤  (23 Tools)     │
    └────────┬────────┘         └────────┬────────┘
             │                           │
             │ Task tool calls           │ Tool execution
             ↓                           ↓
    ┌─────────────────────────────────────────────┐
    │           Subagents (Haiku/Sonnet)         │
    │  ┌─────────────┬─────────────┬───────────┐ │
    │  │DOM Analyzer │  Executor   │ Validator │ │
    │  │   (Haiku)   │  (Sonnet)   │  (Haiku)  │ │
    │  └──────┬──────┴──────┬──────┴─────┬─────┘ │
    └─────────┼─────────────┼────────────┼───────┘
              ↓             ↓            ↓
         ┌──────────────────────────────────┐
         │       Playwright Browser        │
         │    (page, frames, elements)     │
         └──────────────────────────────────┘
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/browser_agent/main.py` | CLI entry point |
| `src/browser_agent/sdk_adapter.py` | Tool adapter for SDK |
| `src/browser_agent/agents/definitions.py` | Agent definitions |
| `src/browser_agent/agents/orchestrator.py` | SDK client wrapper |
| `src/browser_agent/tools/*.py` | Browser automation tools |
| `src/browser_agent/security/` | Destructive action detection |

---

## Next Steps

1. **Read the full specification**: `specs/003-claude-sdk-integration/spec.md`
2. **Review the architecture**: `specs/003-claude-sdk-integration/data-model.md`
3. **Check the implementation plan**: `specs/003-claude-sdk-integration/plan.md`
4. **Run the examples**: `examples/` directory

---

## Getting Help

- **Documentation**: `specs/003-claude-sdk-integration/`
- **Examples**: `examples/` directory
- **Tests**: `tests/` directory for usage examples
- **Issues**: GitHub issues tracker

---

## Performance Tips

1. **Use Haiku for repetitive tasks**: The DOM Analyzer and Validator use Haiku for fast, cheap operations
2. **Limit page state queries**: Call `get_accessibility_tree` once per page, cache results
3. **Use specific element descriptions**: "Search button in header" is faster than "button"
4. **Avoid excessive screenshots**: Only use when visual information is critical

---

## Security Notes

- **Destructive actions require confirmation**: Delete, submit, and payment actions prompt for approval
- **Password input is blocked**: The agent will never type into password fields
- **Session persistence**: Browser sessions are stored in `user_data_dir` for manual login workflows
- **API keys**: Never commit `.env` files to version control
