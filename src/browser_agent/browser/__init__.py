"""
Browser Automation Module

Provides Playwright browser management for the browser automation agent.
Implements FR-001 (visible browser), FR-023 (session persistence), FR-024 (manual login).
"""

from .controller import BrowserController, BrowserConfig, create_browser
from .session import SessionManager, SessionConfig, create_session_manager

__all__ = [
    "BrowserController",
    "BrowserConfig",
    "create_browser",
    "SessionManager",
    "SessionConfig",
    "create_session_manager",
]
