"""
Online scoring utilities — attach evaluation scores to Laminar traces inline.

Usage:
    from lmnr import Laminar
    from utils.laminar_scoring import score_rag_response, score_trace

    span_ctx = Laminar.get_laminar_span_context()
    trace_id = str(span_ctx.trace_id) if span_ctx else None
    score_rag_response(trace_id=trace_id, answer=answer, sources=sources, query=query)
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_laminar_client: Optional[object] = None


def _get_client() -> Optional[object]:
    """Return a singleton LaminarClient, or None when not configured."""
    global _laminar_client
    if _laminar_client is not None:
        return _laminar_client

    api_key = os.getenv("LMNR_PROJECT_API_KEY", "")
    if not api_key:
        return None

    try:
        from lmnr import LaminarClient  # type: ignore[import]

        _laminar_client = LaminarClient(project_api_key=api_key)
        return _laminar_client
    except ImportError:
        logger.debug("lmnr not installed — online scoring disabled")
        return None
    except Exception as exc:
        logger.debug("LaminarClient init failed: %s", exc)
        return None


def score_trace(
    name: str,
    score: float,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Attach an evaluation score to a Laminar trace or span.

    Args:
        name:     Evaluator name, e.g. "answer_length", "has_sources".
        score:    Numeric score (0.0–1.0 for binary/rate; or any float for custom scale).
        trace_id: Attach to the root span of this trace.
        span_id:  Attach to a specific span within the trace.
        metadata: Extra key-value context stored alongside the score.
    """
    if trace_id is None and span_id is None:
        logger.debug("score_trace(%s): no trace_id or span_id — skipping", name)
        return

    client = _get_client()
    if client is None:
        return

    try:
        kwargs: dict = {"name": name, "score": score}
        if trace_id:
            kwargs["trace_id"] = trace_id
        if span_id:
            kwargs["span_id"] = span_id
        if metadata:
            kwargs["metadata"] = metadata
        client.evaluators.score(**kwargs)  # type: ignore[attr-defined]
    except Exception as exc:
        # Scoring failures must never crash the application path.
        logger.debug("score_trace(%s) failed: %s", name, exc)


def score_rag_response(
    trace_id: Optional[str],
    answer: str,
    sources: list[dict],
    query: str,
) -> None:
    """Attach rule-based online scores to a rag_chat trace.

    Runs four lightweight evaluators (no extra LLM call):
      answer_length    1 if answer > 50 chars, else 0
      has_sources      1 if >= 1 source retrieved, else 0
      top_source_score cosine similarity of the best-ranked source (0–1)
      source_count     number of sources / 5, capped at 1.0
    """
    if not trace_id:
        return

    # answer_length
    score_trace(
        "answer_length",
        score=float(len(answer.strip()) > 50),
        trace_id=trace_id,
        metadata={"char_count": len(answer)},
    )

    # has_sources
    score_trace(
        "has_sources",
        score=float(len(sources) > 0),
        trace_id=trace_id,
        metadata={"source_count": len(sources)},
    )

    if sources:
        top_score = float(sources[0].get("score", 0.0))
        score_trace(
            "top_source_score",
            score=top_score,
            trace_id=trace_id,
            metadata={"top_source_id": sources[0].get("id")},
        )

        score_trace(
            "source_count",
            score=min(len(sources) / 5.0, 1.0),
            trace_id=trace_id,
        )
