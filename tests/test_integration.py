"""
Integration Tests

Tests for User Story 1 acceptance scenarios and TUI functionality.

T043: Simple navigation task
T044: Wikipedia search task
T045: Data extraction from arbitrary page
T046: TUI shows all actions in real-time
T047: Time to first action < 5 seconds
"""

import time
from unittest.mock import MagicMock

import pytest

from browser_agent.browser import BrowserController, BrowserConfig
from browser_agent.tools import navigate, get_accessibility_tree, get_page_text
from browser_agent.tools.interactions import type_text
from browser_agent.agents.planner import create_planner
from browser_agent.agents.executor import create_executor
from browser_agent.tui import get_console


# ============================================================================
# T043: Test simple navigation task
# ============================================================================


@pytest.mark.asyncio
async def test_navigate_to_example_com():
    """
    Test simple navigation to example.com.

    Verifies:
    - Browser launches successfully
    - Navigation tool works
    - Page loads with expected content
    """
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,  # Use headless for tests
        persist_session=False,
    )

    async with BrowserController(config) as browser:
        page = browser.current_page

        # Navigate to example.com
        result = await navigate(page, url="https://example.com")

        assert result.success, f"Navigation failed: {result.error}"
        assert result.data is not None
        assert "example.com" in result.data.get("url", "").lower()


@pytest.mark.asyncio
@pytest.mark.xfail(reason="accessibility API needs Playwright fix - page.accessibility deprecated")
async def test_navigate_and_get_title():
    """
    Test navigation with title extraction.
    """
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        persist_session=False,
    )

    async with BrowserController(config) as browser:
        page = browser.current_page

        # Navigate
        result = await navigate(page, url="https://example.com")
        assert result.success

        # Get title from accessibility tree
        tree_result = await get_accessibility_tree(page)
        assert tree_result.success

        tree = tree_result.data
        assert "title" in tree
        assert "Example" in tree["title"]


# ============================================================================
# T044: Test Wikipedia search task
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.xfail(reason="type_text depends on accessibility tree for element finding")
async def test_wikipedia_search():
    """
    Test Wikipedia search flow.

    Verifies:
    - Navigation to Wikipedia
    - Text input into search box
    - Search form submission
    """
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        persist_session=False,
    )

    async with BrowserController(config) as browser:
        page = browser.current_page

        # Navigate to Wikipedia
        nav_result = await navigate(page, url="https://en.wikipedia.org")
        assert nav_result.success, f"Navigation failed: {nav_result.error}"

        # Type in search box
        type_result = await type_text(
            page,
            element_description="search input",
            text="Python programming",
            press_enter=True,
        )
        assert type_result.success, f"Type failed: {type_result.error}"

        # Wait for results page
        await page.wait_for_load_state("networkidle")

        # Verify we're on search results or article page
        url = page.url.lower()
        assert "python" in url or "search" in url


# ============================================================================
# T045: Test data extraction from arbitrary page
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.xfail(reason="accessibility tree API needs Playwright fix")
async def test_data_extraction():
    """
    Test extracting text content from a page.

    Verifies:
    - Page text extraction works
    - Accessibility tree contains meaningful elements
    """
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        persist_session=False,
    )

    async with BrowserController(config) as browser:
        page = browser.current_page

        # Navigate to example.com (simple structure)
        await navigate(page, url="https://example.com")

        # Extract page text
        text_result = await get_page_text(page)
        assert text_result.success
        assert "Example Domain" in text_result.data.get("text", "")

        # Get accessibility tree
        tree_result = await get_accessibility_tree(page)
        assert tree_result.success

        tree = tree_result.data
        assert "elements" in tree
        assert len(tree["elements"]) > 0


# ============================================================================
# T046: Verify TUI shows all actions in real-time
# ============================================================================


def test_tui_console_initialized():
    """
    Test that TUI console is properly initialized.
    """
    console = get_console()
    assert console is not None
    assert console.console is not None


def test_tui_thought_block():
    """
    Test thought block display.
    """
    from browser_agent.tui import print_thought

    # Should not raise
    print_thought("This is a test thought", step=1, total_steps=3)


def test_tui_action_block():
    """
    Test action block display.
    """
    from browser_agent.tui import print_action

    # Should not raise
    print_action("click", params={"element": "button"})


def test_tui_result_block():
    """
    Test result block display.
    """
    from browser_agent.tui import print_result

    # Should not raise
    print_result("Action completed successfully", success=True)
    print_result("Action failed", success=False)


# ============================================================================
# T047: Measure time to first action < 5 seconds
# ============================================================================


@pytest.mark.asyncio
async def test_time_to_first_action():
    """
    Test that first action executes within 5 seconds.

    Measures time from browser launch to first navigation.
    """
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        persist_session=False,
    )

    start_time = time.time()

    async with BrowserController(config) as browser:
        page = browser.current_page

        # First action: navigate
        result = await navigate(page, url="https://example.com")

        first_action_time = time.time() - start_time

        assert result.success, f"Navigation failed: {result.error}"
        assert first_action_time < 5.0, (
            f"First action took {first_action_time:.2f}s, expected < 5s"
        )


@pytest.mark.asyncio
async def test_executor_creation_speed():
    """
    Test that executor can be created quickly.
    """
    async def mock_execute_tool(name: str, args: dict):
        return MagicMock(success=True, data={})

    start_time = time.time()
    executor = create_executor(execute_tool=mock_execute_tool, verbose=False)
    creation_time = time.time() - start_time

    assert executor is not None
    assert creation_time < 0.1, f"Executor creation took {creation_time:.2f}s"


# ============================================================================
# Planner integration test
# ============================================================================


@pytest.mark.asyncio
async def test_planner_initialization():
    """
    Test planner can be initialized with mock LLM.
    """
    async def mock_llm(prompt: str, messages: list) -> dict:
        return {"content": "<thought>Test thought</thought>\n<action>navigate</action>"}

    planner = create_planner(
        llm_complete=mock_llm,
        max_iterations=1,
        verbose=False,
    )

    assert planner is not None
    assert planner.config.max_iterations == 1
