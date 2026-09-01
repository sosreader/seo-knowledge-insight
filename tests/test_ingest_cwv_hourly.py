"""Tests for ingest_cwv_hourly.py.

重點覆蓋三種 Loki 失敗路徑（400 bytes / 500 length / 200 全零），因為它們是這支腳本
最危險的地方——尤其「200 全零」不報錯，會靜默把空資料寫進歷史。
"""
from __future__ import annotations

import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ingest_cwv_hourly import (  # noqa: E402
    DEFAULT_LOOKBACK_HOURS,
    MAX_AGE_HOURS,
    MAX_BACKFILL_HOURS,
    RETENTION_SAFETY_MARGIN_HOURS,
    OUTLIER_MAX_BY_METRIC,
    OUTLIER_MAX_DEFAULT,
    LokiQueryError,
    build_count_query,
    build_outlier_filter,
    build_p75_query,
    build_rows,
    classify_loki_error,
    collect_rows,
    complete_hours,
    compute_unknown_ratios,
    parse_matrix,
    parse_iso_hour,
    resolve_hours,
    run_freshness_check,
    run_ingestion,
    truncate_to_hour,
)

UTC = timezone.utc


def _http_error(status: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", status, "err", {}, BytesIO(body.encode()))


# ══════════════════════════════════════════════════════════════════════
# 時間對齊 — cwv_hourly_source_granularity_ck 要求 rum 嚴格對齊 UTC 整點
# ══════════════════════════════════════════════════════════════════════

class TestHourAlignment:
    def test_truncate_drops_sub_hour_parts(self) -> None:
        moment = datetime(2026, 8, 28, 14, 37, 52, 123456, tzinfo=UTC)
        assert truncate_to_hour(moment) == datetime(2026, 8, 28, 14, 0, tzinfo=UTC)

    def test_truncate_normalises_non_utc_input(self) -> None:
        taipei = timezone(timedelta(hours=8))
        moment = datetime(2026, 8, 28, 22, 37, tzinfo=taipei)  # = 14:37 UTC
        assert truncate_to_hour(moment) == datetime(2026, 8, 28, 14, 0, tzinfo=UTC)

    def test_current_incomplete_hour_is_excluded(self) -> None:
        """14:37 時 14:00-15:00 還沒結束，不得寫入（半滿的桶）。"""
        hours = complete_hours(datetime(2026, 8, 28, 14, 37, tzinfo=UTC), 2)
        assert hours == [
            datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
            datetime(2026, 8, 28, 13, 0, tzinfo=UTC),
        ]

    def test_exact_hour_boundary_still_excludes_current_hour(self) -> None:
        hours = complete_hours(datetime(2026, 8, 28, 14, 0, 0, tzinfo=UTC), 1)
        assert hours == [datetime(2026, 8, 28, 13, 0, tzinfo=UTC)]

    def test_hours_are_ordered_oldest_first(self) -> None:
        hours = complete_hours(datetime(2026, 8, 28, 14, 30, tzinfo=UTC), 5)
        assert hours == sorted(hours)
        assert len(hours) == 5


class TestBackfillGuard:
    def test_default_lookback_overlaps_for_self_healing(self) -> None:
        assert len(resolve_hours(None)) == DEFAULT_LOOKBACK_HOURS
        assert DEFAULT_LOOKBACK_HOURS >= 2, "相鄰執行必須重疊才能自癒"

    def test_span_cap_is_a_typo_guard_not_the_retention_defence(self) -> None:
        # 跨度上限只防打錯字；保留期防線是 MAX_AGE_HOURS 的絕對時間檢查。
        assert MAX_BACKFILL_HOURS == 48
        assert MAX_AGE_HOURS == 168 - RETENTION_SAFETY_MARGIN_HOURS
        assert MAX_AGE_HOURS < 168, "必須留邊界，不頂著保留期門檻跑"

    def test_over_span_rejected_and_points_at_the_real_guard(self) -> None:
        with pytest.raises(ValueError) as excinfo:
            resolve_hours(200)
        message = str(excinfo.value)
        assert "200" in message
        assert "MAX_AGE_HOURS" in message, "錯誤訊息要把人導向真正的門檻，不要讓人以為放寬跨度就安全"

    def test_narrow_but_old_window_is_reachable(self) -> None:
        # 這是舊實作構不到的形狀：只有 34h 寬，但起點在 82h 前。
        # 舊實作把視窗錨死在 now，只能靠加大跨度往回搆，而跨度上限正好禁止。
        now = datetime(2026, 9, 1, 7, 49, tzinfo=timezone.utc)
        hours = resolve_hours(34, until=datetime(2026, 8, 30, 7, 0, tzinfo=timezone.utc), now=now)
        assert len(hours) == 34
        assert hours[0] == datetime(2026, 8, 28, 21, 0, tzinfo=timezone.utc)
        assert hours[-1] == datetime(2026, 8, 30, 6, 0, tzinfo=timezone.utc)

    def test_window_beyond_retention_rejected_by_absolute_age(self) -> None:
        # 跨度合格（2h）但整段已在保留期外——舊的跨度檢查會放行，這裡必須擋下。
        now = datetime(2026, 9, 1, 7, 49, tzinfo=timezone.utc)
        with pytest.raises(ValueError) as excinfo:
            resolve_hours(2, until=datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc), now=now)
        message = str(excinfo.value)
        assert "全零" in message, "要講清楚危險在於靜默回空，不是查詢會失敗"
        assert "救不回來" in message

    def test_future_anchor_rejected(self) -> None:
        now = datetime(2026, 9, 1, 7, 49, tzinfo=timezone.utc)
        with pytest.raises(ValueError) as excinfo:
            resolve_hours(2, until=datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc), now=now)
        assert "未來" in str(excinfo.value)

    def test_naive_anchor_treated_as_utc(self) -> None:
        assert parse_iso_hour("2026-08-30T07:00:00") == parse_iso_hour("2026-08-30T07:00:00Z")

    def test_malformed_anchor_rejected(self) -> None:
        with pytest.raises(ValueError):
            parse_iso_hour("30/08/2026")

    def test_limit_boundary_accepted(self) -> None:
        assert len(resolve_hours(MAX_BACKFILL_HOURS)) == MAX_BACKFILL_HOURS

    def test_zero_and_negative_rejected(self) -> None:
        for bad in (0, -1):
            with pytest.raises(ValueError):
                resolve_hours(bad)


# ══════════════════════════════════════════════════════════════════════
# 三種 Loki 失敗路徑
# ══════════════════════════════════════════════════════════════════════

class TestLokiErrorClassification:
    """status code 分不出來（實測 400/500 兩種都可能是 length 超限），一定要看訊息。"""

    def test_bytes_limit_is_http_400_preflight(self) -> None:
        error = classify_loki_error(
            400, "the query would read too many bytes (query: 5GB, limit: 3GB)"
        )
        assert error.kind == "bytes-limit"
        assert "3GB" in error.detail
        assert "縮小" in error.remedy

    def test_length_limit_surfaces_as_http_400_when_window_alone_exceeds(self) -> None:
        error = classify_loki_error(
            400, "the query time range exceeds the limit (query length: 171h0m0s, limit: 7d2h)"
        )
        assert error.kind == "length-limit"
        assert "170h" in error.detail

    def test_length_limit_surfaces_as_http_500_when_additive_accounting_exceeds(self) -> None:
        """169h 窗 + [2h] selector = 171h：內層 400 被包成 HTTP 500。"""
        error = classify_loki_error(
            500,
            "Failed to get bytes read stats for query: rpc error: code = Code(400) "
            "desc = the query time range exceeds the limit (query length: 171h0m0s, limit: 7d2h)",
        )
        assert error.kind == "length-limit", "同一種違規會依哪層先攔到吐 400 或 500"
        assert "加總" in error.remedy

    def test_bytes_wins_over_length_when_both_words_present(self) -> None:
        error = classify_loki_error(400, "query would read too many bytes; time range is long")
        assert error.kind == "bytes-limit"

    def test_unknown_error_mentions_cloudflare_user_agent_trap(self) -> None:
        error = classify_loki_error(403, "error code: 1010")
        assert error.kind == "unknown"
        assert "User-Agent" in error.remedy

    def test_http_error_is_converted_to_classified_exception(self) -> None:
        from scripts.ingest_cwv_hourly import _loki_get

        env = {
            "GRAFANA_URL": "https://grafana.example",
            "GRAFANA_SERVICE_ACCOUNT_TOKEN": "t",
            "CF_ACCESS_CLIENT_ID": "i",
            "CF_ACCESS_CLIENT_SECRET": "s",
        }
        body = "the query time range exceeds the limit (query length: 171h0m0s, limit: 7d2h)"
        with patch.dict("os.environ", env), patch(
            "urllib.request.urlopen", side_effect=_http_error(400, body)
        ):
            with pytest.raises(LokiQueryError) as excinfo:
                _loki_get("/query_range", {"query": "x"})
        assert excinfo.value.kind == "length-limit"


class TestBeyondRetentionSilentEmpty:
    """最危險的一種：HTTP 200 + 空結果，沒有任何錯誤或警告。"""

    ZERO_STATS = {"streams": 0, "chunks": 0, "entries": 0, "bytes": 0}

    def test_all_zero_response_produces_no_rows_not_zero_rows(self) -> None:
        hours = [datetime(2026, 8, 28, 12, 0, tzinfo=UTC)]
        with patch("scripts.ingest_cwv_hourly.loki_index_stats", return_value=self.ZERO_STATS), \
             patch("scripts.ingest_cwv_hourly.loki_query_range", return_value=[]):
            rows, stats = collect_rows(hours)
        assert rows == [], "sample_count==0 的桶必須不落庫，不是寫 0"
        assert stats["hours_with_rows"] == 0

    def test_run_marks_partial_and_never_writes_zero_rows(self) -> None:
        hours = [datetime(2026, 8, 28, 12, 0, tzinfo=UTC)]
        with patch("scripts.ingest_cwv_hourly.loki_index_stats", return_value=self.ZERO_STATS), \
             patch("scripts.ingest_cwv_hourly.loki_query_range", return_value=[]), \
             patch("scripts.ingest_cwv_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_hourly.upsert_rows", return_value=(0, 0)) as upsert, \
             patch("scripts.ingest_cwv_hourly.finish_run") as finish:
            assert run_ingestion(hours, execute=True) == 0
        upsert.assert_called_once_with([])
        finish.assert_called_once_with("run-1", "partial", 0)

    def test_partial_when_only_some_hours_have_data(self) -> None:
        hours = [datetime(2026, 8, 28, h, 0, tzinfo=UTC) for h in (12, 13)]
        counts = [{
            "metric": {"environment": "production", "metricType": "LCP",
                       "routePattern": "/", "deviceType": "mobile"},
            "values": [[datetime(2026, 8, 28, 14, 0, tzinfo=UTC).timestamp(), "10"]],
        }]
        with patch("scripts.ingest_cwv_hourly.loki_index_stats",
                   return_value={"entries": 10, "bytes": 100}), \
             patch("scripts.ingest_cwv_hourly.loki_query_range", return_value=counts), \
             patch("scripts.ingest_cwv_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_hourly.upsert_rows", return_value=(1, 0)), \
             patch("scripts.ingest_cwv_hourly.finish_run") as finish:
            run_ingestion(hours, execute=True)
        finish.assert_called_once_with("run-1", "partial", 1)

    def test_loki_failure_marks_run_failed_and_exits_nonzero(self) -> None:
        hours = [datetime(2026, 8, 28, 12, 0, tzinfo=UTC)]
        error = LokiQueryError("bytes-limit", "detail", "remedy")
        with patch("scripts.ingest_cwv_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_hourly.collect_rows", side_effect=error), \
             patch("scripts.ingest_cwv_hourly.finish_run") as finish:
            assert run_ingestion(hours, execute=True) == 1
        finish.assert_called_once_with("run-1", "failed", 0)


# ══════════════════════════════════════════════════════════════════════
# LogQL 組裝
# ══════════════════════════════════════════════════════════════════════

class TestQueryConstruction:
    def test_outlier_filter_applies_generic_ceiling_then_per_metric(self) -> None:
        expression = build_outlier_filter()
        assert f"value < {OUTLIER_MAX_DEFAULT:g}" in expression
        for metric, ceiling in OUTLIER_MAX_BY_METRIC.items():
            assert f'metricType != "{metric}" or value < {ceiling:g}' in expression

    def test_inp_ceiling_is_stricter_than_default(self) -> None:
        """LCP > 5s 是真實的 poor 測量值，不能砍；INP > 5s 是背景分頁 artifact。"""
        assert OUTLIER_MAX_BY_METRIC["INP"] < OUTLIER_MAX_DEFAULT

    def test_same_filter_on_count_and_p75_keeps_populations_consistent(self) -> None:
        expression = build_outlier_filter()
        assert expression in build_count_query()
        assert expression in build_count_query("good")
        assert expression in build_p75_query()

    def test_good_query_filters_on_rating_stream_label(self) -> None:
        assert 'rating="good"' in build_count_query("good")
        assert "rating=" not in build_count_query()

    def test_all_four_dimensions_are_grouped(self) -> None:
        for query in (build_count_query(), build_p75_query()):
            for label in ("environment", "metricType", "routePattern", "deviceType"):
                assert label in query


# ══════════════════════════════════════════════════════════════════════
# 聚合
# ══════════════════════════════════════════════════════════════════════

def _series(labels: dict, points: list[tuple[datetime, str]]) -> dict:
    return {"metric": labels, "values": [[ts.timestamp(), value] for ts, value in points]}


DIMS = {"environment": "production", "metricType": "LCP",
        "routePattern": "/article/[id]", "deviceType": "mobile"}


class TestParseMatrix:
    def test_evaluation_point_maps_to_previous_hour(self) -> None:
        """count_over_time 在 T 涵蓋 (T-1h, T]，所以 T 的評估值屬於 T-1h 這個桶。"""
        parsed = parse_matrix([_series(DIMS, [(datetime(2026, 8, 28, 14, 0, tzinfo=UTC), "42")])])
        key = (datetime(2026, 8, 28, 13, 0, tzinfo=UTC),
               ("production", "LCP", "/article/[id]", "mobile"))
        assert parsed == {key: 42.0}

    def test_missing_label_degrades_to_unknown_not_dropped(self) -> None:
        partial = {"environment": "production", "metricType": "LCP"}
        parsed = parse_matrix([_series(partial, [(datetime(2026, 8, 28, 14, 0, tzinfo=UTC), "1")])])
        assert list(parsed)[0][1] == ("production", "LCP", "unknown", "unknown")

    def test_empty_result_yields_empty_mapping(self) -> None:
        assert parse_matrix([]) == {}


class TestUnknownRatio:
    """hour-level 純量：任一維度為 unknown 的樣本數 ÷ 該小時總樣本數。"""

    HOUR = datetime(2026, 8, 28, 13, 0, tzinfo=UTC)

    def test_zero_when_every_dimension_is_allowlisted(self) -> None:
        counts = {(self.HOUR, ("production", "LCP", "/", "mobile")): 100.0}
        assert compute_unknown_ratios(counts) == {self.HOUR: 0.0}

    def test_counts_sample_if_any_single_dimension_degraded(self) -> None:
        counts = {
            (self.HOUR, ("production", "LCP", "/", "mobile")): 75.0,
            (self.HOUR, ("production", "unknown", "/", "mobile")): 15.0,
            (self.HOUR, ("production", "LCP", "/", "unknown")): 10.0,
        }
        assert compute_unknown_ratios(counts)[self.HOUR] == pytest.approx(0.25)

    def test_is_not_degenerate_per_bucket(self) -> None:
        """若按桶各算自己的，桶鍵已固定維度值，比例必為 0 或 1——那才是要避免的定義。"""
        counts = {
            (self.HOUR, ("production", "LCP", "/", "mobile")): 90.0,
            (self.HOUR, ("production", "unknown", "/", "mobile")): 10.0,
        }
        ratio = compute_unknown_ratios(counts)[self.HOUR]
        assert 0.0 < ratio < 1.0
        assert ratio == pytest.approx(0.1)

    def test_hours_are_computed_independently(self) -> None:
        other = datetime(2026, 8, 28, 14, 0, tzinfo=UTC)
        counts = {
            (self.HOUR, ("production", "unknown", "/", "mobile")): 5.0,
            (other, ("production", "LCP", "/", "mobile")): 5.0,
        }
        assert compute_unknown_ratios(counts) == {self.HOUR: 1.0, other: 0.0}


class TestBuildRows:
    HOUR = datetime(2026, 8, 28, 13, 0, tzinfo=UTC)
    KEY = (HOUR, ("production", "LCP", "/article/[id]", "mobile"))

    def test_row_maps_labels_to_columns_and_aligns_hour(self) -> None:
        rows = build_rows({self.KEY: 20.0}, {self.KEY: 15.0}, {self.KEY: 2500.0}, [self.HOUR])
        assert rows == [{
            "hour": "2026-08-28T13:00:00Z",
            "p75": 2500.0,
            "good_rate": 0.75,
            "sample_count": 20,
            "unknown_ratio": 0.0,
            "source": "rum",
            "environment": "production",
            "metric": "LCP",
            "route_type": "/article/[id]",
            "device": "mobile",
        }]

    def test_hour_level_ratio_is_copied_onto_every_row_of_that_hour(self) -> None:
        degraded = (self.HOUR, ("production", "unknown", "/", "mobile"))
        counts = {self.KEY: 30.0, degraded: 10.0}
        rows = build_rows(counts, {}, {self.KEY: 1.0, degraded: 1.0}, [self.HOUR])
        assert len(rows) == 2
        assert {row["unknown_ratio"] for row in rows} == {0.25}

    def test_zero_sample_bucket_is_skipped(self) -> None:
        assert build_rows({self.KEY: 0.0}, {}, {self.KEY: 1.0}, [self.HOUR]) == []

    def test_bucket_without_p75_is_skipped_not_guessed(self) -> None:
        assert build_rows({self.KEY: 5.0}, {self.KEY: 5.0}, {}, [self.HOUR]) == []

    def test_hours_outside_the_requested_window_are_dropped(self) -> None:
        """Loki 的評估點可能落在窗外，不能讓它偷渡進 warehouse。"""
        other = datetime(2026, 8, 28, 9, 0, tzinfo=UTC)
        counts = {self.KEY: 5.0, (other, ("production", "LCP", "/", "mobile")): 5.0}
        rows = build_rows(counts, {}, {k: 1.0 for k in counts}, [self.HOUR])
        assert [row["hour"] for row in rows] == ["2026-08-28T13:00:00Z"]

    def test_good_rate_and_p75_stay_within_check_constraint_bounds(self) -> None:
        rows = build_rows({self.KEY: 10.0}, {self.KEY: 99.0}, {self.KEY: -3.0}, [self.HOUR])
        assert rows[0]["good_rate"] == 1.0  # CHECK good_rate BETWEEN 0 AND 1
        assert rows[0]["p75"] == 0.0        # CHECK p75 >= 0

    def test_missing_good_count_means_zero_good_rate(self) -> None:
        rows = build_rows({self.KEY: 10.0}, {}, {self.KEY: 1.0}, [self.HOUR])
        assert rows[0]["good_rate"] == 0.0


# ══════════════════════════════════════════════════════════════════════
# 新鮮度告警 — 條件是資料的缺席，不是作業回報失敗
# ══════════════════════════════════════════════════════════════════════

class TestFreshnessCheck:
    def test_empty_table_fails(self) -> None:
        with patch("scripts.ingest_cwv_hourly.latest_success_hour", return_value=None):
            assert run_freshness_check() == 1

    def test_stale_data_fails(self) -> None:
        stale = datetime.now(UTC) - timedelta(hours=5)
        with patch("scripts.ingest_cwv_hourly.latest_success_hour", return_value=stale):
            assert run_freshness_check() == 1

    def test_fresh_data_passes(self) -> None:
        fresh = datetime.now(UTC) - timedelta(minutes=90)
        with patch("scripts.ingest_cwv_hourly.latest_success_hour", return_value=fresh):
            assert run_freshness_check() == 0

    def test_threshold_is_multiple_of_hourly_schedule(self) -> None:
        from scripts.ingest_cwv_hourly import FRESHNESS_MAX_AGE_HOURS

        assert FRESHNESS_MAX_AGE_HOURS >= 2, "要容忍單次重試，但不容忍連續兩次靜默"


# ══════════════════════════════════════════════════════════════════════
# Loki HTTP 層
# ══════════════════════════════════════════════════════════════════════

class _FakeResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode()
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


GRAFANA_ENV = {
    "GRAFANA_URL": "https://grafana.example/",
    "GRAFANA_SERVICE_ACCOUNT_TOKEN": "token",
    "CF_ACCESS_CLIENT_ID": "cf-id",
    "CF_ACCESS_CLIENT_SECRET": "cf-secret",
}


class TestLokiTransport:
    def test_headers_carry_bearer_cf_access_and_custom_user_agent(self) -> None:
        from scripts.ingest_cwv_hourly import USER_AGENT, loki_headers

        with patch.dict("os.environ", GRAFANA_ENV):
            headers = loki_headers()
        assert headers["Authorization"] == "Bearer token"
        assert headers["CF-Access-Client-Id"] == "cf-id"
        assert headers["CF-Access-Client-Secret"] == "cf-secret"
        # 預設的 Python-urllib UA 會被 Cloudflare 以 error code 1010 擋掉
        assert headers["User-Agent"] == USER_AGENT
        assert "urllib" not in headers["User-Agent"].lower()

    @pytest.mark.parametrize("missing", sorted(GRAFANA_ENV))
    def test_missing_credential_raises(self, missing: str) -> None:
        from scripts.ingest_cwv_hourly import _loki_get

        env = {key: ("" if key == missing else value) for key, value in GRAFANA_ENV.items()}
        with patch.dict("os.environ", env), pytest.raises(RuntimeError):
            _loki_get("/query_range", {"query": "x"})

    def test_query_range_uses_proxy_path_and_hour_step(self) -> None:
        from scripts.ingest_cwv_hourly import LOKI_DATASOURCE_UID, loki_query_range

        captured: dict[str, str] = {}

        def _capture(request, timeout=0):  # noqa: ANN001
            captured["url"] = request.full_url
            return _FakeResponse('{"data": {"result": [{"metric": {}, "values": []}]}}')

        with patch.dict("os.environ", GRAFANA_ENV), patch("urllib.request.urlopen", _capture):
            result = loki_query_range(
                "q", datetime(2026, 8, 28, 13, 0, tzinfo=UTC), datetime(2026, 8, 28, 14, 0, tzinfo=UTC)
            )
        assert result == [{"metric": {}, "values": []}]
        # 只有 proxy 路徑可用；/resources/ 路徑實測回 404
        assert f"/api/datasources/proxy/uid/{LOKI_DATASOURCE_UID}/loki/api/v1/query_range" in captured["url"]
        assert "step=3600s" in captured["url"]

    def test_index_stats_returns_zero_signature_beyond_retention(self) -> None:
        from scripts.ingest_cwv_hourly import loki_index_stats

        body = '{"streams": 0, "chunks": 0, "entries": 0, "bytes": 0}'
        with patch.dict("os.environ", GRAFANA_ENV), \
             patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            stats = loki_index_stats(
                datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 7, 1, 1, 0, tzinfo=UTC)
            )
        assert stats["entries"] == 0


# ══════════════════════════════════════════════════════════════════════
# Supabase 層
# ══════════════════════════════════════════════════════════════════════

SUPABASE_ENV = {"SUPABASE_URL": "https://db.example/", "SUPABASE_SERVICE_KEY": "svc"}
HOUR = datetime(2026, 8, 28, 13, 0, tzinfo=UTC)


class TestSupabaseTransport:
    @pytest.mark.parametrize("missing", sorted(SUPABASE_ENV))
    def test_missing_credential_raises(self, missing: str) -> None:
        from scripts.ingest_cwv_hourly import supabase_config

        env = {key: ("" if key == missing else value) for key, value in SUPABASE_ENV.items()}
        with patch.dict("os.environ", env), pytest.raises(RuntimeError):
            supabase_config()

    def test_trailing_slash_is_stripped(self) -> None:
        from scripts.ingest_cwv_hourly import supabase_config

        with patch.dict("os.environ", SUPABASE_ENV):
            assert supabase_config()[0] == "https://db.example"

    def test_http_error_is_returned_not_raised(self) -> None:
        from scripts.ingest_cwv_hourly import _supabase_request

        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(409, "conflict")):
            status, body = _supabase_request("POST", "/rest/v1/x", body=[])
        assert (status, body) == (409, "conflict")


class TestIngestionRunLifecycle:
    def test_start_run_inserts_running_row_and_returns_id(self) -> None:
        from scripts.ingest_cwv_hourly import start_run

        with patch("scripts.ingest_cwv_hourly._supabase_request",
                   return_value=(201, '[{"id": "abc"}]')) as request:
            run_id = start_run(HOUR, HOUR + timedelta(hours=2))
        assert run_id == "abc"
        payload = request.call_args.kwargs["body"][0]
        assert payload["status"] == "running"
        assert payload["table_name"] == "cwv_hourly"
        assert payload["window_start"] == "2026-08-28T13:00:00Z"

    def test_start_run_failure_returns_none_without_raising(self) -> None:
        from scripts.ingest_cwv_hourly import start_run

        with patch("scripts.ingest_cwv_hourly._supabase_request", return_value=(500, "boom")):
            assert start_run(HOUR, HOUR + timedelta(hours=1)) is None

    def test_finish_run_sets_terminal_status_and_finished_at(self) -> None:
        from scripts.ingest_cwv_hourly import finish_run

        with patch("scripts.ingest_cwv_hourly._supabase_request",
                   return_value=(204, "")) as request:
            finish_run("abc", "success", 12)
        payload = request.call_args.kwargs["body"]
        assert payload["status"] == "success"
        assert payload["row_count"] == 12
        # CHECK: status <> 'running' → finished_at NOT NULL
        assert payload["finished_at"].endswith("Z")

    def test_finish_run_without_id_is_a_noop(self) -> None:
        from scripts.ingest_cwv_hourly import finish_run

        with patch("scripts.ingest_cwv_hourly._supabase_request") as request:
            finish_run(None, "success", 0)
        request.assert_not_called()

    def test_finish_run_logs_but_does_not_raise_on_failure(self) -> None:
        from scripts.ingest_cwv_hourly import finish_run

        with patch("scripts.ingest_cwv_hourly._supabase_request", return_value=(500, "boom")):
            finish_run("abc", "failed", 0)


class TestUpsert:
    ROW = {"hour": "2026-08-28T13:00:00Z", "source": "rum", "environment": "production",
           "metric": "LCP", "route_type": "/", "device": "mobile",
           "p75": 1.0, "good_rate": 1.0, "sample_count": 1, "unknown_ratio": 0.0}

    def test_uses_merge_duplicates_on_the_unique_dimension_key(self) -> None:
        from scripts.ingest_cwv_hourly import CONFLICT_KEY, upsert_rows

        with patch("scripts.ingest_cwv_hourly._supabase_request",
                   return_value=(204, "")) as request:
            assert upsert_rows([self.ROW]) == (1, 0)
        path = request.call_args.args[1]
        headers = request.call_args.kwargs["extra_headers"]
        assert "resolution=merge-duplicates" in headers["Prefer"]
        for column in CONFLICT_KEY.split(","):
            assert column in path

    def test_ingested_at_is_never_sent_so_reruns_are_true_noops(self) -> None:
        from scripts.ingest_cwv_hourly import upsert_rows

        with patch("scripts.ingest_cwv_hourly._supabase_request",
                   return_value=(204, "")) as request:
            upsert_rows([self.ROW])
        assert "ingested_at" not in request.call_args.kwargs["body"][0]

    def test_failed_batch_is_counted_not_raised(self) -> None:
        from scripts.ingest_cwv_hourly import upsert_rows

        with patch("scripts.ingest_cwv_hourly._supabase_request", return_value=(400, "bad")):
            assert upsert_rows([self.ROW, self.ROW]) == (0, 2)

    def test_rows_are_chunked_by_batch_size(self) -> None:
        from scripts.ingest_cwv_hourly import UPSERT_BATCH_SIZE, upsert_rows

        rows = [self.ROW] * (UPSERT_BATCH_SIZE + 1)
        with patch("scripts.ingest_cwv_hourly._supabase_request",
                   return_value=(204, "")) as request:
            assert upsert_rows(rows) == (len(rows), 0)
        assert request.call_count == 2

    def test_empty_input_makes_no_request(self) -> None:
        from scripts.ingest_cwv_hourly import upsert_rows

        with patch("scripts.ingest_cwv_hourly._supabase_request") as request:
            assert upsert_rows([]) == (0, 0)
        request.assert_not_called()


class TestLatestSuccessHour:
    def test_parses_zulu_timestamp(self) -> None:
        from scripts.ingest_cwv_hourly import latest_success_hour

        with patch("scripts.ingest_cwv_hourly._supabase_request",
                   return_value=(200, '[{"hour": "2026-08-28T13:00:00+00:00"}]')):
            assert latest_success_hour() == HOUR

    def test_empty_table_returns_none(self) -> None:
        from scripts.ingest_cwv_hourly import latest_success_hour

        with patch("scripts.ingest_cwv_hourly._supabase_request", return_value=(200, "[]")):
            assert latest_success_hour() is None

    def test_query_failure_raises(self) -> None:
        from scripts.ingest_cwv_hourly import latest_success_hour

        with patch("scripts.ingest_cwv_hourly._supabase_request", return_value=(500, "boom")), \
             pytest.raises(RuntimeError):
            latest_success_hour()


# ══════════════════════════════════════════════════════════════════════
# 執行模式與 CLI
# ══════════════════════════════════════════════════════════════════════

class TestDryRunAndVerify:
    ROWS = [{"hour": "2026-08-28T13:00:00Z", "environment": "production", "metric": "LCP",
             "route_type": "/", "device": "mobile", "p75": 1200.0, "good_rate": 0.9,
             "sample_count": 30, "unknown_ratio": 0.0, "source": "rum"}] * 10

    def test_dry_run_never_writes(self) -> None:
        stats = {"dimension_buckets": 10, "rows": 10, "hours_with_rows": 1,
                 "hours_requested": 1, "scanned_entries": 100, "scanned_bytes": 1024,
                 "unknown_ratio_by_hour": {HOUR: 0.0}}
        with patch("scripts.ingest_cwv_hourly.collect_rows", return_value=(self.ROWS, stats)), \
             patch("scripts.ingest_cwv_hourly.start_run") as start, \
             patch("scripts.ingest_cwv_hourly.upsert_rows") as upsert:
            assert run_ingestion([HOUR], execute=False) == 0
        start.assert_not_called()
        upsert.assert_not_called()

    def test_execute_reports_failure_when_upsert_fails(self) -> None:
        stats = {"dimension_buckets": 1, "rows": 1, "hours_with_rows": 1,
                 "hours_requested": 1, "scanned_entries": 1, "scanned_bytes": 1,
                 "unknown_ratio_by_hour": {HOUR: 0.0}}
        with patch("scripts.ingest_cwv_hourly.collect_rows", return_value=(self.ROWS[:1], stats)), \
             patch("scripts.ingest_cwv_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_hourly.upsert_rows", return_value=(0, 1)), \
             patch("scripts.ingest_cwv_hourly.finish_run") as finish:
            assert run_ingestion([HOUR], execute=True) == 1
        finish.assert_called_once_with("run-1", "failed", 0)

    def test_partial_when_some_rows_fail(self) -> None:
        stats = {"dimension_buckets": 2, "rows": 2, "hours_with_rows": 1,
                 "hours_requested": 1, "scanned_entries": 2, "scanned_bytes": 2,
                 "unknown_ratio_by_hour": {HOUR: 0.0}}
        with patch("scripts.ingest_cwv_hourly.collect_rows", return_value=(self.ROWS[:2], stats)), \
             patch("scripts.ingest_cwv_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_hourly.upsert_rows", return_value=(1, 1)), \
             patch("scripts.ingest_cwv_hourly.finish_run") as finish:
            run_ingestion([HOUR], execute=True)
        finish.assert_called_once_with("run-1", "partial", 1)

    def test_success_status_when_all_hours_written(self) -> None:
        stats = {"dimension_buckets": 1, "rows": 1, "hours_with_rows": 1,
                 "hours_requested": 1, "scanned_entries": 1, "scanned_bytes": 1,
                 "unknown_ratio_by_hour": {HOUR: 0.0}}
        with patch("scripts.ingest_cwv_hourly.collect_rows", return_value=(self.ROWS[:1], stats)), \
             patch("scripts.ingest_cwv_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_hourly.upsert_rows", return_value=(1, 0)), \
             patch("scripts.ingest_cwv_hourly.finish_run") as finish:
            assert run_ingestion([HOUR], execute=True) == 0
        finish.assert_called_once_with("run-1", "success", 1)

    def test_verify_reads_both_tables(self) -> None:
        from scripts.ingest_cwv_hourly import run_verify

        rows = ('[{"hour": "2026-08-28T13:00:00+00:00", "environment": "production", '
                '"metric": "LCP", "route_type": "/", "device": "mobile", "p75": 1.0, '
                '"good_rate": 1.0, "sample_count": 1, "unknown_ratio": 0.0}]')
        runs = ('[{"id": "abcdefgh-1234", "window_start": "2026-08-28T13:00:00+00:00", '
                '"window_end": "2026-08-28T14:00:00+00:00", "row_count": 1, '
                '"status": "success", "started_at": "x", "finished_at": "y"}]')
        with patch("scripts.ingest_cwv_hourly._supabase_request",
                   side_effect=[(200, rows), (200, runs)]) as request:
            assert run_verify() == 0
        assert request.call_count == 2

    @pytest.mark.parametrize("responses", [
        [(500, "boom")],
        [(200, "[]"), (500, "boom")],
    ])
    def test_verify_returns_nonzero_on_read_failure(self, responses: list) -> None:
        from scripts.ingest_cwv_hourly import run_verify

        with patch("scripts.ingest_cwv_hourly._supabase_request", side_effect=responses):
            assert run_verify() == 1


class TestCli:
    def _run(self, argv: list[str]) -> int:
        from scripts.ingest_cwv_hourly import main

        with patch.object(sys, "argv", ["ingest_cwv_hourly.py", *argv]):
            with pytest.raises(SystemExit) as excinfo:
                main()
        return excinfo.value.code

    def test_verify_flag_dispatches_to_verify(self) -> None:
        with patch("scripts.ingest_cwv_hourly.run_verify", return_value=0) as verify:
            assert self._run(["--verify"]) == 0
        verify.assert_called_once()

    def test_check_freshness_flag_dispatches_to_freshness(self) -> None:
        with patch("scripts.ingest_cwv_hourly.run_freshness_check", return_value=1) as check:
            assert self._run(["--check-freshness"]) == 1
        check.assert_called_once()

    def test_over_limit_backfill_exits_two_without_touching_loki(self) -> None:
        with patch("scripts.ingest_cwv_hourly.run_ingestion") as ingest:
            assert self._run(["--execute", "--backfill-hours", "200"]) == 2
        ingest.assert_not_called()

    def test_default_invocation_is_dry_run(self) -> None:
        with patch("scripts.ingest_cwv_hourly.run_ingestion", return_value=0) as ingest:
            assert self._run([]) == 0
        assert ingest.call_args.kwargs["execute"] is False

    def test_execute_flag_enables_writes(self) -> None:
        with patch("scripts.ingest_cwv_hourly.run_ingestion", return_value=0) as ingest:
            self._run(["--execute"])
        assert ingest.call_args.kwargs["execute"] is True


class TestSupabaseSuccessResponse:
    def test_successful_request_returns_status_and_body(self) -> None:
        from scripts.ingest_cwv_hourly import _supabase_request

        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen",
                   return_value=_FakeResponse('[{"id": "x"}]', status=201)):
            status, body = _supabase_request("POST", "/rest/v1/x", body=[{"a": 1}])
        assert status == 201
        assert body == '[{"id": "x"}]'
