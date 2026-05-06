from __future__ import annotations

import importlib
from unittest.mock import patch


def _import_dedupe_module():
    return importlib.import_module("scripts.03_dedupe_classify")


def test_deduplicate_preserves_single_source_model_on_merge() -> None:
    mod = _import_dedupe_module()
    qa_pairs = [
        {
            "question": "Q1",
            "answer": "A1",
            "source_collection": "ahrefs-blog",
            "source_type": "article",
            "source_url": "https://example.com/a1",
            "stable_id": "source-1",
            "extraction_model": "gpt-5.4-nano",
        },
        {
            "question": "Q2",
            "answer": "A2",
            "source_collection": "ahrefs-blog",
            "source_type": "article",
            "source_url": "https://example.com/a2",
            "stable_id": "source-2",
            "extraction_model": "gpt-5.4-nano",
        },
    ]

    with (
        patch.object(mod, "find_duplicate_groups", return_value=([[0, 1]], [])),
        patch.object(mod, "merge_similar_qas", return_value=({"question": "Merged", "answer": "Merged answer"}, True)),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False),
        patch("time.sleep"),
    ):
        result = mod.deduplicate_qas(qa_pairs)

    assert result[0]["extraction_model"] == "gpt-5.4-nano"
    assert result[0]["extraction_provenance"]["source_models"] == ["gpt-5.4-nano"]
    assert result[0]["extraction_provenance"]["provenance_status"] == "single-source"
    assert result[0]["extraction_provenance"]["merge_model"] == "gpt-5.4-nano"


def test_deduplicate_marks_mixed_source_models_without_overwriting_history() -> None:
    mod = _import_dedupe_module()
    qa_pairs = [
        {
            "question": "Q1",
            "answer": "A1",
            "source_collection": "seo-meetings",
            "source_type": "meeting",
            "source_url": "https://example.com/q1",
            "stable_id": "source-1",
            "extraction_model": "claude-code",
        },
        {
            "question": "Q2",
            "answer": "A2",
            "source_collection": "seo-meetings",
            "source_type": "meeting",
            "source_url": "https://example.com/q2",
            "stable_id": "source-2",
            "extraction_model": "claude-code-heuristic",
        },
    ]

    with (
        patch.object(mod, "find_duplicate_groups", return_value=([[0, 1]], [])),
        patch.object(mod, "merge_similar_qas", return_value=({"question": "Merged", "answer": "Merged answer"}, True)),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False),
        patch("time.sleep"),
    ):
        result = mod.deduplicate_qas(qa_pairs)

    assert result[0]["extraction_model"] == "mixed"
    assert result[0]["extraction_provenance"]["source_models"] == [
        "claude-code",
        "claude-code-heuristic",
    ]
    assert result[0]["extraction_provenance"]["provenance_status"] == "mixed-source"