"""
Agent Orchestration Module

Implements the 4-agent hierarchy for browser automation:
- Planner: High-level task decomposition (sonnet tier)
- DOM Analyzer: Page structure analysis (haiku tier)
- Executor: Browser interaction (sonnet tier)
- Validator: Action verification (haiku tier)

Uses Claude Agent SDK with AgentDefinition pattern (FR-025, FR-026).
Implements ReAct loop pattern for reasoning-action cycles.
"""

from .orchestrator import AgentOrchestrator, create_orchestrator
from .definitions import (
    PLANNER_AGENT,
    DOM_ANALYZER_AGENT,
    EXECUTOR_AGENT,
    VALIDATOR_AGENT,
)
from .planner import (
    ReActPlanner,
    PlannerState,
    PlannerConfig,
    create_planner,
)
from .dom_analyzer import (
    DOMAnalyzer,
    PageAnalysis,
    create_dom_analyzer,
)
from .executor import (
    BrowserExecutor,
    ExecutionResult,
    ExecutionContext,
    create_executor,
)
from .validator import (
    ActionValidator,
    ValidationResult,
    ValidationStatus,
    PageState,
    create_validator,
)
from .reporter import (
    ReportGenerator,
    TaskReport,
    create_reporter,
)

__all__ = [
    # Orchestrator
    "AgentOrchestrator",
    "create_orchestrator",
    # Agent definitions
    "PLANNER_AGENT",
    "DOM_ANALYZER_AGENT",
    "EXECUTOR_AGENT",
    "VALIDATOR_AGENT",
    # ReAct Planner (T025)
    "ReActPlanner",
    "PlannerState",
    "PlannerConfig",
    "create_planner",
    # DOM Analyzer (T026)
    "DOMAnalyzer",
    "PageAnalysis",
    "create_dom_analyzer",
    # Executor (T027)
    "BrowserExecutor",
    "ExecutionResult",
    "ExecutionContext",
    "create_executor",
    # Validator (T032, T034)
    "ActionValidator",
    "ValidationResult",
    "ValidationStatus",
    "PageState",
    "create_validator",
    # Reporter (T035)
    "ReportGenerator",
    "TaskReport",
    "create_reporter",
]
