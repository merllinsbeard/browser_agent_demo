"""
Completion Report Generator

Generates detailed reports of task execution for user review.
Summarizes actions taken, results achieved, and any issues encountered.

Following FR-017: Provide task completion report.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ..tui import print_completion, print_data_result, get_console


@dataclass
class TaskReport:
    """
    Completion report for a task execution.

    Contains summary, actions, results, and metrics.
    """

    task: str
    status: str  # "completed", "partial", "failed", "cancelled"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    actions_taken: list[dict[str, Any]] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate task duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string."""
        seconds = self.duration_seconds
        if seconds is None:
            return "unknown"
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.1f}m"
        hours = minutes / 60
        return f"{hours:.1f}h"


class ReportGenerator:
    """
    Generates completion reports from task execution data.

    Creates human-readable summaries of what was accomplished,
    how long it took, and any issues encountered.
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize the report generator.

        Args:
            verbose: Whether to print report to console
        """
        self.verbose = verbose
        self.console = get_console()

    def generate(
        self,
        task: str,
        history: list[dict[str, Any]],
        completed: bool = True,
        error: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> TaskReport:
        """
        Generate a completion report from execution history.

        Args:
            task: Original task description
            history: Execution history entries
            completed: Whether task completed successfully
            error: Error message if failed
            start_time: Task start time
            end_time: Task end time

        Returns:
            TaskReport with complete summary
        """
        report = TaskReport(
            task=task,
            status="completed" if completed else ("failed" if error else "partial"),
            start_time=start_time,
            end_time=end_time or datetime.now(),
        )

        # Process history
        self._process_history(report, history)

        # Calculate metrics
        self._calculate_metrics(report)

        # Generate summary
        report.summary = self._generate_summary(report)

        # Add error if present
        if error:
            report.errors.append(error)

        # Print report if verbose
        if self.verbose:
            self._print_report(report)

        return report

    def _process_history(
        self, report: TaskReport, history: list[dict[str, Any]]
    ) -> None:
        """Process execution history into report sections."""
        for entry in history:
            entry_type = entry.get("type", "")

            if entry_type == "thought":
                # Track thoughts but don't add to actions
                pass

            elif entry_type == "action":
                report.actions_taken.append({
                    "tool": entry.get("tool"),
                    "arguments": entry.get("arguments"),
                    "iteration": entry.get("iteration"),
                })

            elif entry_type == "observation":
                if entry.get("success"):
                    report.results.append({
                        "data": entry.get("data"),
                        "iteration": entry.get("iteration"),
                    })
                else:
                    error = entry.get("error")
                    if error:
                        report.errors.append(f"Iteration {entry.get('iteration')}: {error}")

    def _calculate_metrics(self, report: TaskReport) -> None:
        """Calculate execution metrics."""
        report.metrics = {
            "total_actions": len(report.actions_taken),
            "successful_results": len(report.results),
            "error_count": len(report.errors),
            "warning_count": len(report.warnings),
        }

        if report.duration_seconds:
            report.metrics["duration_seconds"] = report.duration_seconds

        # Calculate success rate
        total = report.metrics["total_actions"]
        if total > 0:
            success = report.metrics["successful_results"]
            report.metrics["success_rate"] = f"{(success / total) * 100:.0f}%"

        # Get unique tools used
        tools_used = set(a.get("tool") for a in report.actions_taken if a.get("tool"))
        report.metrics["tools_used"] = list(tools_used)

    def _generate_summary(self, report: TaskReport) -> str:
        """Generate human-readable summary."""
        parts = []

        # Status line
        if report.status == "completed":
            parts.append("✅ Task completed successfully")
        elif report.status == "partial":
            parts.append("⚠️ Task partially completed")
        else:
            parts.append("❌ Task failed")

        # Duration
        parts.append(f"Duration: {report.duration_formatted}")

        # Actions summary
        action_count = len(report.actions_taken)
        if action_count > 0:
            tools = report.metrics.get("tools_used", [])
            parts.append(f"Actions: {action_count} ({', '.join(tools[:3])}{'...' if len(tools) > 3 else ''})")

        # Results summary
        result_count = len(report.results)
        if result_count > 0:
            parts.append(f"Results: {result_count} successful")

        # Errors
        error_count = len(report.errors)
        if error_count > 0:
            parts.append(f"Errors: {error_count}")

        return "\n".join(parts)

    def _print_report(self, report: TaskReport) -> None:
        """Print the report to console."""
        # Print completion summary
        print_completion(
            report.summary,
            actions_count=len(report.actions_taken),
            duration=report.duration_formatted,
        )

        # Print detailed metrics if available
        if report.metrics:
            metrics_display = {
                k: v for k, v in report.metrics.items()
                if k not in ["duration_seconds"]
            }
            print_data_result(metrics_display, title="[METRICS]")

    def format_markdown(self, report: TaskReport) -> str:
        """
        Format report as Markdown for file output.

        Args:
            report: TaskReport to format

        Returns:
            Markdown-formatted string
        """
        lines = [
            "# Task Report",
            "",
            f"**Task:** {report.task}",
            f"**Status:** {report.status}",
            f"**Duration:** {report.duration_formatted}",
            "",
            "## Summary",
            "",
            report.summary,
            "",
        ]

        # Actions section
        if report.actions_taken:
            lines.extend([
                "## Actions Taken",
                "",
            ])
            for i, action in enumerate(report.actions_taken, 1):
                tool = action.get("tool", "unknown")
                args = action.get("arguments", {})
                args_str = ", ".join(f"{k}={v!r}" for k, v in list(args.items())[:3])
                lines.append(f"{i}. `{tool}({args_str})`")
            lines.append("")

        # Errors section
        if report.errors:
            lines.extend([
                "## Errors",
                "",
            ])
            for error in report.errors:
                lines.append(f"- {error}")
            lines.append("")

        # Metrics section
        if report.metrics:
            lines.extend([
                "## Metrics",
                "",
                "| Metric | Value |",
                "|--------|-------|",
            ])
            for key, value in report.metrics.items():
                lines.append(f"| {key} | {value} |")
            lines.append("")

        return "\n".join(lines)


def create_reporter(verbose: bool = True) -> ReportGenerator:
    """
    Factory function to create a report generator.

    Args:
        verbose: Whether to print reports to console

    Returns:
        Configured ReportGenerator instance
    """
    return ReportGenerator(verbose=verbose)
