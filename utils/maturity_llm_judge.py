"""
maturity_llm_judge.py — LLM gate for L4 maturity validation.

Rule-based classifier promotes some QAs to L4. This module asks gpt-5.4-nano
to verify the answer demonstrates leading-edge implementation, not just that it
mentions trendy topics (AI Overview / GEO / cross-channel / predictive).

Topic ≠ maturity:
  - 「什麼是 AI Overview」→ L1 awareness, NOT L4
  - 「如何建立 AI Overview citation tracking pipeline」→ L4 implementation
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable

import config
from utils.observability import observe

_logger = logging.getLogger(__name__)


L4_JUDGE_SYSTEM_PROMPT = """你是 SEO 成熟度分類的「真實性審查員」。

L4（領先期）的判定不能只看是否提到 AI / 預測 / 跨通路等趨勢詞——
這些是「主題」（topic），不是「成熟度」（maturity）。

L4 必須同時具備以下兩個條件：

  1. 實作具體性：答案中有可執行的系統設計、模型架構、自動化流程、
     跨工具整合步驟，或可量化的測試/驗證機制
  2. 領先級判斷：超出單一指標追蹤、單一工具設定、單一頁面優化的範疇，
     涉及策略/組織/系統層級的決策

純談趨勢、純列舉名詞、純解釋概念（即使概念是 AI Overview / GEO / 程式化 SEO）
不算 L4。

回傳格式：JSON {"is_l4": true|false, "reason": "<繁中 30 字內>"}
"""


def _has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _format_user_prompt(
    question: str,
    answer: str,
    keywords: Iterable[str],
) -> str:
    kw_list = list(keywords) if keywords else []
    kw_repr = ", ".join(str(k) for k in kw_list) if kw_list else "(無)"
    return (
        "請審查以下 QA 是否真為 L4 等級：\n\n"
        f"[Question]\n{question}\n\n"
        f"[Answer]\n{answer}\n\n"
        f"[Keywords]\n{kw_repr}\n\n"
        "依規則回 JSON。is_l4=false 代表 rule layer 偽陽性，應降為 L3。"
    )


@observe(name="llm_validate_l4")
def llm_validate_l4(
    question: str,
    answer: str,
    keywords: Iterable[str],
) -> bool:
    """Reality-check whether a rule-promoted L4 QA truly meets L4 criteria.

    Returns:
        True  — answer demonstrates concrete implementation / leading-edge depth.
        False — answer is just a trendy-topic explanation; caller should demote to L3.

    Fallback: returns True (no demotion) when OPENAI_API_KEY is missing or the
    LLM call fails. The rule layer's dual-evidence check is the only gate in
    OpenAI-less mode (preserves PR #38 OpenAI-less pipeline).
    """
    if not _has_openai_key():
        return True

    from utils.pipeline_cache import cache_get, cache_set
    from utils.openai_helper import _client

    cache_key = f"{question}\n\n{answer}"
    cache_model = config.CLASSIFY_MODEL

    cached = cache_get("l4_judge", cache_key, model=cache_model)
    if cached is not None:
        return bool(cached.get("is_l4", True))

    try:
        client = _client()
        response = client.chat.completions.create(
            model=config.CLASSIFY_MODEL,
            messages=[
                {"role": "system", "content": L4_JUDGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _format_user_prompt(question, answer, keywords),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "validate_l4",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "is_l4": {"type": "boolean"},
                            "reason": {"type": "string"},
                        },
                        "required": ["is_l4", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
            max_completion_tokens=512,
        )
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
    except (json.JSONDecodeError, Exception) as exc:
        _logger.warning(
            "L4 judge LLM call failed (%s); keeping rule-layer L4 decision",
            exc,
        )
        return True

    is_l4 = bool(result.get("is_l4", True))
    cache_set("l4_judge", cache_key, result, model=cache_model)
    return is_l4
