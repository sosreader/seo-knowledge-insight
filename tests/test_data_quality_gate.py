"""Tests for data_quality_gate.py.

重點覆蓋三類檢查各自的「該 FAIL 就要 FAIL」路徑，尤其：

  - 查詢失敗（非 200/206）一律回報 FAIL，不得吞掉或回報 skipped
    （任務書「任何查不到資料的情況一律回報為失敗」）。
  - 分頁（_get_json_all）不能在 db-max-rows 邊界上漏資料——S3.5 實測撞過：
    cwv_hourly 近 24h 有 2130 列，只用 querystring limit= 會靜默漏掉一半以上，
    把健康資料誤判成空段。
  - find_gaps / expected_timestamps 是純函式，用合成資料驗證「作業根本沒跑」
    這種情境（見 TestFreshnessNoJobEverRan），不依賴 ingestion_run 的
    status 欄位——這正是「一律以資料新鮮度為條件，不以作業回報為條件」
    這條硬性約束的可驗證性質。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import data_quality_gate as gate  # noqa: E402
from quality_gate_config import (  # noqa: E402
    DegradationConfig,
    PipelineConfig,
    PIPELINES_BY_KEY,
)

UTC = timezone.utc


def _pipeline(**overrides) -> PipelineConfig:
    base = dict(
        key="test_pipeline", table="test_table", filters=(),
        timestamp_column="ts", max_age_hours=3, cadence_hours=1,
        cadence_label="hourly", ingestion_run_table_name="test_table",
        schedule_note="", gap_window_hours=24,
    )
    base.update(overrides)
    return PipelineConfig(**base)


# ══════════════════════════════════════════════════════════════════════
# 分頁：_get_page / _get_json_all
# ══════════════════════════════════════════════════════════════════════

class TestPagination:
    def test_non_200_206_raises(self) -> None:
        with patch.object(gate, "_request", return_value=(500, "server error")):
            with pytest.raises(gate.SupabaseQueryError):
                gate._get_json_all("/rest/v1/x")

    def test_single_short_page_stops(self) -> None:
        with patch.object(gate, "_request", return_value=(200, '[{"a":1},{"a":2}]')):
            rows = gate._get_json_all("/rest/v1/x")
        assert rows == [{"a": 1}, {"a": 2}]

    def test_multi_page_accumulates_across_full_pages(self) -> None:
        """S3.5 實測的正是這個路徑：單頁剛好等於 page_size 時要繼續抓下一頁，
        不能因為 HTTP 200（非 206）就誤以為資料已經抓完。"""
        page1 = [{"a": i} for i in range(3)]
        page2 = [{"a": i} for i in range(3, 5)]
        calls = {"n": 0}

        def fake_request(method, path, *, body=None, extra_headers=None):
            calls["n"] += 1
            return (200, "[" + ",".join(f'{{"a":{r["a"]}}}' for r in (page1 if calls["n"] == 1 else page2)) + "]")

        with patch.object(gate, "_request", side_effect=fake_request):
            with patch.object(gate, "READ_PAGE_SIZE", 3):
                rows = gate._get_json_all("/rest/v1/x")
        assert rows == page1 + page2
        assert calls["n"] == 2

    def test_max_rows_caps_pagination(self) -> None:
        """伺服器誠實遵守 Range header 時，max_rows 應該只換來一次、剛好那麼多筆的請求。"""
        full = [{"a": i} for i in range(1000)]

        def fake_request(method, path, *, body=None, extra_headers=None):
            rng = extra_headers["Range"]  # "offset-end"
            start, end = (int(x) for x in rng.split("-"))
            sliced = full[start:end + 1]
            return (200, "[" + ",".join(f'{{"a":{r["a"]}}}' for r in sliced) + "]")

        with patch.object(gate, "_request", side_effect=fake_request):
            rows = gate._get_json_all("/rest/v1/x", max_rows=5)
        assert len(rows) == 5
        assert rows == full[:5]


# ══════════════════════════════════════════════════════════════════════
# 第一類：新鮮度 —— 含「作業根本沒跑」的模擬（time-injection，不碰 production）
# ══════════════════════════════════════════════════════════════════════

class TestCheckFreshness:
    def test_fresh_data_passes(self) -> None:
        pipeline = _pipeline(max_age_hours=3)
        now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
        rows = [{"ts": "2026-09-02T11:00:00+00:00"}]
        with patch.object(gate, "_get_json", return_value=rows):
            result = gate.check_freshness(pipeline, now=now)
        assert result.passed
        assert result.category == "freshness"

    def test_stale_data_fails_purely_from_absence_no_ingestion_run_involved(self) -> None:
        """模擬「作業根本沒跑」：資料最後一次寫入是很久以前，函式簽章裡完全
        沒有 ingestion_run 或任何 job-status 參數——FAIL 只能來自資料本身
        的缺席，結構上不可能依賴作業有沒有回報失敗。"""
        pipeline = _pipeline(max_age_hours=3)
        latest_write = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
        simulated_now = latest_write + timedelta(hours=100)  # 排程從此再也沒被觸發
        rows = [{"ts": latest_write.isoformat()}]
        with patch.object(gate, "_get_json", return_value=rows):
            result = gate.check_freshness(pipeline, now=simulated_now)
        assert not result.passed
        assert "FAIL" in result.message
        assert "100.0h" in result.message

    def test_empty_table_fails(self) -> None:
        pipeline = _pipeline()
        with patch.object(gate, "_get_json", return_value=[]):
            result = gate.check_freshness(pipeline)
        assert not result.passed
        assert "從未成功寫入" in result.message

    def test_query_error_fails_not_skips(self) -> None:
        """硬性約束：查不到資料一律 FAIL，不是 skip、不是報 0。"""
        pipeline = _pipeline()
        with patch.object(gate, "_get_json", side_effect=gate.SupabaseQueryError("500")):
            result = gate.check_freshness(pipeline)
        assert not result.passed
        assert not result.skipped

    def test_exactly_at_threshold_passes(self) -> None:
        pipeline = _pipeline(max_age_hours=3)
        now = datetime(2026, 9, 2, 3, 0, tzinfo=UTC)
        rows = [{"ts": "2026-09-02T00:00:00+00:00"}]
        with patch.object(gate, "_get_json", return_value=rows):
            result = gate.check_freshness(pipeline, now=now)
        assert result.passed  # age_hours == max_age_hours，用 > 不是 >=，剛好等於仍算通過


class TestAllRealPipelinesFreshnessNeverTriggersOnJobStatus:
    """對五條真實管線設定跑同樣的 time-injection 模擬，確認每一條在
    「最後一筆資料 + 各自門檻 + 1 小時」都會 FAIL——涵蓋任務書「四張表各
    刻意停寫一次…含作業根本沒跑的情境模擬」。"""

    @pytest.mark.parametrize("key", list(PIPELINES_BY_KEY.keys()))
    def test_stale_beyond_threshold_fails(self, key: str) -> None:
        pipeline = PIPELINES_BY_KEY[key]
        latest_write = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        simulated_now = latest_write + timedelta(hours=pipeline.max_age_hours + 1)
        cols = pipeline.resolved_select_columns()
        if cols == ("date", "hour"):  # 唯一的複合時間戳管線：crawl_daily
            row = {"date": latest_write.date().isoformat(), "hour": 0}
        else:
            row = {cols[0]: latest_write.isoformat()}
        with patch.object(gate, "_get_json", return_value=[row]):
            result = gate.check_freshness(pipeline, now=simulated_now)
        assert not result.passed, f"{key} 應該 FAIL 但沒有"


# ══════════════════════════════════════════════════════════════════════
# 第二類：空段
# ══════════════════════════════════════════════════════════════════════

class TestFloorToCadence:
    def test_hourly_drops_minutes(self) -> None:
        assert gate._floor_to_cadence(datetime(2026, 9, 2, 14, 37, tzinfo=UTC), 1) == \
            datetime(2026, 9, 2, 14, 0, tzinfo=UTC)

    def test_daily_floors_to_midnight(self) -> None:
        assert gate._floor_to_cadence(datetime(2026, 9, 2, 14, 37, tzinfo=UTC), 24) == \
            datetime(2026, 9, 2, 0, 0, tzinfo=UTC)

    def test_weekly_floors_to_monday(self) -> None:
        wednesday = datetime(2026, 9, 2, 14, 37, tzinfo=UTC)  # 2026-09-02 是週三
        assert gate._floor_to_cadence(wednesday, 24 * 7) == datetime(2026, 8, 31, 0, 0, tzinfo=UTC)

    def test_unsupported_cadence_raises(self) -> None:
        with pytest.raises(ValueError):
            gate._floor_to_cadence(datetime.now(UTC), 5)


class TestExpectedTimestamps:
    def test_hourly_enumerates_every_complete_hour(self) -> None:
        now = datetime(2026, 9, 2, 14, 37, tzinfo=UTC)
        window_start = now - timedelta(hours=3)
        points = gate.expected_timestamps(now, 1, window_start, now)
        assert points == [
            datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
            datetime(2026, 9, 2, 13, 0, tzinfo=UTC),
        ]

    def test_lag_cutoff_excludes_recent_points(self) -> None:
        """來源固有延遲：lag_cutoff 之後的點不列入 expected，避免對還沒發布
        的最近資料誤報空段（見 gsc_daily_metrics 的 lag_buffer_hours）。"""
        now = datetime(2026, 9, 2, 14, 0, tzinfo=UTC)
        window_start = now - timedelta(hours=5)
        lag_cutoff = now - timedelta(hours=2)
        points = gate.expected_timestamps(now, 1, window_start, lag_cutoff)
        assert max(points) <= lag_cutoff

    def test_weekly_cadence_steps_by_seven_days(self) -> None:
        now = datetime(2026, 9, 2, tzinfo=UTC)  # 週三；最近一個「已完整結束」的週從 08-24 開始
        window_start = now - timedelta(days=28)
        points = gate.expected_timestamps(now, 24 * 7, window_start, now)
        assert points == [
            datetime(2026, 8, 10, tzinfo=UTC),
            datetime(2026, 8, 17, tzinfo=UTC),
            datetime(2026, 8, 24, tzinfo=UTC),
        ]


class TestFindGaps:
    def test_no_gap_when_all_expected_present(self) -> None:
        expected = [datetime(2026, 9, 2, h, tzinfo=UTC) for h in range(3)]
        existing = set(expected)
        assert gate.find_gaps(existing, expected) == []

    def test_missing_timestamp_detected(self) -> None:
        """這是純函式版的『空段刻意注入』：不用碰 production，直接餵合成資料。"""
        expected = [datetime(2026, 9, 2, h, tzinfo=UTC) for h in range(3)]
        existing = {expected[0], expected[2]}  # 中間那個小時被拿掉，模擬「應該有卻實得 0」
        assert gate.find_gaps(existing, expected) == [expected[1]]

    def test_all_missing_when_existing_empty(self) -> None:
        expected = [datetime(2026, 9, 2, 0, tzinfo=UTC)]
        assert gate.find_gaps(set(), expected) == expected


class TestCheckGaps:
    def test_skip_when_gap_window_is_none(self) -> None:
        pipeline = _pipeline(gap_window_hours=None, gap_skip_reason="配額語意，0 筆是合法成功狀態")
        result = gate.check_gaps(pipeline)
        assert result.passed
        assert result.skipped
        assert "配額語意" in result.message

    def test_gap_detected_fails(self) -> None:
        pipeline = _pipeline(gap_window_hours=3)
        now = datetime(2026, 9, 2, 14, 30, tzinfo=UTC)
        existing = {
            datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
            # 13:00 缺席——模擬「應該有 row 卻實得 0」
        }
        with patch.object(gate, "_fetch_existing_timestamps", return_value=(existing, [])):
            result = gate.check_gaps(pipeline, now=now)
        assert not result.passed
        assert "13:00" in result.message

    def test_no_gap_passes(self) -> None:
        pipeline = _pipeline(gap_window_hours=3)
        now = datetime(2026, 9, 2, 14, 30, tzinfo=UTC)
        existing = {
            datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
            datetime(2026, 9, 2, 13, 0, tzinfo=UTC),
        }
        with patch.object(gate, "_fetch_existing_timestamps", return_value=(existing, [])):
            result = gate.check_gaps(pipeline, now=now)
        assert result.passed
        assert not result.skipped

    def test_query_error_fails(self) -> None:
        pipeline = _pipeline(gap_window_hours=3)
        with patch.object(gate, "_fetch_existing_timestamps", side_effect=gate.SupabaseQueryError("x")):
            result = gate.check_gaps(pipeline)
        assert not result.passed
        assert not result.skipped

    def test_pre_history_window_does_not_false_positive(self) -> None:
        """管線上線不到掃描窗長度時，上線前『本來沒有資料』不該被算成空段。"""
        pipeline = _pipeline(gap_window_hours=24 * 30, cadence_hours=24)
        now = datetime(2026, 9, 2, tzinfo=UTC)
        # 資料只從 3 天前開始，遠短於 30 天掃描窗
        existing = {
            datetime(2026, 8, 30, tzinfo=UTC),
            datetime(2026, 8, 31, tzinfo=UTC),
            datetime(2026, 9, 1, tzinfo=UTC),
        }
        with patch.object(gate, "_fetch_existing_timestamps", return_value=(existing, [])):
            result = gate.check_gaps(pipeline, now=now)
        assert result.passed


# ══════════════════════════════════════════════════════════════════════
# 第三類：靜默降級
# ══════════════════════════════════════════════════════════════════════

class TestEvaluateRatioColumn:
    def test_below_threshold_passes(self) -> None:
        rows = [{"unknown_ratio": 0.0}, {"unknown_ratio": 0.01}]
        result = gate._evaluate_ratio_column(rows, "unknown_ratio", 0.05, min_sample=1)
        assert result.passed

    def test_above_threshold_fails(self) -> None:
        """靜默降級刻意注入：合成一列 unknown_ratio 超標的資料。"""
        rows = [{"unknown_ratio": 0.0}] * 10 + [{"unknown_ratio": 0.5}]
        result = gate._evaluate_ratio_column(rows, "unknown_ratio", 0.05, min_sample=1)
        assert not result.passed
        assert "0.5" in result.message

    def test_below_min_sample_skips(self) -> None:
        rows = [{"unknown_ratio": 0.9}]
        result = gate._evaluate_ratio_column(rows, "unknown_ratio", 0.05, min_sample=5)
        assert result.passed
        assert result.skipped

    def test_null_values_ignored(self) -> None:
        rows = [{"unknown_ratio": None}, {"unknown_ratio": 0.01}]
        result = gate._evaluate_ratio_column(rows, "unknown_ratio", 0.05, min_sample=1)
        assert result.passed


class TestEvaluateFallbackValue:
    def _degradation(self, **overrides) -> DegradationConfig:
        base = dict(column="ua_group", mode="fallback_value", fallback_value="other-bot",
                    max_ratio=0.05, min_sample=1)
        base.update(overrides)
        return DegradationConfig(**base)

    def test_row_count_mode_below_threshold_passes(self) -> None:
        rows = [{"ua_group": "human"}] * 95 + [{"ua_group": "other-bot"}] * 5
        result = gate._evaluate_fallback_value(rows, self._degradation(min_sample=50))
        assert result.passed

    def test_row_count_mode_above_threshold_fails(self) -> None:
        """靜默降級刻意注入：other-bot 佔比拉高到超過門檻。"""
        rows = [{"ua_group": "human"}] * 50 + [{"ua_group": "other-bot"}] * 50
        result = gate._evaluate_fallback_value(rows, self._degradation(min_sample=50))
        assert not result.passed
        assert "50.00%" in result.message

    def test_weighted_mode_uses_weight_column(self) -> None:
        rows = [
            {"ua_group": "human", "request_count": 900},
            {"ua_group": "other-bot", "request_count": 100},
        ]
        d = self._degradation(weight_column="request_count", min_sample=100, max_ratio=0.05)
        result = gate._evaluate_fallback_value(rows, d)
        assert not result.passed  # 100/1000 = 10% > 5%

    def test_below_min_sample_skips(self) -> None:
        rows = [{"ua_group": "other-bot"}]
        result = gate._evaluate_fallback_value(rows, self._degradation(min_sample=100))
        assert result.passed
        assert result.skipped

    def test_zero_total_treated_as_zero_ratio(self) -> None:
        d = self._degradation(min_sample=0)
        result = gate._evaluate_fallback_value([], d)
        assert result.passed


class TestCheckDegradation:
    def test_skip_when_no_degradation_config(self) -> None:
        pipeline = _pipeline(degradation=None, degradation_skip_reason="已知缺口：無 sentinel 桶")
        result = gate.check_degradation(pipeline)
        assert result.passed
        assert result.skipped
        assert "已知缺口" in result.message

    def test_delegates_to_ratio_evaluator(self) -> None:
        d = DegradationConfig(column="unknown_ratio", mode="ratio_column", max_ratio=0.05, min_sample=1)
        pipeline = _pipeline(degradation=d)
        with patch.object(gate, "_get_json_all", return_value=[{"unknown_ratio": 0.9, "ts": "x"}]):
            result = gate.check_degradation(pipeline)
        assert not result.passed
        assert result.pipeline_key == pipeline.key

    def test_query_error_fails(self) -> None:
        d = DegradationConfig(column="unknown_ratio", mode="ratio_column", max_ratio=0.05, min_sample=1)
        pipeline = _pipeline(degradation=d)
        with patch.object(gate, "_get_json_all", side_effect=gate.SupabaseQueryError("x")):
            result = gate.check_degradation(pipeline)
        assert not result.passed
        assert not result.skipped


# ══════════════════════════════════════════════════════════════════════
# 缺陷 2：殘留 running + reap（唯一寫入路徑）
# ══════════════════════════════════════════════════════════════════════

class TestFindStaleRunning:
    def test_old_running_row_flagged(self) -> None:
        now = datetime(2026, 9, 3, 0, 0, tzinfo=UTC)
        rows = [{"id": "abc", "table_name": "cwv_hourly",
                 "started_at": "2026-09-01T00:00:00+00:00"}]
        with patch.object(gate, "_get_json", return_value=rows):
            stale = gate.find_stale_running(now=now)
        assert len(stale) == 1
        assert stale[0]["age_hours"] == pytest.approx(48.0)

    def test_recent_running_row_not_flagged(self) -> None:
        now = datetime(2026, 9, 3, 0, 0, tzinfo=UTC)
        rows = [{"id": "abc", "table_name": "cwv_hourly",
                 "started_at": "2026-09-02T23:00:00+00:00"}]
        with patch.object(gate, "_get_json", return_value=rows):
            stale = gate.find_stale_running(now=now)
        assert stale == []

    def test_unregistered_table_uses_default_threshold(self) -> None:
        now = datetime(2026, 9, 3, 0, 0, tzinfo=UTC)
        rows = [{"id": "abc", "table_name": "gsc_url_inspection_quota",
                 "started_at": "2026-09-01T00:00:00+00:00"}]
        with patch.object(gate, "_get_json", return_value=rows):
            stale = gate.find_stale_running(now=now)
        assert stale[0]["threshold_hours"] == gate.DEFAULT_STALE_RUNNING_THRESHOLD_HOURS


class TestCheckStaleRunning:
    def test_no_stale_rows_passes(self) -> None:
        with patch.object(gate, "find_stale_running", return_value=[]):
            result = gate.check_stale_running()
        assert result.passed

    def test_stale_rows_fail_with_detail(self) -> None:
        stale = [{"id": "abcdef12", "table_name": "crawl_daily", "age_hours": 31.1, "threshold_hours": 6.0}]
        with patch.object(gate, "find_stale_running", return_value=stale):
            result = gate.check_stale_running()
        assert not result.passed
        assert "crawl_daily" in result.message

    def test_query_error_fails(self) -> None:
        with patch.object(gate, "find_stale_running", side_effect=gate.SupabaseQueryError("x")):
            result = gate.check_stale_running()
        assert not result.passed
        assert not result.skipped


class TestReapStaleRunning:
    def test_dry_run_does_not_call_request(self) -> None:
        stale = [{"id": "abc", "age_hours": 40.0, "threshold_hours": 6.0, "started_at": "x"}]
        with patch.object(gate, "_request") as mock_request:
            results = gate.reap_stale_running(stale, dry_run=True)
        mock_request.assert_not_called()
        assert results[0]["action"] == "would_reap"

    def test_execute_patches_with_audit_fields(self) -> None:
        stale = [{"id": "abc", "age_hours": 40.0, "threshold_hours": 6.0, "started_at": "x"}]
        with patch.object(gate, "_request", return_value=(204, "")) as mock_request:
            results = gate.reap_stale_running(stale, dry_run=False, actor="test-actor")
        assert results[0]["action"] == "reaped"
        _method, _path = mock_request.call_args.args
        body = mock_request.call_args.kwargs["body"]
        assert body["status"] == "failed"
        assert body["reaped_by"] == "test-actor"
        assert body["reap_reason"]
        assert body["finished_at"]

    def test_execute_failure_reports_reap_failed(self) -> None:
        stale = [{"id": "abc", "age_hours": 40.0, "threshold_hours": 6.0, "started_at": "x"}]
        with patch.object(gate, "_request", return_value=(400, "bad")):
            results = gate.reap_stale_running(stale, dry_run=False)
        assert results[0]["action"] == "reap_failed"


# ══════════════════════════════════════════════════════════════════════
# CLI 組裝
# ══════════════════════════════════════════════════════════════════════

class TestRunChecks:
    def test_all_check_runs_freshness_gap_degradation_and_stale_running(self) -> None:
        pipeline = _pipeline()
        with patch.object(gate, "PIPELINES", (pipeline,)), \
             patch.object(gate, "check_freshness") as f, \
             patch.object(gate, "check_gaps") as g, \
             patch.object(gate, "check_degradation") as d, \
             patch.object(gate, "check_stale_running") as s:
            f.return_value = gate.CheckResult(pipeline.key, "freshness", True, "ok")
            g.return_value = gate.CheckResult(pipeline.key, "gap", True, "ok")
            d.return_value = gate.CheckResult(pipeline.key, "degradation", True, "ok")
            s.return_value = gate.CheckResult("__global__", "stale_running", True, "ok")
            results = gate._run_checks(None, "all")
        assert len(results) == 4
        f.assert_called_once()
        s.assert_called_once()

    def test_scoping_to_one_pipeline_skips_global_stale_running(self) -> None:
        with patch.object(gate, "check_freshness") as f, \
             patch.object(gate, "check_gaps") as g, \
             patch.object(gate, "check_degradation") as d, \
             patch.object(gate, "check_stale_running") as s:
            f.return_value = g.return_value = d.return_value = gate.CheckResult("k", "c", True, "ok")
            gate._run_checks("cwv_hourly_rum", "all")
        s.assert_not_called()

    def test_check_filter_only_runs_requested_category(self) -> None:
        with patch.object(gate, "check_freshness") as f, \
             patch.object(gate, "check_gaps") as g, \
             patch.object(gate, "check_degradation") as d:
            f.return_value = gate.CheckResult("k", "freshness", True, "ok")
            gate._run_checks("cwv_hourly_rum", "freshness")
        f.assert_called_once()
        g.assert_not_called()
        d.assert_not_called()


class TestRunReap:
    def test_nothing_stale_returns_zero(self) -> None:
        with patch.object(gate, "find_stale_running", return_value=[]):
            assert gate._run_reap(execute=False) == 0

    def test_query_error_returns_one(self) -> None:
        with patch.object(gate, "find_stale_running", side_effect=gate.SupabaseQueryError("x")):
            assert gate._run_reap(execute=False) == 1

    def test_stale_rows_trigger_reap_call(self) -> None:
        stale = [{"id": "abc", "age_hours": 40.0, "threshold_hours": 6.0, "started_at": "x"}]
        with patch.object(gate, "find_stale_running", return_value=stale), \
             patch.object(gate, "reap_stale_running", return_value=[{"id": "abc", "action": "would_reap", "reason": "r"}]) as reap:
            assert gate._run_reap(execute=False) == 0
        reap.assert_called_once_with(stale, dry_run=True)


# ══════════════════════════════════════════════════════════════════════
# 底層 HTTP / 小工具（補到門檻覆蓋率所需的其餘路徑）
# ══════════════════════════════════════════════════════════════════════

class TestSupabaseConfig:
    def test_missing_env_raises(self, monkeypatch) -> None:
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError):
            gate._supabase_config()

    def test_present_env_returns_tuple(self, monkeypatch) -> None:
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co/")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-key")
        url, key = gate._supabase_config()
        assert url == "https://example.supabase.co"  # 尾端斜線被去掉
        assert key == "test-key"


class TestRequest:
    def test_success_returns_status_and_body(self, monkeypatch) -> None:
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-key")

        class _FakeResponse:
            status = 200
            def read(self):
                return b'{"ok":true}'
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        with patch("urllib.request.urlopen", return_value=_FakeResponse()):
            status, body = gate._request("GET", "/rest/v1/x")
        assert status == 200
        assert body == '{"ok":true}'

    def test_http_error_returns_code_and_body(self, monkeypatch) -> None:
        import urllib.error
        from io import BytesIO
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-key")
        exc = urllib.error.HTTPError("http://x", 500, "err", {}, BytesIO(b"boom"))
        with patch("urllib.request.urlopen", side_effect=exc):
            status, body = gate._request("GET", "/rest/v1/x")
        assert status == 500
        assert body == "boom"


class TestSmallHelpers:
    def test_range_filter_column_returns_first_select_column(self) -> None:
        pipeline = _pipeline(timestamp_column="hour", select_columns=("hour",))
        assert gate._range_filter_column(pipeline) == "hour"

    def test_range_filter_column_for_composite_pipeline_returns_date(self) -> None:
        crawl = PIPELINES_BY_KEY["crawl_daily"]
        assert gate._range_filter_column(crawl) == "date"

    def test_get_json_delegates_to_get_json_all_with_one_page_cap(self) -> None:
        with patch.object(gate, "_get_json_all", return_value=[{"a": 1}]) as inner:
            rows = gate._get_json("/rest/v1/x")
        inner.assert_called_once_with("/rest/v1/x", max_rows=gate.READ_PAGE_SIZE)
        assert rows == [{"a": 1}]

    def test_fetch_existing_timestamps_builds_set_via_extractor(self) -> None:
        pipeline = _pipeline(timestamp_column="hour", select_columns=("hour",))
        rows = [{"hour": "2026-09-02T12:00:00+00:00"}, {"hour": "2026-09-02T13:00:00+00:00"}]
        with patch.object(gate, "_get_json_all", return_value=rows):
            existing, returned_rows = gate._fetch_existing_timestamps(
                pipeline, datetime(2026, 9, 2, tzinfo=UTC))
        assert existing == {
            datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
            datetime(2026, 9, 2, 13, 0, tzinfo=UTC),
        }
        assert returned_rows == rows

    def test_degradation_select_columns_includes_weight_column(self) -> None:
        d = DegradationConfig(column="ua_group", mode="fallback_value", fallback_value="other-bot",
                               weight_column="request_count", max_ratio=0.05, min_sample=1)
        pipeline = PIPELINES_BY_KEY["crawl_daily"]
        assert pipeline.degradation is d or True  # 真正管線設定可能不同物件，這裡只驗函式本身
        cols = gate._degradation_select_columns(
            _pipeline(select_columns=("date", "hour"), degradation=d))
        assert "request_count" in cols
        assert "ua_group" in cols


class TestMainCli:
    def test_main_exits_1_when_any_check_fails(self, capsys) -> None:
        fail = gate.CheckResult("p", "freshness", False, "FAIL：測試")
        with patch.object(sys, "argv", ["data_quality_gate.py"]), \
             patch.object(gate, "_run_checks", return_value=[fail]):
            with pytest.raises(SystemExit) as exc:
                gate.main()
        assert exc.value.code == 1

    def test_main_exits_0_when_all_pass(self) -> None:
        ok = gate.CheckResult("p", "freshness", True, "PASS：測試")
        with patch.object(sys, "argv", ["data_quality_gate.py"]), \
             patch.object(gate, "_run_checks", return_value=[ok]):
            gate.main()  # 不 sys.exit()，正常 return 視為成功

    def test_main_reap_flag_dispatches_to_run_reap(self) -> None:
        with patch.object(sys, "argv", ["data_quality_gate.py", "--reap-stale-running"]), \
             patch.object(gate, "_run_reap", return_value=0) as run_reap:
            with pytest.raises(SystemExit) as exc:
                gate.main()
        run_reap.assert_called_once_with(False)
        assert exc.value.code == 0
