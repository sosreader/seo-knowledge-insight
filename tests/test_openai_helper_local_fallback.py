from __future__ import annotations

import math
import os
from unittest.mock import patch

from utils import openai_helper


def test_get_embeddings_falls_back_without_openai_key() -> None:
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        vectors = openai_helper.get_embeddings(["canonical tag SEO", "canonical tag SEO"])

    assert len(vectors) == 2
    assert len(vectors[0]) == len(vectors[1]) == 256
    assert vectors[0] == vectors[1]
    norm = math.sqrt(sum(value * value for value in vectors[0]))
    assert math.isclose(norm, 1.0, rel_tol=1e-6)


def test_merge_similar_qas_falls_back_without_openai_key() -> None:
    qa_group = [
        {
            "question": "網站 canonical 設錯會造成什麼索引問題？",
            "answer": "canonical 若指向錯誤 URL，Google 可能選錯標準頁，造成索引混亂。",
            "keywords": ["canonical", "索引"],
            "source_date": "2026-03-01",
            "source_title": "A",
            "source_file": "a.md",
            "stable_id": "a1",
        },
        {
            "question": "網站 canonical 設錯時，應如何修正？",
            "answer": "應統一指向乾淨 URL，並在 GSC 驗證 Google 選擇的 canonical 是否符合預期。",
            "keywords": ["canonical", "GSC", "索引"],
            "source_date": "2026-03-08",
            "source_title": "B",
            "source_file": "b.md",
            "stable_id": "b1",
        },
    ]

    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        merged = openai_helper.merge_similar_qas(qa_group)

    assert "canonical" in [keyword.lower() for keyword in merged["keywords"]]
    assert merged["source_dates"] == ["2026-03-01", "2026-03-08"]
    assert len(merged["merged_from"]) == 2
    assert "補充" in merged["answer"] or "GSC" in merged["answer"]


def test_classify_qa_falls_back_without_openai_key() -> None:
    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False),
        patch("utils.pipeline_cache.cache_get", return_value=None),
        patch("utils.pipeline_cache.cache_set"),
    ):
        result = openai_helper.classify_qa(
            "canonical 設錯會帶來哪些索引風險？",
            "若 canonical 指向錯誤頁面，Google 可能選錯標準 URL，導致重複內容與索引訊號分散。",
        )

    assert result["category"] == "索引與檢索"
    assert result["difficulty"] == "進階"
    assert result["evergreen"] is True