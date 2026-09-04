"""Tests for ingest_gsc_search_analytics.py.

重點覆蓋五件本腳本特有、且錯了不會有訊號的事：

1. **兩套維度組合的哨兵值與判別式** —— page/query 兩組共用同一個 unique key 空間，
   判別式錯了就是靜默重複計算。這裡逐項釘住哨兵值、互斥性、以及 PostgREST 判別式。
2. **分頁** —— 25,000 列的頁界與 50,000 列的天花板。
3. **2-3 天延遲用探測處理** —— 探測回空 = 硬失敗（不是延遲），是本腳本最重要的分流。
4. **冪等的收尾（reaping）** —— upsert 零失敗才 reap 的安全閥。
5. **0 rows 一律失敗** —— 三道各自的 exit code。

以及新鮮度門檻用的是「來源固有延遲 + 排程緩衝」而非「排程週期 × N」。
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.error
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ingest_gsc_search_analytics import (  # noqa: E402
    ALLOWED_SEARCH_TYPES,
    COMBO_DIMENSIONS,
    COMBO_PAGE,
    COMBO_QUERY,
    COUNTRY_NOT_REQUESTED,
    DAILY_ROW_CAP,
    DEFAULT_BACKFILL_DAYS,
    DEFAULT_PROBE_DAYS,
    FRESHNESS_MAX_AGE_HOURS,
    MAX_BACKFILL_DAYS,
    MAX_PROBE_DAYS,
    MIN_PROBE_DAYS,
    PAGE_NOT_REQUESTED,
    PROPERTY,
    QUERY_NOT_REQUESTED,
    ROW_LIMIT,
    SURFACE_COMBOS,
    TABLE_GSC,
    TABLE_TOTALS,
    GscQueryError,
    _assert_no_country_dimension,
    _gsc_post,
    _ingest_totals,
    _service_account_info,
    _supabase_request,
    _validate_metrics,
    _verify_surface,
    _write_slice,
    classify_gsc_error,
    collect_day_combo,
    combo_filter,
    count_rows,
    has_rows,
    dedupe_by_key,
    finish_run,
    gsc_access_token,
    latest_date,
    main,
    paginate_query,
    probe_available_dates,
    probe_row_limit,
    reap_orphans,
    resolve_backfill_days,
    resolve_probe_days,
    resolve_search_type,
    row_to_record,
    run_freshness_check,
    run_ingestion,
    run_verify,
    start_run,
    supabase_config,
    upsert_rows,
    write_totals,
)
# COMBO_PAGE_NODEVICE 沒被 ingest 主檔重新匯出（見 gsc_surfaces.py 的 import 注意
# 事項）；本檔要直接測 discover 走這個組合，另外從原模組 import。device 哨兵規則
# （is_device_valid／DEVICE_NOT_SUPPORTED／NO_DEVICE_SURFACES）的測試在
# tests/test_gsc_surfaces.py（含與 025 migration CHECK 文字的對照），不在本檔重複。
from scripts.gsc_surfaces import COMBO_PAGE_NODEVICE  # noqa: E402

MODULE = "scripts.ingest_gsc_search_analytics"
UTC = timezone.utc
DAY = date(2026, 8, 25)
INGESTED_AT = "2026-08-29T00:00:00Z"
SUPABASE_ENV = {"SUPABASE_URL": "https://db.example/", "SUPABASE_SERVICE_KEY": "k"}
SA_JSON = json.dumps({"type": "service_account", "client_email": "sa@example.iam.gserviceaccount.com"})


def _http_error(status: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", status, "err", {}, BytesIO(body.encode()))


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


def _api_row(*keys: str, clicks: int = 3, impressions: int = 10, position: float = 4.5) -> dict:
    return {"keys": list(keys), "clicks": clicks, "impressions": impressions,
            "ctr": clicks / impressions, "position": position}


def _probe_rows(days: list[date]) -> list[dict]:
    """探測（dimensions=["date"]）的回應：每天一列，且本來就帶四個 metric。"""
    return [_api_row(day.isoformat()) for day in days]


# ══════════════════════════════════════════════════════════════════════
# 哨兵值與判別式 —— 錯了就是靜默重複計算
# ══════════════════════════════════════════════════════════════════════

class TestSentinels:
    def test_page_sentinel_passes_schema_check_shape(self) -> None:
        """gsc_daily_metrics_page_ck: page ~ '^https?://' AND octet_length BETWEEN 8 AND 1024。"""
        assert PAGE_NOT_REQUESTED.startswith("https://")
        assert 8 <= len(PAGE_NOT_REQUESTED.encode()) <= 1024

    def test_page_sentinel_cannot_be_a_real_hostname(self) -> None:
        """底線不是合法 DNS hostname 字元，所以 GSC 不可能回傳這個網域的頁面。"""
        host = PAGE_NOT_REQUESTED.split("//", 1)[1].split("/", 1)[0]
        assert "_" in host

    def test_page_sentinel_is_not_the_property_itself(self) -> None:
        """用 property URL 當哨兵會與首頁這筆真實資料撞鍵。"""
        assert PAGE_NOT_REQUESTED != PROPERTY

    def test_country_sentinel_matches_schema_regex(self) -> None:
        assert len(COUNTRY_NOT_REQUESTED) == 3 and COUNTRY_NOT_REQUESTED.isalpha()
        assert COUNTRY_NOT_REQUESTED.islower()

    def test_query_sentinel_is_empty_string(self) -> None:
        """Search Analytics API 對匿名化查詢是整列不回，所以 '' 不會與真實資料撞。"""
        assert QUERY_NOT_REQUESTED == ""


class TestComboFilter:
    def test_query_combo_selects_sentinel_page(self) -> None:
        assert combo_filter(COMBO_QUERY).startswith("page=eq.")

    def test_page_combo_excludes_sentinel_page(self) -> None:
        assert combo_filter(COMBO_PAGE).startswith("page=neq.")

    def test_filters_are_mutually_exclusive_and_exhaustive(self) -> None:
        """判別式以 page 為準，eq/neq 互補，沒有第三種狀態。"""
        query_filter = combo_filter(COMBO_QUERY)
        page_filter = combo_filter(COMBO_PAGE)
        assert query_filter.replace("=eq.", "=neq.") == page_filter

    def test_sentinel_is_url_encoded_in_filter(self) -> None:
        assert "%3A%2F%2F" in combo_filter(COMBO_QUERY)


class TestCountryDimensionAssertion:
    def test_current_combos_pass(self) -> None:
        _assert_no_country_dimension()

    def test_adding_country_dimension_fails_loudly(self) -> None:
        """'zzz' 同時是 GSC 的真實「無法判定地區」值；一旦請求 country 維度，
        哨兵語意就會靜默分岔，這個斷言讓它在啟動時當場失敗。"""
        with patch.dict(COMBO_DIMENSIONS, {"country": ("date", "country")}):
            with pytest.raises(RuntimeError, match="country"):
                _assert_no_country_dimension()

    def test_both_required_combos_are_configured(self) -> None:
        assert COMBO_DIMENSIONS[COMBO_PAGE] == ("date", "page", "device")
        assert COMBO_DIMENSIONS[COMBO_QUERY] == ("date", "query", "device")


# ══════════════════════════════════════════════════════════════════════
# 認證
# ══════════════════════════════════════════════════════════════════════

class TestServiceAccountInfo:
    def test_missing_env_raises(self) -> None:
        with patch.dict("os.environ", {"GSC_READONLY_KEY": ""}), pytest.raises(RuntimeError):
            _service_account_info()

    def test_malformed_json_error_does_not_leak_the_key(self) -> None:
        secret = "this-is-not-json-but-stands-in-for-a-private-key-body"
        with patch.dict("os.environ", {"GSC_READONLY_KEY": secret}):
            with pytest.raises(RuntimeError) as excinfo:
                _service_account_info()
        assert secret not in str(excinfo.value)
        assert str(len(secret)) in str(excinfo.value)

    def test_wrong_type_raises(self) -> None:
        with patch.dict("os.environ", {"GSC_READONLY_KEY": json.dumps({"type": "authorized_user"})}):
            with pytest.raises(RuntimeError, match="service_account"):
                _service_account_info()

    def test_valid_json_returns_dict(self) -> None:
        with patch.dict("os.environ", {"GSC_READONLY_KEY": SA_JSON}):
            assert _service_account_info()["type"] == "service_account"

    def test_surrounding_whitespace_is_tolerated(self) -> None:
        with patch.dict("os.environ", {"GSC_READONLY_KEY": f"\n  {SA_JSON}\n"}):
            assert _service_account_info()["type"] == "service_account"


class TestAccessToken:
    def _patched_google(self, token: str | None):
        credentials = type("C", (), {"token": token, "refresh": lambda self, _r: None})()
        loader = type("L", (), {"from_service_account_info": staticmethod(lambda *a, **k: credentials)})
        module = type("M", (), {"Credentials": loader})
        return module

    def test_returns_token(self) -> None:
        module = self._patched_google("ya29.fake")
        with patch.dict("os.environ", {"GSC_READONLY_KEY": SA_JSON}), \
             patch.dict("sys.modules", {
                 "google.oauth2": type("P", (), {"service_account": module}),
                 "google.oauth2.service_account": module,
                 "google.auth.transport.requests": type("R", (), {"Request": lambda: None}),
             }):
            assert gsc_access_token() == "ya29.fake"

    def test_empty_token_raises(self) -> None:
        module = self._patched_google("")
        with patch.dict("os.environ", {"GSC_READONLY_KEY": SA_JSON}), \
             patch.dict("sys.modules", {
                 "google.oauth2": type("P", (), {"service_account": module}),
                 "google.oauth2.service_account": module,
                 "google.auth.transport.requests": type("R", (), {"Request": lambda: None}),
             }):
            with pytest.raises(RuntimeError, match="access token"):
                gsc_access_token()


class TestErrorClassification:
    @pytest.mark.parametrize("status, needle", [
        (401, "存取權"), (403, "存取權"), (429, "配額"), (400, "參數"), (500, "500"),
    ])
    def test_status_maps_to_readable_reason(self, status: int, needle: str) -> None:
        assert needle in str(classify_gsc_error(status, "body"))

    def test_all_errors_are_systemic(self) -> None:
        """沒有「這筆跳過就好」的分類——全部都該中止整個 run。"""
        assert isinstance(classify_gsc_error(403, ""), GscQueryError)


class TestGscPost:
    def test_success_returns_parsed_json(self) -> None:
        with patch("urllib.request.urlopen", return_value=_FakeResponse('{"rows": []}')):
            assert _gsc_post("t", {}) == {"rows": []}

    def test_http_error_becomes_gsc_query_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_http_error(403, "denied")):
            with pytest.raises(GscQueryError):
                _gsc_post("t", {})

    def test_url_error_becomes_gsc_query_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("dns")):
            with pytest.raises(GscQueryError, match="連線失敗"):
                _gsc_post("t", {})

    def test_property_is_url_encoded_into_path(self) -> None:
        with patch("urllib.request.urlopen", return_value=_FakeResponse("{}")) as opener:
            _gsc_post("t", {})
        assert "https%3A%2F%2Fvocus.cc%2F" in opener.call_args.args[0].full_url


# ══════════════════════════════════════════════════════════════════════
# 探測 —— 2-3 天延遲的處理方式
# ══════════════════════════════════════════════════════════════════════

class TestProbeAvailableDates:
    def test_returns_dates_newest_first(self) -> None:
        payload = {"rows": [{"keys": ["2026-08-20"]}, {"keys": ["2026-08-22"]},
                            {"keys": ["2026-08-21"]}]}
        with patch(f"{MODULE}._gsc_post", return_value=payload):
            assert probe_available_dates("t", "web", date(2026, 8, 25)) == [
                date(2026, 8, 22), date(2026, 8, 21), date(2026, 8, 20)]

    def test_empty_response_returns_empty_list(self) -> None:
        with patch(f"{MODULE}._gsc_post", return_value={}):
            assert probe_available_dates("t", "web", DAY) == []

    def test_probe_is_cheap_single_dimension_query(self) -> None:
        with patch(f"{MODULE}._gsc_post", return_value={"rows": []}) as post:
            probe_available_dates("t", "web", DAY)
        body = post.call_args.args[1]
        assert body["dimensions"] == ["date"]
        assert body["rowLimit"] < ROW_LIMIT

    def test_duplicate_dates_are_collapsed(self) -> None:
        payload = {"rows": [{"keys": ["2026-08-22"]}, {"keys": ["2026-08-22"]}]}
        with patch(f"{MODULE}._gsc_post", return_value=payload):
            assert probe_available_dates("t", "web", DAY) == [date(2026, 8, 22)]


# ══════════════════════════════════════════════════════════════════════
# 分頁 —— 25,000 頁界與 50,000 天花板
# ══════════════════════════════════════════════════════════════════════

class TestPaginateQuery:
    def test_single_short_page_stops_immediately(self) -> None:
        with patch(f"{MODULE}._gsc_post", return_value={"rows": [_api_row("d", "p", "MOBILE")]}) as post:
            rows = paginate_query("t", DAY, ("date", "page", "device"), "web")
        assert len(rows) == 1
        assert post.call_count == 1

    def test_full_page_triggers_next_request(self) -> None:
        full = {"rows": [_api_row("d", f"p{i}", "MOBILE") for i in range(ROW_LIMIT)]}
        with patch(f"{MODULE}._gsc_post", side_effect=[full, {"rows": []}]) as post:
            rows = paginate_query("t", DAY, ("date", "page", "device"), "web")
        assert len(rows) == ROW_LIMIT
        assert post.call_count == 2
        assert post.call_args_list[1].args[1]["startRow"] == ROW_LIMIT

    def test_stops_at_daily_row_cap(self) -> None:
        full = {"rows": [_api_row("d", f"p{i}", "MOBILE") for i in range(ROW_LIMIT)]}
        with patch(f"{MODULE}._gsc_post", return_value=full) as post:
            rows = paginate_query("t", DAY, ("date", "page", "device"), "web")
        assert len(rows) == DAILY_ROW_CAP
        assert post.call_count == DAILY_ROW_CAP // ROW_LIMIT

    def test_row_limit_never_exceeds_api_maximum(self) -> None:
        with patch(f"{MODULE}._gsc_post", return_value={"rows": []}) as post:
            paginate_query("t", DAY, ("date", "page", "device"), "web")
        assert post.call_args.args[1]["rowLimit"] <= ROW_LIMIT

    def test_single_day_window(self) -> None:
        with patch(f"{MODULE}._gsc_post", return_value={"rows": []}) as post:
            paginate_query("t", DAY, ("date", "page", "device"), "web")
        body = post.call_args.args[1]
        assert body["startDate"] == body["endDate"] == DAY.isoformat()


# ══════════════════════════════════════════════════════════════════════
# 列轉換與驗證
# ══════════════════════════════════════════════════════════════════════

def _record(combo: str, *keys: str, **kwargs) -> tuple[dict | None, dict]:
    rejects: dict[str, int] = {}
    record = row_to_record(_api_row(*keys, **kwargs), combo=combo, day=DAY,
                           search_type="web", ingested_at=INGESTED_AT, rejects=rejects)
    return record, rejects


class TestRowToRecordPageCombo:
    def test_maps_all_columns(self) -> None:
        record, rejects = _record(COMBO_PAGE, DAY.isoformat(), "https://vocus.cc/a", "MOBILE")
        assert rejects == {}
        assert record == {
            "date": DAY.isoformat(), "property": PROPERTY, "search_type": "web",
            "page": "https://vocus.cc/a", "query": QUERY_NOT_REQUESTED, "device": "mobile",
            "country": COUNTRY_NOT_REQUESTED, "clicks": 3, "impressions": 10,
            "ctr": 0.3, "position": 4.5, "ingested_at": INGESTED_AT,
        }

    def test_ingested_at_is_in_payload_for_reaping(self) -> None:
        """PostgREST 的 merge-duplicates 只更新 payload 裡有的欄位；
        不顯式帶就會沿用首次寫入的值，reap 的 lt 過濾會把剛寫的列一起刪掉。"""
        record, _ = _record(COMBO_PAGE, DAY.isoformat(), "https://vocus.cc/a", "DESKTOP")
        assert record["ingested_at"] == INGESTED_AT

    @pytest.mark.parametrize("raw, expected", [
        ("MOBILE", "mobile"), ("DESKTOP", "desktop"), ("TABLET", "tablet"), ("mobile", "mobile"),
    ])
    def test_device_is_lowercased(self, raw: str, expected: str) -> None:
        record, _ = _record(COMBO_PAGE, DAY.isoformat(), "https://vocus.cc/a", raw)
        assert record["device"] == expected


class TestRowToRecordQueryCombo:
    def test_query_goes_to_query_column_and_page_gets_sentinel(self) -> None:
        record, rejects = _record(COMBO_QUERY, DAY.isoformat(), "方格子", "DESKTOP")
        assert rejects == {}
        assert record["query"] == "方格子"
        assert record["page"] == PAGE_NOT_REQUESTED

    def test_two_combos_never_collide_on_the_unique_key(self) -> None:
        page_row, _ = _record(COMBO_PAGE, DAY.isoformat(), "https://vocus.cc/a", "MOBILE")
        query_row, _ = _record(COMBO_QUERY, DAY.isoformat(), "方格子", "MOBILE")
        key = ("property", "search_type", "date", "page", "query", "device", "country")
        assert tuple(page_row[k] for k in key) != tuple(query_row[k] for k in key)


class TestRowToRecordRejections:
    @pytest.mark.parametrize("keys, reason_needle", [
        ((DAY.isoformat(), "https://vocus.cc/a"), "keys 長度"),
        (("2026-01-01", "https://vocus.cc/a", "MOBILE"), "date 與查詢日期不符"),
        ((DAY.isoformat(), "https://vocus.cc/a", "WATCH"), "未知 device"),
        ((DAY.isoformat(), "ftp://vocus.cc/a", "MOBILE"), "page 不合法"),
    ])
    def test_rejected_rows_return_none_and_are_counted(self, keys, reason_needle: str) -> None:
        record, rejects = _record(COMBO_PAGE, *keys)
        assert record is None
        assert any(reason_needle in reason for reason in rejects)

    def test_over_long_page_is_rejected_not_truncated(self) -> None:
        record, rejects = _record(COMBO_PAGE, DAY.isoformat(), "https://vocus.cc/" + "a" * 1100, "MOBILE")
        assert record is None and "page 不合法或過長" in rejects

    def test_over_long_query_is_rejected_not_truncated(self) -> None:
        """截斷會讓兩個不同 query 撞成同一個 unique key，只能丟棄。"""
        record, rejects = _record(COMBO_QUERY, DAY.isoformat(), "x" * 600, "MOBILE")
        assert record is None and "query 超過 512 bytes" in rejects

    def test_multibyte_query_length_is_measured_in_octets(self) -> None:
        record, _ = _record(COMBO_QUERY, DAY.isoformat(), "中" * 200, "MOBILE")
        assert record is None  # 200 個中文字 = 600 bytes > 512


class TestValidateMetrics:
    @pytest.mark.parametrize("row, reason", [
        ({"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 3.0}, "impressions<=0"),
        ({"clicks": 5, "impressions": 3, "ctr": 1.0, "position": 3.0}, "clicks 越界"),
        ({"clicks": 1, "impressions": 10, "ctr": 0.1, "position": 0.0}, "position<1"),
        ({"clicks": 1, "impressions": 10, "ctr": 0.9, "position": 3.0},
         "ctr 與 clicks/impressions 不一致"),
    ])
    def test_schema_check_violations_are_rejected_before_write(self, row: dict, reason: str) -> None:
        rejects: dict[str, int] = {}
        assert _validate_metrics(row, rejects) is None
        assert reason in rejects

    def test_valid_row_passes(self) -> None:
        rejects: dict[str, int] = {}
        assert _validate_metrics(
            {"clicks": 2, "impressions": 8, "ctr": 0.25, "position": 1.0}, rejects) == (2, 8, 0.25, 1.0)
        assert rejects == {}

    def test_inconsistent_ctr_is_not_silently_rewritten(self) -> None:
        """ctr 對不上代表 API 欄位語意變了，那是要人看的訊號，改寫會把它藏起來。"""
        rejects: dict[str, int] = {}
        _validate_metrics({"clicks": 1, "impressions": 10, "ctr": 0.5, "position": 2.0}, rejects)
        assert sum(rejects.values()) == 1

    def test_position_exactly_one_is_allowed(self) -> None:
        rejects: dict[str, int] = {}
        assert _validate_metrics(
            {"clicks": 1, "impressions": 1, "ctr": 1.0, "position": 1.0}, rejects) is not None


class TestDedupeByKey:
    def _row(self, page: str, clicks: int) -> dict:
        return {"property": PROPERTY, "search_type": "web", "date": DAY.isoformat(),
                "page": page, "query": "", "device": "mobile", "country": "zzz", "clicks": clicks}

    def test_duplicate_keys_collapse_to_last(self) -> None:
        """相鄰頁重疊時若不去重，整批 500 列會一起死於
        `ON CONFLICT DO UPDATE command cannot affect row a second time`。"""
        rows = dedupe_by_key([self._row("https://a", 1), self._row("https://a", 9)])
        assert len(rows) == 1 and rows[0]["clicks"] == 9

    def test_distinct_keys_are_kept(self) -> None:
        assert len(dedupe_by_key([self._row("https://a", 1), self._row("https://b", 1)])) == 2

    def test_empty_input(self) -> None:
        assert dedupe_by_key([]) == []


# ══════════════════════════════════════════════════════════════════════
# Supabase 存取
# ══════════════════════════════════════════════════════════════════════

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
            assert _supabase_request("POST", "/rest/v1/x", body=[]) == (409, "conflict")

    def test_success_response_is_returned(self) -> None:
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=_FakeResponse('{"ok": true}')):
            assert _supabase_request("GET", "/rest/v1/x") == (200, '{"ok": true}')


class TestIngestionRunLifecycle:
    def test_start_run_records_gsc_table_name(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(201, '[{"id": "abc"}]')) as request:
            run_id = start_run(datetime(2026, 8, 20, tzinfo=UTC), datetime(2026, 8, 26, tzinfo=UTC))
        assert run_id == "abc"
        payload = request.call_args.kwargs["body"][0]
        assert payload["table_name"] == "gsc_daily_metrics"
        assert payload["status"] == "running"
        assert payload["window_start"] == "2026-08-20T00:00:00Z"

    def test_start_run_failure_returns_none(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            assert start_run(datetime(2026, 8, 20, tzinfo=UTC), datetime(2026, 8, 26, tzinfo=UTC)) is None

    def test_finish_run_sets_terminal_status(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(204, "")) as request:
            finish_run("abc", "success", 42)
        payload = request.call_args.kwargs["body"]
        assert payload["status"] == "success" and payload["row_count"] == 42
        assert payload["finished_at"].endswith("Z")

    def test_finish_run_without_id_is_noop(self) -> None:
        with patch(f"{MODULE}._supabase_request") as request:
            finish_run(None, "success", 0)
        request.assert_not_called()

    def test_finish_run_logs_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            finish_run("abc", "failed", 0)
        assert "收尾 ingestion_run 失敗" in caplog.text


class TestUpsert:
    ROW = {"date": DAY.isoformat(), "property": PROPERTY, "search_type": "web",
           "page": "https://vocus.cc/a", "query": "", "device": "mobile", "country": "zzz",
           "clicks": 1, "impressions": 2, "ctr": 0.5, "position": 3.0, "ingested_at": INGESTED_AT}

    def test_all_succeed(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(201, "")):
            assert upsert_rows([self.ROW] * 3) == (3, 0)

    def test_batch_failure_counts_as_failed(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            assert upsert_rows([self.ROW]) == (0, 1)

    def test_conflict_key_matches_dim_uniq_columns(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "")) as request:
            upsert_rows([self.ROW])
        path = request.call_args.args[1]
        assert "on_conflict=property%2Csearch_type%2Cdate%2Cpage%2Cquery%2Cdevice%2Ccountry" in path

    def test_rows_are_sent_in_batches(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(201, "")) as request:
            upsert_rows([self.ROW] * 1200)
        assert request.call_count == 3


class TestWriteTotals:
    """gsc_daily_totals 的寫入路徑：table／on_conflict 用 totals 那一套，
    且在 ingestion_run 另記一列（table_name=gsc_daily_totals），不共用 metrics 那一列。"""

    RECORD = {"date": DAY.isoformat(), "property": PROPERTY, "search_type": "googleNews",
              "clicks": 5, "impressions": 20, "ctr": 0.25, "position": 0.0}
    WINDOW = (datetime(2026, 8, 20, tzinfo=UTC), datetime(2026, 8, 26, tzinfo=UTC))

    def test_uses_totals_table_name_when_starting_the_run(self) -> None:
        with patch(f"{MODULE}.start_run", return_value="run-totals") as start, \
             patch(f"{MODULE}.upsert_rows", return_value=(1, 0)), \
             patch(f"{MODULE}.finish_run"):
            write_totals([self.RECORD], self.WINDOW, "googleNews")
        assert start.call_args.kwargs["table_name"] == "gsc_daily_totals"

    def test_upserts_with_totals_table_and_conflict_key(self) -> None:
        with patch(f"{MODULE}.start_run", return_value="run-totals"), \
             patch(f"{MODULE}.upsert_rows", return_value=(1, 0)) as upsert, \
             patch(f"{MODULE}.finish_run"):
            write_totals([self.RECORD], self.WINDOW, "googleNews")
        assert upsert.call_args.args[1] == "gsc_daily_totals"
        assert upsert.call_args.args[2] == "property,search_type,date"

    def test_all_succeed_is_status_success(self) -> None:
        with patch(f"{MODULE}.start_run", return_value="run-totals"), \
             patch(f"{MODULE}.upsert_rows", return_value=(3, 0)), \
             patch(f"{MODULE}.finish_run") as finish:
            assert write_totals([self.RECORD], self.WINDOW, "googleNews") == (3, 0)
        assert finish.call_args.args[1] == "success"

    def test_partial_failure_is_status_partial(self) -> None:
        with patch(f"{MODULE}.start_run", return_value="run-totals"), \
             patch(f"{MODULE}.upsert_rows", return_value=(2, 1)), \
             patch(f"{MODULE}.finish_run") as finish:
            write_totals([self.RECORD], self.WINDOW, "googleNews")
        assert finish.call_args.args[1] == "partial"

    def test_total_failure_is_status_failed(self) -> None:
        with patch(f"{MODULE}.start_run", return_value="run-totals"), \
             patch(f"{MODULE}.upsert_rows", return_value=(0, 2)), \
             patch(f"{MODULE}.finish_run") as finish:
            write_totals([self.RECORD], self.WINDOW, "googleNews")
        assert finish.call_args.args[1] == "failed"

    def test_url_error_during_upsert_finishes_run_as_failed_and_reraises(self) -> None:
        """Regression（review S4.1 SF-3，2026-09-03）：upsert_rows 內的
        _supabase_request 只擋 HTTPError，URLError（DNS／連線重置／TLS）會穿出來——
        這裡已經 start_run 過，不收尾就會永遠卡在 status='running'。"""
        with patch(f"{MODULE}.start_run", return_value="run-totals"), \
             patch(f"{MODULE}.upsert_rows", side_effect=urllib.error.URLError("network gone")), \
             patch(f"{MODULE}.finish_run") as finish:
            with pytest.raises(urllib.error.URLError):
                write_totals([self.RECORD], self.WINDOW, "googleNews")
        assert finish.call_args.args == ("run-totals", "failed", 0)


class TestIngestTotals:
    """_ingest_totals：探測回應 → gsc_daily_totals，0 列可寫入是硬失敗。"""

    ROWS = [_api_row(DAY.isoformat())]

    def test_no_writable_records_is_a_hard_error(self) -> None:
        errors: list[str] = []
        with patch(f"{MODULE}.build_totals_records", return_value=[]), \
             patch(f"{MODULE}.write_totals") as write:
            written = _ingest_totals(self.ROWS, search_type="web", execute=True,
                                      errors=errors, warnings=[])
        assert written == 0
        assert len(errors) == 1 and "沒有可寫入的全站總數列" in errors[0]
        write.assert_not_called()

    def test_dry_run_does_not_call_write_totals(self) -> None:
        records = [{"date": DAY.isoformat(), "property": PROPERTY, "search_type": "web",
                    "clicks": 1, "impressions": 2, "ctr": 0.5, "position": 3.0}]
        with patch(f"{MODULE}.build_totals_records", return_value=records), \
             patch(f"{MODULE}.write_totals") as write:
            written = _ingest_totals(self.ROWS, search_type="web", execute=False,
                                      errors=[], warnings=[])
        assert written == 0
        write.assert_not_called()

    def test_execute_writes_and_returns_succeeded_count(self) -> None:
        records = [{"date": DAY.isoformat(), "property": PROPERTY, "search_type": "web",
                    "clicks": 1, "impressions": 2, "ctr": 0.5, "position": 3.0}]
        errors: list[str] = []
        with patch(f"{MODULE}.build_totals_records", return_value=records), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)):
            written = _ingest_totals(self.ROWS, search_type="web", execute=True,
                                      errors=errors, warnings=[])
        assert written == 1 and errors == []

    def test_write_failure_is_recorded_as_error(self) -> None:
        records = [{"date": DAY.isoformat(), "property": PROPERTY, "search_type": "web",
                    "clicks": 1, "impressions": 2, "ctr": 0.5, "position": 3.0}]
        errors: list[str] = []
        with patch(f"{MODULE}.build_totals_records", return_value=records), \
             patch(f"{MODULE}.write_totals", return_value=(0, 1)):
            _ingest_totals(self.ROWS, search_type="web", execute=True,
                           errors=errors, warnings=[])
        assert len(errors) == 1 and "1 列寫入失敗" in errors[0]


class TestReapOrphans:
    def test_deletes_only_rows_older_than_this_run(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[{},{}]")) as request:
            assert reap_orphans(DAY, COMBO_PAGE, "web", INGESTED_AT) == 2
        path = request.call_args.args[1]
        assert "ingested_at=lt." in path
        assert f"date=eq.{DAY.isoformat()}" in path

    def test_scopes_delete_to_the_combo(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")) as request:
            reap_orphans(DAY, COMBO_QUERY, "web", INGESTED_AT)
        assert combo_filter(COMBO_QUERY) in request.call_args.args[1]

    def test_failure_returns_zero_and_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            assert reap_orphans(DAY, COMBO_PAGE, "web", INGESTED_AT) == 0
        assert "reap 失敗" in caplog.text

    def test_no_orphans_is_quiet(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")):
            assert reap_orphans(DAY, COMBO_PAGE, "web", INGESTED_AT) == 0


class TestReapOrphansSurfaceScoping:
    """googleNews／discover 只有 page 組；DELETE 判別式必須同時帶 search_type 與
    page 判別式，證明不會刪到 web 的列，也不會刪到（假設性的）query 組的列。"""

    def test_scopes_delete_to_search_type_and_page_discriminator(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")) as request:
            reap_orphans(DAY, COMBO_PAGE, "googleNews", INGESTED_AT)
        path = request.call_args.args[1]
        assert "search_type=eq.googleNews" in path
        assert combo_filter(COMBO_PAGE) in path
        assert "search_type=eq.web" not in path

    def test_does_not_reuse_the_query_combo_discriminator(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")) as request:
            reap_orphans(DAY, COMBO_PAGE, "googleNews", INGESTED_AT)
        path = request.call_args.args[1]
        assert combo_filter(COMBO_QUERY) not in path

    def test_discover_scopes_delete_to_search_type_and_page_nodevice_discriminator(self) -> None:
        """S2.5：discover 走 page_nodevice 組；combo_filter 不特判 page_nodevice，
        判別式與 page 組完全相同，DELETE 只掃得到 discover 自己的列。"""
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")) as request:
            reap_orphans(DAY, COMBO_PAGE_NODEVICE, "discover", INGESTED_AT)
        path = request.call_args.args[1]
        assert f"property=eq.{urllib.parse.quote(PROPERTY, safe='')}" in path
        assert "search_type=eq.discover" in path
        assert combo_filter(COMBO_PAGE_NODEVICE) in path
        assert "page=neq." in path  # page 側判別式，不是 query 側
        assert "ingested_at=lt." in path
        assert "search_type=eq.web" not in path


class TestWriteSlice:
    ROW = TestUpsert.ROW

    def test_reaps_when_upsert_fully_succeeds(self) -> None:
        with patch(f"{MODULE}.upsert_rows", return_value=(5, 0)), \
             patch(f"{MODULE}.reap_orphans", return_value=1) as reap:
            assert _write_slice(DAY, COMBO_PAGE, "web", INGESTED_AT, [self.ROW]) == (5, 0)
        reap.assert_called_once()

    def test_skips_reap_on_partial_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """部分失敗還去刪，會把上一輪的好資料刪掉換來這一輪的殘缺資料。"""
        with patch(f"{MODULE}.upsert_rows", return_value=(3, 2)), \
             patch(f"{MODULE}.reap_orphans") as reap:
            _write_slice(DAY, COMBO_PAGE, "web", INGESTED_AT, [self.ROW])
        reap.assert_not_called()
        assert "跳過 reap" in caplog.text

    def test_skips_reap_when_nothing_was_written(self) -> None:
        with patch(f"{MODULE}.upsert_rows", return_value=(0, 0)), \
             patch(f"{MODULE}.reap_orphans") as reap:
            _write_slice(DAY, COMBO_PAGE, "web", INGESTED_AT, [])
        reap.assert_not_called()


class TestCountRows:
    def test_reads_count_from_content_range(self) -> None:
        """不用 query-string 的 limit：PostgREST 的 db-max-rows（預設 1000）
        會靜默覆蓋它且仍回 200。"""
        response = _FakeResponse("[]", status=206, headers={"Content-Range": "0-0/48210"})
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=response):
            assert count_rows() == 48210

    def test_sends_count_planned_not_exact(self) -> None:
        """(e) count=exact 要 PG 掃過整個結果集，news 480 天回填的 run 33772038727
        就在 Verify last write 這步撞 statement_timeout（57014）；planned 走 planner
        估計、不掃表。驗證用途只需要量級，精確的空/非空判定由 has_rows() 負責。"""
        response = _FakeResponse("[]", status=206, headers={"Content-Range": "0-0/48210"})
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=response) as opener:
            count_rows()
        assert opener.call_args.args[0].headers["Prefer"] == "count=planned"

    def test_extra_query_is_appended(self) -> None:
        response = _FakeResponse("[]", status=206, headers={"Content-Range": "0-0/7"})
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=response) as opener:
            count_rows(f"&{combo_filter(COMBO_QUERY)}")
        assert combo_filter(COMBO_QUERY) in opener.call_args.args[0].full_url

    def test_raises_on_http_error(self) -> None:
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(500, "boom")):
            with pytest.raises(RuntimeError):
                count_rows()

    def test_raises_on_malformed_content_range(self) -> None:
        response = _FakeResponse("[]", headers={"Content-Range": "nope"})
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(RuntimeError):
                count_rows()

    def test_empty_table_reports_zero(self) -> None:
        response = _FakeResponse("[]", headers={"Content-Range": "*/0"})
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", return_value=response):
            assert count_rows() == 0


class TestHasRows:
    """count_rows() 換成 planned 之後補回來的保證：planner 的列數估計有下限 1，
    拿它判斷「0 列」會讓那條檢查永遠通過，所以空/非空一律實際取 1 列來問。"""

    def test_returns_true_when_a_row_comes_back(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, '[{"date": "2026-08-25"}]')):
            assert has_rows() is True

    def test_returns_false_on_empty_result(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")):
            assert has_rows() is False

    def test_raises_on_query_failure_instead_of_reporting_zero(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            with pytest.raises(RuntimeError):
                has_rows()

    def test_extra_query_and_table_are_used(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")) as request:
            has_rows("&search_type=eq.web", "gsc_daily_totals")
        path = request.call_args.args[1]
        assert "gsc_daily_totals" in path and "search_type=eq.web" in path

    def test_uses_date_desc_order_to_hit_the_date_index_not_a_seq_scan(self) -> None:
        """run 33849046525 之後：不帶 order 會 seq scan 從 heap 頭掃到剛寫入的尾端，
        表大到一定程度會逾時；帶 order=date.desc 讓它走 (date DESC) 索引。"""
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")) as request:
            has_rows()
        path = request.call_args.args[1]
        assert "order=date.desc" in path


class TestLatestDate:
    def test_returns_parsed_date(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, '[{"date": "2026-08-25"}]')):
            assert latest_date() == DAY

    def test_empty_table_returns_none(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")):
            assert latest_date() is None

    def test_error_raises(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            with pytest.raises(RuntimeError):
                latest_date()


# ══════════════════════════════════════════════════════════════════════
# 0 rows 一律失敗
# ══════════════════════════════════════════════════════════════════════

class TestCollectDayCombo:
    @staticmethod
    def _collect(rows: list[dict], combo: str = COMBO_PAGE) -> tuple[list[dict], list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        with patch(f"{MODULE}.paginate_query", return_value=rows):
            records = collect_day_combo("t", DAY, combo, "web", INGESTED_AT, errors, warnings)
        return records, errors, warnings

    def test_happy_path_records_no_error(self) -> None:
        records, errors, warnings = self._collect([_api_row(DAY.isoformat(), "https://vocus.cc/a", "MOBILE")])
        assert len(records) == 1 and errors == [] and warnings == []

    def test_zero_rows_is_recorded_as_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """(e)：0 rows 不得靜默通過。探測已說該日有資料，這裡回 0 就是異常。"""
        records, errors, _ = self._collect([])
        assert records == [] and len(errors) == 1 and "0 列" in errors[0]
        assert "視為失敗" in caplog.text

    def test_rejected_rows_are_warnings_not_errors(self) -> None:
        """首次 live 執行的校準：533,314 列裡 2 列 query 超長，不該讓整個 run 紅燈。
        超長 query 是資料的永久性質，天天染紅只會讓人學會忽略 status。"""
        rows = [_api_row(DAY.isoformat(), "https://vocus.cc/a", "MOBILE"),
                _api_row(DAY.isoformat(), "https://vocus.cc/b", "WATCH")]
        records, errors, warnings = self._collect(rows)
        assert len(records) == 1
        assert errors == []
        assert len(warnings) == 1 and "丟棄不合法列" in warnings[0]

    def test_all_rows_rejected_still_errors_because_slice_is_empty(self) -> None:
        records, errors, warnings = self._collect([_api_row(DAY.isoformat(), "https://vocus.cc/a", "WATCH")])
        assert records == [] and len(errors) == 1 and len(warnings) == 1

    def test_duplicate_pages_are_deduped(self) -> None:
        rows = [_api_row(DAY.isoformat(), "https://vocus.cc/a", "MOBILE")] * 2
        records, _, _ = self._collect(rows)
        assert len(records) == 1


# ══════════════════════════════════════════════════════════════════════
# run_ingestion
# ══════════════════════════════════════════════════════════════════════

def _one_record(*_args, **_kwargs) -> list[dict]:
    return [dict(TestUpsert.ROW)]


class TestRunIngestion:
    def test_empty_probe_is_a_hard_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """探測回空 = 權限/property/配額壞了，不是資料延遲——這個分流是本腳本的核心。"""
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=[]):
            assert run_ingestion(execute=True, backfill_days=7, search_type="web") == 1
        assert "不是資料延遲" in caplog.text

    def test_dry_run_does_not_write(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.start_run") as start, \
             patch(f"{MODULE}._write_slice") as write:
            assert run_ingestion(execute=False, backfill_days=7, search_type="web") == 0
        start.assert_not_called()
        write.assert_not_called()

    def test_execute_writes_both_combos_for_each_day(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY, DAY - timedelta(days=1)])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run") as finish, \
             patch(f"{MODULE}._write_slice", return_value=(1, 0)) as write:
            assert run_ingestion(execute=True, backfill_days=7, search_type="web") == 0
        assert write.call_count == 4  # 2 天 × 2 組合
        assert finish.call_args.args[1:] == ("success", 4)

    def test_backfill_days_limits_the_target_dates(self) -> None:
        days = [DAY - timedelta(days=offset) for offset in range(10)]
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows(days)), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record) as collect, \
             patch(f"{MODULE}.start_run", return_value=None), \
             patch(f"{MODULE}.finish_run"), \
             patch(f"{MODULE}._write_slice", return_value=(1, 0)):
            run_ingestion(execute=True, backfill_days=3, search_type="web")
        # len(COMBO_DIMENSIONS) 曾與 web 的組合數巧合相等；page_nodevice 加入後
        # COMBO_DIMENSIONS 變 3 但 web 仍只有 page／query 兩組，改用 SURFACE_COMBOS["web"]。
        assert collect.call_count == 3 * len(SURFACE_COMBOS["web"])

    def test_zero_written_rows_is_status_failed(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", return_value=[]), \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run") as finish:
            assert run_ingestion(execute=True, backfill_days=7, search_type="web") == 1
        assert finish.call_args.args[1] == "failed"

    def test_partial_write_failure_is_status_partial(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run") as finish, \
             patch(f"{MODULE}._write_slice", return_value=(1, 1)):
            assert run_ingestion(execute=True, backfill_days=7, search_type="web") == 1
        assert finish.call_args.args[1] == "partial"

    def test_warnings_alone_do_not_degrade_status(self) -> None:
        """回歸：首次 live 執行時 2 列超長 query 讓 status 變 partial 並 exit 1，那是誤判。"""
        def _with_warning(_token, day, combo, _search_type, _ingested_at, _errors, warnings):
            warnings.append(f"{day}/{combo} 丟棄不合法列：{{'query 超過 512 bytes': 1}}")
            return [dict(TestUpsert.ROW)]

        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_with_warning), \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run") as finish, \
             patch(f"{MODULE}._write_slice", return_value=(1, 0)):
            assert run_ingestion(execute=True, backfill_days=7, search_type="web") == 0
        assert finish.call_args.args[1] == "success"

    def test_systemic_api_error_aborts_the_run(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=GscQueryError("403")), \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run") as finish:
            assert run_ingestion(execute=True, backfill_days=7, search_type="web") == 1
        assert finish.call_args.args[1] == "failed"

    def test_dry_run_with_errors_exits_nonzero(self) -> None:
        def _zero_rows(_token, day, combo, _search_type, _ingested_at, errors, _warnings):
            errors.append(f"{day}/{combo} 回傳 0 列")
            return []

        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_zero_rows):
            assert run_ingestion(execute=False, backfill_days=7, search_type="web") == 1

    def test_url_error_during_totals_finishes_both_runs_as_failed(self) -> None:
        """Regression（review S4.1 SF-3，2026-09-03）：totals 路徑本來在 try 之外，
        URLError 會讓主 run（run_ingestion 開的）與 totals run（write_totals 內
        開的）兩列 ingestion_run 都卡在 status='running'。挪進 try 並擴大 except
        之後，兩列都要被 finish_run 收尾成 'failed'，不能只收主 run 那一列。"""
        totals_records = [{"date": DAY.isoformat(), "property": PROPERTY,
                           "search_type": "web", "clicks": 1, "impressions": 2,
                           "ctr": 0.5, "position": 3.0}]
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.build_totals_records", return_value=totals_records), \
             patch(f"{MODULE}.start_run", side_effect=["run-main", "run-totals"]) as start, \
             patch(f"{MODULE}.upsert_rows", side_effect=urllib.error.URLError("network gone")), \
             patch(f"{MODULE}.finish_run") as finish, \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record):
            assert run_ingestion(execute=True, backfill_days=7, search_type="web") == 1
        assert start.call_count == 2  # 主 run + totals run
        assert finish.call_count == 2  # 兩列都被收尾，不是只有一列
        finished = [(call.args[0], call.args[1]) for call in finish.call_args_list]
        assert finished == [("run-totals", "failed"), ("run-main", "failed")]

    def test_run_window_is_half_open_over_target_dates(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY, DAY - timedelta(days=1)])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.start_run", return_value="r") as start, \
             patch(f"{MODULE}.finish_run"), \
             patch(f"{MODULE}._write_slice", return_value=(1, 0)):
            run_ingestion(execute=True, backfill_days=7, search_type="web")
        window_start, window_end = start.call_args.args
        assert window_start == datetime(2026, 8, 24, tzinfo=UTC)
        assert window_end == datetime(2026, 8, 26, tzinfo=UTC)


class TestRunIngestionGoogleNewsSurface:
    """googleNews 帶 query 維度送出去必定整個 run 400——SURFACE_COMBOS 只給它 page 組，
    這裡直接證明 run_ingestion 真的照著這張表跑，而不是把兩組硬寫死在迴圈裡。"""

    def test_only_page_combo_is_dispatched(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record) as collect, \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run"), \
             patch(f"{MODULE}._write_slice", return_value=(1, 0)):
            assert run_ingestion(execute=True, backfill_days=1, search_type="googleNews") == 0
        combos_used = {call.args[2] for call in collect.call_args_list}
        assert combos_used == {COMBO_PAGE}

    def test_gsc_post_dimensions_never_include_query(self) -> None:
        """不 mock collect_day_combo，讓真正的 paginate_query → _gsc_post 路徑跑一次，
        直接斷言送出去的 body 沒有一次帶 query 維度。"""
        api_response = {"rows": [_api_row(DAY.isoformat(), "https://vocus.cc/a", "MOBILE",
                                          position=0.0)]}
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}._gsc_post", return_value=api_response) as post:
            assert run_ingestion(execute=False, backfill_days=1, search_type="googleNews") == 0
        dimension_sets = [set(call.args[1]["dimensions"]) for call in post.call_args_list]
        assert dimension_sets  # 至少發了一次請求
        assert all("query" not in dims for dims in dimension_sets)


class TestRunIngestionDiscoverSurface:
    """S2.5（2026-09-04）：discover 現在有 page_nodevice 組（SURFACE_COMBOS["discover"]
    == (COMBO_PAGE_NODEVICE,)）。run_ingestion 對它的行為因此改回跟
    TestRunIngestionGoogleNewsSurface 同構——只是 combo 換成 page_nodevice、
    送出去的 dimensions 不帶 device——不再是舊版「combos 為空、什麼組都不送」的行為。
    """

    def test_collect_day_combo_is_called_with_page_nodevice_combo(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record) as collect, \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run"), \
             patch(f"{MODULE}._write_slice", return_value=(1, 0)):
            assert run_ingestion(execute=True, backfill_days=1, search_type="discover") == 0
        combos_used = {call.args[2] for call in collect.call_args_list}
        assert combos_used == {COMBO_PAGE_NODEVICE}

    def test_gsc_post_dimensions_are_date_and_page_only(self) -> None:
        """不 mock collect_day_combo，讓真正的 paginate_query → _gsc_post 路徑跑一次，
        直接斷言送出去的 body 是 {"date","page"}——不帶 device，那正是 400 的原因。"""
        api_response = {"rows": [{"keys": [DAY.isoformat(), "https://vocus.cc/a"],
                                   "clicks": 3, "impressions": 10, "ctr": 0.3, "position": 0.0}]}
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}._gsc_post", return_value=api_response) as post, \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run"), \
             patch(f"{MODULE}.upsert_rows", return_value=(1, 0)), \
             patch(f"{MODULE}.reap_orphans", return_value=0):
            assert run_ingestion(execute=True, backfill_days=1, search_type="discover") == 0
        dimension_sets = [set(call.args[1]["dimensions"]) for call in post.call_args_list]
        assert dimension_sets  # 至少發了一次請求
        assert all(dims == {"date", "page"} for dims in dimension_sets)

    def test_reap_orphans_called_with_page_nodevice_combo(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.upsert_rows", return_value=(1, 0)), \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run"), \
             patch(f"{MODULE}.reap_orphans", return_value=0) as reap:
            assert run_ingestion(execute=True, backfill_days=1, search_type="discover") == 0
        reap.assert_called_once()
        assert reap.call_args.args[1] == COMBO_PAGE_NODEVICE
        assert reap.call_args.args[2] == "discover"

    def test_gsc_daily_metrics_ingestion_run_is_created(self) -> None:
        """discover 現在有非空 combos，頂層 start_run(*run_window(targets))（預設
        table_name=TABLE_GSC）該被呼叫——不再是「combos 為空永遠不建」的舊行為。
        write_totals 內部另有自己那次 start_run(table_name=TABLE_TOTALS)。"""
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.upsert_rows", return_value=(1, 0)), \
             patch(f"{MODULE}.reap_orphans", return_value=0), \
             patch(f"{MODULE}.start_run", side_effect=["run-metrics", "run-totals"]) as start, \
             patch(f"{MODULE}.finish_run"):
            assert run_ingestion(execute=True, backfill_days=1, search_type="discover") == 0
        assert len(start.call_args_list) == 2
        table_names = [call.kwargs.get("table_name", TABLE_GSC) for call in start.call_args_list]
        assert table_names == [TABLE_GSC, TABLE_TOTALS]

    def test_totals_write_failure_is_still_reported_as_failure(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(0, 1)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.upsert_rows", return_value=(1, 0)), \
             patch(f"{MODULE}.reap_orphans", return_value=0), \
             patch(f"{MODULE}.start_run", return_value="run-1"), \
             patch(f"{MODULE}.finish_run"):
            assert run_ingestion(execute=True, backfill_days=1, search_type="discover") == 1

    def test_dry_run_with_healthy_totals_returns_zero(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.write_totals", return_value=(1, 0)), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.start_run") as start, \
             patch(f"{MODULE}._write_slice") as write:
            assert run_ingestion(execute=False, backfill_days=1, search_type="discover") == 0
        start.assert_not_called()
        write.assert_not_called()


class TestIngestionRunHasSeparateRowsPerTable:
    """gsc_daily_metrics 與 gsc_daily_totals 各自的 ingestion_run 列不共用——
    stale-running 之類的 gate 是按 table_name 分組的，混在一起會讓分組失真。"""

    def test_metrics_and_totals_each_get_their_own_start_run_call(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="t"), \
             patch(f"{MODULE}.probe_totals", return_value=_probe_rows([DAY])), \
             patch(f"{MODULE}.collect_day_combo", side_effect=_one_record), \
             patch(f"{MODULE}.upsert_rows", return_value=(1, 0)), \
             patch(f"{MODULE}.reap_orphans", return_value=0), \
             patch(f"{MODULE}.start_run", side_effect=["run-metrics", "run-totals"]) as start, \
             patch(f"{MODULE}.finish_run"):
            assert run_ingestion(execute=True, backfill_days=1, search_type="web") == 0
        assert len(start.call_args_list) == 2
        table_names = [call.kwargs.get("table_name", TABLE_GSC) for call in start.call_args_list]
        assert table_names == [TABLE_GSC, TABLE_TOTALS]


# ══════════════════════════════════════════════════════════════════════
# verify / freshness
# ══════════════════════════════════════════════════════════════════════

class TestRunVerify:
    RECENT = json.dumps([
        {"date": "2026-08-25", "page": "https://vocus.cc/a", "query": "", "device": "mobile",
         "clicks": 5, "impressions": 20, "ctr": 0.25, "position": 3.1},
        {"date": "2026-08-25", "page": PAGE_NOT_REQUESTED, "query": "方格子", "device": "desktop",
         "clicks": 7, "impressions": 30, "ctr": 0.233, "position": 1.2},
    ])
    RUNS = json.dumps([{"id": "abcdef12", "window_start": "2026-08-19T00:00:00Z",
                        "window_end": "2026-08-26T00:00:00Z", "row_count": 10,
                        "status": "success", "finished_at": "2026-08-29T00:00:00Z"}])
    # review S4.1 #9：run_verify 現在每個 search_type 多印一段 totals 列數／最新日期，
    # 多一次 count_rows 呼叫、多一次 _supabase_request 呼叫（排在 TABLE_GSC 那次之前）。
    TOTALS_LATEST = json.dumps([{"date": "2026-08-25"}])

    def test_reports_both_combo_counts_and_the_double_count_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="ingest_gsc_search_analytics"), \
             patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, True)]), \
             patch(f"{MODULE}.count_rows", side_effect=[30]), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify() == 0
        assert "page 組 900 列 / query 組 100 列" in caplog.text
        assert "算兩次" in caplog.text
        assert "totals(web)：30 列（planner 估計），最新日期 2026-08-25" in caplog.text

    def test_labels_each_row_by_the_page_discriminator(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="ingest_gsc_search_analytics"), \
             patch(f"{MODULE}._combo_probe", side_effect=[(1, True), (1, True)]), \
             patch(f"{MODULE}.count_rows", side_effect=[1]), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            run_verify()
        assert f"[{COMBO_QUERY}] 方格子" in caplog.text
        assert f"[{COMBO_PAGE}] https://vocus.cc/a" in caplog.text

    def test_missing_one_combo_fails(self) -> None:
        """query 組實際沒有列（_combo_probe 回 exists=False）就要失敗——即使 planner 把它估成 100。"""
        with patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, False)]), \
             patch(f"{MODULE}.count_rows", side_effect=[30]), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify() == 1

    def test_read_failure_returns_one(self) -> None:
        with patch(f"{MODULE}._combo_probe", side_effect=[(1, True), (1, True)]), \
             patch(f"{MODULE}.count_rows", side_effect=[1]), \
             patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            assert run_verify() == 1

    def test_run_table_read_failure_returns_one(self) -> None:
        with patch(f"{MODULE}._combo_probe", side_effect=[(1, True), (1, True)]), \
             patch(f"{MODULE}.count_rows", side_effect=[1]), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (500, "boom")]):
            assert run_verify() == 1

    def test_totals_read_failure_still_lets_run_verify_continue(self) -> None:
        """totals 查詢失敗不該讓 run_verify 整個中止——沿用 latest_date() 對
        非 200 的處理方式，記 N/A 後繼續看 TABLE_GSC／TABLE_RUN 那兩段。"""
        with patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, True)]), \
             patch(f"{MODULE}.count_rows", side_effect=[30]), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(500, "boom"), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify() == 0

    def test_sample_query_has_no_clicks_sort_only_date_desc(self) -> None:
        """run 33849046525：帶 clicks.desc 迫使 planner 把最新一天全部 surface 的列
        （約 20 萬列）撈回做 Incremental Sort，表到 1.6M 列就逾時。read-back 樣本
        不是 top-N 排行，只需要 order=date.desc 走索引取到 8 列即停。"""
        with patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, True)]), \
             patch(f"{MODULE}.count_rows", side_effect=[30]), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]) as request:
            assert run_verify() == 0
        sample_query_path = request.call_args_list[1].args[1]
        assert "clicks.desc" not in sample_query_path
        assert "order=date.desc&limit=8" in sample_query_path

    def test_sample_query_carries_property_filter(self) -> None:
        """run 33863653352：底表帶 search_type 篩選卻沒帶 property 時，planner 會挑錯
        索引全表掃描；帶 property 才會被 gsc_daily_metrics_dim_uniq 用上（EXPLAIN 實測
        4.2ms vs 26,208ms，見 .verification/2026-09-04/gate-probe-shape/）。"""
        with patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, True)]), \
             patch(f"{MODULE}.count_rows", side_effect=[30]), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]) as request:
            assert run_verify() == 0
        sample_query_path = request.call_args_list[1].args[1]
        assert f"property=eq.{urllib.parse.quote(PROPERTY, safe='')}" in sample_query_path


class TestVerifySurfaceNoRankingBranch:
    """只有 page 組的 surface（googleNews／discover）不該被要求 query 組，
    log 分支也要對；這是 _verify_surface 本身的單元測試，不透過 run_verify 間接跑。"""

    def test_page_only_surface_logs_without_query_count(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="ingest_gsc_search_analytics"), \
             patch(f"{MODULE}._combo_probe", return_value=(42, True)):
            assert _verify_surface("googleNews") is True
        assert "此 surface 不支援 query 維度" in caplog.text

    def test_page_only_surface_empty_is_unhealthy(self) -> None:
        """判定看 _combo_probe 的存在性，不看它回傳的估計列數——planner 估計 1
        也不能救一個真的空的 surface。"""
        with patch(f"{MODULE}._combo_probe", return_value=(1, False)):
            assert _verify_surface("googleNews") is False

    def test_ranking_surface_still_reports_both_combos(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="ingest_gsc_search_analytics"), \
             patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, True)]):
            assert _verify_surface("web") is True
        assert "page 組 900 列 / query 組 100 列" in caplog.text

    def test_verify_surface_makes_exactly_one_probe_per_combo(self) -> None:
        """回歸：每個 combo 只打一次請求，不再各打一次 count_rows() 又一次 has_rows()。"""
        with patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, True)]) as probe:
            _verify_surface("web")
        assert probe.call_count == len(SURFACE_COMBOS["web"]) == 2

    def test_verify_surface_probe_carries_property_filter(self) -> None:
        """run 33863653352：_combo_probe 查底表帶 search_type 卻沒帶 property 時撞過
        57014——planner 選不到 gsc_daily_metrics_dim_uniq，全表掃描。每個 combo 的
        extra_query 都要帶 property=eq.<PROPERTY>。"""
        with patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, True)]) as probe:
            _verify_surface("web")
        expected = f"property=eq.{urllib.parse.quote(PROPERTY, safe='')}"
        assert all(expected in call.args[0] for call in probe.call_args_list)


class TestRunVerifySurfaceScoped:
    """(g)：googleNews page 組 0 列要讓 run_verify 回非 0；web 兩組都有資料時回 0。
    這裡直接控制 search_types 參數，而不是依賴其他測試共用的預設值。"""

    RECENT = TestRunVerify.RECENT
    RUNS = TestRunVerify.RUNS

    TOTALS_LATEST = TestRunVerify.TOTALS_LATEST

    def test_google_news_zero_page_rows_fails(self) -> None:
        with patch(f"{MODULE}._combo_probe", return_value=(1, False)), \
             patch(f"{MODULE}.count_rows", return_value=1), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify(["googleNews"]) == 1

    def test_google_news_nonzero_page_rows_passes(self) -> None:
        with patch(f"{MODULE}._combo_probe", return_value=(10, True)), \
             patch(f"{MODULE}.count_rows", return_value=10), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify(["googleNews"]) == 0

    def test_web_with_both_combos_present_passes(self) -> None:
        with patch(f"{MODULE}._combo_probe", side_effect=[(900, True), (100, True)]), \
             patch(f"{MODULE}.count_rows", side_effect=[30]), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify(["web"]) == 0


class TestRunVerifyDiscoverSurface:
    """S2.5（2026-09-04）：discover 現在有 page_nodevice 組，run_verify 對它的行為
    改回跟 googleNews 同構——_verify_surface 會被呼叫（不再是「combos 為空跳過」）。
    這裡同時鎖住 _verify_surface 對 discover 的 log 分支不會 KeyError——舊版硬取
    counts[COMBO_PAGE]，discover 的 counts dict 只有 page_nodevice 一個 key，
    改版前這裡會直接炸掉。"""

    RECENT = TestRunVerify.RECENT
    RUNS = TestRunVerify.RUNS
    TOTALS_LATEST = TestRunVerify.TOTALS_LATEST

    def test_verify_surface_is_called_for_discover(self) -> None:
        with patch(f"{MODULE}._verify_surface", return_value=True) as verify_surface, \
             patch(f"{MODULE}.count_rows", return_value=29), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify(["discover"]) == 0
        verify_surface.assert_called_once_with("discover")

    def test_page_nodevice_probe_does_not_raise_keyerror(self) -> None:
        """回歸：_verify_surface 對 counts 逐 combo 印，不再硬取 counts[COMBO_PAGE]。
        跑真正的 _verify_surface（不 mock 掉），只 mock 它底下的 _combo_probe，
        若 log 分支還在硬取 COMBO_PAGE 這裡會直接 KeyError 而不是回傳值。"""
        with patch(f"{MODULE}._combo_probe", return_value=(10, True)), \
             patch(f"{MODULE}.count_rows", return_value=10), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify(["discover"]) == 0

    def test_page_nodevice_zero_rows_fails(self) -> None:
        """_combo_probe 回 exists=False（page_nodevice 組實際 0 列）要讓 run_verify
        回非 0，即使 planner 估計值非零。"""
        with patch(f"{MODULE}._combo_probe", return_value=(1, False)), \
             patch(f"{MODULE}.count_rows", return_value=1), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify(["discover"]) == 1

    def test_verify_surface_discover_probe_carries_property_and_page_nodevice_filter(self) -> None:
        """(f)：_verify_surface("discover") 發出的 probe query 必須帶
        property=eq.<PROPERTY>（REQ-3 橫切規則）與 page_nodevice 的判別式。"""
        with patch(f"{MODULE}._combo_probe", return_value=(10, True)) as probe:
            assert _verify_surface("discover") is True
        assert probe.call_count == 1
        extra_query = probe.call_args.args[0]
        assert f"property=eq.{urllib.parse.quote(PROPERTY, safe='')}" in extra_query
        assert combo_filter(COMBO_PAGE_NODEVICE) in extra_query
        assert "search_type=eq.discover" in extra_query

    def test_mixed_web_and_discover_both_go_through_verify_surface(self) -> None:
        """search_types 混合 web／discover：兩者 combos 現在都非空，metrics_types
        兩個都留，_verify_surface 依序對兩者各呼叫一次。"""
        with patch(f"{MODULE}._verify_surface", return_value=True) as verify_surface, \
             patch(f"{MODULE}.count_rows", return_value=5), \
             patch(f"{MODULE}._supabase_request",
                   side_effect=[(200, self.TOTALS_LATEST), (200, self.TOTALS_LATEST),
                               (200, self.RECENT), (200, self.RUNS)]):
            assert run_verify(["web", "discover"]) == 0
        assert [call.args[0] for call in verify_surface.call_args_list] == ["web", "discover"]


class TestFreshnessCheck:
    def test_threshold_accounts_for_source_lag_not_just_schedule_period(self) -> None:
        """KB skill freshness-threshold-...-ignores-source-inherent-lag：
        GSC 天生落後 2-3 天，用「排程週期 24h × 3 = 72h」會對健康資料誤報。"""
        assert FRESHNESS_MAX_AGE_HOURS > 24 * 4

    def test_empty_table_fails(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch(f"{MODULE}.latest_date", return_value=None):
            assert run_freshness_check() == 1
        assert "從未成功寫入" in caplog.text

    def test_fresh_data_passes(self, caplog: pytest.LogCaptureFixture) -> None:
        recent = datetime.now(UTC).date() - timedelta(days=3)
        with caplog.at_level(logging.INFO, logger="ingest_gsc_search_analytics"), \
             patch(f"{MODULE}.latest_date", return_value=recent):
            assert run_freshness_check() == 0
        assert "PASS" in caplog.text

    def test_healthy_three_day_lag_does_not_false_alarm(self) -> None:
        """健康狀態下立刻跑一次——這是那條 KB skill 要求的驗證方式。"""
        for lag_days in (2, 3, 4, 5):
            with patch(f"{MODULE}.latest_date",
                       return_value=datetime.now(UTC).date() - timedelta(days=lag_days)):
                assert run_freshness_check() == 0, f"lag={lag_days} 天不該告警"

    def test_stale_data_fails(self, caplog: pytest.LogCaptureFixture) -> None:
        stale = datetime.now(UTC).date() - timedelta(days=10)
        with patch(f"{MODULE}.latest_date", return_value=stale):
            assert run_freshness_check() == 1
        assert "FAIL" in caplog.text


# ══════════════════════════════════════════════════════════════════════
# 參數與 CLI
# ══════════════════════════════════════════════════════════════════════

class TestArgumentResolution:
    def test_default_backfill_days(self) -> None:
        assert resolve_backfill_days(None) == DEFAULT_BACKFILL_DAYS

    @pytest.mark.parametrize("value", [0, -1, MAX_BACKFILL_DAYS + 1])
    def test_out_of_range_backfill_days_rejected(self, value: int) -> None:
        with pytest.raises(ValueError):
            resolve_backfill_days(value)

    @pytest.mark.parametrize("value", [1, MAX_BACKFILL_DAYS])
    def test_boundary_backfill_days_accepted(self, value: int) -> None:
        assert resolve_backfill_days(value) == value

    @pytest.mark.parametrize("value", ALLOWED_SEARCH_TYPES)
    def test_allowed_search_types(self, value: str) -> None:
        assert resolve_search_type(value) == value

    def test_discover_is_accepted(self) -> None:
        """022 之後 search_type_ck 收 discover、position_ck 對它放行 0，腳本跟著收。"""
        assert resolve_search_type("discover") == "discover"

    def test_unknown_search_type_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="sitemap"):
            resolve_search_type("sitemap")


class TestBackfillDaysCappedByProbeDays:
    """resolve_backfill_days 的上限是 min(MAX_BACKFILL_DAYS, probe_days)，不是
    MAX_BACKFILL_DAYS 本身——探測窗只回看 probe_days 天，超過會被 resolve_targets
    靜默截斷，這裡要求明確報錯而不是截斷。"""

    def test_backfill_beyond_probe_days_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="probe-days=14"):
            resolve_backfill_days(30, probe_days=14)

    def test_backfill_equal_to_probe_days_is_accepted(self) -> None:
        assert resolve_backfill_days(480, probe_days=480) == 480

    def test_backfill_below_probe_days_is_accepted(self) -> None:
        assert resolve_backfill_days(10, probe_days=14) == 10

    def test_default_probe_days_argument_is_max_backfill_days(self) -> None:
        """呼叫端不傳 probe_days 時退回舊行為（上限就是 MAX_BACKFILL_DAYS）。"""
        assert resolve_backfill_days(MAX_BACKFILL_DAYS) == MAX_BACKFILL_DAYS


class TestResolveProbeDays:
    def test_default_when_nothing_set(self) -> None:
        with patch.dict("os.environ", {"PROBE_DAYS": ""}):
            assert resolve_probe_days(None) == DEFAULT_PROBE_DAYS

    def test_env_variable_is_used_when_flag_absent(self) -> None:
        """workflow 舊寫法（env PROBE_DAYS）仍要相容。"""
        with patch.dict("os.environ", {"PROBE_DAYS": "21"}):
            assert resolve_probe_days(None) == 21

    def test_flag_takes_priority_over_env(self) -> None:
        with patch.dict("os.environ", {"PROBE_DAYS": "21"}):
            assert resolve_probe_days(9) == 9

    def test_probe_days_501_is_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="501"):
            resolve_probe_days(501)

    def test_probe_days_zero_is_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            resolve_probe_days(0)

    @pytest.mark.parametrize("value", [MIN_PROBE_DAYS, MAX_PROBE_DAYS])
    def test_boundary_values_are_accepted(self, value: int) -> None:
        assert resolve_probe_days(value) == value


class TestProbeRowLimit:
    """探測每天恰回一列，rowLimit 只需略大於天數；仍受 API 的 25,000 上限。"""

    def test_scales_with_probe_days(self) -> None:
        assert probe_row_limit(14) == 21
        assert probe_row_limit(100) == 107

    def test_capped_at_api_row_limit(self) -> None:
        assert probe_row_limit(30000) == ROW_LIMIT

    def test_max_probe_days_stays_well_under_the_cap(self) -> None:
        """MAX_PROBE_DAYS=500 時遠低於 25,000，封頂邏輯目前是防禦性的，不是常態路徑。"""
        assert probe_row_limit(MAX_PROBE_DAYS) < ROW_LIMIT


class TestCli:
    def _run(self, argv: list[str]) -> int:
        with patch("sys.argv", ["ingest_gsc_search_analytics.py", *argv]):
            with pytest.raises(SystemExit) as excinfo:
                main()
        return excinfo.value.code

    def test_verify_dispatches_to_run_verify(self) -> None:
        with patch(f"{MODULE}.run_verify", return_value=0) as verify:
            assert self._run(["--verify"]) == 0
        verify.assert_called_once()

    def test_check_freshness_dispatches(self) -> None:
        with patch(f"{MODULE}.run_freshness_check", return_value=1) as check:
            assert self._run(["--check-freshness"]) == 1
        check.assert_called_once()

    def test_default_is_dry_run(self) -> None:
        with patch(f"{MODULE}.run_ingestion", return_value=0) as ingest:
            self._run([])
        assert ingest.call_args.kwargs["execute"] is False

    def test_execute_flag_is_passed_through(self) -> None:
        with patch(f"{MODULE}.run_ingestion", return_value=0) as ingest:
            self._run(["--execute", "--backfill-days", "2"])
        assert ingest.call_args.kwargs == {"execute": True, "backfill_days": 2,
                                           "search_type": "web", "probe_days": DEFAULT_PROBE_DAYS}

    def test_invalid_backfill_days_exits_two(self) -> None:
        assert self._run(["--backfill-days", "999"]) == 2

    def test_invalid_search_type_exits_two(self) -> None:
        assert self._run(["--search-type", "sitemap"]) == 2

    def test_probe_days_501_exits_two(self) -> None:
        assert self._run(["--probe-days", "501"]) == 2

    def test_probe_days_is_passed_through(self) -> None:
        with patch(f"{MODULE}.run_ingestion", return_value=0) as ingest:
            self._run(["--execute", "--probe-days", "30", "--backfill-days", "30"])
        assert ingest.call_args.kwargs["probe_days"] == 30
        assert ingest.call_args.kwargs["backfill_days"] == 30

    def test_backfill_beyond_probe_days_exits_two(self) -> None:
        """CLI 層對 (f) 的整合驗證：--backfill-days 30 --probe-days 14 要報錯，不是靜默截斷。"""
        assert self._run(["--backfill-days", "30", "--probe-days", "14"]) == 2
