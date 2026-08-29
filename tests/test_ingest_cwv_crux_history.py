"""Tests for ingest_cwv_crux_history.py.

重點覆蓋四個 schema 對映問題（週界對齊 / sample_count=0 / metric 排除 round_trip_time /
route_type 的 URL-撞鍵防護），以及 CrUX 特有的「404=流量不足」「403=系統性中止」兩種
與 sister ingest_cwv_hourly.py 不同的錯誤語意。
"""
from __future__ import annotations

import json
import sys
import urllib.error
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ingest_cwv_crux_history import (  # noqa: E402
    CRUX_METRIC_TO_COLUMN,
    DEFAULT_COLLECTION_PERIOD_COUNT,
    ALL_DEVICE_SENTINEL,
    FORM_FACTOR_DEVICE_PAIRS,
    FORM_FACTOR_TO_DEVICE,
    ORIGIN_ROUTE_TYPE,
    REPRESENTATIVE_URLS,
    CruxQueryError,
    _assert_no_route_type_collisions,
    _log_summary,
    _ok_status,
    _supabase_request,
    align_to_monday_utc,
    backfill_window,
    classify_crux_error,
    collect_origin_rows,
    collect_url_rows,
    collection_period_to_hour,
    count_rows_by_source,
    crux_date_to_date,
    fetch_history_record,
    finish_run,
    good_rate_from_histogram,
    main,
    normalize_route_type,
    p75_at,
    record_to_rows,
    resolve_collection_period_count,
    run_freshness_check,
    run_ingestion,
    run_verify,
    start_run,
    supabase_config,
    upsert_rows,
)

UTC = timezone.utc


def _http_error(status: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", status, "err", {}, BytesIO(body.encode()))


# ══════════════════════════════════════════════════════════════════════
# 週界對齊 — cwv_hourly_source_granularity_ck 要求 crux 對齊 UTC 週一 00:00
# ══════════════════════════════════════════════════════════════════════

class TestWeekAlignment:
    @pytest.mark.parametrize(
        "day, expected_monday",
        [
            (date(2026, 8, 24), date(2026, 8, 24)),  # 本身就是週一
            (date(2026, 8, 25), date(2026, 8, 24)),  # 週二
            (date(2026, 8, 30), date(2026, 8, 24)),  # 週日（同週）
            (date(2026, 8, 31), date(2026, 8, 31)),  # 下週一
        ],
    )
    def test_align_to_monday_utc(self, day: date, expected_monday: date) -> None:
        result = align_to_monday_utc(day)
        assert result == datetime(
            expected_monday.year, expected_monday.month, expected_monday.day, tzinfo=UTC
        )
        assert result.weekday() == 0

    def test_alignment_is_idempotent_across_calls(self) -> None:
        day = date(2026, 8, 27)
        assert align_to_monday_utc(day) == align_to_monday_utc(day)

    def test_crux_date_to_date_parses_year_month_day(self) -> None:
        assert crux_date_to_date({"year": 2026, "month": 8, "day": 27}) == date(2026, 8, 27)

    def test_collection_period_uses_last_date_not_first_date(self) -> None:
        # 見對映決定 (a)：基準是 lastDate，firstDate 差一整週時結果要不同
        period = {
            "firstDate": {"year": 2026, "month": 8, "day": 1},
            "lastDate": {"year": 2026, "month": 8, "day": 28},
        }
        result = collection_period_to_hour(period)
        assert result == align_to_monday_utc(date(2026, 8, 28))
        assert result != align_to_monday_utc(date(2026, 8, 1))


# ══════════════════════════════════════════════════════════════════════
# route_type 正規化與撞鍵防護
# ══════════════════════════════════════════════════════════════════════

class TestRouteTypeNormalization:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://vocus.cc/", "/"),
            ("https://vocus.cc/article/6a8ff520fd897800016aa2c1", "/article/[id]"),
            ("https://vocus.cc/tags/魚缸調水", "/tags/[...tagname]"),
            ("https://vocus.cc/help_center/NFnD2yLwVsBFzl0TyRh3", "/help_center/[id]"),
            ("https://vocus.cc/terms/privacy", "/terms/[id]"),
            ("https://vocus.cc/salon/some-salon-id", "/salon/[salonUrlId]"),
            ("https://vocus.cc/user/abc123", "/user/[uid]"),
            ("https://vocus.cc/post/xyz789", "/post/[postId]"),
        ],
    )
    def test_known_patterns(self, url: str, expected: str) -> None:
        assert normalize_route_type(url) == expected

    def test_event_page_falls_back_to_raw_path_not_a_rule(self) -> None:
        # /event/* 刻意不進規則表：靜態逐頁檔案，Next.js page 本身就是該路徑
        assert normalize_route_type("https://vocus.cc/event/welcome2026") == "/event/welcome2026"

    def test_unmapped_path_with_illegal_charset_falls_to_unknown(self) -> None:
        assert normalize_route_type("https://vocus.cc/weird path?query=1") == "unknown"

    def test_representative_urls_have_no_route_type_collision(self) -> None:
        # 不應拋例外——這是本腳本硬約束的守門測試
        _assert_no_route_type_collisions(REPRESENTATIVE_URLS)

    def test_colliding_urls_raise_assertion_error(self) -> None:
        colliding = (
            "https://vocus.cc/article/aaa",
            "https://vocus.cc/article/bbb",
        )
        with pytest.raises(AssertionError, match="route_type 衝突"):
            _assert_no_route_type_collisions(colliding)

    def test_representative_urls_cover_distinct_route_types(self) -> None:
        route_types = [normalize_route_type(url) for url in REPRESENTATIVE_URLS]
        assert len(route_types) == len(set(route_types))


# ══════════════════════════════════════════════════════════════════════
# collection-period-count 上限守護
# ══════════════════════════════════════════════════════════════════════

class TestCollectionPeriodCountGuard:
    def test_default_is_forty(self) -> None:
        assert resolve_collection_period_count(None) == DEFAULT_COLLECTION_PERIOD_COUNT == 40

    def test_within_range_is_accepted(self) -> None:
        assert resolve_collection_period_count(4) == 4

    def test_zero_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            resolve_collection_period_count(0)

    def test_over_forty_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            resolve_collection_period_count(41)


# ══════════════════════════════════════════════════════════════════════
# CrUX 錯誤分類 — 403=系統性(auth) / 429=rate-limit / 400=bad-request
# ══════════════════════════════════════════════════════════════════════

class TestCruxErrorClassification:
    def test_403_is_classified_as_auth(self) -> None:
        error = classify_crux_error(403, "PERMISSION_DENIED")
        assert error.kind == "auth"

    def test_429_is_classified_as_rate_limit(self) -> None:
        error = classify_crux_error(429, "quota exceeded")
        assert error.kind == "rate-limit"

    def test_400_is_classified_as_bad_request(self) -> None:
        error = classify_crux_error(400, "invalid argument")
        assert error.kind == "bad-request"

    def test_unrecognized_status_falls_to_unknown(self) -> None:
        error = classify_crux_error(500, "internal error")
        assert error.kind == "unknown"


# ══════════════════════════════════════════════════════════════════════
# CrUX record 解析 — p75 / good_rate 抽取
# ══════════════════════════════════════════════════════════════════════

class TestSeriesExtraction:
    def test_p75_at_returns_value(self) -> None:
        assert p75_at({"p75s": [100.0, 200.0]}, 1) == 200.0

    def test_p75_at_returns_none_for_null_entry(self) -> None:
        assert p75_at({"p75s": [100.0, None]}, 1) is None

    def test_p75_at_returns_none_when_index_out_of_range(self) -> None:
        assert p75_at({"p75s": [100.0]}, 5) is None

    def test_good_rate_is_first_bin_density(self) -> None:
        histogram = [
            {"start": "0", "end": "2500", "densities": [0.8]},
            {"start": "2500", "end": "4000", "densities": [0.15]},
            {"start": "4000", "densities": [0.05]},
        ]
        assert good_rate_from_histogram(histogram, 0) == 0.8

    def test_good_rate_returns_none_when_histogram_empty(self) -> None:
        assert good_rate_from_histogram([], 0) is None


# ══════════════════════════════════════════════════════════════════════
# record_to_rows — 對映決定 (b)(c) 的落地
# ══════════════════════════════════════════════════════════════════════

def _fake_metric_data(p75s: list[float | None], densities: list[float | None]) -> dict:
    return {
        "percentilesTimeseries": {"p75s": p75s},
        "histogramTimeseries": [
            {"densities": densities},
            {"densities": [None] * len(densities)},
            {"densities": [None] * len(densities)},
        ],
    }


class TestRecordToRows:
    def test_sample_count_is_zero_not_fabricated(self) -> None:
        record = {
            "collectionPeriods": [
                {"firstDate": {"year": 2026, "month": 8, "day": 1},
                 "lastDate": {"year": 2026, "month": 8, "day": 28}},
            ],
            "metrics": {"largest_contentful_paint": _fake_metric_data([1200.0], [0.9])},
        }
        rows = record_to_rows(record, device="mobile", route_type=ORIGIN_ROUTE_TYPE)
        assert len(rows) == 1
        assert rows[0]["sample_count"] == 0
        assert rows[0]["unknown_ratio"] == 0.0
        assert rows[0]["source"] == "crux"
        assert rows[0]["metric"] == "LCP"
        assert rows[0]["device"] == "mobile"
        assert rows[0]["route_type"] == ORIGIN_ROUTE_TYPE
        assert rows[0]["environment"] == "production"

    def test_all_device_sentinel_writes_through_cleanly(self) -> None:
        # device='all' 代表不帶 formFactor 的跨裝置聚合查詢結果（見對映決定 d、
        # migration 014）。record_to_rows() 本身不特判這個值，直接寫入——
        # 合不合法是 DB 層 CHECK 的責任，這裡只要確保沒有被意外攔下或改寫。
        record = {
            "collectionPeriods": [
                {"firstDate": {"year": 2026, "month": 8, "day": 1},
                 "lastDate": {"year": 2026, "month": 8, "day": 28}},
            ],
            "metrics": {"largest_contentful_paint": _fake_metric_data([1500.0], [0.85])},
        }
        rows = record_to_rows(record, device=ALL_DEVICE_SENTINEL, route_type=ORIGIN_ROUTE_TYPE)
        assert rows[0]["device"] == "all"

    def test_round_trip_time_never_produces_a_row(self) -> None:
        # round_trip_time 不在 CRUX_METRIC_TO_COLUMN，即使 API 回傳了也不會被寫出
        assert "round_trip_time" not in CRUX_METRIC_TO_COLUMN
        record = {
            "collectionPeriods": [
                {"firstDate": {"year": 2026, "month": 8, "day": 1},
                 "lastDate": {"year": 2026, "month": 8, "day": 28}},
            ],
            "metrics": {"round_trip_time": _fake_metric_data([50.0], [0.9])},
        }
        rows = record_to_rows(record, device="mobile", route_type=ORIGIN_ROUTE_TYPE)
        assert rows == []

    def test_null_p75_skips_that_metric_period_without_guessing(self) -> None:
        record = {
            "collectionPeriods": [
                {"firstDate": {"year": 2026, "month": 8, "day": 1},
                 "lastDate": {"year": 2026, "month": 8, "day": 28}},
            ],
            "metrics": {"largest_contentful_paint": _fake_metric_data([None], [0.9])},
        }
        assert record_to_rows(record, device="mobile", route_type=ORIGIN_ROUTE_TYPE) == []

    def test_multiple_collection_periods_produce_multiple_hours(self) -> None:
        record = {
            "collectionPeriods": [
                {"firstDate": {"year": 2026, "month": 7, "day": 1},
                 "lastDate": {"year": 2026, "month": 7, "day": 28}},
                {"firstDate": {"year": 2026, "month": 8, "day": 1},
                 "lastDate": {"year": 2026, "month": 8, "day": 28}},
            ],
            "metrics": {"cumulative_layout_shift": _fake_metric_data([0.05, 0.08], [0.95, 0.9])},
        }
        rows = record_to_rows(record, device="desktop", route_type="/")
        assert len(rows) == 2
        assert {row["hour"] for row in rows} == {
            align_to_monday_utc(date(2026, 7, 28)).isoformat().replace("+00:00", "Z"),
            align_to_monday_utc(date(2026, 8, 28)).isoformat().replace("+00:00", "Z"),
        }

    def test_good_rate_and_p75_are_clamped_non_negative(self) -> None:
        record = {
            "collectionPeriods": [
                {"firstDate": {"year": 2026, "month": 8, "day": 1},
                 "lastDate": {"year": 2026, "month": 8, "day": 28}},
            ],
            "metrics": {"first_contentful_paint": _fake_metric_data([-5.0], [1.4])},
        }
        rows = record_to_rows(record, device="tablet", route_type="/")
        assert rows[0]["p75"] == 0.0
        assert rows[0]["good_rate"] == 1.0


# ══════════════════════════════════════════════════════════════════════
# CrUX HTTP transport — 404=流量不足(None) / 403=拋例外
# ══════════════════════════════════════════════════════════════════════

class _FakeResponse:
    def __init__(self, body: str, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self._body = body.encode()
        self.status = status
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


CRUX_ENV = {"CRUX_API_KEY": "test-key"}


class TestFetchHistoryRecord:
    def test_missing_key_raises(self) -> None:
        with patch.dict("os.environ", {"CRUX_API_KEY": ""}), pytest.raises(RuntimeError):
            fetch_history_record(origin="https://vocus.cc", form_factor="PHONE", collection_period_count=4)

    def test_both_origin_and_url_raises(self) -> None:
        with pytest.raises(ValueError):
            fetch_history_record(
                origin="https://vocus.cc", url="https://vocus.cc/x",
                form_factor="PHONE", collection_period_count=4,
            )

    def test_neither_origin_nor_url_raises(self) -> None:
        with pytest.raises(ValueError):
            fetch_history_record(form_factor="PHONE", collection_period_count=4)

    def test_200_returns_record(self) -> None:
        body = '{"record": {"collectionPeriods": [], "metrics": {}}}'
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            record = fetch_history_record(
                origin="https://vocus.cc", form_factor="PHONE", collection_period_count=4
            )
        assert record == {"collectionPeriods": [], "metrics": {}}

    def test_404_returns_none_not_an_error(self) -> None:
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(404, "not found")):
            record = fetch_history_record(
                url="https://vocus.cc/article/low-traffic", form_factor="TABLET", collection_period_count=4
            )
        assert record is None

    def test_form_factor_none_omits_the_field_from_request_body(self) -> None:
        # device='all'（跨裝置聚合）走這條路徑，見 ALL_DEVICE_SENTINEL / migration 014。
        # CrUX 把「不帶 formFactor」跟「帶了不合法的 formFactor」當成兩件不同的事，
        # 必須整個省略這個 key，不能傳 None 或空字串進 JSON body。
        captured: dict[str, object] = {}

        def _capture(request, timeout=0):  # noqa: ANN001
            captured["body"] = json.loads(request.data.decode())
            return _FakeResponse('{"record": {"collectionPeriods": [], "metrics": {}}}')

        with patch.dict("os.environ", CRUX_ENV), patch("urllib.request.urlopen", _capture):
            fetch_history_record(origin="https://vocus.cc", form_factor=None, collection_period_count=4)
        assert "formFactor" not in captured["body"]

    def test_form_factor_phone_includes_the_field_in_request_body(self) -> None:
        captured: dict[str, object] = {}

        def _capture(request, timeout=0):  # noqa: ANN001
            captured["body"] = json.loads(request.data.decode())
            return _FakeResponse('{"record": {"collectionPeriods": [], "metrics": {}}}')

        with patch.dict("os.environ", CRUX_ENV), patch("urllib.request.urlopen", _capture):
            fetch_history_record(origin="https://vocus.cc", form_factor="PHONE", collection_period_count=4)
        assert captured["body"]["formFactor"] == "PHONE"

    def test_403_raises_crux_query_error_kind_auth(self) -> None:
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(403, "PERMISSION_DENIED")):
            with pytest.raises(CruxQueryError) as exc_info:
                fetch_history_record(origin="https://vocus.cc", form_factor="PHONE", collection_period_count=4)
        assert exc_info.value.kind == "auth"


# ══════════════════════════════════════════════════════════════════════
# _ok_status — 明帶實際拿到的 collection period 數（省略 collectionPeriodCount
# 會被 API 悄悄砍到預設值 25，帶了才拿得到全部 40，見模組 docstring 對 DEFAULT_
# COLLECTION_PERIOD_COUNT 的實測記錄；不寫死任何期待值，一律印實際值）
# ══════════════════════════════════════════════════════════════════════

class TestFormFactorDevicePairs:
    def test_pairs_extend_form_factor_map_with_all_sentinel(self) -> None:
        # migration 014 讓 device='all' 合法之後，FORM_FACTOR_DEVICE_PAIRS 必須是
        # FORM_FACTOR_TO_DEVICE 的三個 (formFactor, device) 配對，外加一組
        # (None, 'all') 代表「不帶 formFactor」——見對映決定 (d)。
        assert dict(FORM_FACTOR_DEVICE_PAIRS[:-1]) == FORM_FACTOR_TO_DEVICE
        assert FORM_FACTOR_DEVICE_PAIRS[-1] == (None, ALL_DEVICE_SENTINEL)
        assert len(FORM_FACTOR_DEVICE_PAIRS) == len(FORM_FACTOR_TO_DEVICE) + 1


class TestOkStatus:
    def test_reports_actual_period_count(self) -> None:
        record = {"collectionPeriods": [{"lastDate": {"year": 2026, "month": 8, "day": 22}}] * 25}
        assert _ok_status(record) == "ok (25 periods)"

    def test_zero_periods_is_reported_not_hidden(self) -> None:
        assert _ok_status({"collectionPeriods": []}) == "ok (0 periods)"

    def test_missing_collection_periods_key_is_treated_as_zero(self) -> None:
        assert _ok_status({}) == "ok (0 periods)"


# ══════════════════════════════════════════════════════════════════════
# per-call 錯誤策略 — auth 中止整批 / 其他錯誤記錄後繼續
# ══════════════════════════════════════════════════════════════════════

class TestCollectRowsErrorHandling:
    def test_auth_error_propagates_and_aborts(self) -> None:
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(403, "PERMISSION_DENIED")):
            with pytest.raises(CruxQueryError):
                collect_origin_rows(4, [])

    def test_non_auth_error_is_recorded_and_loop_continues(self) -> None:
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(429, "quota exceeded")):
            errors: list[str] = []
            rows, status_by_slice = collect_origin_rows(4, errors)
        assert rows == []
        assert len(errors) == len(FORM_FACTOR_DEVICE_PAIRS)
        assert all(status == "no-data(insufficient-traffic-or-error)" for status in status_by_slice.values())

    def test_404_across_all_form_factors_yields_no_rows_no_errors(self) -> None:
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(404, "not found")):
            errors: list[str] = []
            rows, _ = collect_url_rows(4, errors)
        assert rows == []
        assert errors == []

    def test_collect_url_rows_covers_every_representative_url_and_form_factor(self) -> None:
        body = '{"record": {"collectionPeriods": [{"firstDate": {"year": 2026, "month": 2, "day": 1},' \
               ' "lastDate": {"year": 2026, "month": 2, "day": 28}}], "metrics": {}}}'
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            _, status_by_slice = collect_url_rows(4, [])
        assert len(status_by_slice) == len(REPRESENTATIVE_URLS) * len(FORM_FACTOR_DEVICE_PAIRS)
        # 見對映決定：status 要明帶實際拿到的 collection period 數，不能只回一個籠統的 "ok"
        # （省略 collectionPeriodCount 會被 API 悄悄砍到預設值 25，帶了才拿得到全部 40，
        # 這裡才需要如實回報每次呼叫實際拿到幾個 period，而非假設固定值）
        assert all(status == "ok (1 periods)" for status in status_by_slice.values())


# ══════════════════════════════════════════════════════════════════════
# Supabase 層（同一套 shape，見 ingest_cwv_hourly.py 姊妹測試）
# ══════════════════════════════════════════════════════════════════════

SUPABASE_ENV = {"SUPABASE_URL": "https://db.example/", "SUPABASE_SERVICE_KEY": "svc"}
HOUR = datetime(2026, 8, 24, tzinfo=UTC)


class TestSupabaseTransport:
    @pytest.mark.parametrize("missing", sorted(SUPABASE_ENV))
    def test_missing_credential_raises(self, missing: str) -> None:
        env = {key: ("" if key == missing else value) for key, value in SUPABASE_ENV.items()}
        with patch.dict("os.environ", env), pytest.raises(RuntimeError):
            supabase_config()

    def test_trailing_slash_is_stripped(self) -> None:
        with patch.dict("os.environ", SUPABASE_ENV):
            assert supabase_config()[0] == "https://db.example"

    def test_http_error_is_returned_not_raised(self) -> None:
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(409, "conflict")):
            status, body = _supabase_request("POST", "/rest/v1/x", body=[])
        assert (status, body) == (409, "conflict")

    def test_success_response_is_returned(self) -> None:
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=_FakeResponse('{"ok": true}')):
            status, body = _supabase_request("GET", "/rest/v1/x")
        assert (status, body) == (200, '{"ok": true}')


class TestIngestionRunLifecycle:
    def test_start_run_inserts_running_row_with_crux_table_name(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request",
                   return_value=(201, '[{"id": "abc"}]')) as request:
            run_id = start_run(HOUR, HOUR + timedelta(weeks=40))
        assert run_id == "abc"
        payload = request.call_args.kwargs["body"][0]
        assert payload["status"] == "running"
        assert payload["table_name"] == "cwv_hourly"
        assert payload["window_start"] == "2026-08-24T00:00:00Z"

    def test_start_run_failure_returns_none(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request", return_value=(500, "boom")):
            assert start_run(HOUR, HOUR + timedelta(weeks=1)) is None

    def test_finish_run_sets_terminal_status(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request",
                   return_value=(204, "")) as request:
            finish_run("abc", "success", 42)
        payload = request.call_args.kwargs["body"]
        assert payload["status"] == "success"
        assert payload["row_count"] == 42
        assert payload["finished_at"].endswith("Z")

    def test_finish_run_without_id_is_noop(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request") as request:
            finish_run(None, "success", 0)
        request.assert_not_called()


class TestUpsert:
    ROW = {"hour": "2026-08-24T00:00:00Z", "source": "crux", "environment": "production",
           "metric": "LCP", "route_type": "/", "device": "mobile", "p75": 1200.0,
           "good_rate": 0.8, "sample_count": 0, "unknown_ratio": 0.0}

    def test_all_succeed(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request", return_value=(200, "")):
            succeeded, failed = upsert_rows([self.ROW] * 3)
        assert (succeeded, failed) == (3, 0)

    def test_batch_failure_counts_as_failed(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request", return_value=(500, "boom")):
            succeeded, failed = upsert_rows([self.ROW])
        assert (succeeded, failed) == (0, 1)

    def test_conflict_key_targets_dim_uniq_columns(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request",
                   return_value=(200, "")) as request:
            upsert_rows([self.ROW])
        path = request.call_args.args[1]
        assert "on_conflict=source%2Cenvironment%2Chour%2Cmetric%2Croute_type%2Cdevice" in path


class TestCountRowsBySource:
    def test_reads_exact_count_from_content_range_header(self) -> None:
        # 見 count_rows_by_source docstring：曾經用 len(回傳陣列) 算，被 PostgREST
        # 的 db-max-rows（常見預設 1000）靜默截斷，1369 列被算成 1000。
        # 正解讀 Content-Range，這裡刻意模擬總數(1369) > db-max-rows(1000) 的情境，
        # 確保這條回歸不會再發生。
        response = _FakeResponse("[]", status=206, headers={"Content-Range": "0-0/1369"})
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=response):
            assert count_rows_by_source("crux") == 1369

    def test_raises_on_http_error(self) -> None:
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(500, "boom")):
            with pytest.raises(RuntimeError):
                count_rows_by_source("crux")

    def test_raises_on_malformed_content_range(self) -> None:
        response = _FakeResponse("[]", status=206, headers={"Content-Range": "not-a-range"})
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(RuntimeError):
                count_rows_by_source("crux")

    def test_empty_table_reports_zero(self) -> None:
        response = _FakeResponse("[]", status=200, headers={"Content-Range": "*/0"})
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=response):
            assert count_rows_by_source("crux") == 0


# ══════════════════════════════════════════════════════════════════════
# backfill_window
# ══════════════════════════════════════════════════════════════════════

class TestBackfillWindow:
    def test_window_end_exceeds_window_start(self) -> None:
        start, end = backfill_window(40)
        assert end > start

    def test_window_span_matches_collection_period_count(self) -> None:
        start, end = backfill_window(10)
        assert (end - start) == timedelta(weeks=10)

    def test_window_end_is_monday_aligned(self) -> None:
        _, end = backfill_window(4)
        assert end.weekday() == 0


# ══════════════════════════════════════════════════════════════════════
# 新鮮度告警
# ══════════════════════════════════════════════════════════════════════

class TestFreshnessCheck:
    def test_empty_table_fails(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request", return_value=(200, "[]")):
            assert run_freshness_check() == 1

    def test_recent_data_passes(self) -> None:
        recent = datetime.now(UTC) - timedelta(hours=1)
        body = f'[{{"hour": "{recent.isoformat().replace("+00:00", "Z")}"}}]'
        with patch("scripts.ingest_cwv_crux_history._supabase_request", return_value=(200, body)):
            assert run_freshness_check() == 0

    def test_data_within_cruxs_own_publish_lag_passes_not_a_false_positive(self) -> None:
        # 回歸測試：曾經的門檻（240h）在這個 age 會誤判 FAIL，即使資料完全健康——
        # 286.3h 是 2026-08-29 剛成功 --execute 完那一刻的實測值（CrUX 固有發布延遲
        # + 週界對齊損失，非作業停擺）。見 FRESHNESS_MAX_AGE_HOURS 註解。
        healthy_but_lagged = datetime.now(UTC) - timedelta(hours=286.3)
        body = f'[{{"hour": "{healthy_but_lagged.isoformat().replace("+00:00", "Z")}"}}]'
        with patch("scripts.ingest_cwv_crux_history._supabase_request", return_value=(200, body)):
            assert run_freshness_check() == 0

    def test_stale_data_fails(self) -> None:
        stale = datetime.now(UTC) - timedelta(hours=24 * 25)  # 25 天，超過 20 天門檻
        body = f'[{{"hour": "{stale.isoformat().replace("+00:00", "Z")}"}}]'
        with patch("scripts.ingest_cwv_crux_history._supabase_request", return_value=(200, body)):
            assert run_freshness_check() == 1


# ══════════════════════════════════════════════════════════════════════
# run_ingestion — dry-run / execute / 系統性錯誤中止
# ══════════════════════════════════════════════════════════════════════

class TestRunIngestion:
    def test_dry_run_does_not_call_supabase_write(self) -> None:
        body = '{"record": {"collectionPeriods": [], "metrics": {}}}'
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", return_value=_FakeResponse(body)), \
             patch("scripts.ingest_cwv_crux_history.start_run") as start, \
             patch("scripts.ingest_cwv_crux_history.upsert_rows") as upsert:
            exit_code = run_ingestion(execute=False, collection_period_count=4, origin_only=True)
        assert exit_code == 0
        start.assert_not_called()
        upsert.assert_not_called()

    def test_origin_only_skips_url_level_calls(self) -> None:
        body = '{"record": {"collectionPeriods": [], "metrics": {}}}'
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", return_value=_FakeResponse(body)) as urlopen:
            run_ingestion(execute=False, collection_period_count=4, origin_only=True)
        # 只有 origin 級的 4 個 device 切面呼叫（3 個 formFactor + 不帶的 'all'），沒有 URL 級的呼叫
        assert urlopen.call_count == len(FORM_FACTOR_DEVICE_PAIRS)

    def test_auth_error_marks_run_failed_and_returns_1(self) -> None:
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(403, "PERMISSION_DENIED")), \
             patch("scripts.ingest_cwv_crux_history.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_crux_history.finish_run") as finish:
            exit_code = run_ingestion(execute=True, collection_period_count=4, origin_only=True)
        assert exit_code == 1
        finish.assert_called_once_with("run-1", "failed", 0)

    def test_execute_upserts_and_finishes_run_as_success(self) -> None:
        body = '{"record": {"collectionPeriods": [], "metrics": {}}}'
        with patch.dict("os.environ", CRUX_ENV), \
             patch("urllib.request.urlopen", return_value=_FakeResponse(body)), \
             patch("scripts.ingest_cwv_crux_history.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_crux_history.upsert_rows", return_value=(0, 0)) as upsert, \
             patch("scripts.ingest_cwv_crux_history.finish_run") as finish:
            exit_code = run_ingestion(execute=True, collection_period_count=4, origin_only=True)
        assert exit_code == 0
        upsert.assert_called_once()
        finish.assert_called_once_with("run-1", "success", 0)

    def test_partial_status_when_some_rows_written_and_some_errors(self) -> None:
        row = {"hour": "2026-08-24T00:00:00Z", "environment": "production", "metric": "LCP",
               "route_type": "/", "device": "mobile", "p75": 1.0, "good_rate": 0.9,
               "sample_count": 0, "unknown_ratio": 0.0, "source": "crux"}
        with patch.dict("os.environ", CRUX_ENV), \
             patch("scripts.ingest_cwv_crux_history.collect_origin_rows",
                   return_value=([row], {"origin [PHONE]": "ok"})), \
             patch("scripts.ingest_cwv_crux_history.start_run", return_value="run-1"), \
             patch("scripts.ingest_cwv_crux_history.upsert_rows", return_value=(1, 0)), \
             patch("scripts.ingest_cwv_crux_history.finish_run") as finish:
            # errors list 非空但仍有成功列 → partial
            with patch("scripts.ingest_cwv_crux_history.collect_url_rows",
                       side_effect=lambda count, errors: errors.append("boom") or ([], {})):
                exit_code = run_ingestion(execute=True, collection_period_count=4, origin_only=False)
        assert exit_code == 0  # partial 仍回 0（sister 腳本同語意：只有 failed 才回 1）
        finish.assert_called_once_with("run-1", "partial", 1)


# ══════════════════════════════════════════════════════════════════════
# run_verify — 含 rum/crux 並存檢查
# ══════════════════════════════════════════════════════════════════════

class TestRunVerify:
    def test_verify_reports_source_split_counts(self) -> None:
        recent_body = (
            '[{"hour": "2026-08-24T00:00:00Z", "environment": "production", "metric": "LCP",'
            ' "route_type": "/", "device": "mobile", "p75": 1200.0, "good_rate": 0.9,'
            ' "sample_count": 0, "unknown_ratio": 0.0}]'
        )
        run_body = (
            '[{"id": "abc12345", "window_start": "2026-08-24T00:00:00Z",'
            ' "window_end": "2026-08-31T00:00:00Z", "row_count": 5, "status": "success",'
            ' "started_at": "2026-08-29T00:00:00Z", "finished_at": "2026-08-29T00:01:00Z"}]'
        )
        # count_rows_by_source 走獨立的 urlopen 呼叫（見該函式 docstring），不經 _supabase_request
        count_responses = iter([
            _FakeResponse("[]", status=206, headers={"Content-Range": "0-0/127"}),   # rum
            _FakeResponse("[]", status=206, headers={"Content-Range": "0-0/1369"}),  # crux
        ])
        rest_responses = iter([(200, recent_body), (200, run_body)])
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("scripts.ingest_cwv_crux_history._supabase_request",
                   side_effect=lambda *a, **k: next(rest_responses)), \
             patch("urllib.request.urlopen", side_effect=lambda *a, **k: next(count_responses)):
            assert run_verify() == 0

    def test_verify_returns_1_when_cwv_read_fails(self) -> None:
        with patch("scripts.ingest_cwv_crux_history._supabase_request", return_value=(500, "boom")):
            assert run_verify() == 1


# ══════════════════════════════════════════════════════════════════════
# _log_summary — 多週摘要分支
# ══════════════════════════════════════════════════════════════════════

class TestLogSummary:
    def test_summary_handles_more_than_eight_rows(self) -> None:
        rows = [
            {"hour": f"2026-0{i % 9 + 1}-01T00:00:00Z", "environment": "production", "metric": "LCP",
             "route_type": "/", "device": "mobile", "p75": 1.0, "good_rate": 0.9}
            for i in range(10)
        ]
        _log_summary(rows, {"origin [PHONE]": "ok"}, ["some error"])

    def test_summary_handles_empty_rows(self) -> None:
        _log_summary([], {}, [])


# ══════════════════════════════════════════════════════════════════════
# CLI wiring
# ══════════════════════════════════════════════════════════════════════

class TestCli:
    def test_verify_flag_dispatches_to_run_verify(self) -> None:
        with patch("sys.argv", ["prog", "--verify"]), \
             patch("scripts.ingest_cwv_crux_history.run_verify", return_value=0) as verify, \
             pytest.raises(SystemExit) as exc_info:
            main()
        verify.assert_called_once()
        assert exc_info.value.code == 0

    def test_check_freshness_flag_dispatches(self) -> None:
        with patch("sys.argv", ["prog", "--check-freshness"]), \
             patch("scripts.ingest_cwv_crux_history.run_freshness_check", return_value=1) as check, \
             pytest.raises(SystemExit) as exc_info:
            main()
        check.assert_called_once()
        assert exc_info.value.code == 1

    def test_invalid_collection_period_count_exits_2(self) -> None:
        with patch("sys.argv", ["prog", "--dry-run", "--collection-period-count", "0"]), \
             pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_default_dry_run_dispatches_to_run_ingestion(self) -> None:
        with patch("sys.argv", ["prog"]), \
             patch("scripts.ingest_cwv_crux_history.run_ingestion", return_value=0) as ingest, \
             pytest.raises(SystemExit) as exc_info:
            main()
        ingest.assert_called_once_with(execute=False, collection_period_count=40, origin_only=False)
        assert exc_info.value.code == 0

    def test_execute_and_origin_only_flags_are_forwarded(self) -> None:
        with patch("sys.argv", ["prog", "--execute", "--origin-only", "--collection-period-count", "4"]), \
             patch("scripts.ingest_cwv_crux_history.run_ingestion", return_value=0) as ingest, \
             pytest.raises(SystemExit):
            main()
        ingest.assert_called_once_with(execute=True, collection_period_count=4, origin_only=True)
