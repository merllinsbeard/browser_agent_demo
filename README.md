# Browser Automation Agent

An intelligent browser automation agent powered by Claude AI. Uses a 4-agent hierarchy with ReAct loop pattern to execute complex browser tasks from natural language instructions.

## Features

- **Natural Language Tasks**: Describe what you want to do, the agent figures out how
- **Visible Browser**: Watch the agent interact with web pages in real-time
- **Multi-Step Task Handling**: Complex tasks are decomposed and executed step-by-step
- **Security Safeguards**: Destructive actions require user confirmation
- **Session Persistence**: Login once, stay logged in across sessions
- **Rich TUI Output**: Color-coded thought/action/result display

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Anthropic API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/browser-automation-agent.git
cd browser-automation-agent
```

2. Install dependencies:
```bash
uv sync
```

3. Install Playwright browsers:
```bash
uv run playwright install chromium
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Create a `.env` file with the following variables:

```bash
# Required
ANTHROPIC_API_KEY=your-key-here

# Optional - Model Configuration
LLM_MODEL_TIER_PLANNER=sonnet        # Model for planner (sonnet/haiku)
LLM_MODEL_TIER_EXECUTOR=sonnet       # Model for executor
LLM_MODEL_TIER_ANALYZER=haiku        # Model for DOM analyzer
LLM_MODEL_TIER_VALIDATOR=haiku       # Model for validator

# Optional - Browser Configuration
BROWSER_TYPE=chromium                 # chromium/firefox/webkit
BROWSER_HEADLESS=false               # true for headless mode
BROWSER_VIEWPORT_WIDTH=1280
BROWSER_VIEWPORT_HEIGHT=720

# Optional - Session Configuration
SESSION_PERSIST=true                  # Persist browser sessions
SESSIONS_DIR=.browser-sessions       # Session storage directory
```

See `.env.example` for all available options.

## Usage

### Basic Example

```python
import asyncio
from browser_agent.browser import create_browser
from browser_agent.agents import create_planner

async def main():
    async with create_browser() as browser:
        page = browser.current_page

        # Navigate to a page
        await page.goto("https://example.com")

        # Use the planner for complex tasks
        # planner = create_planner(llm_complete=your_llm_function)
        # result = await planner.execute(task="Find and click the More Information link")

asyncio.run(main())
```

### Running Tests

```bash
uv run pytest tests/ -v
```

## Architecture

The agent uses a 4-tier hierarchy:

1. **Planner** (sonnet): High-level task decomposition and ReAct loop
2. **DOM Analyzer** (haiku): Fast page structure analysis
3. **Executor** (sonnet): Precise browser action execution
4. **Validator** (haiku): Action verification and CAPTCHA detection

### Key Modules

- `browser_agent/browser/` - Playwright browser management
- `browser_agent/agents/` - AI agent implementations
- `browser_agent/tools/` - Browser automation tools
- `browser_agent/tui/` - Rich terminal UI components
- `browser_agent/security/` - Destructive action detection

## Security

The agent includes safety features:

- **Destructive Action Detection**: Delete, send, and payment actions require confirmation
- **Password Blocking**: Password/MFA fields are never automated
- **Manual Login Support**: Login pages prompt for manual authentication
- **CAPTCHA Detection**: Detected CAPTCHAs pause for user completion

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines before submitting PRs.
