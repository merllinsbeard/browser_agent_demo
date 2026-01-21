"""
Agent Orchestration Module

Implements the 4-agent hierarchy for browser automation:
- Planner: High-level task decomposition (sonnet tier)
- DOM Analyzer: Page structure analysis (haiku tier)
- Executor: Browser interaction (sonnet tier)
- Validator: Action verification (haiku tier)

Uses Claude Agent SDK with AgentDefinition pattern (FR-025, FR-026).
"""

from .orchestrator import AgentOrchestrator, create_orchestrator
from .definitions import (
    PLANNER_AGENT,
    DOM_ANALYZER_AGENT,
    EXECUTOR_AGENT,
    VALIDATOR_AGENT,
)

__all__ = [
    "AgentOrchestrator",
    "create_orchestrator",
    "PLANNER_AGENT",
    "DOM_ANALYZER_AGENT",
    "EXECUTOR_AGENT",
    "VALIDATOR_AGENT",
]
