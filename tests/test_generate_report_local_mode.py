from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from unittest.mock import patch


_MOD_PATH = Path(__file__).resolve().parent.parent / "scripts" / "04_generate_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_report_local", _MOD_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


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