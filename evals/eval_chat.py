"""
Laminar offline evaluation: RAG chat quality.

Tests the full rag_chat pipeline end-to-end: given a known SEO scenario,
does the system return a relevant, sourced answer?

Dataset:  eval/golden_retrieval.json (first 10 scenarios, cost-efficient)
Requires: LMNR_PROJECT_API_KEY, OPENAI_API_KEY, output/qa_final.json,
          output/qa_embeddings.npy

Note: This eval initialises the QAStore in-process — it does NOT require a
      running FastAPI server. It calls app.core.chat.rag_chat() directly.

      chat_executor is an async def so lmnr calls it directly (no thread pool),
      preserving the OpenTelemetry context chain.

Run:
    python evals/eval_chat.py
    lmnr eval evals/eval_chat.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Bootstrap QAStore before importing app modules that depend on it.
from app.core.store import store  # noqa: E402

_qa_json = PROJECT_ROOT / "output" / "qa_final.json"
_npy = PROJECT_ROOT / "output" / "qa_embeddings.npy"
if _qa_json.exists() and _npy.exists():
    store.load(json_path=_qa_json, npy_path=_npy)
else:
    print(
        "[eval_chat] qa_final.json or qa_embeddings.npy not found — "
        "run Steps 1–3 of the pipeline first.",
        file=sys.stderr,
    )
    sys.exit(1)

from lmnr import evaluate  # noqa: E402  # type: ignore[import]

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

async def chat_executor(data: dict) -> dict:
    """Run rag_chat and return answer + metadata.

    Declared async so lmnr calls it directly (not via run_in_executor),
    which preserves the OpenTelemetry context chain for correct span nesting.
    """
    from app.core.chat import rag_chat  # deferred to avoid circular init

    result = await rag_chat(data["question"])
    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "source_count": len(result.get("sources", [])),
    }


# ── Evaluators ────────────────────────────────────────────────────────────────

def has_answer(output: dict, *_: object) -> float:
    """1 if the answer is non-trivially long (> 50 chars)."""
    return float(len(output.get("answer", "").strip()) > 50)


def has_sources(output: dict, *_: object) -> float:
    """1 if at least 1 source was retrieved."""
    return float(output.get("source_count", 0) > 0)


def answer_keyword_coverage(output: dict, target: dict) -> float:
    """Fraction of expected keywords present in the answer text."""
    answer: str = output.get("answer", "").lower()
    expected_kws: list[str] = target.get("expected_keywords", [])

    if not expected_kws:
        return 1.0

    hits = sum(1 for kw in expected_kws if kw.lower() in answer)
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
