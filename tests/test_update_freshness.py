"""Tests for update_freshness.py."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import math
from datetime import datetime, timezone
from unittest.mock import Mock
from unittest.mock import patch

from scripts.update_freshness import (
    HALF_LIFE_DAYS,
    LAMBDA,
    _verify,
    _fetch_items,
    _patch_batch,
    compute_freshness_score,
    update_freshness,
)


class TestComputeFreshnessScore:
    """Test the exponential decay freshness function."""

    def test_evergreen_always_one(self):
        assert compute_freshness_score("2020-01-01", evergreen=True) == 1.0

    def test_today_returns_one(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert compute_freshness_score(today, evergreen=False) == 1.0

    def test_future_date_returns_one(self):
        assert compute_freshness_score("2099-01-01", evergreen=False) == 1.0

    def test_half_life_returns_half(self):
        ref = datetime(2026, 1, 1, tzinfo=timezone.utc)
        half_life_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        from datetime import timedelta
        past = half_life_date - timedelta(days=HALF_LIFE_DAYS)
        score = compute_freshness_score(
            past.strftime("%Y-%m-%d"),
            evergreen=False,
            reference_date=ref,
        )
        assert abs(score - 0.5) < 0.01

    def test_very_old_near_zero(self):
        ref = datetime(2026, 3, 10, tzinfo=timezone.utc)
        score = compute_freshness_score("2018-01-01", evergreen=False, reference_date=ref)
        assert score < 0.1
        assert score >= 0.01  # floor

    def test_unknown_date_returns_one(self):
        assert compute_freshness_score("", evergreen=False) == 1.0
        assert compute_freshness_score("invalid", evergreen=False) == 1.0

    def test_score_monotonically_decreasing(self):
        ref = datetime(2026, 3, 10, tzinfo=timezone.utc)
        s1 = compute_freshness_score("2026-01-01", False, ref)
        s2 = compute_freshness_score("2025-01-01", False, ref)
        s3 = compute_freshness_score("2024-01-01", False, ref)
        assert s1 > s2 > s3

    def test_floor_at_001(self):
        ref = datetime(2026, 1, 1, tzinfo=timezone.utc)
        score = compute_freshness_score("2000-01-01", False, ref)
        assert score == 0.01


class TestUpdateFreshnessDryRun:
    @patch("scripts.update_freshness._fetch_items")
    def test_dry_run_no_write(self, mock_fetch):
        mock_fetch.return_value = [
            {"id": "a1", "source_date": "2023-01-01", "evergreen": False, "freshness_score": 1.0},
        ]
        result = update_freshness("http://fake", "key", dry_run=True)
        assert result["dry_run"] is True
        assert result["need_update"] > 0

    @patch("scripts.update_freshness._fetch_items")
    def test_evergreen_skipped(self, mock_fetch):
        mock_fetch.return_value = [
            {"id": "a1", "source_date": "2020-01-01", "evergreen": True, "freshness_score": 1.0},
        ]
        result = update_freshness("http://fake", "key", dry_run=True)
        assert result["skipped"] == 1
        assert result["need_update"] == 0

    @patch("scripts.update_freshness._fetch_items")
    def test_no_items(self, mock_fetch):
        mock_fetch.return_value = []
        result = update_freshness("http://fake", "key", dry_run=True)
        assert result["total"] == 0

    @patch("scripts.update_freshness._patch_batch")
    @patch("scripts.update_freshness._fetch_items")
    def test_execute_calls_patch(self, mock_fetch, mock_patch):
        mock_fetch.return_value = [
            {"id": "a1", "source_date": "2023-01-01", "evergreen": False, "freshness_score": 1.0},
        ]
        mock_patch.return_value = (1, 0)

        result = update_freshness("http://fake", "key", dry_run=False)
        assert result["updated"] == 1
        mock_patch.assert_called_once()


class TestUpdateFreshnessSupabaseIO:
    @patch("scripts.update_freshness.requests.get")
    def test_fetch_items_paginates_past_1000(self, mock_get):
        first = Mock(status_code=200)
        first.json.return_value = [
            {"id": f"id-{i}", "source_date": "2023-01-01", "evergreen": False, "freshness_score": 1.0}
            for i in range(1000)
        ]
        second = Mock(status_code=200)
        second.json.return_value = [
            {"id": f"id-{1000 + i}", "source_date": "2023-01-01", "evergreen": False, "freshness_score": 1.0}
            for i in range(329)
        ]
        mock_get.side_effect = [first, second]

        result = _fetch_items("http://fake", "key")

        assert len(result) == 1329
        assert mock_get.call_count == 2
        assert "offset=1000" in mock_get.call_args_list[1].args[0]

    @patch("scripts.update_freshness.requests.patch")
    def test_patch_batch_uses_partial_patch_by_score(self, mock_patch):
        mock_patch.return_value = Mock(status_code=204, text="")

        success, fail = _patch_batch(
            "http://fake",
            "key",
            [
                {"id": "a1", "score": 0.2625},
                {"id": "a2", "score": 0.2625},
                {"id": "b1", "score": 0.5},
            ],
        )

        assert (success, fail) == (3, 0)
        assert mock_patch.call_count == 2
        first_call = mock_patch.call_args_list[0]
        assert "id=in.(a1,a2)" in first_call.args[0]
        assert first_call.kwargs["json"] == {"freshness_score": 0.2625}

    @patch("scripts.update_freshness.requests.get")
    def test_verify_excludes_unknown_dates(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        mock_get.return_value.json.return_value = []

        _verify("http://fake", "key")

        request_url = mock_get.call_args.args[0]
        assert "source_date=gte.1900-01-01" in request_url
        assert "source_date=lt.2024-01-01" in request_url
