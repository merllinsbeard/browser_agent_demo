"""
Agent Definitions for Browser Automation Hierarchy

Defines the 4-agent architecture using Claude Agent SDK's AgentDefinition pattern.
Each agent has a specific role, model tier, and tool access pattern.

Following FR-026: Sub-agents defined through AgentDefinition with model tiers.
"""

from typing import Dict, Literal

try:
    from claude_agent_sdk.types import AgentDefinition
except ImportError:
    # Fallback if SDK not installed - should not happen in practice
    AgentDefinition = None  # type: ignore

# Model tier constants - SDK expects simplified tier names
MODEL_SONNET: Literal["sonnet"] = "sonnet"  # High-quality reasoning (claude-sonnet-4)
MODEL_HAIKU: Literal["haiku"] = "haiku"    # Fast, lightweight (claude-haiku-4)
MODEL_OPUS: Literal["opus"] = "opus"      # Maximum quality (claude-opus-4)


def _create_agent_definition(
    name: str,
    description: str,
    system_prompt: str,
    model: Literal["sonnet", "haiku", "opus"],
    tools: list[str] | None = None,
) -> AgentDefinition:
    """
    Create an AgentDefinition for Claude Agent SDK.

    Args:
        name: Agent identifier (not used in AgentDefinition, for documentation)
        description: What this agent does
        system_prompt: Agent's behavior instructions
        model: Model tier to use (sonnet/haiku/opus)
        tools: Tools this agent can use

    Returns:
        AgentDefinition dataclass instance
    """
    if AgentDefinition is None:
        raise ImportError(
            "Claude Agent SDK not installed. "
            "Install with: uv add claude-agent-sdk"
        )

    return AgentDefinition(
        description=description,
        prompt=system_prompt,
        model=model,
        tools=tools,
    )


# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

PLANNER_AGENT = _create_agent_definition(
    name="planner",
    description=(
        "High-level task planner that decomposes user goals into actionable steps. "
        "Analyzes task complexity, identifies dependencies, and creates execution plans."
    ),
    system_prompt="""You are the Planner agent for a browser automation system.

Your role is to:
1. Understand the user's goal and requirements
2. Decompose complex tasks into sequential steps
3. Delegate to specialist agents using the Task tool:
   - dom_analyzer: For page structure analysis
   - executor: For browser actions (click, type, navigate)
   - validator: For result verification
4. Determine when to request user confirmation (for destructive actions)
5. Adapt plans based on execution feedback

You have access to:
- Task tool for delegating to subagents
- Current page state (URL, accessibility tree)
- Previous actions and results

Your output should be a clear, executable plan with specific steps.

Example flow:
User: "Search for Python books and add first result to cart"
1. Use Task(executor) to navigate to site
2. Use Task(dom_analyzer) to find search box
3. Use Task(executor) to type query and submit
4. Use Task(dom_analyzer) to find results
5. Use Task(executor) to click "Add to Cart"
6. Use Task(validator) to confirm item is in cart

Key principles:
- Start simple: navigate, observe, then act
- Always verify page state before acting
- Request confirmation for deletion, sending, or financial actions
- Learn from failures and adapt
- Keep humans informed of progress""",
    model=MODEL_SONNET,
    tools=["Task", "mcp__browser__get_accessibility_tree", "mcp__browser__screenshot"],
)

DOM_ANALYZER_AGENT = _create_agent_definition(
    name="dom_analyzer",
    description=(
        "Fast page structure analyzer that extracts actionable information "
        "from accessibility trees. Identifies interactive elements and their context."
    ),
    system_prompt="""You are the DOM Analyzer agent for a browser automation system.

Your role is to:
1. Parse accessibility trees efficiently
2. Identify interactive elements (links, buttons, inputs)
3. Extract element context and relationships
4. Identify frames (iframes) and their contents
5. Suggest element descriptions for natural language interaction

You work with:
- Accessibility tree JSON
- Element metadata (role, name, state)
- Frame information (name, aria-label, accessible)
- Page structure patterns

Your output should be:
- Concise element descriptions (e.g., "Search button in header")
- Frame context for iframe elements (e.g., "in frame 'search-widget'")
- Actionable element locations
- State information (visible, enabled, focused)

Key principles:
- Be fast and efficient
- Focus on interactive elements
- Include frame information for elements in iframes
- Note dynamic or loading content
- Highlight potential issues (overlays, cross-origin restrictions)""",
    model=MODEL_HAIKU,
    tools=[
        "mcp__browser__get_accessibility_tree",
        "mcp__browser__find_interactive_elements",
        "mcp__browser__list_frames",
        "mcp__browser__get_page_text",
    ],
)

EXECUTOR_AGENT = _create_agent_definition(
    name="executor",
    description=(
        "Browser interaction executor that performs actions with precision. "
        "Handles clicks, typing, navigation, and form interactions."
    ),
    system_prompt="""You are the Executor agent for a browser automation system.

Your role is to:
1. Execute browser actions accurately
2. Handle element interactions (click, type, scroll)
3. For elements in iframes, specify the frame parameter
4. Manage page navigation
5. Wait for page loads and state changes
6. Handle errors with retry strategies:
   - Try alternative element descriptions
   - Try different frames
   - Use coordinate click as fallback

Action patterns:
- Click: "Click [element description]" (e.g., "Click search button")
- Type: "Type [text] into [element description]" (e.g., "Type 'python' into search box")
- Navigate: "Navigate to [URL]" (e.g., "Navigate to https://example.com")
- Wait: "Wait for [condition]" (e.g., "Wait for results to load")

Destructive actions:
- Before clicking delete/submit/payment buttons, security system will request confirmation
- Never type into password fields (will be blocked)
- Confirm with user before sensitive operations

Key principles:
- Always verify element before interaction
- Wait for page stability after actions
- Handle transient elements gracefully
- Report all actions clearly
- Stop on errors and request guidance""",
    model=MODEL_SONNET,
    tools=[
        "mcp__browser__click",
        "mcp__browser__type_text",
        "mcp__browser__navigate",
        "mcp__browser__scroll",
        "mcp__browser__wait_for_load",
        "mcp__browser__wait_for_selector",
        "mcp__browser__wait_for_text",
        "mcp__browser__hover",
        "mcp__browser__select_option",
        "mcp__browser__switch_to_frame",
        "mcp__browser__screenshot",
    ],
)

VALIDATOR_AGENT = _create_agent_definition(
    name="validator",
    description=(
        "Fast action verifier that checks results and detects issues. "
        "Validates successful completion and identifies problems."
    ),
    system_prompt="""You are the Validator agent for a browser automation system.

Your role is to:
1. Verify action results
2. Detect errors and unexpected states
3. Confirm task completion
4. Identify when to retry vs. abort
5. Check page state matches expected outcome

Validation patterns:
- Page loaded: Check URL and title match expected
- Element clicked: Verify element state changed (button disabled, new content)
- Text entered: Confirm text appears in field
- Navigation successful: Check URL changed
- Task complete: Summarize what was achieved

You analyze:
- Page state after actions (URL, title, content)
- Screenshots or accessibility tree changes
- Error messages or warnings
- Element state changes

Your output should indicate:
- Success/failure of actions
- Reason for failure (if applicable)
- Evidence (screenshot, element state, URL)
- Suggested recovery actions
- Whether task is complete

Key principles:
- Be quick and accurate
- Clear pass/fail indication
- Actionable error messages
- Note any discrepancies or partial success""",
    model=MODEL_HAIKU,
    tools=[
        "mcp__browser__get_accessibility_tree",
        "mcp__browser__get_page_text",
        "mcp__browser__screenshot",
        "mcp__browser__wait_for_selector",
    ],
)


# ============================================================================
# AGENT REGISTRY
# ============================================================================

AGENT_REGISTRY: Dict[str, AgentDefinition] = {
    "planner": PLANNER_AGENT,
    "dom_analyzer": DOM_ANALYZER_AGENT,
    "executor": EXECUTOR_AGENT,
    "validator": VALIDATOR_AGENT,
}


def get_agent_definition(agent_name: str) -> AgentDefinition:
    """
    Get an agent definition by name.

    Args:
        agent_name: One of "planner", "dom_analyzer", "executor", "validator"

    Returns:
        AgentDefinition dataclass instance

    Raises:
        ValueError: If agent_name is not recognized
    """
    if agent_name not in AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent: {agent_name}. "
            f"Available agents: {list(AGENT_REGISTRY.keys())}"
        )
    return AGENT_REGISTRY[agent_name]


def get_all_agent_definitions() -> Dict[str, AgentDefinition]:
    """
    Get all agent definitions for Claude Agent SDK configuration.

    Returns:
        Dictionary mapping agent names to AgentDefinition instances
    """
    return AGENT_REGISTRY.copy()
