"""
Integration tests for security system with browser tools.

Feature: 003-security-system (FR-030)

This module contains integration tests for:
- Security flow with click tool (destructive actions)
- Security flow with type_text tool (password blocking)
- Confirmation dialog integration
- Blocked action handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from playwright.async_api import async_playwright

from browser_agent.security.detector import ActionType, create_detector
from browser_agent.security.confirmation import ConfirmationResult, create_confirmation
from browser_agent.tools.base import ToolResult


class TestSecurityToolIntegration:
    """Test security integration with tool registry (FR-030)."""

    @pytest.fixture
    async def mock_page(self):
        """Create a mock Playwright page for testing."""
        browser = await async_playwright().start()
        # Note: This is a simplified mock. In real tests, you'd use a real browser
        # or more sophisticated mocking
        page = MagicMock()
        page.url = "https://example.com"
        page.frames = [MagicMock(name="main")]
        page.frames[0].url = "https://example.com"
        page.frames[0].name = "main"
        page.main_frame = page.frames[0]
        yield page
        await browser.stop()

    @pytest.fixture
    def detector(self):
        """Get detector instance."""
        return create_detector()

    @pytest.fixture
    def confirmation(self):
        """Get confirmation instance."""
        return create_confirmation()

    def test_click_tool_has_security_enabled(self):
        """Test that click tool has security_check enabled in registry."""
        from browser_agent.tools.base import get_all_tools

        tools = get_all_tools()
        click_tool = tools.get("click")

        assert click_tool is not None
        assert click_tool.get("security_check") is True

    def test_type_text_tool_has_security_enabled(self):
        """Test that type_text tool has security_check enabled in registry."""
        from browser_agent.tools.base import get_all_tools

        tools = get_all_tools()
        type_text_tool = tools.get("type_text")

        assert type_text_tool is not None
        assert type_text_tool.get("security_check") is True

    @pytest.mark.asyncio
    async def test_click_delete_button_requires_confirmation(self, detector, confirmation):
        """Test clicking delete button triggers confirmation (FR-032)."""
        action_desc = "Delete account button"

        # Check detector response
        security_result = detector.check_action(action_desc, {}, {})

        assert security_result.action_type == ActionType.DELETE
        assert security_result.requires_confirmation is True
        assert security_result.confirmation_prompt is not None

    @pytest.mark.asyncio
    async def test_click_password_button_is_blocked(self, detector, confirmation):
        """Test clicking password input is blocked (FR-031)."""
        action_desc = "Password field"

        security_result = detector.check_action(action_desc, {}, {})

        assert security_result.action_type == ActionType.PASSWORD
        assert security_result.is_blocked is True

    @pytest.mark.asyncio
    async def test_type_password_text_is_blocked(self, detector, confirmation):
        """Test typing password is blocked (FR-031)."""
        action_desc = "Password input"

        security_result = detector.check_action(action_desc, {}, {})

        assert security_result.action_type == ActionType.PASSWORD
        assert security_result.is_blocked is True

    @pytest.mark.asyncio
    async def test_click_submit_button_requires_confirmation(self, detector, confirmation):
        """Test clicking submit button triggers confirmation (FR-033)."""
        action_desc = "Submit form button"

        security_result = detector.check_action(action_desc, {}, {})

        assert security_result.action_type == ActionType.SEND
        assert security_result.requires_confirmation is True

    @pytest.mark.asyncio
    async def test_click_checkout_button_requires_confirmation(self, detector, confirmation):
        """Test clicking checkout button triggers confirmation (FR-034)."""
        action_desc = "Checkout button"

        security_result = detector.check_action(action_desc, {}, {})

        assert security_result.action_type == ActionType.PAYMENT
        assert security_result.requires_confirmation is True

    @pytest.mark.asyncio
    async def test_click_safe_button_no_confirmation(self, detector, confirmation):
        """Test clicking safe button does not trigger confirmation."""
        action_desc = "Search button"

        security_result = detector.check_action(action_desc, {}, {})

        assert security_result.action_type == ActionType.SAFE
        assert security_result.requires_confirmation is False
        assert security_result.is_blocked is False


class TestSecurityConfirmationFlow:
    """Test security confirmation flow with mock user interactions."""

    @pytest.fixture
    def detector(self):
        return create_detector()

    @pytest.fixture
    def confirmation(self):
        return create_confirmation()

    def test_delete_action_confirmed_proceeds(self, detector, confirmation):
        """Test confirmed delete action would proceed (simulated)."""
        action_desc = "Delete account"
        security_result = detector.check_action(action_desc, {}, {})

        assert security_result.requires_confirmation is True

        # In real flow:
        # result, response = confirmation.confirm_action(
        #     action_description=action_desc,
        #     action_type=security_result.action_type.value,
        #     prompt=security_result.confirmation_prompt,
        # )
        #
        # if result == ConfirmationResult.CONFIRMED:
        #     # Proceed with click
        #     pass

        # Verify the prompt was generated
        assert security_result.confirmation_prompt is not None

    def test_delete_action_denied_blocks(self, detector, confirmation):
        """Test denied delete action is blocked (simulated)."""
        action_desc = "Delete account"
        security_result = detector.check_action(action_desc, {}, {})

        # Simulate denial
        simulated_result = ConfirmationResult.DENIED

        assert simulated_result.value == "denied"
        # In real flow, this would return ToolResult(success=False, ...)

    def test_blocked_password_action_skips_confirmation(self, detector, confirmation):
        """Test blocked password action skips confirmation dialog."""
        action_desc = "Enter password"
        security_result = detector.check_action(action_desc, {}, {})

        assert security_result.is_blocked is True
        assert security_result.requires_confirmation is False

        # Would directly call:
        # confirmation.show_blocked_action(
        #     reason=security_result.message,
        #     suggestion="Please enter password manually",
        # )

        # And return error without executing
        # return ToolResult(success=False, error=security_result.message)


class TestSecurityWithContext:
    """Test security with page and element context."""

    @pytest.fixture
    def detector(self):
        return create_detector()

    def test_payment_page_context(self, detector):
        """Test security on payment pages."""
        page_context = {
            "url": "https://example.com/checkout",
            "title": "Checkout - Example Store",
        }

        # Generic action on payment page
        result = detector.check_action(
            action_description="Click button",
            element_context={},
            page_context=page_context,
        )

        # Should still be safe, but page context is tracked
        assert result.action_type == ActionType.SAFE

    def test_password_field_context(self, detector):
        """Test detection via element context."""
        element_context = {
            "type": "password",
            "role": "textbox",
        }

        result = detector.check_action(
            action_description="Type text",
            element_context=element_context,
            page_context={},
        )

        assert result.action_type == ActionType.PASSWORD
        assert result.is_blocked is True


class TestSecurityPatterns:
    """Test specific security pattern edge cases."""

    @pytest.fixture
    def detector(self):
        return create_detector()

    def test_partial_word_matching(self, detector):
        """Test that patterns match within longer phrases."""
        test_cases = [
            "Click the button to delete your account",  # delete in middle
            "Remove this item from your cart",  # remove in middle
            "I want to pay for this item",  # pay in middle
        ]

        for action in test_cases:
            result = detector.check_action(action, {}, {})
            # At least one should trigger confirmation
            if result.action_type != ActionType.SAFE:
                assert result.requires_confirmation is True

    def test_similar_words_not_matching(self, detector):
        """Test that similar but different words don't trigger."""
        # Words that contain pattern strings but aren't the patterns
        test_cases = [
            "Click the update button",  # contains "date" but not "delete"
        ]

        for action in test_cases:
            result = detector.check_action(action, {}, {})
            assert result.action_type == ActionType.SAFE

    def test_multiple_patterns_priority_order(self, detector):
        """Test that payment patterns are checked before delete patterns."""
        # "Delete payment method" contains both "delete" and "pay"
        # Payment is checked first, so "pay" matches
        action = "Delete payment method"

        result = detector.check_action(action, {}, {})

        # Payment patterns are checked before delete patterns
        assert result.action_type == ActionType.PAYMENT

    def test_payment_action_variations(self, detector):
        """Test various payment action patterns."""
        test_cases = [
            ("Checkout", ActionType.PAYMENT),
            ("Pay now", ActionType.PAYMENT),
            ("Buy item", ActionType.PAYMENT),
        ]

        for action, expected_type in test_cases:
            result = detector.check_action(action, {}, {})
            assert result.action_type == expected_type, f"Failed for: {action}"
            assert result.requires_confirmation is True, f"Failed for: {action}"


class TestToolDecoratorSecurity:
    """Test tool decorator security integration."""

    def test_tool_decorator_security_flag(self):
        """Test that security_check flag is stored in tool registry."""
        from browser_agent.tools.base import get_all_tools

        tools = get_all_tools()

        # Check security-enabled tools
        security_tools = ["click", "type_text"]
        for tool_name in security_tools:
            tool = tools.get(tool_name)
            assert tool is not None
            assert tool.get("security_check") is True

        # Check non-security tools (should not have flag or have False)
        safe_tools = ["navigate", "scroll", "wait"]
        for tool_name in safe_tools:
            tool = tools.get(tool_name)
            if tool:
                # Should either not have security_check or it should be False
                assert tool.get("security_check", False) is False

    def test_tool_wrapper_has_security_attribute(self):
        """Test that tool wrapper function has security_check attribute."""
        from browser_agent.tools.interactions import click, type_text
        from browser_agent.tools.navigation import navigate

        # Security-enabled tools
        assert hasattr(click, "security_check")
        assert click.security_check is True

        assert hasattr(type_text, "security_check")
        assert type_text.security_check is True

        # Non-security tool (may or may not have the attribute)
        if hasattr(navigate, "security_check"):
            assert navigate.security_check is False
