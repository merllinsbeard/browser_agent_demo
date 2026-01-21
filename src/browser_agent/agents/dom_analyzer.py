"""
DOM Analyzer Sub-Agent

Fast page structure analyzer using the haiku model tier.
Extracts actionable information from accessibility trees
and identifies interactive elements for the planner.

Following FR-011 (Accessibility Tree extraction) and FR-013 (no hardcoded selectors).
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Awaitable

from ..tui import print_result, action_spinner


@dataclass
class PageAnalysis:
    """
    Result of DOM analysis.

    Contains structured information about page elements
    for use by the planner and executor.
    """

    url: str
    title: str
    interactive_elements: list[dict[str, Any]] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    text_summary: str = ""
    page_type: str = "unknown"  # e.g., "search", "form", "article", "list"
    actionable_suggestions: list[str] = field(default_factory=list)


class DOMAnalyzer:
    """
    DOM Analyzer sub-agent for fast page structure analysis.

    Uses the haiku model tier for quick, efficient analysis
    of accessibility trees. Provides structured page information
    to help the planner make decisions.
    """

    def __init__(
        self,
        llm_complete: Optional[Callable[[str], Awaitable[str]]] = None,
        verbose: bool = True,
    ):
        """
        Initialize the DOM Analyzer.

        Args:
            llm_complete: Optional LLM for intelligent analysis.
                         If None, uses rule-based analysis only.
            verbose: Whether to print progress
        """
        self.llm_complete = llm_complete
        self.verbose = verbose

    async def analyze(
        self,
        url: str,
        title: str,
        accessibility_tree: dict[str, Any],
        interactive_elements: list[dict[str, Any]],
        page_text: Optional[str] = None,
    ) -> PageAnalysis:
        """
        Analyze page structure and extract actionable information.

        Args:
            url: Current page URL
            title: Page title
            accessibility_tree: Raw accessibility tree from Playwright
            interactive_elements: Pre-extracted interactive elements
            page_text: Optional page text content

        Returns:
            PageAnalysis with structured page information
        """
        analysis = PageAnalysis(url=url, title=title)

        if self.verbose:
            with action_spinner("Analyzing page structure..."):
                analysis = await self._perform_analysis(
                    analysis, accessibility_tree, interactive_elements, page_text
                )
        else:
            analysis = await self._perform_analysis(
                analysis, accessibility_tree, interactive_elements, page_text
            )

        if self.verbose:
            summary = self._format_summary(analysis)
            print_result(summary, success=True, title="[DOM ANALYSIS]")

        return analysis

    async def _perform_analysis(
        self,
        analysis: PageAnalysis,
        tree: dict[str, Any],
        elements: list[dict[str, Any]],
        text: Optional[str],
    ) -> PageAnalysis:
        """Perform the actual analysis."""
        # Process interactive elements
        analysis.interactive_elements = self._categorize_elements(elements)

        # Extract forms
        analysis.forms = self._extract_forms(elements)

        # Extract headings from tree
        analysis.headings = self._extract_headings(tree)

        # Create text summary
        analysis.text_summary = self._create_text_summary(text, analysis.headings)

        # Determine page type
        analysis.page_type = self._determine_page_type(analysis)

        # Generate actionable suggestions
        analysis.actionable_suggestions = self._generate_suggestions(analysis)

        # If LLM available, enhance with intelligent analysis
        if self.llm_complete:
            analysis = await self._llm_enhance_analysis(analysis)

        return analysis

    def _categorize_elements(
        self, elements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Categorize and enrich interactive elements.

        Args:
            elements: Raw interactive elements

        Returns:
            Categorized elements with additional metadata
        """
        categorized = []

        for elem in elements:
            role = elem.get("role", "")

            # Add category
            if role in ["button", "link"]:
                category = "action"
            elif role in ["textbox", "searchbox", "combobox"]:
                category = "input"
            elif role in ["checkbox", "radio", "switch"]:
                category = "selection"
            else:
                category = "other"

            # Add natural language description
            description = self._create_element_description(elem)

            categorized.append({
                **elem,
                "category": category,
                "description": description,
            })

        return categorized

    def _create_element_description(self, elem: dict[str, Any]) -> str:
        """Create a natural language description for an element."""
        role = elem.get("role", "element")
        name = elem.get("name", "")

        if name:
            return f'{role} "{name}"'
        return role

    def _extract_forms(
        self, elements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract form structures from elements."""
        forms = []
        input_elements = [
            e for e in elements
            if e.get("role") in ["textbox", "searchbox", "combobox", "checkbox", "radio"]
        ]

        if input_elements:
            # Group inputs that might belong to the same form
            forms.append({
                "inputs": input_elements,
                "input_count": len(input_elements),
            })

        return forms

    def _extract_headings(self, tree: dict[str, Any]) -> list[str]:
        """Extract headings from accessibility tree."""
        headings = []
        self._find_headings_recursive(tree, headings)
        return headings[:10]  # Limit to first 10

    def _find_headings_recursive(
        self, node: dict[str, Any], headings: list[str]
    ) -> None:
        """Recursively find heading elements."""
        role = node.get("role", "")
        name = node.get("name", "")

        if role == "heading" and name:
            headings.append(name)

        for child in node.get("children", []):
            self._find_headings_recursive(child, headings)

    def _create_text_summary(
        self, text: Optional[str], headings: list[str]
    ) -> str:
        """Create a brief text summary of the page."""
        if text:
            # First 500 chars of text
            summary = text[:500].strip()
            if len(text) > 500:
                summary += "..."
            return summary

        if headings:
            return "Headings: " + ", ".join(headings[:5])

        return ""

    def _determine_page_type(self, analysis: PageAnalysis) -> str:
        """Determine the type of page based on its content."""
        url = analysis.url.lower()
        title = analysis.title.lower()
        elements = analysis.interactive_elements

        # Check URL patterns
        if any(x in url for x in ["search", "query", "q="]):
            return "search_results"
        if any(x in url for x in ["login", "signin", "auth"]):
            return "login"
        if any(x in url for x in ["cart", "basket", "checkout"]):
            return "shopping"
        if any(x in url for x in ["article", "post", "blog"]):
            return "article"

        # Check element patterns
        input_count = sum(1 for e in elements if e.get("category") == "input")
        action_count = sum(1 for e in elements if e.get("category") == "action")

        if input_count > 3:
            return "form"
        if action_count > 10:
            return "navigation"

        # Check title
        if any(x in title for x in ["search", "results"]):
            return "search_results"
        if any(x in title for x in ["login", "sign in"]):
            return "login"

        return "general"

    def _generate_suggestions(self, analysis: PageAnalysis) -> list[str]:
        """Generate actionable suggestions based on page analysis."""
        suggestions = []
        page_type = analysis.page_type

        if page_type == "search_results":
            suggestions.append("Look for search result links to click")
            suggestions.append("Check for pagination or 'load more' buttons")

        elif page_type == "login":
            suggestions.append("Find username/email and password fields")
            suggestions.append("Look for the login/sign in button")

        elif page_type == "form":
            suggestions.append("Identify required form fields")
            suggestions.append("Look for submit button")

        elif page_type == "shopping":
            suggestions.append("Check for add to cart buttons")
            suggestions.append("Look for quantity selectors")

        # Generic suggestions based on elements
        inputs = [e for e in analysis.interactive_elements if e.get("category") == "input"]
        if inputs:
            suggestions.append(f"Found {len(inputs)} input field(s) to interact with")

        buttons = [
            e for e in analysis.interactive_elements
            if e.get("role") == "button"
        ]
        if buttons:
            button_names = [b.get("name", "unnamed") for b in buttons[:3]]
            suggestions.append(f"Available buttons: {', '.join(button_names)}")

        return suggestions[:5]  # Limit suggestions

    async def _llm_enhance_analysis(self, analysis: PageAnalysis) -> PageAnalysis:
        """Use LLM to enhance analysis with intelligent insights."""
        if not self.llm_complete:
            return analysis

        prompt = f"""Analyze this web page and provide insights:

Page: {analysis.title} ({analysis.url})
Type: {analysis.page_type}
Elements: {len(analysis.interactive_elements)} interactive
Forms: {len(analysis.forms)}

Based on this, what are the most important elements to interact with?
Keep your response brief (2-3 sentences)."""

        try:
            insight = await self.llm_complete(prompt)
            if insight:
                analysis.actionable_suggestions.insert(0, f"AI insight: {insight[:200]}")
        except Exception:
            pass  # LLM enhancement is optional

        return analysis

    def _format_summary(self, analysis: PageAnalysis) -> str:
        """Format analysis as human-readable summary."""
        lines = [
            f"Page: {analysis.title}",
            f"Type: {analysis.page_type}",
            f"Elements: {len(analysis.interactive_elements)} interactive",
        ]

        if analysis.forms:
            lines.append(f"Forms: {len(analysis.forms)} detected")

        if analysis.actionable_suggestions:
            lines.append("\nSuggestions:")
            for suggestion in analysis.actionable_suggestions[:3]:
                lines.append(f"  • {suggestion}")

        return "\n".join(lines)


def create_dom_analyzer(
    llm_complete: Optional[Callable[[str], Awaitable[str]]] = None,
    verbose: bool = True,
) -> DOMAnalyzer:
    """
    Factory function to create a DOM Analyzer.

    Args:
        llm_complete: Optional LLM function for intelligent analysis
        verbose: Whether to print progress

    Returns:
        Configured DOMAnalyzer instance
    """
    return DOMAnalyzer(llm_complete=llm_complete, verbose=verbose)
