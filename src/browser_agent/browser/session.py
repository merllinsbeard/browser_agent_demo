"""
Session Manager

Manages browser session persistence and manual login detection (FR-023, FR-024).
Integrates with security module for login page detection and user prompts.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..security.confirmation import UserConfirmation, create_confirmation
from ..tui import print_result, print_action


@dataclass
class SessionConfig:
    """
    Session management configuration.
    """

    # Session persistence directory
    sessions_dir: Path

    # Session name for organization
    session_name: str = "default"

    # Enable auto-login detection
    detect_login: bool = True

    # Login page patterns (URL fragments)
    login_patterns: tuple[str, ...] = (
        "login",
        "signin",
        "sign-in",
        "auth",
        "authenticate",
        "sso",
        "oauth",
        "account/login",
    )

    @classmethod
    def from_env(cls) -> "SessionConfig":
        """Create configuration from environment variables."""
        return cls(
            sessions_dir=Path(os.getenv("SESSIONS_DIR", ".browser-sessions")),
            session_name=os.getenv("SESSION_NAME", "default"),
            detect_login=os.getenv("DETECT_LOGIN", "true").lower() in ("true", "1", "yes"),
        )


class SessionManager:
    """
    Manages browser session state and login detection.

    Provides:
    - Login page detection during navigation
    - User prompts for manual authentication
    - Session status tracking
    """

    def __init__(
        self,
        config: Optional[SessionConfig] = None,
        confirmation: Optional[UserConfirmation] = None,
    ):
        """
        Initialize session manager.

        Args:
            config: Session configuration
            confirmation: User confirmation handler
        """
        self.config = config or SessionConfig.from_env()
        self.confirmation = confirmation or create_confirmation()
        self._logged_in_domains: set[str] = set()

    def is_login_page(self, url: str, page_title: str = "") -> bool:
        """
        Check if URL appears to be a login page.

        Args:
            url: Page URL
            page_title: Page title

        Returns:
            True if page appears to be a login page
        """
        if not self.config.detect_login:
            return False

        url_lower = url.lower()
        title_lower = page_title.lower()

        for pattern in self.config.login_patterns:
            if pattern in url_lower:
                return True

        # Title-based detection
        login_title_patterns = ["log in", "login", "sign in", "signin", "authenticate"]
        for pattern in login_title_patterns:
            if pattern in title_lower:
                return True

        return False

    async def check_login_required(
        self,
        url: str,
        page_title: str = "",
        page_content: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Check if login is required and prompt user if needed.

        Args:
            url: Current page URL
            page_title: Page title
            page_content: Optional page accessibility tree or content

        Returns:
            True if login was completed, False if cancelled
        """
        if not self.is_login_page(url, page_title):
            return True  # No login needed

        # Extract domain
        domain = self._extract_domain(url)

        # Check if already logged in to this domain
        if domain in self._logged_in_domains:
            return True

        # Detect login form elements
        has_password_field = False
        if page_content:
            elements = page_content.get("elements", [])
            for elem in elements:
                role = elem.get("role", "")
                name = elem.get("name", "").lower()
                if role == "textbox" and any(
                    p in name for p in ["password", "passwd", "pwd"]
                ):
                    has_password_field = True
                    break

        if not has_password_field:
            return True  # No password field found, skip login prompt

        # Prompt user for manual login
        print_action(
            f"Login page detected: {url}",
            params={"domain": domain, "title": page_title},
        )

        completed = self.confirmation.request_manual_input(
            message=(
                f"Please log in to {domain} manually.\n\n"
                "The browser will wait for you to complete the login process.\n"
                "Navigate to where you need to go, then press Enter to continue."
            ),
            wait_message="Press Enter when login is complete...",
        )

        if completed:
            self._logged_in_domains.add(domain)
            print_result(
                f"Login completed for {domain}",
                success=True,
                title="[LOGIN COMPLETE]",
            )
            return True
        else:
            print_result(
                f"Login cancelled for {domain}",
                success=False,
                title="[LOGIN CANCELLED]",
            )
            return False

    def mark_logged_in(self, url: str) -> None:
        """
        Mark a domain as logged in.

        Args:
            url: URL of the domain
        """
        domain = self._extract_domain(url)
        self._logged_in_domains.add(domain)

    def is_logged_in(self, url: str) -> bool:
        """
        Check if already logged in to a domain.

        Args:
            url: URL to check

        Returns:
            True if logged in to this domain
        """
        domain = self._extract_domain(url)
        return domain in self._logged_in_domains

    def get_session_path(self) -> Path:
        """Get the session storage path."""
        return self.config.sessions_dir / self.config.session_name

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        # Simple domain extraction
        url = url.lower()
        if "://" in url:
            url = url.split("://", 1)[1]
        if "/" in url:
            url = url.split("/", 1)[0]
        if ":" in url:
            url = url.split(":", 1)[0]
        return url


def create_session_manager(
    config: Optional[SessionConfig] = None,
    confirmation: Optional[UserConfirmation] = None,
) -> SessionManager:
    """
    Factory function to create a session manager.

    Args:
        config: Session configuration
        confirmation: User confirmation handler

    Returns:
        Configured SessionManager instance
    """
    return SessionManager(config=config, confirmation=confirmation)
