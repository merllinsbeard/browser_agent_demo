# Phase 0 Research: Claude Agent SDK Integration

**Date**: 2026-01-24
**Feature**: 003-claude-sdk-integration
**Source**: Official Claude Agent SDK documentation (Python)

## Research Questions & Findings

### 1. AgentDefinition Structure and Model Tiering

**Question**: How do I define agents with model tiers (Sonnet vs Haiku) in Claude Agent SDK?

**Decision**: Use `AgentDefinition` dataclass with `model` parameter.

```python
from claude_agent_sdk import AgentDefinition

# Structure:
@dataclass
class AgentDefinition:
    description: str      # Natural language description of when to use this agent
    prompt: str           # The agent's system prompt
    tools: list[str] | None = None  # Allowed tools (inherits all if omitted)
    model: Literal["sonnet", "opus", "haiku", "inherit"] | None = None
```

**Implementation for 4-agent hierarchy**:

```python
agents = {
    "planner": AgentDefinition(
        description="Decomposes complex tasks into sub-tasks",
        prompt="You are a task planning agent. Break down user requests into atomic steps...",
        model="sonnet"  # Complex reasoning
    ),
    "dom_analyzer": AgentDefinition(
        description="Analyzes page structure and extracts interactive elements",
        prompt="You are a DOM analysis agent. Extract accessibility tree...",
        model="haiku",  # Volume operations
        tools=["get_accessibility_tree", "find_interactive_elements"]
    ),
    "executor": AgentDefinition(
        description="Executes browser actions",
        prompt="You are a browser action executor. Perform clicks, typing...",
        model="sonnet",  # Complex decision-making
        tools=["click", "type_text", "navigate", "scroll", "wait_for_load"]
    ),
    "validator": AgentDefinition(
        description="Validates task completion",
        prompt="You are a result validator. Verify that outcomes match expectations...",
        model="haiku",  # Lightweight checks
        tools=["get_accessibility_tree", "get_page_text"]
    )
}
```

**Rationale**: The SDK's `AgentDefinition` directly supports model tiering via the `model` field, aligning with Constitution Principle V (Model Tiering).

**Alternatives considered**:
- Setting `model` at global level (rejected - no per-agent control)
- Using `model` and `fallback_model` in `ClaudeAgentOptions` (rejected - applies to all agents uniformly)

---

### 2. Tool Registration with @tool Decorator

**Question**: How do I register existing @tool decorated functions with the SDK?

**Decision**: Use `create_sdk_mcp_server()` to create an in-process MCP server.

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

# Option 1: Register existing tool functions
# Need to wrap existing tools to return SDK-compatible format
@tool("click", "Click an element", {"element_description": str, "frame": str})
async def click_adapter(args: dict[str, Any]) -> dict[str, Any]:
    from browser_agent.tools.interactions import click
    result = await click(page, args["element_description"], frame=args.get("frame"))
    return {
        "content": [{"type": "text", "text": str(result)}],
        "is_error": not result.success
    }

# Option 2: Create server from all tools
browser_server = create_sdk_mcp_server(
    name="browser",
    version="1.0.0",
    tools=[click_adapter, type_text_adapter, ...]  # All 23 tools
)
```

**Integration Pattern for Existing Tools**:

Since existing tools use a custom `@tool` decorator in `src/browser_agent/tools/base.py`, we need an adapter layer:

```python
# src/browser_agent/sdk_adapter.py
from claude_agent_sdk import tool, create_sdk_mcp_server
from browser_agent.tools.base import get_all_tools

def adapt_tool_for_sdk(tool_name: str, tool_func: Callable) -> SdkMcpTool:
    """Adapt existing @tool decorated function to SDK format."""
    # Extract schema from existing tool registry
    tools = get_all_tools()
    metadata = tools[tool_name]

    @tool(tool_name, metadata["description"], metadata["parameters"])
    async def adapter(args: dict[str, Any]) -> dict[str, Any]:
        # Call existing tool function
        result = await tool_func(page, **args)
        return {
            "content": [{"type": "text", "text": str(result.data) if result.success else result.error}],
            "is_error": not result.success
        }

    return adapter

# Create server with all adapted tools
def create_browser_server(page: Page) -> McpSdkServerConfig:
    adapted_tools = []
    for tool_name, tool_info in get_all_tools().items():
        adapted = adapt_tool_for_sdk(tool_name, tool_info["function"])
        adapted_tools.append(adapted)

    return create_sdk_mcp_server(
        name="browser",
        version="1.0.0",
        tools=adapted_tools
    )
```

**Rationale**: The adapter pattern preserves existing tool implementations while satisfying SDK's input/output format requirements.

**Alternatives considered**:
- Rewriting all 23 tools with SDK @tool decorator (rejected - ~2000 lines of changes, breaks existing tests)
- Using MCP stdio servers (rejected - adds process overhead, more complex setup)

---

### 3. SDK ReAct Loop Management

**Question**: How does SDK handle the ReAct loop vs custom implementation?

**Decision**: Use SDK's `query()` for one-off tasks or `ClaudeSDKClient` for continuous sessions.

**Comparison**:

| Approach | Use Case | Session Management | Complexity |
|----------|----------|-------------------|------------|
| `query()` | One-off automation tasks | New session each call | Low |
| `ClaudeSDKClient` | Interactive, multi-turn conversations | Persistent session | Medium |

**For this project**: Use `ClaudeSDKClient` for session continuity (the Planner may call subagents multiple times).

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async def run_browser_agent(task: str):
    options = ClaudeAgentOptions(
        agents={  # 4-agent hierarchy
            "planner": AgentDefinition(model="sonnet", ...),
            "dom_analyzer": AgentDefinition(model="haiku", ...),
            "executor": AgentDefinition(model="sonnet", ...),
            "validator": AgentDefinition(model="haiku", ...)
        },
        mcp_servers={"browser": browser_server},  # Our 23 tools
        allowed_tools=["Task", "mcp__browser__click", "mcp__browser__type_text", ...]
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(task)

        async for message in client.receive_messages():
            # SDK handles ReAct loop internally
            # We just consume messages
            yield message
```

**Rationale**: The SDK manages the ReAct loop automatically, eliminating the need for custom loop logic (~150 lines removed).

**Key differences from custom ReActPlanner**:

| Custom ReActPlanner | SDK Managed Loop |
|-------------------|------------------|
| Manual state machine (PlannerState) | Automatic session tracking |
| Manual tool execution with retry | Built-in error handling |
| Manual context windowing | Automatic compaction |
| Manual LLM API calls | Handled by SDK |

**Migration impact**:
- Remove: `ReActPlanner` class (~150 lines)
- Remove: Custom loop logic (~100 lines)
- Add: SDK client initialization (~20 lines)

---

### 4. Tool Calling Format

**Question**: What format does Claude Agent SDK expect for tool calls?

**Decision**: SDK expects MCP tool format with specific response structure.

**Tool Input Format**:

```python
{
    "name": str,           # Tool name (e.g., "mcp__browser__click")
    "input": dict[str, Any]  # Parameters from tool schema
}
```

**Tool Output Format**:

```python
{
    "content": list[dict],  # Content blocks
    "is_error": bool | None
}
```

**Content Block Types**:

```python
# Text content
{"type": "text", "text": "Operation succeeded"}

# Error content
{"type": "text", "text": "Element not found"}

# Rich content (for complex responses)
{
    "type": "resource",
    "resource": {
        "uri": "file:///path/to/screenshot.png",
        "mimeType": "image/png"
    }
}
```

**Adapter Implementation**:

```python
def tool_result_to_sdk_format(result: ToolResult) -> dict[str, Any]:
    """Convert existing ToolResult to SDK format."""
    if result.success:
        return {
            "content": [{"type": "text", "text": str(result.data)}],
            "is_error": False
        }
    else:
        return {
            "content": [{"type": "text", "text": result.error or "Unknown error"}],
            "is_error": True
        }
```

**Rationale**: The adapter pattern enables existing tools to work with SDK without modification.

---

### 5. Multi-Agent Orchestration

**Question**: How do I orchestrate 4 agents (Planner → DOM Analyzer/Executor/Validator) in SDK?

**Decision**: Use the Task tool with subagent delegation pattern.

**Orchestration Flow**:

```
User Task → Planner (Sonnet) → [Task tool calls]
                              ↓
                    +---- DOM Analyzer (Haiku)
                    +---- Executor (Sonnet) → [uses browser tools]
                    +---- Validator (Haiku)
```

**Implementation**:

```python
# In the Planner agent's system prompt
PLANNER_PROMPT = """
You are a task planning agent. When given a user request:
1. Break it down into sub-tasks
2. Use the Task tool to delegate to specialist agents:
   - dom_analyzer: For page structure analysis
   - executor: For browser actions
   - validator: For result verification
3. Combine results and report back

Example:
User: "Search for Python books and add first result to cart"
Your response: Use Task tool with subagent_type="executor" to navigate, search, and add to cart.
"""

# Define agents with Task tool access
agents = {
    "planner": AgentDefinition(
        description="Main planning agent",
        prompt=PLANNER_PROMPT,
        model="sonnet",
        tools=["Task"]  # Required for subagent delegation
    ),
    "dom_analyzer": AgentDefinition(
        description="Page structure analyzer",
        prompt="Extract accessibility tree and find interactive elements...",
        model="haiku",
        tools=["mcp__browser__get_accessibility_tree", "mcp__browser__find_interactive_elements"]
    ),
    # ... other agents
}
```

**Task Tool Input Format**:

```python
{
    "description": str,      # Short (3-5 word) description
    "prompt": str,           # The task for the subagent
    "subagent_type": str     # Must match key in `agents` dict
}
```

**Rationale**: The SDK's Task tool provides built-in subagent orchestration with proper context isolation and result aggregation.

**Message Tracking**: Messages from subagents include `parent_tool_use_id` field for tracking which subagent execution produced them.

---

## Summary of Decisions

| Area | Decision | Lines of Code Impact |
|------|----------|---------------------|
| Model Tiering | Use `AgentDefinition.model` field | +20 (agent definitions) |
| Tool Registration | Create adapter layer for existing @tool tools | +100 (adapter) |
| ReAct Loop | Use SDK's `ClaudeSDKClient` (remove custom loop) | -150 (ReActPlanner) |
| Tool Format | Adapter converts `ToolResult` → SDK response | +50 (converter) |
| Orchestration | Use Task tool for agent delegation | +30 (prompts) |

**Net Change**: -250 lines (removal of ReActPlanner) + ~200 lines (adapters/orchestration) = **~50 lines net new code**

**Key Integration Points**:

1. **Adapter Layer** (`src/browser_agent/sdk_adapter.py`):
   - `adapt_tool_for_sdk()` - Wraps existing tools
   - `create_browser_server()` - Creates MCP server
   - `tool_result_to_sdk_format()` - Converts responses

2. **Agent Definitions** (`src/browser_agent/agents/definitions.py`):
   - Update existing `PLANNER_AGENT`, `DOM_ANALYZER_AGENT`, etc. with `model` field
   - Add Task tool to planner's allowed_tools

3. **Orchestrator** (`src/browser_agent/agents/orchestrator.py`):
   - Replace empty implementation with `ClaudeSDKClient` wrapper
   - Wire up browser server and agent definitions

4. **Main Entry Point** (`src/browser_agent/main.py`):
   - Create `ClaudeAgentOptions` with agents and MCP servers
   - Implement CLI argument parsing
   - Run queries and display results

---

## Open Questions Resolved

| Question | Answer |
|----------|--------|
| How to specify Sonnet vs Haiku? | `AgentDefinition(model="sonnet" | "haiku")` |
| How to register existing tools? | Adapter layer with `create_sdk_mcp_server()` |
| Does SDK handle ReAct loop? | Yes, via `query()` or `ClaudeSDKClient` |
| Tool response format? | `{"content": [...], "is_error": bool}` |
| Subagent orchestration? | Use Task tool with agent definitions |

---

## Next Steps (Phase 1)

1. Create `data-model.md` with agent definitions and tool schemas
2. Generate `contracts/tools.json` and `contracts/agent-definitions.json`
3. Create `quickstart.md` for developer onboarding
4. Update agent-specific context files

**Status**: ✅ All research questions resolved. Ready for Phase 1 design.
