"""
Agent Definitions for Browser Automation Hierarchy

Defines the 4-agent architecture using Claude Agent SDK's AgentDefinition pattern.
Each agent has a specific role, model tier, and tool access pattern.

Following FR-026: Sub-agents defined through AgentDefinition with model tiers.
"""

from typing import Dict, Any

# Model tier constants from spec
MODEL_SONNET = "claude-sonnet-4-20250514"  # High-quality reasoning
MODEL_HAIKU = "claude-haiku-4-20250514"  # Fast, lightweight


def _create_agent_definition(
    name: str,
    description: str,
    system_prompt: str,
    model: str,
    tools: list[str] | None = None,
) -> Dict[str, Any]:
    """
    Create an AgentDefinition for Claude Agent SDK.

    Args:
        name: Agent identifier
        description: What this agent does
        system_prompt: Agent's behavior instructions
        model: Model tier to use (sonnet/haiku)
        tools: Tools this agent can use

    Returns:
        AgentDefinition dictionary
    """
    definition: Dict[str, Any] = {
        "description": description,
        "prompt": system_prompt,
        "model": model,
    }

    if tools is not None:
        definition["tools"] = tools

    return definition


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
3. Identify potential risks and edge cases
4. Determine when to request user confirmation (for destructive actions)
5. Adapt plans based on execution feedback

You have access to:
- Current page state (URL, accessibility tree)
- Previous actions and results
- Browser interaction tools

Your output should be a clear, executable plan with specific steps.

Key principles:
- Start simple: navigate, observe, then act
- Always verify page state before acting
- Request confirmation for deletion, sending, or financial actions
- Learn from failures and adapt
- Keep humans informed of progress""",
    model=MODEL_SONNET,
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
4. Suggest element descriptions for natural language interaction
5. Detect dynamic content changes

You work with:
- Accessibility tree JSON
- Element metadata (role, name, state)
- Page structure patterns

Your output should be:
- Concise element descriptions
- Actionable element locations
- Relationship information (parent/child, order)
- State information (visible, enabled, focused)

Key principles:
- Be fast and efficient
- Focus on interactive elements
- Preserve element hierarchy
- Note dynamic or loading content""",
    model=MODEL_HAIKU,
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
3. Manage page navigation
4. Wait for page loads and state changes
5. Handle unexpected popups or modals

You have access to:
- Browser control tools (click, type, navigate, scroll)
- Page state information
- Element location strategies

Your actions should be:
- Precise and targeted
- Patient (wait for loads)
- Safe (avoid accidental actions)
- Observable (report each action)

Key principles:
- Always verify element before interaction
- Wait for page stability after actions
- Handle transient elements gracefully
- Report all actions clearly
- Stop on errors and request guidance""",
    model=MODEL_SONNET,
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
5. Check for destructive action risks

You analyze:
- Page state after actions
- Screenshots or accessibility tree changes
- Error messages or warnings
- Element state changes

Your output should indicate:
- Success/failure of actions
- Reason for failure (if applicable)
- Suggested recovery actions
- Whether task is complete

Key principles:
- Be quick and accurate
- Clear pass/fail indication
- Actionable error messages
- Detect destructive action risks early""",
    model=MODEL_HAIKU,
)


# ============================================================================
# AGENT REGISTRY
# ============================================================================

AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "planner": PLANNER_AGENT,
    "dom_analyzer": DOM_ANALYZER_AGENT,
    "executor": EXECUTOR_AGENT,
    "validator": VALIDATOR_AGENT,
}


def get_agent_definition(agent_name: str) -> Dict[str, Any]:
    """
    Get an agent definition by name.

    Args:
        agent_name: One of "planner", "dom_analyzer", "executor", "validator"

    Returns:
        AgentDefinition dictionary

    Raises:
        ValueError: If agent_name is not recognized
    """
    if agent_name not in AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent: {agent_name}. "
            f"Available agents: {list(AGENT_REGISTRY.keys())}"
        )
    return AGENT_REGISTRY[agent_name]


def get_all_agent_definitions() -> Dict[str, Dict[str, Any]]:
    """
    Get all agent definitions for Claude Agent SDK configuration.

    Returns:
        Dictionary mapping agent names to AgentDefinition dicts
    """
    return AGENT_REGISTRY.copy()
