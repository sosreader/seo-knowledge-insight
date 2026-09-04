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
    GSC_PROPERTY,
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
            schedule_note="", lag_buffer_hours=0.0,  # 與本測試主題無關，滿足必填欄位
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
        gsc_daily_metrics（補充決策：surface 資訊不進 table_name，維持分組相容）。

        2026-09-04 過渡：filters 補上 property（排在 search_type 前面）——run
        33863650667／33863653352 撞 57014，理由見 GSC_PROPERTY 常數註解。"""
        pipeline = PIPELINES_BY_KEY["gsc_googlenews"]
        assert pipeline.table == "gsc_page_daily"
        assert pipeline.filters == (("property", GSC_PROPERTY), ("search_type", "googleNews"))
        assert pipeline.ingestion_run_table_name == "gsc_daily_metrics"

    def test_gsc_googlenews_gap_check_is_skipped(self) -> None:
        """Regression（review S4.1 SF-2，2026-09-03）：googleNews 曝光本質斷續，
        沿用 web 的 30 天 gap 窗會把『本來就沒曝光的日子』誤判成空段、連紅 30 天。
        改成 gap_window_hours=None 只留新鮮度檢查。"""
        pipeline = PIPELINES_BY_KEY["gsc_googlenews"]
        assert pipeline.gap_window_hours is None
        assert pipeline.gap_skip_reason

    @pytest.mark.parametrize("search_type", ["image", "video"])
    def test_gsc_image_video_pipeline_filters_and_ingestion_run_table(self, search_type: str) -> None:
        """2026-09-04：image／video 併入排程後補的兩條 gate。與 gsc_googlenews 不同——
        image／video 是有排名的 surface（SURFACE_COMBOS 給 page＋query 兩組，與 web 同構），
        不屬於 NO_RANKING_SURFACES；查視圖、以 search_type 篩選，ingestion_run_table_name
        沿用 gsc_daily_metrics（補充決策：surface 資訊不進 table_name）。

        2026-09-04 過渡：filters 補上 property（排在 search_type 前面）——run
        33863650667 撞 57014，EXPLAIN 實測 video 的 freshness 查詢在視圖上不帶 property
        時 planner 選錯索引、26–33 秒；帶了命中 dim_uniq，個位數毫秒。理由見
        GSC_PROPERTY 常數註解。table 仍是 gsc_page_daily，不改指 gsc_daily_totals
        （上一輪的 totals 改法已作廢）。"""
        pipeline = PIPELINES_BY_KEY[f"gsc_{search_type}"]
        assert pipeline.table == "gsc_page_daily"
        assert pipeline.filters == (("property", GSC_PROPERTY), ("search_type", search_type))
        assert pipeline.ingestion_run_table_name == "gsc_daily_metrics"

    @pytest.mark.parametrize("search_type", ["image", "video"])
    def test_gsc_image_video_gap_check_is_skipped(self, search_type: str) -> None:
        """image／video 在 2026-09-04 之前 warehouse 從未 ingest 過（S3.6 一致性驗證
        G38/G39），沒有 live 資料能確認逐日是否連續有曝光——舊 GSC UI 週彙總看不出逐日
        分佈，且 image 的量級（20,767/週）其實高於 news（934/週），不能假設『流量稀疏』。
        在有實測分佈之前比照 googleNews／discover 保守跳過空段檢查，改成
        gap_window_hours=None 只留新鮮度檢查，同時仍保留排名檢查（不在 NO_RANKING_SURFACES 裡）。
        待累積數週資料後應回頭用實測分佈重新評估，非永久性判斷。"""
        pipeline = PIPELINES_BY_KEY[f"gsc_{search_type}"]
        assert pipeline.gap_window_hours is None
        assert pipeline.gap_skip_reason

    def test_gsc_image_video_not_in_no_ranking_surfaces(self) -> None:
        """回歸鎖：image／video 有排名，不可誤加進 NO_RANKING_SURFACES——
        那會讓 is_position_valid() 對 image／video 放行 position=0 的列。"""
        from gsc_surfaces import NO_RANKING_SURFACES
        assert "image" not in NO_RANKING_SURFACES
        assert "video" not in NO_RANKING_SURFACES

    def test_gsc_discover_pipeline_points_to_totals_table(self) -> None:
        """S2.5 discover-fix（2026-09-03）：live run 證實 discover 連 page 組
        （date+page+device）都回 400，SURFACE_COMBOS["discover"] 改空 tuple，
        discover 只收 gsc_daily_totals；本管線跟著改指向 totals 表，
        ingestion_run_table_name 也從 gsc_daily_metrics 換成 gsc_daily_totals。"""
        pipeline = PIPELINES_BY_KEY["gsc_discover"]
        assert pipeline.table == "gsc_daily_totals"
        assert pipeline.filters == (("search_type", "discover"),)
        assert pipeline.ingestion_run_table_name == "gsc_daily_totals"

    def test_gsc_discover_gap_check_is_skipped(self) -> None:
        """Regression（review S4.1 SF-2，2026-09-03）：discover 曝光本質斷續，
        理由同 gsc_googlenews。"""
        pipeline = PIPELINES_BY_KEY["gsc_discover"]
        assert pipeline.gap_window_hours is None
        assert pipeline.gap_skip_reason

    def test_gsc_discover_pages_pipeline_points_to_page_daily_view(self) -> None:
        """S2.4／S2.5：discover 的 page_nodevice 組把 (date, page) 列寫進
        gsc_page_daily（見 gsc_surfaces.py SURFACE_COMBOS／025 device_surface_ck）。
        totals（gsc_discover）與 page 層是兩個母體、兩條寫入路徑，各自要有自己的
        新鮮度訊號，因此本條目不改 gsc_discover 的指向，另立一條。filters 第一項
        必須是 property（REQ-3 橫切規則，讓 planner 用上 dim_uniq 前綴）。"""
        pipeline = PIPELINES_BY_KEY["gsc_discover_pages"]
        assert pipeline.table == "gsc_page_daily"
        assert pipeline.filters == (("property", GSC_PROPERTY), ("search_type", "discover"))
        assert pipeline.ingestion_run_table_name == "gsc_daily_metrics"

    def test_gsc_discover_pages_gap_check_is_skipped(self) -> None:
        """曝光本質斷續，理由同 gsc_discover（totals）——母體從 totals 換成 page
        明細，斷續的本質沒換。"""
        pipeline = PIPELINES_BY_KEY["gsc_discover_pages"]
        assert pipeline.gap_window_hours is None
        assert pipeline.gap_skip_reason

    def test_gsc_property_matches_gsc_surfaces_property(self) -> None:
        """(g)：GSC_PROPERTY 是本檔的本地常數，quality_gate_config.py 沒有 import
        gsc_surfaces（見 GSC_PROPERTY 常數註解）——這條相等斷言是它與 ingest 端
        寫入用的同一個值不漂移的唯一防線。兩邊哪天分岔，這裡先紅於 gsc_discover_pages
        的 filters 悄悄查錯 property。"""
        from gsc_surfaces import PROPERTY
        assert GSC_PROPERTY == PROPERTY

    def test_gsc_daily_totals_pipeline_filters_and_ingestion_run_table(self) -> None:
        """totals 查自己的表（全量母體，與 gsc_page_daily 抽樣母體不同）、
        filters 取 web 當代表；ingestion_run_table_name 是新的
        'gsc_daily_totals'（write_totals() 另記一列，見補充決策）。"""
        pipeline = PIPELINES_BY_KEY["gsc_daily_totals"]
        assert pipeline.table == "gsc_daily_totals"
        assert pipeline.filters == (("search_type", "web"),)
        assert pipeline.ingestion_run_table_name == "gsc_daily_totals"

    def test_lag_buffer_hours_is_mandatory(self) -> None:
        """Regression（2026-09-03，team-lead 覆核發現）：`lag_buffer_hours`
        不再有 default——cwv_hourly_crux 曾經漏填、吃 default 0.0，對一個
        有 7 天發布延遲的來源必然誤報。拿掉 default 逼每條管線顯式填一個值，
        解掉「欄位不存在」與「刻意填 0」的歧義：建構子漏填要直接 TypeError，
        不能悄悄吃到一個看起來合理的預設值。"""
        with pytest.raises(TypeError):
            PipelineConfig(  # noqa: 故意漏 lag_buffer_hours
                key="broken", table="x", filters=(), max_age_hours=1,
                cadence_hours=1, cadence_label="hourly",
                ingestion_run_table_name="x", schedule_note="",
            )

    def test_every_pipeline_has_a_non_negative_lag_buffer(self) -> None:
        """必填不等於填對——這裡只鎖「有填、非負」這個最低限度的健全性；
        個別管線的取值是否有實測依據，見各自的 regression test
        （例如 cwv_hourly_crux 見 test_data_quality_gate.py 的
        test_crux_lag_buffer_covers_documented_publish_cadence_ceiling）。"""
        for pipeline in PIPELINES:
            assert pipeline.lag_buffer_hours >= 0, (
                f"{pipeline.key}: lag_buffer_hours={pipeline.lag_buffer_hours} 不可為負"
            )


class TestAiSovPipeline:
    """S6.2（2026-09-03）新增的週頻管線。每個數字都鎖它的**推導**而不是魔術數字，
    推導寫在 quality_gate_config.py 的 ai_sov 區塊。"""

    @property
    def pipeline(self) -> PipelineConfig:
        return PIPELINES_BY_KEY["ai_sov"]

    def test_timestamp_column_is_the_week_bucket_not_the_run_time(self) -> None:
        """空段檢查用 _floor_to_cadence() 把週頻管線對齊到週一 00:00 UTC 做集合比對。
        時間戳若取 run_at（週一 06:20 之類）永遠對不上，每一週都會被判成空段——
        那不是門檻問題，是對齊方式本身錯了。migration 024 有 CHECK 綁死
        week_start 必為 ISO 週一。"""
        assert self.pipeline.timestamp_column == "week_start"
        assert self.pipeline.cadence_hours == 24 * 7

    def test_max_age_is_one_cadence_plus_a_day_not_three_cadences(self) -> None:
        """『週期 × 3』對這條管線是 504h ≈ 3 週。這份資料**無法回填**
        （沒辦法事後去問上週的 LLM 會怎麼回答），三週才叫等於三週的洞。"""
        p = self.pipeline
        assert p.max_age_hours == 168 + 24
        assert p.max_age_hours < p.cadence_hours * 2

    def test_max_age_covers_worst_case_steady_state_age(self) -> None:
        """穩態最壞年齡 ≈ 168（週期）+ 6（cron 排在桶起點後 6h）
        + 1.8（GHA schedule 漂移實測上限）+ 1（run 時長）≈ 176.8h。"""
        worst_case_hours = 168 + 6 + 1.8 + 1
        assert self.pipeline.max_age_hours > worst_case_hours

    def test_gap_window_is_four_weeks_shorter_than_crux(self) -> None:
        """補不回來的洞掃再久也只是常紅告警，而常紅告警就是被忽略的告警。
        4 週＝這個指標可判讀序列的最短長度。"""
        assert self.pipeline.gap_window_hours == 24 * 28
        assert self.pipeline.gap_window_hours < PIPELINES_BY_KEY["cwv_hourly_crux"].gap_window_hours

    def test_lag_buffer_is_deliberately_zero_because_cron_runs_at_week_start(self) -> None:
        """buffer 的語意是「桶**關閉**後容忍多久沒資料」。本管線 cron 排在週一 06:00，
        資料在桶起點後 6h 就寫好、桶關閉時已就位約 162h，沒有需要容忍的延遲。
        ⚠ 這個 0.0 綁在「cron 排在週初」這個前提上：排程若改到週末，這個值必須跟著改。"""
        assert self.pipeline.lag_buffer_hours == 0.0
        workflow = (Path(__file__).resolve().parent.parent
                    / ".github" / "workflows" / "ai-sov-weekly.yml").read_text()
        assert "cron: '0 6 * * 1'" in workflow, "排程已不在週初，lag_buffer_hours=0.0 的前提不再成立"

    def test_degradation_watches_ungrounded_share(self) -> None:
        """零 citation 的回應沒有引用任何人。把它算進 SoV 分母會讓 provider 端的
        檢索行為變動偽裝成站方可見度下降——聚合視圖已排除，這個檢查讓
        「被排除的那一堆變很大」本身也會叫。"""
        d = self.pipeline.degradation
        assert d is not None
        assert (d.column, d.mode, d.fallback_value) == ("grounding", "fallback_value", "ungrounded")
        assert d.min_sample <= 36 * 3, "單週 108 列必須達得到 min_sample，否則檢查永遠 SKIP"

    def test_ingestion_run_table_name_and_stale_threshold(self) -> None:
        assert self.pipeline.ingestion_run_table_name == "ai_sov_response"
        assert STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE["ai_sov_response"] == 24.0

    def test_queries_the_base_table_because_views_are_aggregates(self) -> None:
        """其他管線「一律查視圖」是因為底表有重複計算的陷阱。這裡相反：
        三個視圖都是**週級聚合**，新鮮度與空段檢查要的是逐列時間戳，
        查聚合視圖會拿到已經被 GROUP BY 過的東西。"""
        assert self.pipeline.table == "ai_sov_response"


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
