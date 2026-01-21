"""
Validator Sub-Agent

Fast action verifier using the haiku model tier.
Validates action results, detects issues (CAPTCHA, errors),
and checks for destructive action risks.

Following FR-029 (CAPTCHA detection) and FR-016 (page change adaptation).
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Awaitable
from enum import Enum

from ..tui import print_result, print_error, action_spinner


class ValidationStatus(Enum):
    """Status of validation check."""

    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    NEEDS_USER_INPUT = "needs_user_input"
    CAPTCHA_DETECTED = "captcha_detected"
    PAGE_CHANGED = "page_changed"
    DESTRUCTIVE_ACTION = "destructive_action"


@dataclass
class ValidationResult:
    """
    Result of validation check.

    Contains status, details, and any required user actions.
    """

    status: ValidationStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    user_action_required: Optional[str] = None
    suggestions: list[str] = field(default_factory=list)


@dataclass
class PageState:
    """
    Snapshot of page state for comparison.

    Used to detect page changes between actions.
    """

    url: str
    title: str
    element_count: int
    text_hash: str
    timestamp: float


class ActionValidator:
    """
    Validator sub-agent for action verification.

    Uses the haiku model tier for fast validation.
    Detects CAPTCHA, page changes, and destructive actions.
    """

    def __init__(
        self,
        llm_complete: Optional[Callable[[str], Awaitable[str]]] = None,
        verbose: bool = True,
    ):
        """
        Initialize the validator.

        Args:
            llm_complete: Optional LLM for intelligent validation
            verbose: Whether to print progress
        """
        self.llm_complete = llm_complete
        self.verbose = verbose
        self._previous_state: Optional[PageState] = None

    async def validate_action_result(
        self,
        action: str,
        result: Any,
        page_state: dict[str, Any],
    ) -> ValidationResult:
        """
        Validate the result of an action.

        Args:
            action: Description of the action performed
            result: Result from the action
            page_state: Current page state

        Returns:
            ValidationResult with status and details
        """
        validations = []

        # Check for explicit errors
        if isinstance(result, dict):
            if result.get("error"):
                return ValidationResult(
                    status=ValidationStatus.FAILURE,
                    message=f"Action failed: {result['error']}",
                    details={"error": result["error"]},
                    suggestions=["Retry the action", "Try a different approach"],
                )

        # Check for CAPTCHA
        captcha_result = await self._check_captcha(page_state)
        if captcha_result:
            validations.append(captcha_result)

        # Check for page changes
        page_change_result = self._check_page_change(page_state)
        if page_change_result:
            validations.append(page_change_result)

        # Check for destructive action indicators
        destructive_result = self._check_destructive_action(action, page_state)
        if destructive_result:
            validations.append(destructive_result)

        # Return most critical validation issue
        for validation in validations:
            if validation.status in [
                ValidationStatus.CAPTCHA_DETECTED,
                ValidationStatus.DESTRUCTIVE_ACTION,
                ValidationStatus.NEEDS_USER_INPUT,
            ]:
                if self.verbose:
                    print_error(
                        validation.message,
                        error_type=validation.status.value,
                        suggestion=validation.user_action_required,
                    )
                return validation

        # Update stored state
        self._update_state(page_state)

        # Success
        success_result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            message="Action completed successfully",
            details={"action": action},
        )

        if self.verbose:
            print_result(
                success_result.message,
                success=True,
                title="[VALIDATION]",
            )

        return success_result

    async def _check_captcha(
        self, page_state: dict[str, Any]
    ) -> Optional[ValidationResult]:
        """
        Check if CAPTCHA is present on the page.

        Args:
            page_state: Current page state

        Returns:
            ValidationResult if CAPTCHA detected, None otherwise
        """
        text = page_state.get("text", "").lower()
        title = page_state.get("title", "").lower()
        url = page_state.get("url", "").lower()

        # Common CAPTCHA indicators
        captcha_patterns = [
            "captcha",
            "recaptcha",
            "hcaptcha",
            "verify you are human",
            "prove you're not a robot",
            "i'm not a robot",
            "security check",
            "challenge",
            "verify your identity",
            "human verification",
            "bot detection",
        ]

        for pattern in captcha_patterns:
            if pattern in text or pattern in title or pattern in url:
                return ValidationResult(
                    status=ValidationStatus.CAPTCHA_DETECTED,
                    message="CAPTCHA detected on page",
                    details={"pattern": pattern},
                    user_action_required="Please solve the CAPTCHA manually and press Enter to continue",
                    suggestions=[
                        "Wait for user to solve CAPTCHA",
                        "Try alternative navigation",
                    ],
                )

        # Check for common CAPTCHA element roles
        elements = page_state.get("interactive_elements", [])
        for elem in elements:
            name = (elem.get("name") or "").lower()
            if any(p in name for p in ["captcha", "recaptcha", "hcaptcha"]):
                return ValidationResult(
                    status=ValidationStatus.CAPTCHA_DETECTED,
                    message=f"CAPTCHA element detected: {elem.get('name')}",
                    details={"element": elem},
                    user_action_required="Please solve the CAPTCHA manually",
                )

        return None

    def _check_page_change(
        self, page_state: dict[str, Any]
    ) -> Optional[ValidationResult]:
        """
        Check if the page has changed unexpectedly.

        Args:
            page_state: Current page state

        Returns:
            ValidationResult if significant change detected
        """
        if self._previous_state is None:
            return None

        current_url = page_state.get("url", "")

        # Check URL change
        if current_url != self._previous_state.url:
            # Significant URL change (not just fragment)
            prev_base = self._previous_state.url.split("#")[0].split("?")[0]
            curr_base = current_url.split("#")[0].split("?")[0]

            if prev_base != curr_base:
                return ValidationResult(
                    status=ValidationStatus.PAGE_CHANGED,
                    message=f"Page navigated: {self._previous_state.url} → {current_url}",
                    details={
                        "previous_url": self._previous_state.url,
                        "current_url": current_url,
                    },
                    suggestions=[
                        "Re-analyze page structure",
                        "Update action plan for new page",
                    ],
                )

        return None

    def _check_destructive_action(
        self, action: str, page_state: dict[str, Any]
    ) -> Optional[ValidationResult]:
        """
        Check if action might be destructive and needs confirmation.

        Args:
            action: Action being performed
            page_state: Current page state

        Returns:
            ValidationResult if destructive action detected
        """
        action_lower = action.lower()
        text = page_state.get("text", "").lower()

        # Destructive action patterns
        delete_patterns = ["delete", "remove", "erase", "clear all"]
        send_patterns = ["send", "submit", "post", "publish"]
        payment_patterns = ["pay", "checkout", "purchase", "buy", "order", "confirm payment"]

        # Check action description
        for pattern in delete_patterns:
            if pattern in action_lower:
                return ValidationResult(
                    status=ValidationStatus.DESTRUCTIVE_ACTION,
                    message=f"Destructive action detected: {action}",
                    details={"action": action, "type": "delete"},
                    user_action_required="Confirm deletion before proceeding (yes/no)",
                    suggestions=["Request user confirmation"],
                )

        for pattern in send_patterns:
            if pattern in action_lower:
                return ValidationResult(
                    status=ValidationStatus.DESTRUCTIVE_ACTION,
                    message=f"Send action detected: {action}",
                    details={"action": action, "type": "send"},
                    user_action_required="Confirm sending before proceeding (yes/no)",
                )

        for pattern in payment_patterns:
            if pattern in action_lower or pattern in text:
                return ValidationResult(
                    status=ValidationStatus.DESTRUCTIVE_ACTION,
                    message=f"Payment/checkout action detected: {action}",
                    details={"action": action, "type": "payment"},
                    user_action_required="Confirm payment before proceeding (yes/no)",
                )

        return None

    def _update_state(self, page_state: dict[str, Any]) -> None:
        """Update stored page state."""
        import time
        import hashlib

        text = page_state.get("text", "")
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]

        self._previous_state = PageState(
            url=page_state.get("url", ""),
            title=page_state.get("title", ""),
            element_count=len(page_state.get("interactive_elements", [])),
            text_hash=text_hash,
            timestamp=time.time(),
        )

    async def check_task_completion(
        self,
        task: str,
        page_state: dict[str, Any],
        action_history: list[dict[str, Any]],
    ) -> ValidationResult:
        """
        Check if the task has been completed.

        Args:
            task: Original task description
            page_state: Current page state
            action_history: History of actions taken

        Returns:
            ValidationResult indicating completion status
        """
        # Simple heuristic: if we have multiple successful actions
        # and no errors in recent history, likely complete
        recent_actions = action_history[-5:] if action_history else []
        success_count = sum(
            1 for a in recent_actions
            if a.get("type") == "observation" and a.get("success")
        )

        if success_count >= 2:
            # Use LLM if available for intelligent completion check
            if self.llm_complete:
                prompt = f"""Task: {task}

Recent actions: {len(action_history)}
Current page: {page_state.get('title')} ({page_state.get('url')})

Is this task complete? Answer YES or NO with brief explanation."""

                try:
                    with action_spinner("Checking completion..."):
                        response = await self.llm_complete(prompt)

                    if response and "YES" in response.upper():
                        return ValidationResult(
                            status=ValidationStatus.SUCCESS,
                            message="Task appears complete",
                            details={"llm_assessment": response[:200]},
                        )
                except Exception:
                    pass

        return ValidationResult(
            status=ValidationStatus.WARNING,
            message="Task completion uncertain",
            suggestions=["Continue with next action", "Verify task completion manually"],
        )


def create_validator(
    llm_complete: Optional[Callable[[str], Awaitable[str]]] = None,
    verbose: bool = True,
) -> ActionValidator:
    """
    Factory function to create an action validator.

    Args:
        llm_complete: Optional LLM function for intelligent validation
        verbose: Whether to print progress

    Returns:
        Configured ActionValidator instance
    """
    return ActionValidator(llm_complete=llm_complete, verbose=verbose)
