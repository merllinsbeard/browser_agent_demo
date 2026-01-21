"""
Security Module for Browser Automation Agent

Implements safety checks and user confirmation flows for destructive actions:
- FR-019: Confirmation before deleting data
- FR-020: Confirmation before sending messages
- FR-021: Confirmation before financial operations
- FR-022: Block password automation
"""

from .detector import (
    ActionType,
    SecurityCheck,
    DestructiveActionDetector,
    create_detector,
)
from .confirmation import (
    ConfirmationResult,
    UserConfirmation,
    create_confirmation,
)

__all__ = [
    # Detector (T036)
    "ActionType",
    "SecurityCheck",
    "DestructiveActionDetector",
    "create_detector",
    # Confirmation (T037, T038)
    "ConfirmationResult",
    "UserConfirmation",
    "create_confirmation",
]
