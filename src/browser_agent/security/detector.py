"""
Destructive Action Detector

Detects actions that require user confirmation before execution:
- FR-019: Deleting data
- FR-020: Sending messages
- FR-021: Financial operations
- FR-022: Password/credential operations (blocked)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ActionType(Enum):
    """Types of actions that require special handling."""

    SAFE = "safe"
    DELETE = "delete"
    SEND = "send"
    PAYMENT = "payment"
    PASSWORD = "password"  # Blocked (FR-022)
    MFA = "mfa"  # Blocked (FR-022)


@dataclass
class SecurityCheck:
    """
    Result of a security check on an action.

    Contains the detected action type, whether it needs confirmation,
    and context for the confirmation prompt.
    """

    action_type: ActionType
    requires_confirmation: bool
    is_blocked: bool = False
    message: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    confirmation_prompt: Optional[str] = None


class DestructiveActionDetector:
    """
    Detects destructive or sensitive actions from browser operations.

    Analyzes action descriptions, page content, and element context
    to identify operations that need user confirmation or should be blocked.
    """

    def __init__(self):
        """Initialize the detector with pattern definitions."""
        # Deletion patterns (FR-019)
        self.delete_patterns = [
            "delete",
            "remove",
            "erase",
            "clear",
            "trash",
            "discard",
            "destroy",
            "wipe",
            "purge",
            "unsubscribe",
            "deactivate",
            "cancel account",
            "close account",
        ]

        # Send patterns (FR-020)
        self.send_patterns = [
            "send",
            "submit",
            "post",
            "publish",
            "share",
            "forward",
            "reply",
            "compose",
            "tweet",
            "message",
            "email",
            "broadcast",
        ]

        # Payment patterns (FR-021)
        self.payment_patterns = [
            "pay",
            "purchase",
            "buy",
            "checkout",
            "confirm order",
            "place order",
            "complete order",
            "payment",
            "billing",
            "credit card",
            "debit card",
            "subscribe",
            "donate",
            "transfer money",
            "wire transfer",
            "add to cart",  # Warning only
            "proceed to checkout",
        ]

        # Password/MFA patterns (FR-022 - blocked)
        self.password_patterns = [
            "password",
            "passwd",
            "passcode",
            "pin code",
            "secret",
            "credential",
            "login",
            "sign in",
            "sign up",
            "register",
            "create account",
            "authentication",
        ]

        self.mfa_patterns = [
            "mfa",
            "2fa",
            "two-factor",
            "two factor",
            "verification code",
            "otp",
            "one-time",
            "authenticator",
            "security code",
            "sms code",
        ]

    def check_action(
        self,
        action_description: str,
        element_context: Optional[dict[str, Any]] = None,
        page_context: Optional[dict[str, Any]] = None,
    ) -> SecurityCheck:
        """
        Check if an action requires confirmation or should be blocked.

        Args:
            action_description: Description of the action
            element_context: Context about the target element
            page_context: Context about the current page

        Returns:
            SecurityCheck with detection results
        """
        action_lower = action_description.lower()
        element_context = element_context or {}
        page_context = page_context or {}

        # Check for blocked actions first (FR-022)
        blocked = self._check_blocked(action_lower, element_context, page_context)
        if blocked:
            return blocked

        # Check for payment actions (FR-021)
        payment = self._check_payment(action_lower, element_context, page_context)
        if payment.requires_confirmation:
            return payment

        # Check for send actions (FR-020)
        send = self._check_send(action_lower, element_context, page_context)
        if send.requires_confirmation:
            return send

        # Check for delete actions (FR-019)
        delete = self._check_delete(action_lower, element_context, page_context)
        if delete.requires_confirmation:
            return delete

        # Safe action
        return SecurityCheck(
            action_type=ActionType.SAFE,
            requires_confirmation=False,
            message="Action is safe to proceed",
        )

    def _check_blocked(
        self,
        action: str,
        element: dict[str, Any],
        page: dict[str, Any],
    ) -> Optional[SecurityCheck]:
        """Check for blocked password/MFA operations."""
        # Password field detection
        element_type = element.get("type", "").lower()
        element_role = element.get("role", "").lower()

        if element_type == "password" or "password" in element_role:
            return SecurityCheck(
                action_type=ActionType.PASSWORD,
                requires_confirmation=False,
                is_blocked=True,
                message="Password field automation is blocked for security (FR-022)",
                confirmation_prompt=None,
            )

        # Pattern matching for password actions
        for pattern in self.password_patterns:
            if pattern in action:
                return SecurityCheck(
                    action_type=ActionType.PASSWORD,
                    requires_confirmation=False,
                    is_blocked=True,
                    message=f"Password/login automation blocked: '{pattern}' detected (FR-022)",
                    context={"pattern": pattern},
                )

        # MFA detection
        for pattern in self.mfa_patterns:
            if pattern in action:
                return SecurityCheck(
                    action_type=ActionType.MFA,
                    requires_confirmation=False,
                    is_blocked=True,
                    message=f"MFA automation blocked: '{pattern}' detected (FR-022)",
                    context={"pattern": pattern},
                )

        return None

    def _check_delete(
        self,
        action: str,
        element: dict[str, Any],
        page: dict[str, Any],
    ) -> SecurityCheck:
        """Check for deletion actions (FR-019)."""
        for pattern in self.delete_patterns:
            if pattern in action:
                return SecurityCheck(
                    action_type=ActionType.DELETE,
                    requires_confirmation=True,
                    message=f"Deletion action detected: '{pattern}'",
                    context={"pattern": pattern, "action": action},
                    confirmation_prompt="⚠️ This will DELETE data. Continue? (yes/no)",
                )

        return SecurityCheck(
            action_type=ActionType.SAFE,
            requires_confirmation=False,
        )

    def _check_send(
        self,
        action: str,
        element: dict[str, Any],
        page: dict[str, Any],
    ) -> SecurityCheck:
        """Check for send/publish actions (FR-020)."""
        for pattern in self.send_patterns:
            if pattern in action:
                return SecurityCheck(
                    action_type=ActionType.SEND,
                    requires_confirmation=True,
                    message=f"Send action detected: '{pattern}'",
                    context={"pattern": pattern, "action": action},
                    confirmation_prompt="⚠️ This will SEND/PUBLISH content. Continue? (yes/no)",
                )

        return SecurityCheck(
            action_type=ActionType.SAFE,
            requires_confirmation=False,
        )

    def _check_payment(
        self,
        action: str,
        element: dict[str, Any],
        page: dict[str, Any],
    ) -> SecurityCheck:
        """Check for payment/financial actions (FR-021)."""
        page_url = page.get("url", "").lower()
        page_title = page.get("title", "").lower()

        # Check for payment page indicators
        payment_page = any(
            indicator in page_url or indicator in page_title
            for indicator in ["checkout", "payment", "billing", "cart", "order"]
        )

        for pattern in self.payment_patterns:
            if pattern in action:
                # Higher severity for actual payment vs just "add to cart"
                if pattern in ["add to cart"]:
                    return SecurityCheck(
                        action_type=ActionType.PAYMENT,
                        requires_confirmation=False,  # Just warning
                        message=f"Shopping action detected: '{pattern}'",
                        context={"pattern": pattern, "action": action},
                    )

                return SecurityCheck(
                    action_type=ActionType.PAYMENT,
                    requires_confirmation=True,
                    message=f"Payment action detected: '{pattern}'",
                    context={
                        "pattern": pattern,
                        "action": action,
                        "payment_page": payment_page,
                    },
                    confirmation_prompt="⚠️ This is a PAYMENT action. Confirm purchase? (yes/no)",
                )

        return SecurityCheck(
            action_type=ActionType.SAFE,
            requires_confirmation=False,
        )

    def check_page_context(
        self,
        page_url: str,
        page_title: str,
        page_text: str,
    ) -> list[SecurityCheck]:
        """
        Check page context for potential security concerns.

        Returns list of warnings/issues detected on the page.
        """
        warnings = []

        url_lower = page_url.lower()
        title_lower = page_title.lower()

        # Payment page detection
        payment_indicators = ["checkout", "payment", "billing", "order summary"]
        for indicator in payment_indicators:
            if indicator in url_lower or indicator in title_lower:
                warnings.append(SecurityCheck(
                    action_type=ActionType.PAYMENT,
                    requires_confirmation=False,
                    message=f"Currently on payment page: {indicator}",
                    context={"indicator": indicator, "url": page_url},
                ))
                break

        # Login page detection
        login_indicators = ["login", "sign in", "signin", "auth"]
        for indicator in login_indicators:
            if indicator in url_lower:
                warnings.append(SecurityCheck(
                    action_type=ActionType.PASSWORD,
                    requires_confirmation=False,
                    is_blocked=True,
                    message="Login page detected - manual authentication required",
                    context={"indicator": indicator, "url": page_url},
                ))
                break

        return warnings


def create_detector() -> DestructiveActionDetector:
    """
    Factory function to create a destructive action detector.

    Returns:
        Configured DestructiveActionDetector instance
    """
    return DestructiveActionDetector()
