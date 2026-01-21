"""
Browser Automation Module

Provides Playwright browser management for the browser automation agent.
Implements FR-001 (visible browser) and FR-023 (session persistence).
"""

from .controller import BrowserController, BrowserConfig, create_browser

__all__ = [
    "BrowserController",
    "BrowserConfig",
    "create_browser",
]
