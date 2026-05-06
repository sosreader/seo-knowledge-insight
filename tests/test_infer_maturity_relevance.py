"""Tests for scripts/03_dedupe_classify.py::_infer_maturity_relevance.

Verifies the LLM-gate integration:
- Pre-existing maturity_relevance is preserved.
- Without OPENAI_API_KEY, the rule layer is the sole gate (no LLM call).
- With OPENAI_API_KEY, only L4 candidates trigger the LLM gate.
- LLM gate False demotes to L3.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def dedupe_module():
    return importlib.import_module("scripts.03_dedupe_classify")


def _l4_qa() -> dict:
    """A QA that the rule layer should classify as L4."""
    return {
        "question": "如何建立 SEO 排名預測模型？",
        "answer": (
            "排名預測模型可使用 machine learning 方法，"
            "結合歷史 GSC 資料、競爭對手指標、季節性因子訓練模型。"
            "建議用 random forest 架構，定期 retrain 並驗證 forecasting 準確度。"
        ),
        "keywords": ["排名預測", "預測模型", "machine learning"],
    }


def _l2_qa() -> dict:
    """A QA that the rule layer should classify as L2 (no LLM gate expected)."""
    return {
        "question": "如何用 GSC 追蹤 SEO 指標？",
        "answer": "在 Google Search Console 設定效能報表，追蹤點擊、曝光、CTR 和排名。",
        "keywords": ["Google Search Console", "追蹤", "指標"],
    }


def test_existing_maturity_preserved(dedupe_module, monkeypatch):
    """Pre-existing maturity_relevance must short-circuit (no rule, no LLM)."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    spy = Mock()
    monkeypatch.setattr(
        "utils.maturity_llm_judge.llm_validate_l4", spy
    )
    qa = {**_l4_qa(), "maturity_relevance": "L1"}
    assert dedupe_module._infer_maturity_relevance(qa) == "L1"
    spy.assert_not_called()


def test_l2_does_not_call_llm_gate(dedupe_module, monkeypatch):
    """Non-L4 rule outcomes must not trigger the LLM gate."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    spy = Mock()
    monkeypatch.setattr(
        "utils.maturity_llm_judge.llm_validate_l4", spy
    )
    result = dedupe_module._infer_maturity_relevance(_l2_qa())
    assert result == "L2"
    spy.assert_not_called()


def test_l4_without_api_key_skips_llm(dedupe_module, monkeypatch):
    """OpenAI-less mode: rule-layer L4 must NOT call LLM gate."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    spy = Mock(return_value=False)
    monkeypatch.setattr(
        "utils.maturity_llm_judge.llm_validate_l4", spy
    )
    result = dedupe_module._infer_maturity_relevance(_l4_qa())
    assert result == "L4"
    spy.assert_not_called()


def test_l4_with_llm_true_keeps_l4(dedupe_module, monkeypatch):
    """LLM is_l4=true keeps the L4 verdict."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    spy = Mock(return_value=True)
    monkeypatch.setattr(
        "utils.maturity_llm_judge.llm_validate_l4", spy
    )
    result = dedupe_module._infer_maturity_relevance(_l4_qa())
    assert result == "L4"
    spy.assert_called_once()


def test_l4_with_llm_false_demotes_to_l3(dedupe_module, monkeypatch):
    """LLM is_l4=false demotes the QA to L3."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    spy = Mock(return_value=False)
    monkeypatch.setattr(
        "utils.maturity_llm_judge.llm_validate_l4", spy
    )
    result = dedupe_module._infer_maturity_relevance(_l4_qa())
    assert result == "L3"
    spy.assert_called_once()


def test_blank_api_key_treated_as_missing(dedupe_module, monkeypatch):
    """Whitespace-only OPENAI_API_KEY must skip the LLM gate."""
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    spy = Mock(return_value=False)
    monkeypatch.setattr(
        "utils.maturity_llm_judge.llm_validate_l4", spy
    )
    result = dedupe_module._infer_maturity_relevance(_l4_qa())
    assert result == "L4"
    spy.assert_not_called()
