from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import Mock, call

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def dedupe_module():
    return importlib.import_module("scripts.03_dedupe_classify")


def test_classify_all_qas_only_sleeps_when_helper_reports_remote_call(dedupe_module, monkeypatch):
    qa_pairs = [
        {"question": "快取命中問題", "answer": "快取命中回答"},
        {"question": "快取未命中問題", "answer": "快取未命中回答"},
    ]

    sleep_mock = Mock()
    classify_mock = Mock(side_effect=[
        ({"category": "其他", "difficulty": "基礎", "evergreen": True}, False),
        ({"category": "技術SEO", "difficulty": "進階", "evergreen": False}, True),
    ])

    monkeypatch.setattr(dedupe_module.time, "sleep", sleep_mock)
    monkeypatch.setattr(dedupe_module, "classify_qa", classify_mock)

    result = dedupe_module.classify_all_qas(qa_pairs)

    assert [item["category"] for item in result] == ["其他", "技術SEO"]
    assert classify_mock.call_args_list == [
        call("快取命中問題", "快取命中回答", return_used_remote=True),
        call("快取未命中問題", "快取未命中回答", return_used_remote=True),
    ]
    sleep_mock.assert_called_once_with(0.3)


def test_classify_all_qas_exception_path_does_not_sleep(dedupe_module, monkeypatch):
    qa_pairs = [{"question": "例外問題", "answer": "例外回答"}]

    sleep_mock = Mock()
    classify_mock = Mock(side_effect=RuntimeError("boom"))

    monkeypatch.setattr(dedupe_module.time, "sleep", sleep_mock)
    monkeypatch.setattr(dedupe_module, "classify_qa", classify_mock)

    result = dedupe_module.classify_all_qas(qa_pairs)

    assert result[0]["category"] == "其他"
    assert result[0]["difficulty"] == "基礎"
    assert result[0]["evergreen"] is True
    sleep_mock.assert_not_called()


def test_deduplicate_qas_only_sleeps_when_merge_reports_remote_call(dedupe_module, monkeypatch):
    qa_pairs = [
        {
            "question": "重複問題 A",
            "answer": "回答 A",
            "source_collection": "test-collection",
            "source_type": "article",
            "source_url": "https://example.com/a",
            "stable_id": "a1",
        },
        {
            "question": "重複問題 B",
            "answer": "回答 B",
            "source_collection": "test-collection",
            "source_type": "article",
            "source_url": "https://example.com/b",
            "stable_id": "b1",
        },
        {
            "question": "唯一問題",
            "answer": "唯一回答",
            "source_collection": "test-collection",
            "source_type": "article",
            "source_url": "https://example.com/c",
            "stable_id": "c1",
        },
        {
            "question": "唯一問題 2",
            "answer": "唯一回答 2",
            "source_collection": "test-collection",
            "source_type": "article",
            "source_url": "https://example.com/d",
            "stable_id": "d1",
        },
    ]

    sleep_mock = Mock()
    merge_mock = Mock(side_effect=[
        (
            {
                "question": "合併後問題 1",
                "answer": "合併後回答 1",
                "keywords": ["seo"],
                "source_dates": [],
                "merged_from": [],
            },
            False,
        ),
        (
            {
                "question": "合併後問題 2",
                "answer": "合併後回答 2",
                "keywords": ["seo"],
                "source_dates": [],
                "merged_from": [],
            },
            True,
        ),
    ])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(dedupe_module.time, "sleep", sleep_mock)
    monkeypatch.setattr(dedupe_module, "merge_similar_qas", merge_mock)
    monkeypatch.setattr(dedupe_module, "find_duplicate_groups", Mock(return_value=([[0, 1], [2, 3]], [])))

    result = dedupe_module.deduplicate_qas(qa_pairs)

    assert len(result) == 2
    assert [item["question"] for item in result] == ["合併後問題 1", "合併後問題 2"]
    assert merge_mock.call_args_list == [
        call([qa_pairs[0], qa_pairs[1]], return_used_remote=True),
        call([qa_pairs[2], qa_pairs[3]], return_used_remote=True),
    ]
    sleep_mock.assert_called_once_with(0.5)