"""
Browser Controller

Manages Playwright browser instance with configurable options.
Implements FR-001 (visible mode) and FR-023 (session persistence).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


BrowserType = Literal["chromium", "firefox", "webkit"]


@dataclass
class BrowserConfig:
    """
    Configuration for browser instance.

    Reads from environment variables with sensible defaults.
    """

    # Browser type (chromium is Playwright's Chrome-based browser)
    browser_type: BrowserType = "chromium"

    # Headless mode - default False for visible browser (FR-001)
    headless: bool = False

    # Viewport size
    viewport_width: int = 1280
    viewport_height: int = 720

    # Slow motion delay in ms (useful for debugging)
    slow_mo: int = 0

    # Session persistence directory (FR-023)
    sessions_dir: Path = field(default_factory=lambda: Path(".browser-sessions"))

    # Enable session persistence
    persist_session: bool = True

    # Page load timeout in ms
    page_load_timeout: int = 30000

    # Navigation timeout in ms
    navigation_timeout: int = 30000

    @classmethod
    def from_env(cls) -> "BrowserConfig":
        """
        Create BrowserConfig from environment variables.

        Environment variables:
            BROWSER_TYPE: chromium, firefox, or webkit (default: chromium)
            BROWSER_HEADLESS: true/false (default: false)
            BROWSER_VIEWPORT_WIDTH: int (default: 1280)
            BROWSER_VIEWPORT_HEIGHT: int (default: 720)
            BROWSER_SLOW_MO: int in ms (default: 0)
            SESSIONS_DIR: path (default: .browser-sessions)
            SESSION_PERSIST: true/false (default: true)
            PAGE_LOAD_TIMEOUT: int in ms (default: 30000)
        """
        # Map config browser type to Playwright's expected values
        env_type = os.getenv("BROWSER_TYPE", "chrome").lower()
        browser_type_map = {
            "chrome": "chromium",
            "chromium": "chromium",
            "firefox": "firefox",
            "webkit": "webkit",
            "safari": "webkit",
        }
        browser_type = browser_type_map.get(env_type, "chromium")

        headless_str = os.getenv("BROWSER_HEADLESS", "false").lower()
        headless = headless_str in ("true", "1", "yes")

        persist_str = os.getenv("SESSION_PERSIST", "true").lower()
        persist = persist_str in ("true", "1", "yes")

        return cls(
            browser_type=browser_type,
            headless=headless,
            viewport_width=int(os.getenv("BROWSER_VIEWPORT_WIDTH", "1280")),
            viewport_height=int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "720")),
            slow_mo=int(os.getenv("BROWSER_SLOW_MO", "0")),
            sessions_dir=Path(os.getenv("SESSIONS_DIR", ".browser-sessions")),
            persist_session=persist,
            page_load_timeout=int(os.getenv("PAGE_LOAD_TIMEOUT", "30000")),
            navigation_timeout=int(os.getenv("NAVIGATION_TIMEOUT", "30000")),
        )


class BrowserController:
    """
    Controls the Playwright browser instance.

    Provides high-level browser management including:
    - Browser initialization and cleanup
    - Session persistence (FR-023)
    - Page management
    - Visible browser mode (FR-001)

    Usage:
        >>> async with BrowserController.create() as browser:
        ...     page = await browser.new_page()
        ...     await page.goto("https://example.com")
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialize browser controller.

        Args:
            config: Browser configuration (uses env if None)
        """
        self.config = config or BrowserConfig.from_env()

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._pages: list[Page] = []

    @property
    def is_initialized(self) -> bool:
        """Check if browser is initialized."""
        return self._browser is not None

    @property
    def current_page(self) -> Optional[Page]:
        """Get the most recently created page."""
        if self._pages:
            return self._pages[-1]
        return None

    async def initialize(self) -> None:
        """
        Initialize Playwright and launch browser.

        Creates a persistent context if session persistence is enabled.
        """
        if self._playwright is not None:
            return

        # Start Playwright
        self._playwright = await async_playwright().start()

        # Get browser launcher
        launcher = self._get_browser_launcher()

        # Prepare launch options
        launch_options = {
            "headless": self.config.headless,
            "slow_mo": self.config.slow_mo,
        }

        if self.config.persist_session:
            # Use persistent context for session persistence (FR-023)
            self.config.sessions_dir.mkdir(parents=True, exist_ok=True)
            user_data_dir = str(self.config.sessions_dir / self.config.browser_type)

            self._context = await launcher.launch_persistent_context(
                user_data_dir,
                **launch_options,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )
            # Get existing pages or create new one
            if self._context.pages:
                self._pages = list(self._context.pages)
            else:
                page = await self._context.new_page()
                self._pages.append(page)
        else:
            # Launch browser without persistence
            self._browser = await launcher.launch(**launch_options)
            self._context = await self._browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )
            page = await self._context.new_page()
            self._pages.append(page)

        # Set default timeouts
        if self._context:
            self._context.set_default_timeout(self.config.page_load_timeout)
            self._context.set_default_navigation_timeout(
                self.config.navigation_timeout
            )

    def _get_browser_launcher(self):
        """Get the appropriate browser launcher based on config."""
        if self._playwright is None:
            raise RuntimeError("Playwright not initialized")

        launchers = {
            "chromium": self._playwright.chromium,
            "firefox": self._playwright.firefox,
            "webkit": self._playwright.webkit,
        }
        return launchers.get(self.config.browser_type, self._playwright.chromium)

    async def new_page(self) -> Page:
        """
        Create a new browser page.

        Returns:
            New Playwright Page instance
        """
        if self._context is None:
            await self.initialize()

        page = await self._context.new_page()
        self._pages.append(page)
        return page

    async def close_page(self, page: Optional[Page] = None) -> None:
        """
        Close a specific page or the current page.

        Args:
            page: Page to close (current page if None)
        """
        target = page or self.current_page
        if target:
            await target.close()
            if target in self._pages:
                self._pages.remove(target)

    async def close(self) -> None:
        """Close the browser and cleanup resources."""
        for page in self._pages[:]:
            try:
                await page.close()
            except Exception:
                pass
        self._pages.clear()

        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    async def __aenter__(self) -> "BrowserController":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    @classmethod
    async def create(cls, config: Optional[BrowserConfig] = None) -> "BrowserController":
        """
        Factory method to create and initialize a browser controller.

        Args:
            config: Browser configuration (uses env if None)

        Returns:
            Initialized BrowserController instance
        """
        controller = cls(config)
        await controller.initialize()
        return controller


def create_browser(config: Optional[BrowserConfig] = None) -> BrowserController:
    """
    Factory function to create a browser controller.

    Use with async context manager:
        >>> async with create_browser() as browser:
        ...     page = browser.current_page
        ...     await page.goto("https://example.com")

    Args:
        config: Browser configuration (uses env if None)

    Returns:
        BrowserController instance (not yet initialized)
    """
    return BrowserController(config)
