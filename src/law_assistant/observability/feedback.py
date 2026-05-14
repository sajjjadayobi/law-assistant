"""
Feedback integration with Arize Phoenix.

Sends user feedback (👍/👎) to Phoenix as span annotations so they
appear alongside traces in the Phoenix UI for eval-driven development.

Phoenix REST API: POST /v1/span_annotations
Requires a span_id (hex string) — not trace_id.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from law_assistant.config.settings import get_settings

logger = logging.getLogger(__name__)

_ANNOTATION_NAME = "user_feedback"


class PhoenixFeedbackClient:
    """Sends user feedback to Arize Phoenix as span annotations."""

    def __init__(self, phoenix_endpoint: str | None = None):
        # Use provided endpoint or load from settings
        if phoenix_endpoint is None:
            settings = get_settings()
            phoenix_endpoint = settings.observability.phoenix_endpoint
            timeout = settings.observability.http_timeout
        else:
            settings = get_settings()
            timeout = settings.observability.http_timeout

        self.endpoint = phoenix_endpoint.rstrip("/")
        self._http = httpx.AsyncClient(timeout=timeout)

    async def send_feedback(
        self,
        span_id: str,
        feedback_type: str,  # "positive" | "negative"
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
        identifier: str | None = None,  # user identifier shown in Phoenix "user" column
        **kwargs: Any,
    ) -> bool:
        """POST /v1/span_annotations with a HUMAN annotation.

        Args:
            span_id:       16-char hex span_id from OpenTelemetry context.
            feedback_type: "positive" or "negative".
            comment:       Explanation text — includes user comment + message preview.
            metadata:      Extra key-value pairs stored with the annotation
                           (question, response_preview, session_id, user_comment).

        Returns:
            True if Phoenix accepted the annotation.
        """
        label = "thumbs_up" if feedback_type == "positive" else "thumbs_down"
        score = 1.0 if feedback_type == "positive" else 0.0

        annotation: dict[str, Any] = {
            "span_id": span_id,
            "name": _ANNOTATION_NAME,
            "annotator_kind": "HUMAN",
            "result": {
                "label": label,
                "score": score,
                "explanation": comment or "",
            },
            "metadata": metadata or {},
        }
        if identifier:
            annotation["identifier"] = identifier

        payload = {"data": [annotation]}

        try:
            resp = await self._http.post(
                f"{self.endpoint}/v1/span_annotations",
                json=payload,
            )
            if resp.status_code in (200, 201):
                logger.info("Phoenix feedback sent span_id=%s label=%s", span_id, label)
                return True
            logger.warning(
                "Phoenix feedback rejected status=%s body=%s", resp.status_code, resp.text[:200]
            )
            return False
        except Exception as e:
            logger.debug("Phoenix feedback error: %s", e)
            return False

    async def send_note(
        self,
        span_id: str,
        note: str,
    ) -> bool:
        """POST /v1/span_notes — adds free-text note visible in Phoenix Notes panel.

        Notes are separate from annotations and support multiple entries per span.
        The user's comment appears directly in the Notes panel (N key shortcut) in
        the trace detail view, which is more prominent than the annotation explanation.

        Args:
            span_id: 16-char hex OTel span_id.
            note:    Text to appear in the Notes panel.

        Returns:
            True if Phoenix accepted the note.
        """
        payload = {"data": {"span_id": span_id, "note": note}}
        try:
            resp = await self._http.post(
                f"{self.endpoint}/v1/span_notes",
                json=payload,
            )
            if resp.status_code in (200, 201):
                logger.info("Phoenix note sent span_id=%s chars=%d", span_id, len(note))
                return True
            logger.warning(
                "Phoenix note rejected status=%s body=%s", resp.status_code, resp.text[:200]
            )
            return False
        except Exception as e:
            logger.debug("Phoenix note error: %s", e)
            return False

    async def close(self) -> None:
        await self._http.aclose()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_feedback_client: PhoenixFeedbackClient | None = None


def initialize_feedback_client(phoenix_endpoint: str | None = None) -> None:
    global _feedback_client
    if phoenix_endpoint is None:
        settings = get_settings()
        phoenix_endpoint = settings.observability.phoenix_endpoint

    _feedback_client = PhoenixFeedbackClient(phoenix_endpoint)
    logger.info("Phoenix feedback client initialized at %s", phoenix_endpoint)


def get_feedback_client() -> PhoenixFeedbackClient | None:
    return _feedback_client


# ---------------------------------------------------------------------------
# Convenience wrappers (backwards compat)
# ---------------------------------------------------------------------------


async def send_feedback_to_phoenix(
    trace_id: str,  # kept for signature compat — value used as span_id
    feedback_type: str,
    comment: str | None = None,
    tags: list[str] | None = None,
) -> bool:
    if _feedback_client is None:
        return False
    return await _feedback_client.send_feedback(
        span_id=trace_id,
        feedback_type=feedback_type,
        comment=comment,
    )


def log_feedback_local(
    trace_id: str,
    feedback_type: str,
    comment: str | None = None,
    tags: list[str] | None = None,
) -> None:
    logger.info("Feedback local: trace_id=%s type=%s comment=%s", trace_id, feedback_type, comment)
