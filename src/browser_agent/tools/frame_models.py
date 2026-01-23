"""
Data models for iframe interaction support.

This module defines Pydantic models for frame-aware browser automation:
- FrameContext: Represents a frame (main or iframe) with metadata
- FrameLocatorResult: Result of element search across frames
- InteractionAttempt: Record of a single interaction attempt
- RetryChain: Manages retry strategy sequence for failed interactions

Feature: 002-iframe-interaction-fixes
Date: 2026-01-22
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any


class FrameContext(BaseModel):
    """Frame context for element targeting.

    Represents the context of a frame (main frame or iframe) for element targeting.
    Used by list_frames tool and included in ToolResult metadata for frame-aware operations.

    Validation Rules:
    - index must be >= 0
    - accessible defaults to True
    - At least one of name, aria_label, or title should be present for semantic identification
    """

    name: Optional[str] = None
    """Frame name attribute (if present)."""

    index: int = Field(ge=0, description="Frame index in page.frames list (0 = main)")
    """Frame index in page.frames list. 0 represents the main frame."""

    src: Optional[str] = None
    """Frame src URL."""

    aria_label: Optional[str] = None
    """aria-label attribute of iframe element."""

    title: Optional[str] = None
    """title attribute of iframe element."""

    accessible: bool = True
    """Whether frame content is accessible (false for cross-origin)."""

    parent_index: Optional[int] = None
    """Index of parent frame (for nested iframes)."""


class FrameLocatorResult(BaseModel):
    """Result of searching for element across frames.

    Internal result type for _find_element_in_all_frames() utility.

    Validation Rules:
    - confidence_score must be between 0.0 and 1.0
    - frame_context is None only when found is False
    - locator is the Playwright Locator object (stored as Any to avoid Pydantic issues)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    found: bool
    """Whether element was found."""

    frame_context: Optional[FrameContext] = None
    """Frame where element was found."""

    locator: Optional[Any] = None
    """Playwright Locator object for the found element."""

    locator_description: Optional[str] = None
    """Description used to find element."""

    search_strategy: Optional[str] = None
    """Strategy that succeeded (e.g., "get_by_role", "get_by_text")."""

    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    """Match confidence 0.0-1.0 (for future ranking)."""


class InteractionAttempt(BaseModel):
    """Record of single interaction attempt.

    Records a single attempt to interact with an element (for retry chain).
    Collected in RetryChain and included in structured error response (FR-019).

    Validation Rules:
    - duration_ms must be >= 0
    - error should be None if success is True
    """

    strategy: str
    """Strategy used (e.g., "main_frame", "iframe_0", "coordinate_click")."""

    frame_context: Optional[FrameContext] = None
    """Frame context for this attempt."""

    success: bool
    """Whether attempt succeeded."""

    duration_ms: int = Field(ge=0)
    """Time taken for this attempt in milliseconds."""

    error: Optional[str] = None
    """Error message if failed."""


class RetryChain(BaseModel):
    """Manages retry strategy sequence for element interaction.

    Implements state machine for trying multiple interaction strategies.
    Created by click/type_text tools when auto-retry is needed (FR-015, FR-017).

    Default Strategy Order:
    1. main_frame - Try main frame first
    2. iframe_<name> - Try each iframe with semantic label (prioritized)
    3. iframe_<index> - Try remaining iframes by index
    4. coordinate_click - Final fallback

    Validation Rules:
    - current_index must be < len(strategies)
    - max_attempts should equal len(strategies)
    - timeout_per_frame_ms default is 10000, configurable via FR-020
    """

    strategies: list[str]
    """Ordered list of strategies to try."""

    current_index: int = 0
    """Current position in strategy list."""

    max_attempts: int
    """Total max attempts (1 per frame + coordinate_click)."""

    attempts: list[InteractionAttempt] = []
    """History of all attempts."""

    timeout_per_frame_ms: int = 10000
    """Timeout for each frame attempt in milliseconds (default 10000)."""

    @property
    def current_strategy(self) -> Optional[str]:
        """Get the current strategy to attempt.

        Returns None if all strategies are exhausted.
        """
        if self.current_index >= len(self.strategies):
            return None
        return self.strategies[self.current_index]

    @property
    def is_exhausted(self) -> bool:
        """Check if all retry strategies have been attempted."""
        return self.current_index >= len(self.strategies)

    @property
    def has_succeeded(self) -> bool:
        """Check if any attempt has succeeded."""
        return any(attempt.success for attempt in self.attempts)

    def advance(self) -> None:
        """Advance to the next strategy in the chain."""
        self.current_index += 1

    def add_attempt(
        self,
        strategy: str,
        success: bool,
        duration_ms: int,
        error: Optional[str] = None,
        frame_context: Optional["FrameContext"] = None,
    ) -> None:
        """Add an attempt to the retry chain.

        Args:
            strategy: Strategy name that was used
            success: Whether the attempt succeeded
            duration_ms: Time taken in milliseconds
            error: Error message if failed
            frame_context: Frame context for this attempt
        """
        attempt = InteractionAttempt(
            strategy=strategy,
            success=success,
            duration_ms=duration_ms,
            error=error,
            frame_context=frame_context,
        )
        self.attempts.append(attempt)

    def to_error_dict(self) -> dict:
        """Convert retry chain to dictionary for structured error response (FR-019).

        Returns:
            Dictionary with all attempts and metadata
        """
        return {
            "strategies": self.strategies,
            "max_attempts": self.max_attempts,
            "attempts": [attempt.model_dump() for attempt in self.attempts],
            "timeout_per_frame_ms": self.timeout_per_frame_ms,
            "final_index": self.current_index,
            "exhausted": self.is_exhausted,
            "succeeded": self.has_succeeded,
        }
