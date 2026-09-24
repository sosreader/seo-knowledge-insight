from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import pytest


_MOD_PATH = Path(__file__).resolve().parent.parent / "scripts" / "04_generate_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_report_local", _MOD_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.mark.parametrize("model", ["gpt-6-sol", "gpt-5.4"])
def test_remote_report_preserves_reasoning_and_model_metadata(model, monkeypatch):
    mod = _load_module()
    monkeypatch.setitem(mod.config.__dict__, "OPENAI_API_KEY", "test-key")
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="週報內容"))])
    with patch.object(mod, "_has_openai_key", return_value=True), \
         patch.object(mod.config, "REPORT_MODEL", model), \
         patch.object(mod, "OpenAI") as client:
        create = client.return_value.chat.completions.create
        create.return_value = response
        report = mod.generate_report("指標摘要", [], "2026/09/23")
    request = create.call_args.kwargs
    assert request["model"] == model
    assert request["max_completion_tokens"] == 16384
    if model == "gpt-6-sol":
        assert request["reasoning_effort"] == "none"
    else:
        assert "reasoning_effort" not in request
    assert f'"model": "{model}"' in report


def test_report_cache_isolates_generation_and_rerank_models(monkeypatch, tmp_path):
    mod = _load_module()
    import utils.pipeline_cache as cache

    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path)
    monkeypatch.setitem(mod.config.__dict__, "REPORT_MODEL", "gpt-5.4")
    monkeypatch.setitem(mod.config.__dict__, "EVAL_JUDGE_MODEL", "gpt-5.4-nano")
    with patch.object(mod, "_has_openai_key", return_value=True), \
         patch.object(mod, "generate_report", side_effect=["old", "new", "reranked", "forced"]) as generate:
        args = ("summary", [], "2026/09/23", 1, "qa-v1")
        assert mod._generate_report_cached(*args) == "old"
        assert mod._generate_report_cached(*args) == "old"
        monkeypatch.setitem(mod.config.__dict__, "REPORT_MODEL", "gpt-6-sol")
        assert mod._generate_report_cached(*args) == "new"
        monkeypatch.setitem(mod.config.__dict__, "EVAL_JUDGE_MODEL", "gpt-6-luna")
        assert mod._generate_report_cached(*args) == "reranked"
        assert mod._generate_report_cached(*args, no_cache=True) == "forced"
        assert generate.call_count == 4


def test_rerank_qas_returns_original_order_without_openai_key() -> None:
    mod = _load_module()
    candidates = [
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2", "answer": "A2"},
        {"question": "Q3", "answer": "A3"},
    ]

    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        result = mod._rerank_qas(candidates, "summary", top_k=2)

    assert result == candidates[:2]


def test_generate_report_uses_local_fallback_without_openai_key() -> None:
    mod = _load_module()
    relevant_qas = [
        {
            "id": 1,
            "question": "Q1",
            "answer": "[What] 指標 A 下滑 [Why] 可能是索引面問題 [How] 先查 Search Console [Evidence] 來自會議。",
            "source_title": "SEO Meeting",
            "source_date": "2026-04-27",
            "source_collection": "seo-meetings",
        },
        {
            "id": 2,
            "question": "Q2",
            "answer": "[What] 指標 B 波動 [Why] 可能是頁型重分配 [How] 分頁型檢查 [Evidence] 來自會議。",
            "source_title": "SEO Meeting",
            "source_date": "2026-04-27",
            "source_collection": "seo-meetings",
        },
        {
            "id": 3,
            "question": "Q3",
            "answer": "[What] 指標 C 惡化 [Why] 可能是 CSR 問題 [How] 改查 SSR [Evidence] 來自會議。",
            "source_title": "SEO Meeting",
            "source_date": "2026-04-27",
            "source_collection": "seo-meetings",
        },
        {
            "id": 4,
            "question": "Q4",
            "answer": "[What] 指標 D 回升 [Why] 可能是修復生效 [How] 持續監測 [Evidence] 來自會議。",
            "source_title": "SEO Meeting",
            "source_date": "2026-04-27",
            "source_collection": "seo-meetings",
        },
    ]
    metrics_summary = "\n".join([
        "【核心指標】",
        "曝光: 最新 100 | 月趨勢 -20.0% | 週趨勢 -10.0%",
        "CTR: 最新 2.1% | 月趨勢 +5.0% | 週趨勢 +2.0%",
        "【顯著下滑（月趨勢）】",
        "Discover: -25.0% (月) / -18.0% (週)",
        "檢索未索引: -18.0% (月) / +12.0% (週)",
        "【顯著上升（月趨勢）】",
        "AMP Ratio: +20.0% (月) / +5.0% (週)",
    ])

    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        report = mod.generate_report(metrics_summary, relevant_qas, "2026/05/02", weeks=2)

    assert "Claude Code 生成（無 OpenAI / 外部 LLM 依賴）" in report
    assert "## 一、本週 SEO 情勢快照" in report
    assert "## 七、來源" in report
    assert "[知識庫1 →](/admin/seoInsight/1)" in report
    assert "[1]" in report
