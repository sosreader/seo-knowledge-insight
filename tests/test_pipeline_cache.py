"""
Unit tests for utils/pipeline_cache.py and utils/pipeline_version.py

Run with: pytest tests/test_pipeline_cache.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ──────────────────────────────────────────────────────
# Helpers: override CACHE_DIR / VERSIONS_DIR to tmp dir
# ──────────────────────────────────────────────────────

import pytest
import utils.pipeline_cache as _pc
import utils.pipeline_version as _pv


@pytest.fixture(autouse=True)
def _tmp_dirs(tmp_path):
    """Redirect cache and version dirs to a temp directory for every test."""
    cache_dir = tmp_path / ".cache"
    versions_dir = tmp_path / ".versions"

    with (
        patch.object(_pc, "_CACHE_DIR", cache_dir),
        patch.object(_pv, "_VERSIONS_DIR", versions_dir),
        patch.object(_pv, "_REGISTRY_FILE", versions_dir / "registry.json"),
    ):
        yield


# ──────────────────────────────────────────────────────
# pipeline_cache: basic get/set
# ──────────────────────────────────────────────────────

class TestCacheGetSet:
    def test_miss_returns_none(self):
        result = _pc.cache_get("extraction", "some content")
        assert result is None

    def test_set_then_get(self):
        payload = {"qa_pairs": [{"question": "Q1", "answer": "A1"}]}
        _pc.cache_set("extraction", "meeting content", payload)
        result = _pc.cache_get("extraction", "meeting content")
        assert result == payload

    def test_different_namespaces_are_isolated(self):
        _pc.cache_set("extraction", "text", {"type": "extraction"})
        _pc.cache_set("embedding", "text", {"type": "embedding"})
        assert _pc.cache_get("extraction", "text")["type"] == "extraction"
        assert _pc.cache_get("embedding", "text")["type"] == "embedding"

    def test_different_content_gives_different_keys(self):
        _pc.cache_set("extraction", "content_a", {"qa_pairs": [{"q": "a"}]})
        # content_b has not been cached
        assert _pc.cache_get("extraction", "content_b") is None

    def test_overwrite_is_idempotent_for_same_content(self):
        _pc.cache_set("extraction", "my content", {"v": 1})
        _pc.cache_set("extraction", "my content", {"v": 2})
        # Second write overwrites; cache_get should return latest
        assert _pc.cache_get("extraction", "my content")["v"] == 2

    def test_empty_content_key(self):
        # Edge case: empty string content is still storable
        _pc.cache_set("extraction", "", {"empty": True})
        assert _pc.cache_get("extraction", "") == {"empty": True}

    def test_unicode_content(self):
        content = "SEO 會議 canonical 設定"
        payload = {"qa_pairs": [{"question": "canonical 怎麼設定？"}]}
        _pc.cache_set("classify", content, payload)
        result = _pc.cache_get("classify", content)
        assert result["qa_pairs"][0]["question"] == "canonical 怎麼設定？"


# ──────────────────────────────────────────────────────
# pipeline_cache: cache_exists
# ──────────────────────────────────────────────────────

class TestCacheExists:
    def test_false_before_set(self):
        assert not _pc.cache_exists("embedding", "vec text")

    def test_true_after_set(self):
        _pc.cache_set("embedding", "vec text", [0.1, 0.2])
        assert _pc.cache_exists("embedding", "vec text")


# ──────────────────────────────────────────────────────
# pipeline_cache: cache_stats
# ──────────────────────────────────────────────────────

class TestCacheStats:
    def test_empty_namespace(self):
        stats = _pc.cache_stats("extraction")
        assert stats == {"count": 0, "size_bytes": 0}

    def test_counts_entries(self):
        for i in range(3):
            _pc.cache_set("extraction", f"content_{i}", {"idx": i})
        stats = _pc.cache_stats("extraction")
        assert stats["count"] == 3
        assert stats["size_bytes"] > 0

    def test_size_increases_with_data(self):
        _pc.cache_set("report", "small", {"text": "x"})
        _pc.cache_set("report", "large", {"text": "x" * 10000})
        stats = _pc.cache_stats("report")
        assert stats["size_bytes"] > 1000


# ──────────────────────────────────────────────────────
# pipeline_cache: cache_clear
# ──────────────────────────────────────────────────────

class TestCacheClear:
    def test_clear_empty_namespace(self):
        n = _pc.cache_clear("extraction")
        assert n == 0

    def test_clear_removes_entries(self):
        _pc.cache_set("extraction", "c1", {"v": 1})
        _pc.cache_set("extraction", "c2", {"v": 2})
        n = _pc.cache_clear("extraction")
        assert n == 2
        assert _pc.cache_get("extraction", "c1") is None
        assert _pc.cache_stats("extraction")["count"] == 0

    def test_clear_only_affects_target_namespace(self):
        _pc.cache_set("extraction", "c", {"v": 1})
        _pc.cache_set("embedding", "c", {"v": 2})
        _pc.cache_clear("extraction")
        assert _pc.cache_get("extraction", "c") is None
        assert _pc.cache_get("embedding", "c") == {"v": 2}


# ──────────────────────────────────────────────────────
# pipeline_cache: atomic write (test file integrity)
# ──────────────────────────────────────────────────────

class TestAtomicWrite:
    def test_written_file_is_valid_json(self, tmp_path):
        """cache_set should always produce a valid JSON file."""
        _pc.cache_set("extraction", "payload", {"qa": [{"q": "Q", "a": "A"}]})
        path = _pc.cache_path("extraction", "payload")
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed["qa"][0]["q"] == "Q"


# ──────────────────────────────────────────────────────
# pipeline_version: record_artifact
# ──────────────────────────────────────────────────────

class TestRecordArtifact:
    def test_returns_entry_with_required_fields(self):
        data = {"qa_database": [{"id": 1, "question": "Q", "answer": "A"}]}
        entry = _pv.record_artifact(step=3, data=data)
        assert "version_id" in entry
        assert "content_hash" in entry
        assert "artifact_path" in entry
        assert "timestamp" in entry
        assert entry["step"] == 3

    def test_idempotent_same_content(self):
        data = {"qa_database": []}
        e1 = _pv.record_artifact(step=3, data=data)
        e2 = _pv.record_artifact(step=3, data=data)
        assert e1["version_id"] == e2["version_id"]
        assert e1["content_hash"] == e2["content_hash"]

    def test_different_data_gives_different_version(self):
        e1 = _pv.record_artifact(step=3, data={"total": 10})
        e2 = _pv.record_artifact(step=3, data={"total": 11})
        assert e1["version_id"] != e2["version_id"]

    def test_metadata_merged_into_entry(self):
        entry = _pv.record_artifact(
            step=3,
            data={"qa_database": []},
            metadata={"qa_count": 42},
        )
        assert entry["qa_count"] == 42

    def test_artifact_file_is_written(self):
        data = {"version": "1.0", "qa_database": []}
        entry = _pv.record_artifact(step=3, data=data)
        artifact_path = Path(entry["artifact_path"])
        assert artifact_path.exists()
        loaded = json.loads(artifact_path.read_text())
        assert loaded == data


# ──────────────────────────────────────────────────────
# pipeline_version: get_latest_version / get_version_history
# ──────────────────────────────────────────────────────

class TestVersionHistory:
    def test_latest_none_when_empty(self):
        assert _pv.get_latest_version(3) is None

    def test_latest_returns_last_written(self):
        _pv.record_artifact(step=3, data={"n": 1})
        _pv.record_artifact(step=3, data={"n": 2})
        latest = _pv.get_latest_version(3)
        assert latest is not None
        # The registry "latest" key should point to the last recorded version
        assert latest["step"] == 3

    def test_history_length_grows(self):
        for i in range(4):
            _pv.record_artifact(step=3, data={"n": i})
        history = _pv.get_version_history(3)
        assert len(history) == 4

    def test_history_sorted_newest_first(self):
        _pv.record_artifact(step=3, data={"n": 1})
        _pv.record_artifact(step=3, data={"n": 2})
        _pv.record_artifact(step=3, data={"n": 3})
        history = _pv.get_version_history(3)
        # Timestamps should be in descending order
        for i in range(len(history) - 1):
            assert history[i]["timestamp"] >= history[i + 1]["timestamp"]

    def test_steps_are_isolated(self):
        _pv.record_artifact(step=2, data={"step": 2})
        _pv.record_artifact(step=3, data={"step": 3})
        assert len(_pv.get_version_history(2)) == 1
        assert len(_pv.get_version_history(3)) == 1

    def test_history_empty_for_unknown_step(self):
        assert _pv.get_version_history(99) == []


# ──────────────────────────────────────────────────────
# pipeline_version: content_hash
# ──────────────────────────────────────────────────────

class TestContentHash:
    def test_same_data_same_hash(self):
        data = {"qa_database": [{"id": 1, "q": "Q"}]}
        assert _pv.content_hash(data) == _pv.content_hash(data)

    def test_different_data_different_hash(self):
        assert _pv.content_hash({"n": 1}) != _pv.content_hash({"n": 2})

    def test_key_order_does_not_matter(self):
        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        assert _pv.content_hash(d1) == _pv.content_hash(d2)

    def test_hash_is_16_chars(self):
        assert len(_pv.content_hash({"x": "y"})) == 16


# ──────────────────────────────────────────────────────
# pipeline_version: token stats
# ──────────────────────────────────────────────────────

class TestTokenStats:
    def test_empty_registry(self):
        stats = _pv.get_all_token_stats()
        assert stats["total_used"] == 0
        assert stats["total_saved"] == 0

    def test_accumulates_across_steps(self):
        _pv.record_artifact(step=2, data={"s": "a"}, tokens_used=1000, tokens_saved=0)
        _pv.record_artifact(step=3, data={"s": "b"}, tokens_used=500, tokens_saved=2000)
        stats = _pv.get_all_token_stats()
        assert stats["total_used"] == 1500
        assert stats["total_saved"] == 2000
        assert stats["by_step"][2]["used"] == 1000
        assert stats["by_step"][3]["saved"] == 2000


# ──────────────────────────────────────────────────
# Phase A: Version Registry 增強測試
# ──────────────────────────────────────────────────

class TestResolveStep:
    def test_int_passthrough(self):
        assert _pv.resolve_step(2) == 2

    def test_str_name_extract_qa(self):
        assert _pv.resolve_step("extract-qa") == 2

    def test_str_digit(self):
        assert _pv.resolve_step("3") == 3

    def test_unknown_str_raises_value_error(self):
        import pytest
        with pytest.raises(ValueError, match="未知"):
            _pv.resolve_step("unknown-step")

    def test_wrong_type_raises_type_error(self):
        import pytest
        with pytest.raises(TypeError):
            _pv.resolve_step(3.14)  # type: ignore[arg-type]


class TestRecordArtifactStepName:
    def test_entry_has_step_name_field(self):
        entry = _pv.record_artifact(step=2, data={"test": True})
        assert entry.get("step_name") == "extract-qa"

    def test_str_step_name_accepted(self):
        entry = _pv.record_artifact(step="extract-qa", data={"str_step": True})
        assert entry["step"] == 2

    def test_label_stored_in_entry(self):
        entry = _pv.record_artifact(step=3, data={"label_test": True}, label="全量重跑@2026-03-02")
        assert entry.get("label") == "全量重跑@2026-03-02"

    def test_no_label_key_absent(self):
        entry = _pv.record_artifact(step=3, data={"no_label": True})
        assert "label" not in entry


class TestLabelVersion:
    def test_label_existing_version(self):
        entry = _pv.record_artifact(step=2, data={"to_label": True})
        vid = entry["version_id"]
        result = _pv.label_version(vid, "初版@2026-03-02")
        assert result is not None
        assert result.get("label") == "初版@2026-03-02"

    def test_label_persists_in_registry(self):
        entry = _pv.record_artifact(step=2, data={"persist": True})
        vid = entry["version_id"]
        _pv.label_version(vid, "持久標籤@2026-03-02")
        history = _pv.get_version_history(2)
        labeled = next((v for v in history if v["version_id"] == vid), None)
        assert labeled is not None
        assert labeled.get("label") == "持久標籤@2026-03-02"

    def test_unknown_version_returns_none(self):
        assert _pv.label_version("nonexistent_id", "some_label") is None

    def test_overwrite_existing_label(self):
        entry = _pv.record_artifact(step=2, data={"overwrite": True})
        vid = entry["version_id"]
        _pv.label_version(vid, "舊標籤@2026-02-28")
        result = _pv.label_version(vid, "新標籤@2026-03-02")
        assert result.get("label") == "新標籤@2026-03-02"


class TestRegisterExistingFile:
    def test_register_json_file(self, tmp_path):
        f = tmp_path / "qa_final.json"
        f.write_text('{"qa_database": []}', encoding="utf-8")
        entry = _pv.register_existing_file(step=3, file_path=f)
        assert entry["step"] == 3
        assert entry["step_name"] == "dedupe-classify"

    def test_idempotent(self, tmp_path):
        f = tmp_path / "qa_test.json"
        f.write_text('{"test": 1}', encoding="utf-8")
        e1 = _pv.register_existing_file(step=3, file_path=f)
        e2 = _pv.register_existing_file(step=3, file_path=f)
        assert e1["version_id"] == e2["version_id"]

    def test_with_label(self, tmp_path):
        f = tmp_path / "labeled.json"
        f.write_text('{"data": true}', encoding="utf-8")
        entry = _pv.register_existing_file(step=2, file_path=f, label="帶標籤@2026-03-02")
        assert entry.get("label") == "帶標籤@2026-03-02"

    def test_file_not_found_raises(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            _pv.register_existing_file(step=2, file_path=Path("/nonexistent/path.json"))

    def test_str_step_name(self, tmp_path):
        f = tmp_path / "str_step.json"
        f.write_text('{"step": "name"}', encoding="utf-8")
        entry = _pv.register_existing_file(step="extract-qa", file_path=f)
        assert entry["step"] == 2


class TestVersionHistoryStepName:
    def test_str_name_equals_int(self):
        _pv.record_artifact(step=2, data={"hist_test": True})
        by_int = _pv.get_version_history(2)
        by_name = _pv.get_version_history("extract-qa")
        assert len(by_int) == len(by_name)
        assert by_int[0]["version_id"] == by_name[0]["version_id"]

    def test_get_latest_by_str_name(self):
        _pv.record_artifact(step=3, data={"latest_name": True})
        by_int = _pv.get_latest_version(3)
        by_name = _pv.get_latest_version("dedupe-classify")
        assert by_int is not None
        assert by_name is not None
        assert by_int["version_id"] == by_name["version_id"]

    def test_unknown_step_name_history_empty(self):
        import pytest
        with pytest.raises(ValueError):
            _pv.get_version_history("nonexistent-step")
