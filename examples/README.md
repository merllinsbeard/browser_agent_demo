# Browser Agent Examples

Example scripts demonstrating browser automation capabilities.

## Prerequisites

1. Set your Anthropic API key:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

2. Install the browser agent:
   ```bash
   pip install -e .
   # or
   uv pip install -e .
   ```

## Examples

### Simple Navigation

Basic browser automation: navigate and interact with elements.

```bash
python examples/simple_navigation.py
```

### Multi-Step Task

Complex automation with task decomposition and planning.

```bash
python examples/multi_step_task.py
```

### Interactive Session

Multi-turn conversation with context preservation.

```bash
python examples/interactive_session.py
```

## Using the CLI

For full-featured automation, use the CLI:

```bash
# Single task
python -m browser_agent.main "Navigate to example.com and click the first link"

# Interactive mode (no task argument)
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

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key (required) | - |
| `LOG_LEVEL` | Logging level: DEBUG, INFO, WARNING, ERROR | INFO |
| `PLANNER_MODEL` | Model for planning: sonnet, haiku, opus | sonnet |
