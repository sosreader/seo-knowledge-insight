from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import numpy as np
import pytest


_MOD_PATH = Path(__file__).resolve().parent.parent / "scripts" / "04_generate_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_report_step", _MOD_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_mod = _load_module()


def _unit_vector(index: int, dim: int) -> list[float]:
    vector = [0.0] * dim
    vector[index] = 1.0
    return vector


def test_find_relevant_qas_uses_local_fallback_for_persisted_embedding_dim_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    qa_pairs = [
        {
            "question": "canonical 設定錯誤會造成什麼索引問題？",
            "answer": "canonical 指向錯誤 URL 會讓 Google 選錯標準頁。",
        },
        {
            "question": "GA4 事件追蹤掉資料要怎麼排查？",
            "answer": "先檢查事件是否真的送出與報表是否正確接收。",
        },
    ]
    persisted_embs = np.array([
        _unit_vector(0, 256),
        _unit_vector(1, 256),
    ])

    monkeypatch.setattr(_mod, "_load_persisted_embeddings", lambda qa_count: persisted_embs)
    monkeypatch.setattr(_mod, "get_embeddings", lambda texts: [_unit_vector(0, 1536) for _ in texts])
    monkeypatch.setattr(_mod, "get_local_embeddings", lambda texts: [_unit_vector(0, 256) for _ in texts])
    monkeypatch.setattr(
        _mod,
        "_compute_keyword_boost",
        lambda queries, pairs, boost=None, max_hits=None: np.zeros((len(queries), len(pairs))),
    )

    with caplog.at_level(logging.WARNING):
        results = _mod.find_relevant_qas_multi(
            queries=["canonical 問題"],
            qa_pairs=qa_pairs,
            top_k_per_query=1,
            total_max=1,
            min_score=-1,
        )

    assert len(results) == 1
    assert results[0]["question"] == qa_pairs[0]["question"]
    assert results[0]["_queries"] == ["canonical 問題"]
    assert "local fallback" in caplog.text


def test_find_relevant_qas_raises_when_no_compatible_embedding_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    qa_pairs = [{"question": "canonical", "answer": "answer"}]
    persisted_embs = np.array([_unit_vector(0, 384)])

    monkeypatch.setattr(_mod, "_load_persisted_embeddings", lambda qa_count: persisted_embs)
    monkeypatch.setattr(_mod, "get_embeddings", lambda texts: [_unit_vector(0, 1536) for _ in texts])
    monkeypatch.setattr(_mod, "get_local_embeddings", lambda texts: [_unit_vector(0, 256) for _ in texts])

    with pytest.raises(ValueError, match="qa_embeddings.npy"):
        _mod.find_relevant_qas_multi(
            queries=["canonical"],
            qa_pairs=qa_pairs,
            top_k_per_query=1,
            total_max=1,
            min_score=-1,
        )