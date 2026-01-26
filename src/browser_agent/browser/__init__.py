"""
Browser Automation Module

Provides Playwright browser management for the browser automation agent.
Implements FR-001 (visible browser).
"""

from .controller import BrowserController, BrowserConfig, create_browser

__all__ = [
    "BrowserController",
    "BrowserConfig",
    "create_browser",
]
