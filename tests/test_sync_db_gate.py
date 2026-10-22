"""scripts/sync_db_gate.py：發布閘門（語意對齊已移除的 TS 版 publication-gate.ts 備份版）。"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync_db_gate as gate  # noqa: E402

CONTENT = "# 測試稿\n評分尚待確認\n".encode("utf-8")
FILENAME = "report_20260912_aaaaaaaa.md"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entry(filename: str = FILENAME, status: str = "approved", **override) -> dict:
    base = {
        "filename": filename,
        "sha256": _sha(CONTENT),
        "status": status,
        "reviewed_by": "test-reviewer",
        "reviewed_at": "2026-09-12",
        "reason": "僅測試 fixture",
    }
    return {**base, **override}


def _manifest(*entries: dict, version: int = 1) -> dict:
    return {"version": version, "entries": list(entries)}


class TestBlockReason:
    def test_approved_and_hash_match_passes(self):
        assert gate.publication_block_reason(_manifest(_entry()), FILENAME, CONTENT) is None

    @pytest.mark.parametrize("status", ["pending", "historical"])
    def test_non_approved_status_blocks_with_status(self, status):
        assert gate.publication_block_reason(_manifest(_entry(status=status)), FILENAME, CONTENT) == status

    def test_missing_entry_blocks(self):
        assert gate.publication_block_reason(_manifest(), FILENAME, CONTENT) == "missing_review"

    def test_hash_drift_blocks_as_content_changed(self):
        reason = gate.publication_block_reason(_manifest(_entry()), FILENAME, CONTENT + b"x")
        assert reason == "content_changed"

    def test_invalid_filename_blocks_before_manifest(self):
        assert gate.publication_block_reason(None, "../" + FILENAME, CONTENT) == "invalid_filename"

    def test_legacy_report_without_hash_suffix_is_valid(self):
        legacy = "report_20260912.md"
        assert gate.publication_block_reason(_manifest(_entry(legacy)), legacy, CONTENT) is None

    def test_meeting_prep_filename_requires_hash_suffix(self):
        assert gate.publication_block_reason(_manifest(), "meeting_prep_20260912.md", CONTENT) == "invalid_filename"

    @pytest.mark.parametrize("manifest", [None, [], {}, {"version": 1, "entries": None},
                                          {"version": 1, "entries": [None]}, {"version": 2, "entries": []}])
    def test_invalid_root_closes_gate(self, manifest):
        assert gate.publication_block_reason(manifest, FILENAME, CONTENT) == "invalid_review_manifest"

    @pytest.mark.parametrize("override", [
        {"reviewed_by": ""},
        {"reviewed_by": "   "},
        {"reviewed_at": "yesterday"},
        {"reviewed_at": "2026-02-30"},
        {"reason": " "},
        {"filename": "../" + FILENAME},
        {"sha256": "bad"},
        {"sha256": "A" * 64},
        {"status": True},
        {"status": "rejected"},
    ])
    def test_invalid_entry_closes_whole_manifest(self, override):
        manifest = _manifest(_entry(**override))
        assert gate.publication_block_reason(manifest, FILENAME, CONTENT) == "invalid_review_manifest"

    @pytest.mark.parametrize("override", [
        {"filename": FILENAME + "\n"}, {"sha256": "a" * 64 + "\n"}, {"reviewed_at": "2026-09-12\n"},
    ])
    def test_trailing_newline_closes_manifest_like_ts(self, override):
        assert gate.publication_block_reason(_manifest(_entry(**override)), FILENAME, CONTENT) == "invalid_review_manifest"

    def test_trailing_newline_target_filename_is_invalid(self):
        assert gate.publication_block_reason(_manifest(_entry()), FILENAME + "\n", CONTENT) == "invalid_filename"

    def test_duplicate_filenames_close_manifest(self):
        assert gate.publication_block_reason(_manifest(_entry(), _entry()), FILENAME, CONTENT) == "invalid_review_manifest"

    def test_does_not_mutate_manifest(self):
        manifest = _manifest(_entry())
        snapshot = json.dumps(manifest, sort_keys=True)
        gate.publication_block_reason(manifest, FILENAME, CONTENT)
        assert json.dumps(manifest, sort_keys=True) == snapshot


class TestLoadManifest:
    def test_missing_file_is_unavailable(self, tmp_path):
        with pytest.raises(gate.PublicationBlocked) as exc:
            gate.load_manifest(tmp_path / "nope.json")
        assert exc.value.reason == "review_manifest_unavailable"

    def test_malformed_json_is_unavailable_and_does_not_leak(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text("malformed-private-details", encoding="utf-8")
        with pytest.raises(gate.PublicationBlocked) as exc:
            gate.load_manifest(path)
        assert exc.value.reason == "review_manifest_unavailable"
        assert "malformed-private-details" not in str(exc.value)

    def test_oversized_manifest_is_unavailable(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(" " * (gate.MAX_MANIFEST_BYTES + 1), encoding="utf-8")
        with pytest.raises(gate.PublicationBlocked) as exc:
            gate.load_manifest(path)
        assert exc.value.reason == "review_manifest_unavailable"

    def test_invalid_structure_raises_invalid(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps({"version": 1, "entries": [{"filename": "x"}]}), encoding="utf-8")
        with pytest.raises(gate.PublicationBlocked) as exc:
            gate.load_manifest(path)
        assert exc.value.reason == "invalid_review_manifest"

    def test_valid_manifest_returns_frozen_entries(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps(_manifest(_entry())), encoding="utf-8")
        entries = gate.load_manifest(path)
        assert isinstance(entries, tuple)
        assert entries[0].filename == FILENAME
        assert entries[0].status == "approved"
        with pytest.raises(AttributeError):
            entries[0].status = "pending"  # type: ignore[misc]


class TestEvaluate:
    def test_evaluate_returns_entry_for_approved(self):
        entries = gate.parse_manifest(_manifest(_entry()))
        decision = gate.evaluate(entries, FILENAME, CONTENT)
        assert decision.reason is None
        assert decision.entry is not None and decision.entry.reviewed_at == "2026-09-12"
        assert decision.sha256 == _sha(CONTENT)

    def test_evaluate_reports_drift_with_both_hashes(self):
        entries = gate.parse_manifest(_manifest(_entry()))
        decision = gate.evaluate(entries, FILENAME, b"other")
        assert decision.reason == "content_changed"
        assert decision.entry.sha256 == _sha(CONTENT)
        assert decision.sha256 == _sha(b"other")


def test_repo_manifest_is_valid_and_keeps_historical_blocked():
    root = Path(__file__).resolve().parent.parent
    manifest = json.loads((root / "data/content-publication-review.json").read_text(encoding="utf-8"))
    entries = gate.parse_manifest(manifest)
    assert entries is not None
    for filename in ("report_20260904_9d41f7b2.md", "meeting_prep_20260904_c7a2e9f1.md"):
        assert gate.publication_block_reason(manifest, filename, CONTENT) == "historical"
    approved = {e.filename for e in entries if e.status == "approved"}
    assert {"report_20261012_900a1937.md", "meeting_prep_20261009_0fc3dcbc.md"} <= approved
