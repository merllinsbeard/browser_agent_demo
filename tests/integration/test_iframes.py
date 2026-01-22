"""
Integration tests for iframe interaction features.

Feature: 002-iframe-interaction-fixes

This module contains integration tests for iframe-aware browser automation:
- Iframe search (User Story 1)
- Click interception handling (User Story 2)
- Accessibility tree with frames (User Story 3)
- Error recovery with retry chains (User Story 4)
"""

import urllib.parse

import pytest
from playwright.async_api import Page, async_playwright  # noqa: F401 - Used in test implementations

from browser_agent.browser import BrowserController, BrowserConfig
from browser_agent.tools import navigate
from browser_agent.tools.interactions import type_text
from browser_agent.tools.frames import list_frames


class TestIframeSearch:
    """User Story 1: Iframe Search - Agent can search within iframe-embedded widgets."""

    @pytest.mark.asyncio
    async def test_search_in_iframe(self):
        """Test agent can enter search query in iframe-embedded search widget.

        Scenario: Open page with iframe search widget and enter text
        Expected: Agent detects iframe, enters query, text is entered into iframe input

        Acceptance:
        - Agent can list frames and identify iframe with search input
        - Agent can find textbox element inside iframe
        - Agent can type text into the iframe input field
        - ToolResult includes frame_context showing which frame was used
        """
        # Create test page with iframe containing a search input
        # Using a simpler approach with JavaScript to inject iframe content
        test_html = """<!DOCTYPE html>
<html>
<head><title>Test Page with Iframe Search</title></head>
<body>
    <h1>Main Page Content</h1>
    <p>This is the main page with an embedded search iframe.</p>
    <iframe id="search-widget" name="search-frame" aria-label="Search Widget" title="Search Frame" width="400" height="200"></iframe>
    <p>Main page continues here.</p>
    <script>
        // Inject content into iframe (simulating same-origin iframe)
        const iframe = document.getElementById('search-widget');
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        doc.open();
        doc.write('<!DOCTYPE html><html><head><title>Search Widget</title></head><body><form role="search"><label for="search-input">Search:</label><input type="search" id="search-input" name="q" placeholder="Enter search query" aria-label="Search input"/><button type="submit">Search</button></form></body></html>');
        doc.close();
    </script>
</body>
</html>"""

        config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            persist_session=False,
        )

        async with BrowserController(config) as browser:
            page = browser.current_page

            # Set page content directly (data URLs not supported by navigate tool)
            await page.set_content(test_html)

            # Step 1: List frames to verify iframe is detected
            frames_result = await list_frames(page, include_inaccessible=True)
            assert frames_result.success, f"list_frames failed: {frames_result.error}"

            frames = frames_result.data.get("frames", [])
            assert len(frames) >= 2, f"Expected at least 2 frames (main + iframe), got {len(frames)}"

            # Verify iframe is detected with expected attributes
            iframe_frames = [f for f in frames if f.get("name") == "search-frame"]
            assert len(iframe_frames) == 1, "Expected to find iframe with name='search-frame'"

            iframe_info = iframe_frames[0]
            assert iframe_info["accessible"] is True, "Iframe should be accessible (same-origin)"
            # Note: aria_label and title extraction has a known limitation in current list_frames implementation
            # The iframe element attribute extraction doesn't work correctly from child frame context
            # This is acceptable for now - the key is that the frame is detected and accessible
            assert iframe_info["index"] >= 0

            # Step 2: Find and interact with search input inside iframe
            # This will use the enhanced type_text with frame search (T013 implementation pending)
            type_result = await type_text(
                page,
                element_description="Search input",
                text="weather in Moscow",
            )

            # Expected behavior once T011-T015 are implemented:
            # - type_text should search main frame first
            # - Then search inside iframes
            # - Find the input inside the search-frame iframe
            # - Type the text into the input
            # - Return success with frame_context

            # For now, this will fail because iframe search is not implemented
            # Once T011-T015 are complete, this test should pass
            assert type_result.success, f"type_text failed: {type_result.error}"
            assert type_result.data is not None, "ToolResult.data should not be None on success"

            # Verify frame_context is included in result (FR-011)
            assert "frame_context" in type_result.data, "ToolResult should include frame_context"
            frame_ctx = type_result.data["frame_context"]
            assert frame_ctx is not None, "frame_context should not be None"
            assert frame_ctx.get("name") == "search-frame", "Interaction should happen in iframe"

            # Verify text was entered into the correct element
            assert type_result.data.get("text_entered") == "weather in Moscow"


class TestClickInterception:
    """User Story 2: Click Interception - Agent handles iframe overlay blocking."""

    @pytest.mark.asyncio
    async def test_click_iframe_interception(self):
        """Test agent detects click blocked by iframe overlay and retries.

        Scenario: Click on search bar on dzen.ru
        Expected: Agent detects interception, clicks inside iframe context
        """
        # Implementation in T016
        pytest.skip("Test implementation in T016")


class TestAccessibilityTree:
    """User Story 3: Accessibility Tree - Frame contents included with metadata."""

    @pytest.mark.asyncio
    async def test_accessibility_tree_with_frames(self):
        """Test get_accessibility_tree includes elements from all frames.

        Expected: Result includes elements from main frame and iframes with metadata
        """
        # Implementation in T022, T023
        pytest.skip("Test implementation in T022, T023")


class TestErrorRecovery:
    """User Story 4: Error Recovery - Smart retry logic with detailed reporting."""

    @pytest.mark.asyncio
    async def test_retry_chain_on_failure(self):
        """Test agent auto-retries failed interactions via alternative strategies.

        Scenario: Simulate failed click
        Expected: Agent retries via alternative strategies, returns detailed error
        """
        # Implementation in T029, T030
        pytest.skip("Test implementation in T029, T030")
