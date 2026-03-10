"""Tests for backfill_extraction_model.py."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from unittest.mock import patch

from scripts.backfill_extraction_model import (
    _compute_stable_id,
    _scan_per_meeting_files,
    backfill,
)


class TestComputeStableId:
    def test_deterministic(self):
        sid1 = _compute_stable_id("file.md", "What is SEO?")
        sid2 = _compute_stable_id("file.md", "What is SEO?")
        assert sid1 == sid2

    def test_hex_16_chars(self):
        sid = _compute_stable_id("test.md", "How to optimize?")
        assert len(sid) == 16
        assert all(c in "0123456789abcdef" for c in sid)

    def test_different_inputs(self):
        sid1 = _compute_stable_id("a.md", "Q1")
        sid2 = _compute_stable_id("b.md", "Q2")
        assert sid1 != sid2


class TestScanPerMeetingFiles:
    def test_returns_empty_when_dir_missing(self, tmp_path):
        with patch(
            "scripts.backfill_extraction_model.ROOT_DIR",
            tmp_path,
        ):
            result = _scan_per_meeting_files()
            assert result == {}

    def test_scans_files_with_model(self, tmp_path):
        qa_dir = tmp_path / "output" / "qa_per_meeting"
        qa_dir.mkdir(parents=True)

        qa_data = {
            "extraction_model": "gpt-4o",
            "qa_pairs": [
                {
                    "question": "What is SEO?",
                    "source_file": "test.md",
                }
            ],
        }
        (qa_dir / "test_qa.json").write_text(json.dumps(qa_data))

        with patch(
            "scripts.backfill_extraction_model.ROOT_DIR",
            tmp_path,
        ):
            result = _scan_per_meeting_files()
            assert len(result) == 1
            model = list(result.values())[0]
            assert model == "gpt-4o"

    def test_skips_invalid_json(self, tmp_path):
        qa_dir = tmp_path / "output" / "qa_per_meeting"
        qa_dir.mkdir(parents=True)
        (qa_dir / "bad_qa.json").write_text("not json")

        with patch(
            "scripts.backfill_extraction_model.ROOT_DIR",
            tmp_path,
        ):
            result = _scan_per_meeting_files()
            assert result == {}


class TestBackfillDryRun:
    @patch("scripts.backfill_extraction_model._fetch_null_model_ids")
    @patch("scripts.backfill_extraction_model._scan_per_meeting_files")
    def test_dry_run_no_write(self, mock_scan, mock_fetch):
        mock_scan.return_value = {}
        mock_fetch.return_value = [
            {"id": "abc123", "question": "Q1", "source_title": "S1"},
        ]

        result = backfill("http://fake", "key", dry_run=True)
        assert result["dry_run"] is True
        assert result["total"] == 1
        assert result["updated"] == 0

    @patch("scripts.backfill_extraction_model._fetch_null_model_ids")
    @patch("scripts.backfill_extraction_model._scan_per_meeting_files")
    def test_no_items_returns_zero(self, mock_scan, mock_fetch):
        mock_scan.return_value = {}
        mock_fetch.return_value = []

        result = backfill("http://fake", "key", dry_run=True)
        assert result["total"] == 0

    @patch("scripts.backfill_extraction_model._patch_batch")
    @patch("scripts.backfill_extraction_model._fetch_null_model_ids")
    @patch("scripts.backfill_extraction_model._scan_per_meeting_files")
    def test_execute_calls_patch(self, mock_scan, mock_fetch, mock_patch):
        mock_scan.return_value = {}
        mock_fetch.return_value = [
            {"id": "abc123", "question": "Q1", "source_title": "S1"},
        ]
        mock_patch.return_value = (1, 0)

        result = backfill("http://fake", "key", dry_run=False)
        assert result["updated"] == 1
        mock_patch.assert_called_once()
