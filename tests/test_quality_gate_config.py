"""Tests for quality_gate_config.py.

重點：五條管線的設定本身要一致（key 不重複、每條都能正確解析出 extractor/
select_columns），以及 _parse_iso 對「純日期字串」（DATE 欄位）與「完整時間戳」
兩種輸入都要回傳 tz-aware datetime——S3.5 實測撞過的 bug：gsc_page_daily.date
是純日期字串，混進 tz-aware 比較會直接 TypeError。
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from quality_gate_config import (  # noqa: E402
    DEFAULT_STALE_RUNNING_THRESHOLD_HOURS,
    PIPELINES,
    PIPELINES_BY_KEY,
    STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE,
    DegradationConfig,
    PipelineConfig,
    _crawl_daily_extractor,
    _parse_iso,
)

UTC = timezone.utc


class TestParseIso:
    def test_full_timestamp_with_offset(self) -> None:
        assert _parse_iso("2026-09-02T15:00:00+00:00") == datetime(2026, 9, 2, 15, 0, tzinfo=UTC)

    def test_z_suffix_timestamp(self) -> None:
        assert _parse_iso("2026-09-02T15:00:00Z") == datetime(2026, 9, 2, 15, 0, tzinfo=UTC)

    def test_bare_date_gets_utc_attached(self) -> None:
        """gsc_page_daily.date 這類 DATE 欄位沒有時間/時區部分。"""
        result = _parse_iso("2026-08-30")
        assert result == datetime(2026, 8, 30, 0, 0, tzinfo=UTC)
        assert result.tzinfo is not None

    def test_microseconds_preserved(self) -> None:
        result = _parse_iso("2026-09-02T08:44:57.552694+00:00")
        assert result.microsecond == 552694


class TestCrawlDailyExtractor:
    def test_combines_date_and_hour(self) -> None:
        row = {"date": "2026-09-02", "hour": 15}
        assert _crawl_daily_extractor(row) == datetime(2026, 9, 2, 15, 0, tzinfo=UTC)

    def test_hour_zero(self) -> None:
        row = {"date": "2026-01-01", "hour": 0}
        assert _crawl_daily_extractor(row) == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)

    def test_hour_as_string_coerced(self) -> None:
        row = {"date": "2026-09-02", "hour": "23"}
        assert _crawl_daily_extractor(row) == datetime(2026, 9, 2, 23, 0, tzinfo=UTC)


class TestPipelineConfigResolution:
    def test_all_keys_unique(self) -> None:
        keys = [p.key for p in PIPELINES]
        assert len(keys) == len(set(keys))

    def test_all_pipelines_resolve_extractor(self) -> None:
        for pipeline in PIPELINES:
            extractor = pipeline.resolved_extractor()
            assert callable(extractor)

    def test_all_pipelines_resolve_select_columns(self) -> None:
        for pipeline in PIPELINES:
            cols = pipeline.resolved_select_columns()
            assert len(cols) >= 1

    def test_standard_extractor_matches_timestamp_column(self) -> None:
        pipeline = PIPELINES_BY_KEY["cwv_hourly_rum"]
        row = {"hour": "2026-09-02T15:00:00+00:00"}
        assert pipeline.resolved_extractor()(row) == datetime(2026, 9, 2, 15, 0, tzinfo=UTC)

    def test_missing_timestamp_column_and_extractor_raises(self) -> None:
        broken = PipelineConfig(
            key="broken", table="x", filters=(), max_age_hours=1,
            cadence_hours=1, cadence_label="hourly", ingestion_run_table_name="x",
            schedule_note="",
        )
        with pytest.raises(ValueError):
            broken.resolved_extractor()
        with pytest.raises(ValueError):
            broken.resolved_select_columns()

    def test_gsc_daily_metrics_queries_view_not_base_table(self) -> None:
        """任務書硬性要求：一律查視圖，不可直接查 gsc_daily_metrics 底表。"""
        pipeline = PIPELINES_BY_KEY["gsc_daily_metrics"]
        assert pipeline.table in ("gsc_page_daily", "gsc_query_daily")
        assert pipeline.table != "gsc_daily_metrics"

    def test_gsc_googlenews_pipeline_filters_and_ingestion_run_table(self) -> None:
        """googleNews 查視圖、以 search_type 篩選；ingestion_run_table_name 沿用
        gsc_daily_metrics（補充決策：surface 資訊不進 table_name，維持分組相容）。"""
        pipeline = PIPELINES_BY_KEY["gsc_googlenews"]
        assert pipeline.table == "gsc_page_daily"
        assert pipeline.filters == (("search_type", "googleNews"),)
        assert pipeline.ingestion_run_table_name == "gsc_daily_metrics"

    def test_gsc_discover_pipeline_filters_and_ingestion_run_table(self) -> None:
        pipeline = PIPELINES_BY_KEY["gsc_discover"]
        assert pipeline.table == "gsc_page_daily"
        assert pipeline.filters == (("search_type", "discover"),)
        assert pipeline.ingestion_run_table_name == "gsc_daily_metrics"

    def test_gsc_daily_totals_pipeline_filters_and_ingestion_run_table(self) -> None:
        """totals 查自己的表（全量母體，與 gsc_page_daily 抽樣母體不同）、
        filters 取 web 當代表；ingestion_run_table_name 是新的
        'gsc_daily_totals'（write_totals() 另記一列，見補充決策）。"""
        pipeline = PIPELINES_BY_KEY["gsc_daily_totals"]
        assert pipeline.table == "gsc_daily_totals"
        assert pipeline.filters == (("search_type", "web"),)
        assert pipeline.ingestion_run_table_name == "gsc_daily_totals"


class TestDegradationOrGapMustExplainWhySkipped:
    """degradation=None 或 gap_window_hours=None 時必須附一句非空理由——
    「查不到資料/沒有檢查」不可以是靜默的，見任務書「不得在報表層以 0 呈現」的精神。
    """

    def test_every_pipeline_without_degradation_has_a_reason(self) -> None:
        for pipeline in PIPELINES:
            if pipeline.degradation is None:
                assert pipeline.degradation_skip_reason
                assert isinstance(pipeline.degradation_skip_reason, str)
                assert len(pipeline.degradation_skip_reason) > 20

    def test_every_pipeline_without_gap_check_has_a_reason(self) -> None:
        for pipeline in PIPELINES:
            if pipeline.gap_window_hours is None:
                assert pipeline.gap_skip_reason
                assert isinstance(pipeline.gap_skip_reason, str)
                assert len(pipeline.gap_skip_reason) > 20

    def test_degradation_config_when_present_has_valid_mode(self) -> None:
        for pipeline in PIPELINES:
            if pipeline.degradation is not None:
                assert pipeline.degradation.mode in ("ratio_column", "fallback_value")
                if pipeline.degradation.mode == "fallback_value":
                    assert pipeline.degradation.fallback_value is not None


class TestStaleRunningThresholds:
    def test_hourly_pipelines_get_tight_threshold(self) -> None:
        assert STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE["cwv_hourly"] == 6.0
        assert STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE["crawl_daily"] == 6.0

    def test_daily_and_weekly_pipelines_get_looser_threshold(self) -> None:
        assert STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE["gsc_daily_metrics"] == 24.0
        assert STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE["gsc_url_inspection"] == 24.0

    def test_unregistered_table_falls_back_to_default(self) -> None:
        assert "gsc_url_inspection_quota" not in STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE
        assert DEFAULT_STALE_RUNNING_THRESHOLD_HOURS == 24.0

    def test_cwv_hourly_threshold_uses_the_tighter_of_rum_and_crux(self) -> None:
        """rum（hourly）與 crux（weekly）共用 table_name='cwv_hourly'——
        缺陷 1 的直接後果：兩條管線在 ingestion_run 層級不可分辨，
        stale-running 門檻只能取較嚴格者，才不會讓卡死的 rum run 躲過偵測。"""
        assert STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE["cwv_hourly"] == 6.0


class TestDegradationConfigDefaults:
    def test_weight_column_optional(self) -> None:
        d = DegradationConfig(column="x", mode="ratio_column", max_ratio=0.1, min_sample=1)
        assert d.weight_column is None
        assert d.fallback_value is None
        assert d.sample_limit == 500
