"""
Laminar offline evaluation: RAG chat quality.

Tests the full RAG chat pipeline end-to-end via the TypeScript Hono API:
given a known SEO scenario, does the system return a relevant, sourced answer?

Dataset:  eval/golden_retrieval.json (first 10 scenarios, cost-efficient)
Requires: LMNR_PROJECT_API_KEY, running TS API (cd api && pnpm dev)

Run:
    python evals/eval_chat.py
    lmnr eval evals/eval_chat.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

from lmnr import evaluate  # type: ignore[import]

# ── Config ────────────────────────────────────────────────────────────────────

_API_BASE = os.environ.get("EVAL_API_BASE", "http://localhost:8002")
_API_KEY = os.environ.get("SEO_API_KEY", "")

# ── Dataset ───────────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_retrieval.json"
if not _golden_path.exists():
    print(f"[eval_chat] Golden dataset not found: {_golden_path}", file=sys.stderr)
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

# Use first 10 scenarios to keep cost low.
_dataset = [
    {
        "data": {"question": item["query"]},
        "target": {
            "expected_keywords": item["expected_keywords"],
            "expected_categories": item.get("expected_categories", []),
            "scenario": item["scenario"],
        },
    }
    for item in _golden_raw[:10]
]


# ── Executor ──────────────────────────────────────────────────────────────────

def chat_executor(data: dict) -> dict:
    """Call the TS Hono chat API and return answer + sources."""
    question: str = data["question"]

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["X-API-Key"] = _API_KEY

    try:
        resp = requests.post(
            f"{_API_BASE}/api/v1/chat",
            json={"message": question, "history": []},
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 200:
            body = resp.json()
            result = body.get("data", {})
            answer = result.get("answer") or ""
            sources = result.get("sources", [])
            mode = result.get("mode", "unknown")
            return {
                "answer": answer,
                "sources": sources,
                "source_count": len(sources),
                "mode": mode,
            }
        logger.warning("[eval_chat] API returned %s: %s", resp.status_code, resp.text[:200])
    except requests.ConnectionError:
        logger.error("[eval_chat] API not reachable at %s — is the server running?", _API_BASE)
    except Exception as e:
        logger.warning("[eval_chat] API call failed: %s", e)

    return {"answer": "", "sources": [], "source_count": 0, "mode": "error"}


# ── Evaluators ────────────────────────────────────────────────────────────────

def has_answer(output: dict, *_: object) -> float:
    """1 if the answer is non-trivially long (> 50 chars), or context-only mode has sources."""
    answer = output.get("answer") or ""
    if len(answer.strip()) > 50:
        return 1.0
    # context-only mode: no answer but has sources is still valid
    if output.get("mode") == "context-only" and output.get("source_count", 0) > 0:
        return 1.0
    return 0.0


def has_sources(output: dict, *_: object) -> float:
    """1 if at least 1 source was retrieved."""
    return float(output.get("source_count", 0) > 0)


def answer_keyword_coverage(output: dict, target: dict) -> float:
    """Fraction of expected keywords present in the answer + sources text."""
    expected_kws: list[str] = target.get("expected_keywords", [])
    if not expected_kws:
        return 1.0

    # Build pool from answer + all source questions/answers
    answer = output.get("answer") or ""
    sources = output.get("sources", [])
    pool_parts = [answer]
    for src in sources:
        pool_parts.append(src.get("question", ""))
        pool_parts.append(src.get("answer", ""))
        pool_parts.extend(src.get("keywords", []))
    pool = " ".join(pool_parts).lower()

    hits = sum(1 for kw in expected_kws if kw.lower() in pool)
    return hits / len(expected_kws)


def top_source_in_expected_category(output: dict, target: dict) -> float:
    """1 if top-1 source category is in expected_categories."""
    sources: list[dict] = output.get("sources", [])
    expected_cats: list[str] = target.get("expected_categories", [])

    if not sources or not expected_cats:
        return 0.0

    return 1.0 if sources[0].get("category", "") in expected_cats else 0.0


# ── Run ───────────────────────────────────────────────────────────────────────

evaluate(
    data=_dataset,
    executor=chat_executor,
    evaluators={
        "has_answer": has_answer,
        "has_sources": has_sources,
        "answer_keyword_coverage": answer_keyword_coverage,
        "top_source_in_expected_category": top_source_in_expected_category,
    },
    group_name="chat_quality",
)
