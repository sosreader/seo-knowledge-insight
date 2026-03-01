"""
Online scoring utilities — attach evaluation scores to Laminar spans via events.

Must be called INSIDE an active @observe span. Laminar.event() records the
score as a span event visible in the Laminar dashboard.

Usage (inside an @observe-decorated function):
    from utils.laminar_scoring import score_rag_response

    @observe(name="rag_chat")
    async def rag_chat(message: str) -> dict:
        ...
        answer = resp.choices[0].message.content or ""
        sources = [...]
        score_rag_response(answer=answer, sources=sources)
        return {"answer": answer, "sources": sources}
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def score_event(name: str, value: float) -> None:
    """Attach a named numeric score to the current Laminar span as an event.

    Must be called inside an active span (@observe or start_as_current_span).
    Silently skips when called outside a span context.

    Args:
        name:  Evaluator name, e.g. "answer_length", "has_sources".
        value: Numeric score (typically 0.0 or 1.0 for binary; 0.0–1.0 for continuous).
    """
    try:
        from lmnr import Laminar  # type: ignore[import]

        Laminar.event(name, value)
    except ImportError:
        logger.debug("lmnr not installed — score_event(%s) skipped", name)
    except Exception as exc:
        # Scoring failures must never crash the main application path.
        logger.debug("score_event(%s=%.3f) failed: %s", name, value, exc)


def score_rag_response(
    answer: str,
    sources: list[dict],
    query: Optional[str] = None,
) -> None:
    """Attach rule-based online scores to the current rag_chat span.

    Runs four lightweight evaluators (no extra LLM call). Must be called
    inside the @observe(name="rag_chat") decorated function.

    Evaluators:
        answer_length    1.0 if answer > 50 chars, else 0.0
        has_sources      1.0 if >= 1 source retrieved, else 0.0
        top_source_score cosine similarity of the best-ranked source (0.0–1.0)
        source_count     number of sources / 5, capped at 1.0

    Args:
        answer:  The LLM-generated answer string.
        sources: List of source dicts returned by the retrieval step.
        query:   The original user query (unused in scoring, reserved for future use).
    """
    score_event("answer_length", float(len(answer.strip()) > 50))
    score_event("has_sources", float(len(sources) > 0))

    if sources:
        top_score = float(sources[0].get("score", 0.0))
        score_event("top_source_score", top_score)
        score_event("source_count", min(len(sources) / 5.0, 1.0))


def score_enrichment_boost(synonym_hits: int, freshness_score: float) -> None:
    """Attach enrichment quality scores to the current Laminar span.

    Records how many synonyms were matched and the freshness quality of
    returned Q&A. Must be called inside an active @observe span.

    Args:
        synonym_hits:    Number of synonym terms that matched the query.
        freshness_score: Average freshness score of returned Q&A (0.0–1.0).
    """
    score_event("synonym_hits", float(synonym_hits))
    score_event("freshness_score", min(max(freshness_score, 0.0), 1.0))


def score_search_miss(query: str, top_score: float) -> None:
    """Record a search miss event to the current Laminar span.

    A search miss occurs when no Q&A meets the minimum relevance threshold.
    Tracking these helps identify coverage gaps in the knowledge base.

    Args:
        query:     The user query that produced no results.
        top_score: The highest similarity score achieved (< threshold).
    """
    score_event("search_miss", 1.0)
    score_event("search_top_score", min(max(top_score, 0.0), 1.0))
    logger.debug("score_search_miss: query=%r top_score=%.4f", query, top_score)
