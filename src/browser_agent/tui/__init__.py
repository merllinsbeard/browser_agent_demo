"""
Rich TUI Interface Module

Provides terminal user interface components for the browser automation agent.
Uses the Rich library for formatted, colorful output.

Components:
- AgentConsole: Main console wrapper with themed output
- TUIConfig: Configuration for colors and display options
- Block display functions for THOUGHT/ACTION/RESULT output
- Thought module: Enhanced formatting for agent reasoning (FR-003)
"""

from browser_agent.tui.console import (
    AgentConsole,
    BlockType,
    TUIConfig,
    create_console,
    get_console,
)
from browser_agent.tui.thought import (
    format_thought_content,
    print_analysis,
    print_reasoning_chain,
    print_thought,
)
from browser_agent.tui.action import (
    format_action_params,
    print_action,
    print_interaction,
    print_navigation,
    print_tool_call,
)
from browser_agent.tui.result import (
    print_code_result,
    print_completion,
    print_data_result,
    print_error,
    print_extracted_text,
    print_page_info,
    print_result,
)
from browser_agent.tui.progress import (
    ActionProgress,
    StepTracker,
    action_spinner,
    create_task_progress,
    progress_indicator,
    step_progress,
)

__all__ = [
    # Console infrastructure
    "AgentConsole",
    "BlockType",
    "TUIConfig",
    "create_console",
    "get_console",
    # Thought block functions (FR-003)
    "format_thought_content",
    "print_analysis",
    "print_reasoning_chain",
    "print_thought",
    # Action block functions (FR-004)
    "format_action_params",
    "print_action",
    "print_interaction",
    "print_navigation",
    "print_tool_call",
    # Result block functions (FR-005)
    "print_code_result",
    "print_completion",
    "print_data_result",
    "print_error",
    "print_extracted_text",
    "print_page_info",
    "print_result",
    # Progress indicators (T020)
    "ActionProgress",
    "StepTracker",
    "action_spinner",
    "create_task_progress",
    "progress_indicator",
    "step_progress",
]
