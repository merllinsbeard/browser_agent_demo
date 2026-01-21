"""
User Confirmation Module

Implements user confirmation flow for destructive actions:
- T037: UserConfirmation flow
- T038: Confirmation UI in terminal
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text


class ConfirmationResult(Enum):
    """Result of user confirmation."""

    CONFIRMED = "confirmed"
    DENIED = "denied"
    CANCELLED = "cancelled"
    MODIFIED = "modified"


@dataclass
class UserConfirmation:
    """
    Handles user confirmation for destructive actions.

    Displays a confirmation prompt in the terminal and waits
    for user input before proceeding with the action.
    """

    console: Console = None

    def __post_init__(self):
        """Initialize console if not provided."""
        if self.console is None:
            self.console = Console()

    def confirm_action(
        self,
        action_description: str,
        action_type: str,
        details: Optional[dict[str, Any]] = None,
        prompt: Optional[str] = None,
    ) -> tuple[ConfirmationResult, Optional[str]]:
        """
        Request user confirmation for an action.

        Args:
            action_description: Description of the action
            action_type: Type of action (delete, send, payment)
            details: Additional details to show user
            prompt: Custom confirmation prompt

        Returns:
            Tuple of (result, user_response)
        """
        # Build confirmation panel content
        content = self._build_content(action_description, action_type, details)

        # Color based on action type
        color = self._get_color(action_type)

        # Display confirmation panel
        panel = Panel(
            content,
            title=f"[bold {color}]⚠️ Confirmation Required[/]",
            border_style=color,
            padding=(1, 2),
        )
        self.console.print(panel)

        # Get user response
        default_prompt = prompt or "Proceed with this action?"
        try:
            confirmed = Confirm.ask(
                f"[{color}]{default_prompt}[/]",
                default=False,
                console=self.console,
            )

            if confirmed:
                return ConfirmationResult.CONFIRMED, "yes"
            else:
                return ConfirmationResult.DENIED, "no"

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Cancelled by user[/]")
            return ConfirmationResult.CANCELLED, None

    def confirm_with_options(
        self,
        action_description: str,
        options: list[str],
        details: Optional[dict[str, Any]] = None,
    ) -> tuple[ConfirmationResult, Optional[str]]:
        """
        Request confirmation with multiple options.

        Args:
            action_description: Description of the action
            options: List of options to present
            details: Additional details

        Returns:
            Tuple of (result, selected_option)
        """
        # Display action info
        content = Text()
        content.append(f"{action_description}\n\n", style="bold")

        if details:
            for key, value in details.items():
                content.append(f"{key}: ", style="dim")
                content.append(f"{value}\n")

        content.append("\nOptions:\n", style="bold yellow")
        for i, option in enumerate(options, 1):
            content.append(f"  {i}. {option}\n")
        content.append("  0. Cancel\n")

        panel = Panel(
            content,
            title="[bold yellow]⚠️ Choose an Option[/]",
            border_style="yellow",
            padding=(1, 2),
        )
        self.console.print(panel)

        try:
            choice = Prompt.ask(
                "Enter choice",
                choices=[str(i) for i in range(len(options) + 1)],
                default="0",
                console=self.console,
            )

            if choice == "0":
                return ConfirmationResult.CANCELLED, None

            selected = options[int(choice) - 1]
            return ConfirmationResult.CONFIRMED, selected

        except (KeyboardInterrupt, ValueError):
            self.console.print("\n[yellow]Cancelled[/]")
            return ConfirmationResult.CANCELLED, None

    def request_manual_input(
        self,
        message: str,
        wait_message: Optional[str] = None,
    ) -> bool:
        """
        Request user to perform manual action (e.g., CAPTCHA, login).

        Args:
            message: Message explaining what user needs to do
            wait_message: Message shown while waiting

        Returns:
            True if user confirms they completed the action
        """
        content = Text()
        content.append("🔐 Manual Action Required\n\n", style="bold yellow")
        content.append(message, style="white")

        panel = Panel(
            content,
            title="[bold yellow]User Action Needed[/]",
            border_style="yellow",
            padding=(1, 2),
        )
        self.console.print(panel)

        wait = wait_message or "Press Enter when done..."
        try:
            Prompt.ask(f"[yellow]{wait}[/]", console=self.console)
            return True
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Cancelled[/]")
            return False

    def show_blocked_action(
        self,
        reason: str,
        suggestion: Optional[str] = None,
    ) -> None:
        """
        Display a message about a blocked action.

        Args:
            reason: Why the action is blocked
            suggestion: Suggested alternative
        """
        content = Text()
        content.append("🚫 Action Blocked\n\n", style="bold red")
        content.append(reason, style="white")

        if suggestion:
            content.append(f"\n\n💡 {suggestion}", style="italic yellow")

        panel = Panel(
            content,
            title="[bold red]Security Block[/]",
            border_style="red",
            padding=(1, 2),
        )
        self.console.print(panel)

    def _build_content(
        self,
        action: str,
        action_type: str,
        details: Optional[dict[str, Any]],
    ) -> Text:
        """Build the confirmation panel content."""
        content = Text()

        # Action type indicator
        type_icons = {
            "delete": "🗑️ DELETE",
            "send": "📤 SEND",
            "payment": "💳 PAYMENT",
        }
        icon = type_icons.get(action_type, "⚠️ ACTION")
        content.append(f"{icon}\n\n", style="bold")

        # Action description
        content.append(action, style="white")
        content.append("\n")

        # Details
        if details:
            content.append("\n")
            for key, value in details.items():
                content.append(f"{key}: ", style="dim")
                content.append(f"{value}\n")

        return content

    def _get_color(self, action_type: str) -> str:
        """Get color for action type."""
        colors = {
            "delete": "red",
            "send": "yellow",
            "payment": "magenta",
        }
        return colors.get(action_type, "yellow")


def create_confirmation(console: Optional[Console] = None) -> UserConfirmation:
    """
    Factory function to create a user confirmation handler.

    Args:
        console: Optional Rich console to use

    Returns:
        Configured UserConfirmation instance
    """
    return UserConfirmation(console=console)
