# Browser Automation Agent

An intelligent browser automation agent powered by Claude Agent SDK. Uses a 4-agent hierarchy to execute complex browser tasks from natural language instructions.

## Features

- **Natural Language Tasks**: Describe what you want to do, the agent figures out how
- **Claude Agent SDK**: Powered by Anthropic's official agent framework
- **Visible Browser**: Watch the agent interact with web pages in real-time
- **Multi-Step Task Handling**: Complex tasks are decomposed and executed with planning
- **Security Safeguards**: Destructive actions require user confirmation
- **Session Persistence**: Login once, stay logged in across sessions
- **Rich TUI Output**: Color-coded thought/action/result display
- **Multi-Turn Conversations**: Interactive sessions with context preservation

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Anthropic API key

## Quickstart

### 1. Install

```bash
# Clone and enter directory
git clone https://github.com/your-org/browser-automation-agent.git
cd browser-automation-agent

# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### 2. Configure

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run

```bash
# Single task
python -m browser_agent.main "Navigate to example.com and tell me the page title"

# Interactive mode
python -m browser_agent.main

# With options
python -m browser_agent.main "Search for Python" --verbose --headless
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--verbose`, `-v` | Show detailed output including tool calls |
| `--headless` | Run browser without visible window |
| `--model` | Model tier: sonnet (default), haiku, opus |
| `--start-url` | Navigate to URL before running task |
| `--max-turns` | Maximum agent iterations (default: 15) |
| `--max-budget` | Maximum spend in USD (default: 10.0) |
| `--dev` | Development mode with debug logging |

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional - Logging
LOG_LEVEL=INFO                        # DEBUG, INFO, WARNING, ERROR

# Optional - Model Configuration
PLANNER_MODEL=sonnet                  # Model for planning: sonnet, haiku, opus

# Optional - Browser Configuration
BROWSER_HEADLESS=false                # true for headless mode
BROWSER_VIEWPORT_WIDTH=1280
BROWSER_VIEWPORT_HEIGHT=720

# Optional - Session Configuration
SESSION_PERSIST=true                  # Persist browser sessions
SESSIONS_DIR=.browser-sessions        # Session storage directory
```

## Usage Examples

### Python API

```python
import asyncio
from browser_agent.agents.orchestrator import create_orchestrator

async def main():
    # Create orchestrator with visible browser
    orchestrator = create_orchestrator(
        headless=False,
        max_turns=15,
    )

    async with orchestrator:
        # Execute task with streaming output
        async for message in orchestrator.execute_task_stream(
            "Navigate to wikipedia.org and search for Python"
        ):
            print(message)

asyncio.run(main())
```

### Interactive Session (Multi-Turn)

```python
import asyncio
from browser_agent.agents.orchestrator import create_orchestrator

async def main():
    orchestrator = create_orchestrator(headless=False)

    async with orchestrator:
        # Create session with context preservation
        async with await orchestrator.create_session() as session:
            # First query
            async for msg in session.query("Navigate to example.com"):
                print(msg)

            # Follow-up (remembers we're on example.com)
            async for msg in session.query("Click the first link"):
                print(msg)

asyncio.run(main())
```

See `examples/` directory for more usage examples.

## Architecture

The agent uses Claude Agent SDK with a 4-tier hierarchy:

1. **Planner** (sonnet): High-level task decomposition and coordination
2. **DOM Analyzer** (haiku): Fast page structure analysis
3. **Executor** (sonnet): Precise browser action execution with retry strategies
4. **Validator** (haiku): Action verification and result checking

### Key Modules

- `browser_agent/agents/` - Agent orchestration with Claude SDK
- `browser_agent/sdk_adapter.py` - SDK adapter layer for browser tools
- `browser_agent/browser/` - Playwright browser management
- `browser_agent/tools/` - 23 browser automation tools
- `browser_agent/tui/` - Rich terminal UI components
- `browser_agent/security/` - Destructive action detection

### Tool Categories

| Category | Tools |
|----------|-------|
| Navigation | navigate, go_back, go_forward, reload |
| Interaction | click, type_text, scroll, hover, select_option |
| Accessibility | get_accessibility_tree, find_interactive_elements, get_page_text |
| Frames | list_frames, switch_to_frame, get_frame_content |
| Waiting | wait_for_load, wait_for_selector, wait_for_text |
| Screenshots | screenshot, save_screenshot, get_viewport_info |

## Security

The agent includes safety features:

- **Destructive Action Detection**: Delete, send, and payment actions require confirmation
- **Password Blocking**: Password/MFA fields are never automated
- **Manual Login Support**: Login pages prompt for manual authentication
- **CAPTCHA Detection**: Detected CAPTCHAs pause for user completion

### Action Categories

| Category | Behavior |
|----------|----------|
| Safe | Executed immediately (navigation, scroll, read) |
| Delete | Requires confirmation (remove, clear, destroy) |
| Send | Requires confirmation (submit, send, publish) |
| Payment | Requires confirmation (pay, checkout, purchase) |
| Password | **Blocked** (password, MFA, OTP fields) |

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=src/browser_agent --cov-report=html
```

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines before submitting PRs.
