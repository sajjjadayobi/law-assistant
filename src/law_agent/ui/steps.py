"""
Tool step visualization for Chainlit UI.

Manages display of agent tool calls (search_documents, get_document, etc.)
as expandable steps with parameters and results.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolStep:
    """Represents a tool call step for visualization."""

    tool_name: str
    input_params: dict[str, Any]
    output: dict[str, Any]
    execution_time_ms: float | None = None
    status: str = "completed"  # completed, running, error


class ToolStepManager:
    """Manages tool call visualization in Chainlit."""

    # Patterns to extract tool call information from agent responses
    SEARCH_TOOL_PATTERN = re.compile(
        r'searching for:?\s*["\']([^"\']+)["\']',
        re.IGNORECASE | re.DOTALL,
    )

    def __init__(self) -> None:
        """Initialize step manager."""
        self.steps: list[ToolStep] = []

    def extract_steps(self, response_text: str) -> list[dict[str, Any]]:
        """Extract tool call steps from agent response text.

        Args:
            response_text: Full agent response text

        Returns:
            List of step dictionaries for Chainlit display
        """
        steps: list[dict[str, Any]] = []

        # Extract search tool invocations
        search_steps = self._extract_search_steps(response_text)
        steps.extend(search_steps)

        # Extract document retrieval steps
        doc_steps = self._extract_document_steps(response_text)
        steps.extend(doc_steps)

        return steps

    def _extract_search_steps(self, text: str) -> list[dict[str, Any]]:
        """Extract search_documents tool steps.

        Args:
            text: Response text

        Returns:
            List of search step dictionaries
        """
        steps: list[dict[str, Any]] = []

        # Pattern for search operations in response
        search_markers = re.findall(
            r"(searching|searching for:?|found|results?)\s+(?:for\s+)?['\"]?([^'\"\.]+)['\"]?",
            text,
            re.IGNORECASE,
        )

        for i, (_action, query) in enumerate(search_markers):
            steps.append(
                {
                    "tool_name": "search_documents",
                    "input": {
                        "query": query.strip(),
                        "limit": 20,
                    },
                    "output": {
                        "step": f"Search {i + 1}",
                        "query": query.strip(),
                    },
                }
            )

        return steps

    def _extract_document_steps(self, text: str) -> list[dict[str, Any]]:
        """Extract get_document tool steps.

        Args:
            text: Response text

        Returns:
            List of document retrieval step dictionaries
        """
        steps: list[dict[str, Any]] = []

        # Pattern for document reading operations
        doc_patterns = re.findall(
            r"(reading|retrieving|loading|document\s+#?(\d+))",
            text,
            re.IGNORECASE,
        )

        for _i, (_action, doc_num) in enumerate(doc_patterns):
            if doc_num:
                steps.append(
                    {
                        "tool_name": "get_document",
                        "input": {
                            "doc_id": int(doc_num),
                        },
                        "output": {
                            "step": f"Retrieve Document {doc_num}",
                            "status": "retrieved",
                        },
                    }
                )

        return steps

    def create_step_html(self, step: ToolStep) -> str:
        """Create HTML representation of a tool step.

        Args:
            step: ToolStep to format

        Returns:
            HTML string
        """
        html = f"""
        <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin: 10px 0; direction: rtl; text-align: right;">
            <strong style="color: #0066cc;">{step.tool_name}</strong>
            <details>
                <summary>معاملات</summary>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; direction: ltr; text-align: left;">
{json.dumps(step.input_params, ensure_ascii=False, indent=2)}
                </pre>
            </details>
            <details>
                <summary>خروجی</summary>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; direction: ltr; text-align: left;">
{json.dumps(step.output, ensure_ascii=False, indent=2)}
                </pre>
            </details>
        </div>
        """
        return html

    def format_steps_for_display(self, steps: list[ToolStep]) -> list[str]:
        """Format tool steps for Chainlit display.

        Args:
            steps: List of ToolStep objects

        Returns:
            List of HTML strings for each step
        """
        return [self.create_step_html(step) for step in steps]

    def add_step(
        self,
        tool_name: str,
        input_params: dict[str, Any],
        output: dict[str, Any],
        execution_time_ms: float | None = None,
    ) -> None:
        """Add a tool step to the list.

        Args:
            tool_name: Name of the tool called
            input_params: Input parameters passed to tool
            output: Output/results from tool
            execution_time_ms: Execution time in milliseconds
        """
        step = ToolStep(
            tool_name=tool_name,
            input_params=input_params,
            output=output,
            execution_time_ms=execution_time_ms,
        )
        self.steps.append(step)

    def clear_steps(self) -> None:
        """Clear all stored steps."""
        self.steps.clear()

    def get_steps(self) -> list[ToolStep]:
        """Get all stored steps.

        Returns:
            List of ToolStep objects
        """
        return self.steps.copy()

    def create_search_step(
        self,
        query: str,
        doc_types: list[str] | None = None,
        result_count: int = 0,
    ) -> dict[str, Any]:
        """Create a search step data structure.

        Args:
            query: Search query
            doc_types: Document types searched
            result_count: Number of results found

        Returns:
            Dictionary with search step data
        """
        return {
            "tool_name": "search_documents",
            "input": {
                "query": query,
                "doc_types": doc_types or [],
                "limit": 20,
            },
            "output": {
                "result_count": result_count,
                "status": "completed" if result_count > 0 else "no_results",
            },
        }

    def create_document_step(
        self,
        doc_id: int,
        doc_title: str,
        content_length: int,
    ) -> dict[str, Any]:
        """Create a document retrieval step data structure.

        Args:
            doc_id: Document ID
            doc_title: Document title
            content_length: Length of retrieved content

        Returns:
            Dictionary with document step data
        """
        return {
            "tool_name": "get_document",
            "input": {
                "doc_id": doc_id,
            },
            "output": {
                "doc_id": doc_id,
                "title": doc_title,
                "content_length": content_length,
                "status": "retrieved",
            },
        }

    def create_relations_step(
        self,
        doc_id: int,
        related_count: int,
    ) -> dict[str, Any]:
        """Create a get_related_documents step data structure.

        Args:
            doc_id: Source document ID
            related_count: Number of related documents found

        Returns:
            Dictionary with relations step data
        """
        return {
            "tool_name": "get_related_documents",
            "input": {
                "doc_id": doc_id,
            },
            "output": {
                "related_count": related_count,
                "status": "completed",
            },
        }
