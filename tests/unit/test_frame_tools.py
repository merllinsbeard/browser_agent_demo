"""
Unit tests for iframe tool utilities.

Feature: 002-iframe-interaction-fixes

This module contains unit tests for frame tool utilities:
- Element finding across frames
- Frame prioritization logic
- Retry chain state machine
- Coordinate click fallback
- Structured error responses
"""

import pytest
from browser_agent.tools.frame_models import (
    FrameContext,
    FrameLocatorResult,
    InteractionAttempt,
    RetryChain,
)


class TestFrameModels:
    """Test Pydantic model validation and serialization."""

    def test_frame_context_validation(self):
        """Test FrameContext model validation rules."""
        # Valid frame context
        frame = FrameContext(
            name="search-frame",
            index=1,
            src="https://example.com/frame",
            aria_label="Search",
            title="Search Widget",
            accessible=True,
        )
        assert frame.index == 1
        assert frame.accessible is True

    def test_frame_context_default_values(self):
        """Test FrameContext default values."""
        frame = FrameContext(index=0)
        assert frame.accessible is True  # Default
        assert frame.name is None
        assert frame.src is None

    def test_frame_locator_result_validation(self):
        """Test FrameLocatorResult model validation."""
        frame = FrameContext(index=0)
        result = FrameLocatorResult(
            found=True,
            frame_context=frame,
            locator_description="Search button",
            search_strategy="get_by_role",
            confidence_score=0.95,
        )
        assert result.found is True
        assert result.confidence_score == 0.95

    def test_interaction_attempt_validation(self):
        """Test InteractionAttempt model validation."""
        attempt = InteractionAttempt(
            strategy="main_frame",
            success=False,
            duration_ms=1500,
            error="Element not found",
        )
        assert attempt.success is False
        assert attempt.duration_ms == 1500
        assert attempt.error == "Element not found"

    def test_retry_chain_initialization(self):
        """Test RetryChain model initialization."""
        chain = RetryChain(
            strategies=["main_frame", "iframe_0", "coordinate_click"],
            max_attempts=3,
        )
        assert len(chain.strategies) == 3
        assert chain.current_index == 0
        assert chain.max_attempts == 3
        assert len(chain.attempts) == 0


class TestFindElementInAllFrames:
    """Test _find_element_in_all_frames utility (T010)."""

    @pytest.mark.asyncio
    async def test_find_element_in_main_frame(self):
        """Test element found in main frame when element exists there."""
        from browser_agent.tools.interactions import _find_element_in_all_frames
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with element in main frame
            await page.set_content("""
                <html>
                <body>
                    <input type="text" aria-label="Search input" placeholder="Search..." />
                </body>
                </html>
            """)

            # Search for element
            result = await _find_element_in_all_frames(page, "Search input")

            # Verify element found in main frame
            assert result.found is True
            assert result.frame_context is not None
            assert result.frame_context.index == 0  # Main frame
            assert result.locator is not None

            await browser.close()

    @pytest.mark.asyncio
    async def test_find_element_in_iframe(self):
        """Test element found in iframe when not in main frame."""
        from browser_agent.tools.interactions import _find_element_in_all_frames
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with iframe containing the element
            await page.set_content("""
                <html>
                <body>
                    <p>Main page content</p>
                    <iframe id="search-widget" name="search-frame" aria-label="Search Widget"></iframe>
                    <script>
                        const iframe = document.getElementById('search-widget');
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        doc.open();
                        doc.write('<html><body><input type="search" aria-label="Search input" placeholder="Search..."/></body></html>');
                        doc.close();
                    </script>
                </body>
                </html>
            """)

            # Search for element
            result = await _find_element_in_all_frames(page, "Search input")

            # Verify element found in iframe
            assert result.found is True
            assert result.frame_context is not None
            assert result.frame_context.name == "search-frame"
            assert result.frame_context.index > 0  # Not main frame
            assert result.locator is not None

            await browser.close()

    @pytest.mark.asyncio
    async def test_frame_prioritization_order(self):
        """Test frames are searched in priority order (main -> semantic -> non-semantic)."""
        from browser_agent.tools.interactions import _find_element_in_all_frames
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with multiple iframes, element in main frame
            await page.set_content("""
                <html>
                <body>
                    <input type="text" aria-label="Search box" />
                    <iframe name="frame1" title="Frame 1"></iframe>
                    <iframe name="frame2" aria-label="Important Frame"></iframe>
                    <script>
                        // Inject content into frame1
                        const f1 = document.getElementsByName('frame1')[0];
                        const d1 = f1.contentDocument || f1.contentWindow.document;
                        d1.open();
                        d1.write('<html><body><input aria-label="Search box"/></body></html>');
                        d1.close();

                        // Inject content into frame2
                        const f2 = document.getElementsByName('frame2')[0];
                        const d2 = f2.contentDocument || f2.contentWindow.document;
                        d2.open();
                        d2.write('<html><body><input aria-label="Search box"/></body></html>');
                        d2.close();
                    </script>
                </body>
                </html>
            """)

            # Search for element
            result = await _find_element_in_all_frames(page, "Search box")

            # Verify main frame is searched first (should find there)
            assert result.found is True
            assert result.frame_context.index == 0  # Main frame

            await browser.close()

    @pytest.mark.asyncio
    async def test_element_not_found(self):
        """Test returns not found when element doesn't exist in any frame."""
        from browser_agent.tools.interactions import _find_element_in_all_frames
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page without the target element
            await page.set_content("""
                <html>
                <body>
                    <p>Some content</p>
                </body>
                </html>
            """)

            # Search for non-existent element
            result = await _find_element_in_all_frames(page, "Non-existent input")

            # Verify not found
            assert result.found is False
            assert result.frame_context is None
            assert result.locator is None
            assert result.search_strategy is not None

            await browser.close()

    @pytest.mark.asyncio
    async def test_cross_origin_frame_handling(self):
        """Test cross-origin frames are skipped gracefully."""
        from browser_agent.tools.interactions import _find_element_in_all_frames
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with same-origin element and cross-origin iframe reference
            await page.set_content("""
                <html>
                <body>
                    <input type="text" aria-label="Search input" />
                    <iframe src="https://example.com/external" name="external-frame"></iframe>
                </body>
                </html>
            """)

            # Search for element
            result = await _find_element_in_all_frames(page, "Search input")

            # Verify element found in main frame despite cross-origin iframe
            assert result.found is True
            assert result.frame_context.index == 0
            assert result.locator is not None

            await browser.close()

    @pytest.mark.asyncio
    async def test_semantic_frame_priority(self):
        """Test aria-label frames have higher priority than non-semantic frames."""
        from browser_agent.tools.interactions import _find_element_in_all_frames
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page where element is in aria-labeled iframe
            await page.set_content("""
                <html>
                <body>
                    <iframe name="plain-frame"></iframe>
                    <iframe name="search-frame" aria-label="Search Widget"></iframe>
                    <script>
                        // Element in plain frame
                        const f1 = document.getElementsByName('plain-frame')[0];
                        const d1 = f1.contentDocument || f1.contentWindow.document;
                        d1.open();
                        d1.write('<html><body><input aria-label="Search box"/></body></html>');
                        d1.close();

                        // Element in semantic frame
                        const f2 = document.getElementsByName('search-frame')[0];
                        const d2 = f2.contentDocument || f2.contentWindow.document;
                        d2.open();
                        d2.write('<html><body><input aria-label="Search box"/></body></html>');
                        d2.close();
                    </script>
                </body>
                </html>
            """)

            # Search for element
            result = await _find_element_in_all_frames(page, "Search box")

            # Verify semantic frame is prioritized (should find there first)
            assert result.found is True
            assert result.frame_context.aria_label == "Search Widget"
            assert result.frame_context.name == "search-frame"

            await browser.close()


class TestCoordinateClick:
    """Test coordinate_click fallback mechanism (T017).

    FR-024: coordinate_click fallback MUST get element bounding box,
    calculate center coordinates, and click at those x,y coordinates.
    """

    @pytest.mark.asyncio
    async def test_coordinate_click_calculates_center(self):
        """Test coordinate_click calculates correct center from bounding box."""
        from browser_agent.tools.interactions import coordinate_click
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with a button at known position
            await page.set_content("""
                <html>
                <body style="margin: 0; padding: 0;">
                    <button id="test-btn" style="
                        position: absolute;
                        left: 100px;
                        top: 50px;
                        width: 200px;
                        height: 40px;
                    ">Click Me</button>
                    <div id="result"></div>
                    <script>
                        document.getElementById('test-btn').addEventListener('click', function(e) {
                            document.getElementById('result').textContent = 'clicked';
                        });
                    </script>
                </body>
                </html>
            """)

            # Get the button locator
            button = page.locator("#test-btn")

            # Call coordinate_click
            result = await coordinate_click(page, button)

            # Verify click succeeded
            assert result.success is True
            assert result.data.get("method") == "coordinate_click"
            assert "center_x" in result.data
            assert "center_y" in result.data

            # Verify the click actually happened (check DOM state)
            result_text = await page.locator("#result").text_content()
            assert result_text == "clicked"

            await browser.close()

    @pytest.mark.asyncio
    async def test_coordinate_click_returns_coordinates(self):
        """Test coordinate_click returns the calculated coordinates in result data."""
        from browser_agent.tools.interactions import coordinate_click
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.set_content("""
                <html>
                <body style="margin: 0; padding: 0;">
                    <button id="test-btn" style="
                        position: absolute;
                        left: 100px;
                        top: 50px;
                        width: 200px;
                        height: 40px;
                    ">Click Me</button>
                </body>
                </html>
            """)

            button = page.locator("#test-btn")
            result = await coordinate_click(page, button)

            # Verify result contains coordinate information
            assert result.success is True
            # Center should be at approximately (200, 70) based on position
            # left=100, width=200 => center_x = 100 + 200/2 = 200
            # top=50, height=40 => center_y = 50 + 40/2 = 70
            assert abs(result.data["center_x"] - 200) < 5  # Allow small margin
            assert abs(result.data["center_y"] - 70) < 5

            await browser.close()

    @pytest.mark.asyncio
    async def test_coordinate_click_handles_no_bounding_box(self):
        """Test coordinate_click handles elements with no bounding box."""
        from browser_agent.tools.interactions import coordinate_click
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with hidden element (no bounding box)
            await page.set_content("""
                <html>
                <body>
                    <button id="hidden-btn" style="display: none;">Hidden</button>
                </body>
                </html>
            """)

            button = page.locator("#hidden-btn")
            result = await coordinate_click(page, button)

            # Should fail gracefully with error message
            assert result.success is False
            assert "bounding box" in result.error.lower() or "hidden" in result.error.lower()

            await browser.close()

    @pytest.mark.asyncio
    async def test_coordinate_click_handles_element_outside_viewport(self):
        """Test coordinate_click scrolls to element if needed."""
        from browser_agent.tools.interactions import coordinate_click
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_viewport_size({"width": 800, "height": 600})

            # Create page with element far below viewport
            await page.set_content("""
                <html>
                <body style="margin: 0; height: 2000px;">
                    <button id="far-btn" style="
                        position: absolute;
                        left: 100px;
                        top: 1500px;
                        width: 100px;
                        height: 40px;
                    ">Far Button</button>
                    <div id="result"></div>
                    <script>
                        document.getElementById('far-btn').addEventListener('click', function() {
                            document.getElementById('result').textContent = 'clicked';
                        });
                    </script>
                </body>
                </html>
            """)

            button = page.locator("#far-btn")
            result = await coordinate_click(page, button)

            # Should succeed after scrolling element into view
            assert result.success is True
            result_text = await page.locator("#result").text_content()
            assert result_text == "clicked"

            await browser.close()

    @pytest.mark.asyncio
    async def test_coordinate_click_with_frame_context(self):
        """Test coordinate_click includes frame context when clicking in iframe."""
        from browser_agent.tools.interactions import coordinate_click
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with iframe containing a button
            await page.set_content("""
                <html>
                <body style="margin: 0; padding: 0;">
                    <iframe id="test-frame" name="test-frame" style="width: 400px; height: 200px; border: none;"></iframe>
                    <script>
                        const iframe = document.getElementById('test-frame');
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        doc.open();
                        doc.write(`
                            <html>
                            <body style="margin: 0; padding: 0;">
                                <button id="iframe-btn" style="
                                    position: absolute;
                                    left: 50px;
                                    top: 30px;
                                    width: 100px;
                                    height: 30px;
                                ">Iframe Button</button>
                                <div id="result"></div>
                                <script>
                                    document.getElementById('iframe-btn').addEventListener('click', function() {
                                        document.getElementById('result').textContent = 'iframe-clicked';
                                    });
                                <\/script>
                            </body>
                            </html>
                        `);
                        doc.close();
                    </script>
                </body>
                </html>
            """)

            # Get button locator from iframe
            frame = page.frame(name="test-frame")
            assert frame is not None
            button = frame.locator("#iframe-btn")

            # Use coordinate_click with the frame
            result = await coordinate_click(page, button, frame=frame)

            # Should succeed and include frame context
            assert result.success is True
            assert result.data.get("method") == "coordinate_click"

            # Verify click actually happened in iframe
            result_text = await frame.locator("#result").text_content()
            assert result_text == "iframe-clicked"

            await browser.close()

    @pytest.mark.asyncio
    async def test_coordinate_click_uses_mouse_click(self):
        """Test coordinate_click uses page.mouse.click for the actual click."""
        from browser_agent.tools.interactions import coordinate_click
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page that records click coordinates
            await page.set_content("""
                <html>
                <body style="margin: 0; padding: 0;">
                    <div id="target" style="
                        position: absolute;
                        left: 50px;
                        top: 50px;
                        width: 100px;
                        height: 100px;
                        background: red;
                    "></div>
                    <div id="coords"></div>
                    <script>
                        document.addEventListener('click', function(e) {
                            document.getElementById('coords').textContent = e.clientX + ',' + e.clientY;
                        });
                    </script>
                </body>
                </html>
            """)

            target = page.locator("#target")
            result = await coordinate_click(page, target)

            assert result.success is True

            # Verify click was at center (50+50=100, 50+50=100)
            coords_text = await page.locator("#coords").text_content()
            click_x, click_y = map(int, coords_text.split(","))

            # Center of 100x100 div at (50, 50) should be (100, 100)
            assert abs(click_x - 100) < 5
            assert abs(click_y - 100) < 5

            await browser.close()


class TestRetryChainStateMachine:
    """Test RetryChain state machine progression (T029)."""

    def test_retry_chain_state_machine(self):
        """Test retry chain advances through strategies correctly."""
        # Implementation in T029
        pytest.skip("Test implementation in T029")


class TestStructuredErrorResponse:
    """Test structured error response format (T030)."""

    def test_structured_error_response(self):
        """Test error includes all attempts in response."""
        # Implementation in T030
        pytest.skip("Test implementation in T030")


class TestFramePrioritization:
    """Test frame prioritization logic (T005)."""

    def test_frame_prioritization(self):
        """Test frames prioritized by semantic labeling."""
        from browser_agent.tools.frames import _prioritize_frames

        # Create test frames
        frames = [
            FrameContext(index=0),  # Main frame
            FrameContext(index=2, name="frame2"),  # Has name
            FrameContext(index=3, aria_label="Search"),  # Has aria-label (highest priority)
            FrameContext(index=1, title="Widget"),  # Has title
            FrameContext(index=4),  # No semantic label
        ]

        # Prioritize frames
        prioritized = _prioritize_frames(frames)

        # Verify main frame is first
        assert prioritized[0].index == 0

        # Verify aria-label frame comes before title frame
        assert prioritized[1].aria_label == "Search"
        assert prioritized[1].index == 3

        # Verify title frame comes before name frame
        assert prioritized[2].title == "Widget"
        assert prioritized[2].index == 1

        # Verify name frame comes before non-semantic frame
        assert prioritized[3].name == "frame2"
        assert prioritized[3].index == 2

        # Verify non-semantic frame is last
        assert prioritized[4].index == 4
        assert prioritized[4].aria_label is None
        assert prioritized[4].title is None
        assert prioritized[4].name is None

    def test_frame_prioritization_filters_inaccessible(self):
        """Test inaccessible frames are filtered when include_inaccessible=False."""
        from browser_agent.tools.frames import _prioritize_frames

        frames = [
            FrameContext(index=0, accessible=True),
            FrameContext(index=1, accessible=False),
            FrameContext(index=2, aria_label="Search", accessible=True),
        ]

        # Without inaccessible frames
        prioritized = _prioritize_frames(frames, include_inaccessible=False)
        assert len(prioritized) == 2
        assert all(f.accessible for f in prioritized)

        # With inaccessible frames
        prioritized = _prioritize_frames(frames, include_inaccessible=True)
        assert len(prioritized) == 3


class TestDynamicIframeWaiting:
    """Test dynamic iframe waiting mechanism (T006)."""

    @pytest.mark.asyncio
    async def test_dynamic_iframe_wait(self):
        """Test dynamic iframe polling with timeout."""
        from browser_agent.tools.frames import _wait_for_dynamic_iframes
        from playwright.async_api import async_playwright

        # Test with real browser (brief test)
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Navigate to simple page
            await page.goto("about:blank")

            # Wait for frames (should return immediately with just main frame)
            frames = await _wait_for_dynamic_iframes(page, timeout_ms=1000)
            assert len(frames) >= 1  # At least main frame

            await browser.close()

    @pytest.mark.asyncio
    async def test_dynamic_iframe_wait_with_expected_count(self):
        """Test waiting until expected frame count is reached."""
        from browser_agent.tools.frames import _wait_for_dynamic_iframes
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("about:blank")

            # Expect at least 1 frame (should return immediately)
            frames = await _wait_for_dynamic_iframes(
                page,
                timeout_ms=1000,
                expected_count=1,
            )
            assert len(frames) >= 1

            await browser.close()


class TestCrossOriginDetection:
    """Test cross-origin frame detection with warning logging (T007)."""

    @pytest.mark.asyncio
    async def test_cross_origin_detection(self):
        """Test cross-origin iframe detection with warning logging."""
        from browser_agent.tools.frames import is_cross_origin_frame
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("about:blank")

            # Main frame should not be cross-origin
            main_frame = page.main_frame
            assert not is_cross_origin_frame(main_frame)

            await browser.close()

    @pytest.mark.asyncio
    async def test_skip_cross_origin_frames_gracefully(self):
        """Test graceful skipping of cross-origin frames."""
        from browser_agent.tools.frames import skip_cross_origin_frames_gracefully
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto("about:blank")

            # All frames on same-origin page should be accessible
            frames = await skip_cross_origin_frames_gracefully(page.frames)
            assert len(frames) >= 1  # At least main frame

            await browser.close()


class TestRecursiveAccessibilityTree:
    """Test recursive frame traversal (T022)."""

    def test_recursive_accessibility_tree(self):
        """Test accessibility tree merges nested frames."""
        # Implementation in T022
        pytest.skip("Test implementation in T022")


class TestFrameMetadataFormat:
    """Test frame metadata markers in tree (T023)."""

    def test_frame_metadata_format(self):
        """Test frame context markers in accessibility output."""
        # Implementation in T023
        pytest.skip("Test implementation in T023")


class TestIframeInterceptionDetection:
    """Test iframe interception detection on TimeoutError (T020)."""

    @pytest.mark.asyncio
    async def test_detect_iframe_covering_element(self):
        """Test detection when iframe covers element."""
        from browser_agent.tools.interactions import _detect_iframe_interception
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with button covered by iframe
            await page.set_content(
                """
                <button id="covered-btn" style="position: absolute; top: 100px; left: 100px; width: 100px; height: 50px;">
                    Covered Button
                </button>
                <iframe id="overlay-iframe" style="position: absolute; top: 50px; left: 50px; width: 200px; height: 150px; z-index: 10;"
                        srcdoc="<div>Overlay Content</div>">
                </iframe>
            """
            )

            # Get locator for covered button
            button = page.locator("#covered-btn")
            await button.wait_for(state="attached")

            # Detect interception
            interception = await _detect_iframe_interception(page, button)

            # Should detect iframe interception
            assert interception is not None
            assert interception.index == 1
            assert interception.name == "overlay-iframe"
            assert interception.accessible is True

            await browser.close()

    @pytest.mark.asyncio
    async def test_no_interception_when_no_iframe_covers(self):
        """Test no false positives when element is not covered."""
        from browser_agent.tools.interactions import _detect_iframe_interception
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with button and non-overlapping iframe
            await page.set_content(
                """
                <button id="visible-btn" style="position: absolute; top: 100px; left: 100px;">
                    Visible Button
                </button>
                <iframe id="separate-iframe" style="position: absolute; top: 500px; left: 500px;"
                        srcdoc="<div>Separate Content</div>">
                </iframe>
            """
            )

            # Get locator for visible button
            button = page.locator("#visible-btn")
            await button.wait_for(state="attached")

            # Detect interception
            interception = await _detect_iframe_interception(page, button)

            # Should NOT detect interception (button is not covered)
            assert interception is None

            await browser.close()

    @pytest.mark.asyncio
    async def test_no_interception_for_hidden_element(self):
        """Test edge case for hidden elements with no bounding box."""
        from browser_agent.tools.interactions import _detect_iframe_interception
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Create page with hidden element
            await page.set_content(
                """
                <button id="hidden-btn" style="display: none;">
                    Hidden Button
                </button>
                <iframe id="overlay-iframe" style="position: absolute; top: 0; left: 0;"
                        srcdoc="<div>Overlay Content</div>">
                </iframe>
            """
            )

            # Get locator for hidden button
            button = page.locator("#hidden-btn")

            # Detect interception
            interception = await _detect_iframe_interception(page, button)

            # Should return None (hidden element has no bounding box)
            assert interception is None

            await browser.close()
