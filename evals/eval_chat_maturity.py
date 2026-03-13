"""
Laminar offline evaluation: Chat maturity appropriateness.

Tests whether RAG chat responses are appropriately tailored to the
client's maturity level (L1 = basic, L3 = advanced).

Dataset:  eval/golden_chat_maturity.json (10 scenarios: 5 queries × L1/L3)
Requires: LMNR_PROJECT_API_KEY, running TS API (cd api && pnpm dev), OPENAI_API_KEY

Run:
    python evals/eval_chat_maturity.py
    python evals/eval_chat_maturity.py --limit 4
    lmnr eval evals/eval_chat_maturity.py
"""
from __future__ import annotations

import argparse
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

# ── CLI args ──────────────────────────────────────────────────────────────────

_parser = argparse.ArgumentParser(description="Chat maturity eval")
_parser.add_argument("--limit", type=int, default=0, help="Limit golden cases (0=all)")
_args, _unknown = _parser.parse_known_args()

# ── Config ────────────────────────────────────────────────────────────────────

_API_BASE = os.environ.get("EVAL_API_BASE", "http://localhost:8002")
_API_KEY = os.environ.get("SEO_API_KEY", "")

# ── Golden dataset ────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_chat_maturity.json"
if not _golden_path.exists():
    print(
        f"[eval_chat_maturity] Golden dataset not found: {_golden_path}",
        file=sys.stderr,
    )
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

if _args.limit > 0:
    _golden_raw = _golden_raw[: _args.limit]

_dataset = [
    {
        "data": {
            "query": item["query"],
            "maturity_level": item["maturity_level"],
        },
        "target": {
            "should_contain": item["expected_traits"]["should_contain"],
            "should_not_contain": item["expected_traits"]["should_not_contain"],
            "description": item["description"],
        },
    }
    for item in _golden_raw
]


# ── Executor ──────────────────────────────────────────────────────────────────


def chat_executor(data: dict) -> dict:
    """Call the chat API with maturity_level and return the answer."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["X-API-Key"] = _API_KEY

    try:
        resp = requests.post(
            f"{_API_BASE}/api/v1/chat",
            json={
                "message": data["query"],
                "maturity_level": data["maturity_level"],
            },
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 200:
            body = resp.json()
            answer = body.get("data", {}).get("answer", "") or ""
            mode = body.get("data", {}).get("mode", "unknown")
            return {"answer": answer, "mode": mode}
        else:
            return {"answer": "", "mode": "error", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"answer": "", "mode": "error", "error": str(e)}


# ── Evaluators ────────────────────────────────────────────────────────────────


def appropriateness(output: dict, target: dict) -> float:
    """Check if the answer contains expected terms and avoids forbidden terms.

    Score = (should_contain hits / total should_contain) weighted 0.7
          + (should_not_contain avoidance) weighted 0.3
    """
    answer = output.get("answer", "").lower()
    if not answer:
        return 0.0

    # Should contain
    should_contain: list[str] = target.get("should_contain", [])
    if should_contain:
        hits = sum(1 for term in should_contain if term.lower() in answer)
        contain_score = hits / len(should_contain)
    else:
        contain_score = 1.0

    # Should not contain
    should_not_contain: list[str] = target.get("should_not_contain", [])
    if should_not_contain:
        violations = sum(1 for term in should_not_contain if term.lower() in answer)
        avoid_score = 1.0 - (violations / len(should_not_contain))
    else:
        avoid_score = 1.0

    return contain_score * 0.7 + avoid_score * 0.3


def has_answer(output: dict, target: dict) -> float:
    """Chat returned a non-empty answer (not context-only)."""
    answer = output.get("answer", "")
    return 1.0 if answer and len(answer) > 20 else 0.0


# ── Run ───────────────────────────────────────────────────────────────────────

evaluate(
    data=_dataset,
    executor=chat_executor,
    evaluators={
        "appropriateness": appropriateness,
        "has_answer": has_answer,
    },
    group_id="chat_maturity_quality",
)
