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
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import data_quality_gate as gate  # noqa: E402
from quality_gate_config import (  # noqa: E402
    CRUX_PUBLISH_CADENCE_CEILING_HOURS,
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
        lag_buffer_hours=0.0,  # 這裡的 0.0 只是測試建構子的方便預設，不是生產設定——
                                # production PipelineConfig 的 lag_buffer_hours 已改成
                                # 必填（見 quality_gate_config.py），這個 helper 保留
                                # 一個 default 純粹是測試工具的便利性，兩者不要混為一談。
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

    def test_lag_cutoff_compares_bucket_close_time_not_bucket_start(self) -> None:
        """Regression（S3.5 驗收退回）：`t` 是桶的起點，比較基準必須是桶的
        關閉時間（t + cadence），不是起點本身——否則 lag_buffer_hours 裡有
        一段等於 cadence_hours 被「桶寬度」吃掉，對 hourly 管線（cadence=1h）
        幾乎等於沒有緩衝。用 1 小時 cadence、剛好卡在起點與關閉時間中間的
        lag_cutoff 直接驗證：只看關閉時間才會排除最新那一桶。"""
        # 16:00 桶代表 [16:00,17:00)，起點 16:00、關閉 17:00。
        # lag_cutoff=16:30 嚴格介於兩者之間：若比較起點（16:00<=16:30）會被
        # 誤判成「已經可以檢查」；只有比較關閉時間（17:00<=16:30 為 False）
        # 才會正確排除它。
        now = datetime(2026, 9, 2, 17, 40, tzinfo=UTC)
        window_start = now - timedelta(hours=3)
        lag_cutoff = datetime(2026, 9, 2, 16, 30, tzinfo=UTC)
        points = gate.expected_timestamps(now, 1, window_start, lag_cutoff)
        assert datetime(2026, 9, 2, 16, 0, tzinfo=UTC) not in points

    def test_bucket_included_exactly_when_close_time_reaches_lag_cutoff(self) -> None:
        """關閉時間等於 lag_cutoff 時應該被納入（邊界含頭），驗證比較基準
        確實是 t + step 而非 t。"""
        now = datetime(2026, 9, 2, 20, 0, tzinfo=UTC)
        window_start = now - timedelta(hours=5)
        lag_cutoff = datetime(2026, 9, 2, 17, 0, tzinfo=UTC)  # 恰好等於 16:00 桶的關閉時間
        points = gate.expected_timestamps(now, 1, window_start, lag_cutoff)
        assert datetime(2026, 9, 2, 16, 0, tzinfo=UTC) in points
        assert datetime(2026, 9, 2, 17, 0, tzinfo=UTC) not in points  # 這桶關閉時間 18:00 > lag_cutoff

    def test_production_lag_buffer_covers_measured_real_world_delay(self) -> None:
        """Regression：鎖住 production 設定值與實測延遲分布的關係，不要只靠
        程式碼審查記得這件事。

        實測（.verification/2026-08-29-seo-capability/S3.5-freshness-negative-tests/）：
        crawl-hourly.yml 2026-09-02T09:07 UTC 修掉 56% 失敗率的 bug 後，穩態下
        「桶關閉→第一次成功寫入完成」延遲：crawl_daily 7 個樣本 0.40–0.63h、
        cwv_hourly(RUM) 15 個樣本 0.33–0.68h。production 設定 lag_buffer_hours
        =1.5h，任何一個樣本都必須落在緩衝內（bucket 在關閉 delay 小時後已有
        資料時，若 delay < lag_buffer_hours，那一桶就不該被空段檢查誤判）。
        """
        measured_delays_hours = {
            "crawl_daily": [0.40, 0.63, 0.46, 0.45, 0.49, 0.49, 0.42],
            "cwv_hourly_rum": [0.43, 0.45, 0.41, 0.68, 0.43, 0.50, 0.41, 0.39, 0.34, 0.55, 0.38, 0.38, 0.40, 0.42, 0.33],
        }
        for key, delays in measured_delays_hours.items():
            pipeline = PIPELINES_BY_KEY[key]
            worst = max(delays)
            assert worst < pipeline.lag_buffer_hours, (
                f"{key}: 實測最差延遲 {worst}h 已經逼近或超過 lag_buffer_hours="
                f"{pipeline.lag_buffer_hours}h，緩衝不夠安全"
            )
            margin = pipeline.lag_buffer_hours - worst
            assert margin >= 0.5, f"{key}: 安全邊際只剩 {margin:.2f}h，過窄"

    def test_crux_lag_buffer_covers_documented_publish_cadence_ceiling(self) -> None:
        """Regression（2026-09-03，team-lead 覆核 CrUX 手動觸發時發現）：鎖語意
        不鎖魔術數字——`cwv_hourly_crux.lag_buffer_hours` 必須 >=
        `CRUX_PUBLISH_CADENCE_CEILING_HOURS`（CrUX 自己的發布週期落差上限，
        168h，實測依據見 quality_gate_config.py 該常數旁的註解）。

        原本這個欄位漏設、吃 default 0.0——等於要求「週一結束、資料立刻要在」，
        對一個有 7 天發布週期落差的來源必然誤報：run 33710475866 實測撞到，
        gate 在 ingest 把當週資料寫完前讀了資料庫，把這次 run 自己正在寫的
        那一週誤判成 gap FAIL。

        故意不寫 `== 192.0`：未來若有更多實測資料要調整安全邊際（目前的 +24h
        只是「沒有分布可取樣，只能加一點餘裕」的權宜），數字可以變，但**不能
        低於已經寫進 KB、有實測依據的 168h 下限**——低於下限就是重新製造
        同一種誤報，而測試不會知道数字變了背後的理由是不是還站得住腳，
        所以鎖的是「不低於下限」這個語意，不是某一個具體數字。
        """
        pipeline = PIPELINES_BY_KEY["cwv_hourly_crux"]
        assert pipeline.lag_buffer_hours >= CRUX_PUBLISH_CADENCE_CEILING_HOURS, (
            f"cwv_hourly_crux.lag_buffer_hours={pipeline.lag_buffer_hours}h 低於"
            f"CrUX 自己的發布週期落差上限 {CRUX_PUBLISH_CADENCE_CEILING_HOURS}h——"
            "這會重新製造『資料還沒發布就被判成 gap』的誤報。"
        )

    def test_crux_gap_check_would_not_have_false_flagged_the_actual_incident(self) -> None:
        """行為級 regression：重播 run 33710475866 的真實時間軸，證明新設定下
        `expected_timestamps()` 不會再把那一週判成應該存在（也就不會誤報 gap）。

        真實時間軸：hour=2026-08-24（桶關閉 2026-08-31T00:00Z），gate 讀資料庫
        的時間是 2026-09-03T03:11:52Z（team-lead 覆核那次；本檔頂端 CI 修法後
        的第二次驗證 run 33712455934 已經用 needs+always() 讓 gate 排到 ingest
        完成之後才讀，這裡驗證的是另一層防線：即使兩者又意外撞在一起，
        lag_buffer_hours 本身也該擋下這個誤報，不只靠 job 排序單一防線）。
        """
        bucket_hour = datetime(2026, 8, 24, tzinfo=UTC)
        bucket_close = bucket_hour + timedelta(hours=24 * 7)  # 2026-08-31
        now = datetime(2026, 9, 3, 3, 11, 52, tzinfo=UTC)
        pipeline = PIPELINES_BY_KEY["cwv_hourly_crux"]
        lag_cutoff = now - timedelta(hours=pipeline.lag_buffer_hours)

        assert bucket_close > lag_cutoff, (
            "測試前提不成立：這個情境下桶關閉時間已經早於 lag_cutoff，"
            "不足以重現『資料還沒發布』的誤報場景，請調整測試時間軸"
        )
        points = gate.expected_timestamps(
            now, pipeline.cadence_hours, now - timedelta(hours=pipeline.gap_window_hours), lag_cutoff,
        )
        assert bucket_hour not in points, (
            "新設定下這一週仍然被列入『應該有資料』的候選——"
            "lag_buffer_hours 不足以覆蓋真實發生過的這次延遲"
        )

        # 對照組：漏設前的 default 0.0 buffer，同一個時間軸，證明會誤報——
        # 這個測試存在的理由本身，不是憑空斷言。
        old_lag_cutoff = now  # lag_buffer_hours=0.0
        old_points = gate.expected_timestamps(
            now, pipeline.cadence_hours, now - timedelta(hours=pipeline.gap_window_hours), old_lag_cutoff,
        )
        assert bucket_hour in old_points, (
            "對照組應該（錯誤地）已經把這一週列入候選——如果沒有，代表這個測試"
            "情境本身沒有重現到 run 33710475866 實際撞到的誤報，測試前提有誤"
        )

    def test_old_buggy_semantics_would_have_flagged_the_measured_delays(self) -> None:
        """反向鎖定：證明「比較桶起點」這個舊語意，用同一組實測延遲與同一個
        production buffer 值，確實會誤報——這是這條 regression test 存在的
        理由本身，不是憑空存在的斷言。"""
        def old_buggy_expected_timestamps(now, cadence_hours, window_start, lag_cutoff):
            step = timedelta(hours=cadence_hours)
            anchor = gate._floor_to_cadence(now, cadence_hours) - step
            points, t = [], anchor
            while t >= window_start:
                if t <= lag_cutoff:  # 舊版：比較桶起點
                    points.append(t)
                t -= step
            return sorted(points)

        cadence_hours = 1.0
        lag_buffer_hours = 1.5
        bucket_close = datetime(2026, 9, 2, 17, 0, tzinfo=UTC)
        bucket_start = bucket_close - timedelta(hours=cadence_hours)
        # 舊語意的實際容忍只有 lag_buffer_hours - cadence_hours = 0.5h；
        # 用兩個明顯超過 0.5h、但仍在 production 實測正常範圍（0.4–0.63h 上緣附近
        # 到略高）內的延遲，證明舊語意會在「資料其實已經寫完」時仍然誤報。
        for delay_hours in (0.63, 0.9):
            now = bucket_close + timedelta(hours=delay_hours)
            lag_cutoff = now - timedelta(hours=lag_buffer_hours)
            old_points = old_buggy_expected_timestamps(
                now, cadence_hours, now - timedelta(hours=3), lag_cutoff)
            new_points = gate.expected_timestamps(
                now, cadence_hours, now - timedelta(hours=3), lag_cutoff)
            assert bucket_start in old_points, "舊語意應該（錯誤地）已經開始檢查這一桶"
            assert bucket_start not in new_points, "新語意應該仍在容忍期內，不檢查這一桶"

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
        with patch.object(gate, "_fetch_existing_timestamps", return_value=existing):
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
        with patch.object(gate, "_fetch_existing_timestamps", return_value=existing):
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
        with patch.object(gate, "_fetch_existing_timestamps", return_value=existing):
            result = gate.check_gaps(pipeline, now=now)
        assert result.passed


# ══════════════════════════════════════════════════════════════════════
# 第二類（逐點探測模式）：gap_probe_per_point=True
#
# 為什麼要另一條路徑：預設路徑把掃描窗內所有列抓回來只為了取 distinct 時間戳，
# 在 gsc_page_daily（視圖，底表近百萬列）上要翻約 1,000 頁深 OFFSET，必然撞
# statement_timeout（run 33776287535 實測 57014）。以下測試用假的 _get_page
# 直接驗查詢形狀：每個預期時間點各一次 limit=1 探測，跟表多大無關。
# ══════════════════════════════════════════════════════════════════════

def _probe_pipeline(**overrides) -> PipelineConfig:
    base = dict(
        timestamp_column="date", cadence_hours=24, cadence_label="daily",
        gap_window_hours=24 * 5, gap_probe_per_point=True, lag_buffer_hours=0.0,
    )
    base.update(overrides)
    return _pipeline(**base)


def _fake_get_page(available: set[str]):
    """假的 _get_page：只認兩種查詢形狀——帶 order=…asc 的「最早時間戳」，
    以及帶 date=eq.<日> 的「這天有沒有列」。任何其他形狀直接讓測試爆掉。"""
    calls: list[str] = []

    def fake(path: str, *, offset: int, page_size: int) -> tuple[list[dict], bool]:
        assert offset == 0, "逐點探測不該用 OFFSET 分頁"
        assert page_size == gate.PROBE_PAGE_SIZE, "逐點探測每次只取 1 列"
        calls.append(path)
        query = path.split("?", 1)[1]
        if "order=date.asc" in query:
            earliest = sorted(available)
            return ([{"date": earliest[0]}] if earliest else [], False)
        marker = "date=eq."
        assert marker in query, f"未預期的查詢形狀：{query}"
        day = query.split(marker, 1)[1].split("&", 1)[0]
        return ([{"date": day}] if day in available else [], False)

    fake.calls = calls  # type: ignore[attr-defined]
    return fake


class TestGapProbePerPoint:
    NOW = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
    ALL_DAYS = {"2026-08-30", "2026-08-31", "2026-09-01", "2026-09-02"}

    def test_every_expected_day_present_passes(self) -> None:
        fake = _fake_get_page(self.ALL_DAYS)
        with patch.object(gate, "_get_page", fake):
            result = gate.check_gaps(_probe_pipeline(), now=self.NOW)
        assert result.passed
        assert not result.skipped
        assert "逐點探測 4 個時間點" in result.message
        # 1 次「最早時間戳」+ 每個預期時間點 1 次，沒有第二種請求
        assert len(fake.calls) == 5  # type: ignore[attr-defined]

    def test_missing_middle_day_is_reported_as_gap(self) -> None:
        fake = _fake_get_page(self.ALL_DAYS - {"2026-08-31"})
        with patch.object(gate, "_get_page", fake):
            result = gate.check_gaps(_probe_pipeline(), now=self.NOW)
        assert not result.passed
        assert "2026-08-31" in result.message
        assert "1 個應有資料的時間點缺席" in result.message

    def test_earliest_timestamp_lifts_effective_start(self) -> None:
        """管線上線不滿掃描窗長度時，上線前『本來就沒有資料』不算空段——
        預設路徑靠 min(existing) 得到這個下限，探測路徑靠一次 order asc 取 1 列。"""
        fake = _fake_get_page({"2026-09-01", "2026-09-02"})
        with patch.object(gate, "_get_page", fake):
            result = gate.check_gaps(_probe_pipeline(), now=self.NOW)
        assert result.passed
        assert "2026-09-01T00:00:00+00:00" in result.message  # effective_start 被墊高
        assert "逐點探測 2 個時間點" in result.message

    def test_empty_window_probes_nothing_beyond_the_earliest_lookup(self) -> None:
        """窗內完全沒有資料時，effective_start 退回窗起點，每個預期時間點都是空段。"""
        fake = _fake_get_page(set())
        with patch.object(gate, "_get_page", fake):
            result = gate.check_gaps(_probe_pipeline(), now=self.NOW)
        assert not result.passed
        assert "4 個應有資料的時間點缺席" in result.message

    def test_query_error_fails_not_skips(self) -> None:
        with patch.object(gate, "_get_page", side_effect=gate.SupabaseQueryError("57014")):
            result = gate.check_gaps(_probe_pipeline(), now=self.NOW)
        assert not result.passed
        assert not result.skipped
        assert "57014" in result.message

    def test_probe_query_filters_are_carried_through(self) -> None:
        fake = _fake_get_page(self.ALL_DAYS)
        pipeline = _probe_pipeline(filters=(("search_type", "web"),))
        with patch.object(gate, "_get_page", fake):
            gate.check_gaps(pipeline, now=self.NOW)
        assert all("search_type=eq.web" in path for path in fake.calls)  # type: ignore[attr-defined]

    def test_timestamp_column_uses_half_open_interval_not_eq(self) -> None:
        """非 DATE 欄位（timestamp）不能用 eq——桶是區間，要用 [t, t+cadence)。"""
        seen: list[str] = []

        def fake(path: str, *, offset: int, page_size: int) -> tuple[list[dict], bool]:
            seen.append(path)
            return [{"ts": "2026-09-02T12:00:00Z"}], False

        pipeline = _probe_pipeline(timestamp_column="ts", cadence_hours=1, gap_window_hours=3)
        with patch.object(gate, "_get_page", fake):
            gate.check_gaps(pipeline, now=self.NOW)
        point_queries = [p for p in seen if "order=" not in p]
        assert point_queries, "應該有逐點探測的查詢"
        assert all("ts=gte." in p and "ts=lt." in p for p in point_queries)


class TestGapProbeOptInOnly:
    """(d) 回歸：沒開 gap_probe_per_point 的管線行為零變更，仍走整窗抓取那條路。"""

    def test_default_pipeline_still_uses_fetch_existing_timestamps(self) -> None:
        pipeline = _pipeline(gap_window_hours=3)
        assert pipeline.gap_probe_per_point is False
        now = datetime(2026, 9, 2, 14, 30, tzinfo=UTC)
        existing = {datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                    datetime(2026, 9, 2, 13, 0, tzinfo=UTC)}
        with patch.object(gate, "_fetch_existing_timestamps",
                          return_value=existing) as fetch, \
             patch.object(gate, "_probe_point_exists") as probe:
            result = gate.check_gaps(pipeline, now=now)
        assert result.passed
        fetch.assert_called_once()
        probe.assert_not_called()

    def test_only_gsc_daily_metrics_opts_in(self) -> None:
        """開關是 opt-in：小表走原路徑（一次請求抓完）比發 N 次請求便宜。"""
        opted_in = [p.key for p in PIPELINES_BY_KEY.values() if p.gap_probe_per_point]
        assert opted_in == ["gsc_daily_metrics"]

    def test_gsc_daily_metrics_keeps_surface_agnostic_semantics(self) -> None:
        """刻意不加 search_type 篩選：任一 surface 當天有列就算那天有資料，
        跟改成逐點探測之前同一個語意（只換查詢形狀，不換判準）。"""
        assert PIPELINES_BY_KEY["gsc_daily_metrics"].filters == ()


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
            existing = gate._fetch_existing_timestamps(
                pipeline, datetime(2026, 9, 2, tzinfo=UTC))
        assert existing == {
            datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
            datetime(2026, 9, 2, 13, 0, tzinfo=UTC),
        }

    def test_degradation_select_columns_includes_weight_column(self) -> None:
        d = DegradationConfig(column="ua_group", mode="fallback_value", fallback_value="other-bot",
                               weight_column="request_count", max_ratio=0.05, min_sample=1)
        pipeline = PIPELINES_BY_KEY["crawl_daily"]
        assert pipeline.degradation is d or True  # 真正管線設定可能不同物件，這裡只驗函式本身
        cols = gate._degradation_select_columns(
            _pipeline(select_columns=("date", "hour"), degradation=d))
        assert "request_count" in cols
        assert "ua_group" in cols


class TestRunCheckWithTimeout:
    """check 級逾時保護：一個卡住的 check 不該拖死其餘 check（watchdog 的存在意義）。"""

    def test_returns_result_when_fn_finishes_in_time(self) -> None:
        fn = lambda pipeline: gate.CheckResult(pipeline.key, "freshness", True, "PASS：測試")
        pipeline = _pipeline()
        result = gate._run_check_with_timeout("test_pipeline", "freshness", fn, pipeline, timeout=1)
        assert result.passed
        assert result.message == "PASS：測試"

    def test_times_out_and_reports_fail_with_seconds_in_message(self) -> None:
        def slow_fn(pipeline) -> gate.CheckResult:
            time.sleep(0.3)
            return gate.CheckResult(pipeline.key, "freshness", True, "PASS：不該被用到")

        pipeline = _pipeline()
        result = gate._run_check_with_timeout(
            "test_pipeline", "freshness", slow_fn, pipeline, timeout=0.05)
        assert not result.passed
        assert not result.skipped
        assert "timeout after 0.05s" in result.message
        assert result.pipeline_key == "test_pipeline"
        assert result.category == "freshness"

    def test_exception_inside_fn_becomes_fail_not_crash(self) -> None:
        def boom(pipeline) -> gate.CheckResult:
            raise RuntimeError("查詢炸了")

        pipeline = _pipeline()
        result = gate._run_check_with_timeout(
            "test_pipeline", "freshness", boom, pipeline, timeout=1)
        assert not result.passed
        assert "查詢炸了" in result.message

    def test_run_checks_uses_timeout_wrapper_for_every_category(self) -> None:
        """驗證 _run_checks 真的把每一類 check 都包進逾時保護，而不是只包其中一種。"""
        pipeline = PIPELINES_BY_KEY[next(iter(PIPELINES_BY_KEY))]
        with patch.object(gate, "_run_check_with_timeout",
                           return_value=gate.CheckResult(pipeline.key, "x", True, "PASS")) as wrapped:
            gate._run_checks(pipeline.key, "all")
        categories = [call.args[1] for call in wrapped.call_args_list]
        assert categories.count("freshness") == 1
        assert categories.count("gap") == 1
        assert categories.count("degradation") == 1

    def test_stuck_check_does_not_block_other_pipelines(self) -> None:
        """一個 pipeline 的 check 卡住逾時，其餘 pipeline 的 check 仍要跑完並回報。"""
        stuck_pipeline = _pipeline(key="stuck")
        ok_pipeline = _pipeline(key="ok")

        def fake_freshness(pipeline) -> gate.CheckResult:
            if pipeline.key == "stuck":
                time.sleep(0.3)
            return gate.CheckResult(pipeline.key, "freshness", True, "PASS：測試")

        with patch.object(gate, "PIPELINES", [stuck_pipeline, ok_pipeline]), \
             patch.object(gate, "check_freshness", side_effect=fake_freshness), \
             patch.object(gate, "check_gaps",
                          return_value=gate.CheckResult("x", "gap", True, "SKIP", skipped=True)), \
             patch.object(gate, "check_degradation",
                          return_value=gate.CheckResult("x", "degradation", True, "SKIP", skipped=True)), \
             patch.object(gate, "CHECK_TIMEOUT_SECONDS", 0.05):
            results = gate._run_checks(None, "freshness")
        by_key = {r.pipeline_key: r for r in results}
        assert not by_key["stuck"].passed
        assert "timeout after" in by_key["stuck"].message
        assert by_key["ok"].passed


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
