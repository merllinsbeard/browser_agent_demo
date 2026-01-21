"""
Task Decomposition Module

Breaks down complex multi-step tasks into manageable subtasks.
Supports dependency tracking and progress monitoring.

Following User Story 2 - Complex multi-step task handling.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable, Awaitable

from ..tui import print_thought, get_console


class SubtaskStatus(Enum):
    """Status of a subtask."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Subtask:
    """
    A single subtask within a decomposed task.
    """

    id: int
    description: str
    status: SubtaskStatus = SubtaskStatus.PENDING
    dependencies: list[int] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        """Check if subtask is ready to execute (dependencies met)."""
        return self.status == SubtaskStatus.PENDING

    def mark_in_progress(self) -> None:
        """Mark subtask as in progress."""
        self.status = SubtaskStatus.IN_PROGRESS

    def mark_completed(self, result: Any = None) -> None:
        """Mark subtask as completed."""
        self.status = SubtaskStatus.COMPLETED
        self.result = result

    def mark_failed(self, error: str) -> None:
        """Mark subtask as failed."""
        self.status = SubtaskStatus.FAILED
        self.error = error


@dataclass
class TaskPlan:
    """
    A decomposed task plan with subtasks and dependencies.
    """

    original_task: str
    subtasks: list[Subtask] = field(default_factory=list)
    current_subtask_id: int = 0

    @property
    def is_complete(self) -> bool:
        """Check if all subtasks are complete."""
        return all(
            s.status in (SubtaskStatus.COMPLETED, SubtaskStatus.SKIPPED)
            for s in self.subtasks
        )

    @property
    def progress(self) -> float:
        """Get completion progress as a percentage."""
        if not self.subtasks:
            return 0.0
        completed = sum(
            1 for s in self.subtasks
            if s.status in (SubtaskStatus.COMPLETED, SubtaskStatus.SKIPPED)
        )
        return (completed / len(self.subtasks)) * 100

    @property
    def current_subtask(self) -> Optional[Subtask]:
        """Get the current subtask being executed."""
        for subtask in self.subtasks:
            if subtask.id == self.current_subtask_id:
                return subtask
        return None

    def get_next_subtask(self) -> Optional[Subtask]:
        """Get the next subtask to execute."""
        for subtask in self.subtasks:
            if subtask.status == SubtaskStatus.PENDING:
                # Check dependencies
                deps_met = all(
                    self._get_subtask(dep_id).status == SubtaskStatus.COMPLETED
                    for dep_id in subtask.dependencies
                )
                if deps_met:
                    return subtask
        return None

    def _get_subtask(self, subtask_id: int) -> Subtask:
        """Get subtask by ID."""
        for subtask in self.subtasks:
            if subtask.id == subtask_id:
                return subtask
        raise ValueError(f"Subtask {subtask_id} not found")

    def add_subtask(
        self,
        description: str,
        dependencies: Optional[list[int]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Subtask:
        """Add a subtask to the plan."""
        subtask_id = len(self.subtasks)
        subtask = Subtask(
            id=subtask_id,
            description=description,
            dependencies=dependencies or [],
            metadata=metadata or {},
        )
        self.subtasks.append(subtask)
        return subtask

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the task plan."""
        return {
            "original_task": self.original_task,
            "total_subtasks": len(self.subtasks),
            "completed": sum(
                1 for s in self.subtasks if s.status == SubtaskStatus.COMPLETED
            ),
            "failed": sum(
                1 for s in self.subtasks if s.status == SubtaskStatus.FAILED
            ),
            "pending": sum(
                1 for s in self.subtasks if s.status == SubtaskStatus.PENDING
            ),
            "progress": f"{self.progress:.0f}%",
        }


class TaskDecomposer:
    """
    Decomposes complex tasks into subtasks using LLM.

    Uses the planner's LLM to analyze tasks and create
    structured execution plans with dependencies.
    """

    def __init__(
        self,
        llm_complete: Optional[Callable[[str, list], Awaitable[dict]]] = None,
        verbose: bool = True,
    ):
        """
        Initialize task decomposer.

        Args:
            llm_complete: Async LLM completion function
            verbose: Whether to print progress
        """
        self.llm_complete = llm_complete
        self.verbose = verbose
        self.console = get_console()

    async def decompose(
        self,
        task: str,
        context: Optional[dict[str, Any]] = None,
    ) -> TaskPlan:
        """
        Decompose a task into subtasks.

        Args:
            task: The main task to decompose
            context: Optional context about current page/state

        Returns:
            TaskPlan with subtasks
        """
        plan = TaskPlan(original_task=task)

        if self.llm_complete:
            # Use LLM for intelligent decomposition
            subtasks = await self._llm_decompose(task, context)
        else:
            # Use rule-based decomposition
            subtasks = self._rule_based_decompose(task)

        for i, description in enumerate(subtasks):
            # Add dependencies: each subtask depends on previous
            deps = [i - 1] if i > 0 else []
            plan.add_subtask(description, dependencies=deps)

        if self.verbose and plan.subtasks:
            self._print_plan(plan)

        return plan

    async def _llm_decompose(
        self,
        task: str,
        context: Optional[dict[str, Any]],
    ) -> list[str]:
        """Use LLM to decompose task."""
        system_prompt = """You are a task decomposition expert for browser automation.
Break down the user's task into clear, sequential subtasks.
Each subtask should be a single, actionable step.

Format your response as a numbered list:
1. First subtask
2. Second subtask
3. Third subtask

Keep subtasks atomic and focused on one action each."""

        user_prompt = f"Task: {task}"
        if context:
            user_prompt += f"\n\nCurrent context:\n{context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self.llm_complete("", messages)
            content = response.get("content", "")
            return self._parse_subtask_list(content)
        except Exception:
            # Fall back to rule-based
            return self._rule_based_decompose(task)

    def _rule_based_decompose(self, task: str) -> list[str]:
        """Simple rule-based task decomposition."""
        task_lower = task.lower()

        # Check for common multi-step patterns
        if "search" in task_lower and "click" in task_lower:
            return [
                "Navigate to the target website",
                "Find and interact with the search field",
                "Enter the search query",
                "Submit the search",
                "Wait for results to load",
                "Find and click the target result",
            ]

        if "login" in task_lower or "sign in" in task_lower:
            return [
                "Navigate to the login page",
                "Wait for the user to complete manual login",
                "Verify login was successful",
            ]

        if "order" in task_lower or "buy" in task_lower or "purchase" in task_lower:
            return [
                "Navigate to the target website",
                "Search for the desired item",
                "Select the item from results",
                "Add item to cart",
                "Proceed to checkout",
                "Review order details",
                "Confirm the order (with user approval)",
            ]

        if "fill" in task_lower and "form" in task_lower:
            return [
                "Navigate to the form page",
                "Identify all form fields",
                "Fill in each required field",
                "Review the filled form",
                "Submit the form",
            ]

        # Default: simple sequential steps
        return [
            "Navigate to the target page",
            "Analyze the page structure",
            "Execute the main action",
            "Verify the result",
        ]

    def _parse_subtask_list(self, content: str) -> list[str]:
        """Parse numbered list from LLM response."""
        lines = content.strip().split("\n")
        subtasks = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove number prefix (1., 2., etc.)
            if line[0].isdigit():
                # Find the first non-digit, non-dot, non-space character
                idx = 0
                while idx < len(line) and (line[idx].isdigit() or line[idx] in ".)- "):
                    idx += 1
                line = line[idx:].strip()

            if line:
                subtasks.append(line)

        return subtasks if subtasks else ["Execute the task"]

    def _print_plan(self, plan: TaskPlan) -> None:
        """Print the decomposed plan."""
        content = f"Task: {plan.original_task}\n\n"
        content += f"Decomposed into {len(plan.subtasks)} subtasks:\n"
        for subtask in plan.subtasks:
            deps = ""
            if subtask.dependencies:
                deps = f" (after step {subtask.dependencies[0] + 1})"
            content += f"  {subtask.id + 1}. {subtask.description}{deps}\n"

        print_thought(content, title="[TASK DECOMPOSITION]")


def create_task_decomposer(
    llm_complete: Optional[Callable[[str, list], Awaitable[dict]]] = None,
    verbose: bool = True,
) -> TaskDecomposer:
    """
    Factory function to create a task decomposer.

    Args:
        llm_complete: Async LLM completion function
        verbose: Whether to print progress

    Returns:
        Configured TaskDecomposer instance
    """
    return TaskDecomposer(llm_complete=llm_complete, verbose=verbose)
