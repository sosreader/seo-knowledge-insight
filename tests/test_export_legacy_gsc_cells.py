"""Tests for export_legacy_gsc_cells.py。

重點覆蓋五件本腳本特有、且錯了不會有訊號的事：

1. **config.mjs 解析** —— 15+5 筆數量、pattern 跳脫（雙反斜線→單反斜線）、
   multiType 的 searchType/path 兩種來源、CELL 起始格號、各種格式異常。
2. **視窗計算** —— --start/--end 需成對、預設 days/end-offset 算式、邊界錯誤。
3. **request body 組法** —— includingRegex 過濾 vs 不分組的 surface 總量、equals 對照組。
4. **重試/致命分類** —— 429 暫時性重試、401/403 與配額耗盡字樣立即中止。
5. **輸出格式** —— JSON/CSV 內容、controls 只進 JSON 不進 CSV。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.export_legacy_gsc_cells import (  # noqa: E402
    CSV_FIELDS,
    ConfigParseError,
    LegacyCell,
    LegacyExportError,
    MAX_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
    ResultRow,
    build_request_body,
    extract_clicks,
    load_config_text,
    parse_legacy_cells,
    query_cell,
    resolve_window,
    run_equals_control,
    run_export,
    write_outputs,
)
from scripts import export_legacy_gsc_cells as mod

CONFIG_TEXT = r'''
export const SEARCH_PERFORMANCE = {
  days: 7,
  queryPage: [
    { label: "首頁", type: "page", pattern: "^https://vocus\\.cc/$" },
    { label: "/article/", type: "page", pattern: "/article/" },
    { label: "/post", type: "page", pattern: "/post" },
    { label: "/user", type: "page", pattern: "/user" },
    { label: "/salon/", type: "page", pattern: "/salon/" },
    { label: "/tags/", type: "page", pattern: "/tags/" },
    { label: "/search", type: "page", pattern: "/search" },
    { label: "影評", type: "query", pattern: "影評" },
    { label: "電影", type: "query", pattern: "電影" },
    { label: "評價", type: "query", pattern: "評價" },
    { label: "攻略", type: "query", pattern: "攻略" },
    { label: "股", type: "query", pattern: "股" },
    { label: "劇", type: "query", pattern: "劇" },
    { label: "保養", type: "query", pattern: "保養" },
    { label: "必買", type: "query", pattern: "必買" },
  ],
  multiType: [
    { label: "圖片", path: "performance/search-analytics", searchType: "image" },
    { label: "影片", path: "performance/search-analytics", searchType: "video" },
    { label: "新聞", path: "performance/search-analytics", searchType: "news" },
    { label: "探索", path: "performance/discover" },
    { label: "Google News", path: "performance/google-news" },
  ],
};

export const CELL = {
  searchPerformance: 2,
  aiExposure: 12,
  queryPage: 20,
  multiType: 38,
};
'''

MISSING_CELL_CONFIG_TEXT = CONFIG_TEXT.split("export const CELL")[0]


def _query_page_entries(n: int) -> str:
    """回傳 n 筆合法 queryPage entry（用來造『數量不對』的異常樣本）。"""
    lines = [
        '    { label: "首頁", type: "page", pattern: "^https://vocus\\\\.cc/$" },',
        '    { label: "/article/", type: "page", pattern: "/article/" },',
    ]
    return "\n".join(lines[:n])


# ══════════════════════════════════════════════════════════════════════
# config.mjs 解析
# ══════════════════════════════════════════════════════════════════════

class TestParseLegacyCells:
    def test_parses_20_cells_in_order(self) -> None:
        cells = parse_legacy_cells(CONFIG_TEXT)
        assert len(cells) == 20
        assert [c.cell for c in cells] == [f"G{n}" for n in range(20, 35)] + [f"G{n}" for n in range(38, 43)]

    def test_pattern_unescapes_double_backslash_to_single(self) -> None:
        cells = parse_legacy_cells(CONFIG_TEXT)
        homepage = cells[0]
        assert homepage.label == "首頁"
        assert homepage.pattern == r"^https://vocus\.cc/$"  # 單反斜線，不是雙

    def test_page_and_query_kinds_split_correctly(self) -> None:
        cells = parse_legacy_cells(CONFIG_TEXT)
        page_cells = [c for c in cells if c.kind == "page"]
        query_cells = [c for c in cells if c.kind == "query"]
        assert len(page_cells) == 7 and len(query_cells) == 8
        assert all(c.search_type == "web" for c in page_cells + query_cells)

    def test_multi_type_uses_search_type_field_when_present(self) -> None:
        cells = parse_legacy_cells(CONFIG_TEXT)
        surfaces = {c.label: c.search_type for c in cells if c.kind == "surface"}
        assert surfaces["圖片"] == "image"
        assert surfaces["影片"] == "video"
        assert surfaces["新聞"] == "news"

    def test_multi_type_maps_discover_and_google_news_from_path(self) -> None:
        cells = parse_legacy_cells(CONFIG_TEXT)
        surfaces = {c.label: c.search_type for c in cells if c.kind == "surface"}
        assert surfaces["探索"] == "discover"
        assert surfaces["Google News"] == "googleNews"

    def test_surface_cells_have_no_dimension_or_pattern(self) -> None:
        cells = parse_legacy_cells(CONFIG_TEXT)
        for c in cells:
            if c.kind == "surface":
                assert c.dimension is None and c.pattern is None

    def test_cell_numbers_fall_back_to_default_when_cell_block_missing(self) -> None:
        cells = parse_legacy_cells(MISSING_CELL_CONFIG_TEXT)
        assert cells[0].cell == "G20"
        assert cells[15].cell == "G38"

    def test_missing_search_performance_block_raises(self) -> None:
        with pytest.raises(ConfigParseError, match="SEARCH_PERFORMANCE"):
            parse_legacy_cells("export const CELL = {\n  queryPage: 20,\n};\n")

    def test_wrong_query_page_count_raises(self) -> None:
        bad = CONFIG_TEXT.replace(
            '{ label: "必買", type: "query", pattern: "必買" },\n', ""
        )
        with pytest.raises(ConfigParseError, match="queryPage"):
            parse_legacy_cells(bad)

    def test_wrong_multi_type_count_raises(self) -> None:
        bad = CONFIG_TEXT.replace(
            '{ label: "Google News", path: "performance/google-news" },\n', ""
        )
        with pytest.raises(ConfigParseError, match="multiType"):
            parse_legacy_cells(bad)

    def test_multi_type_unknown_path_without_search_type_raises(self) -> None:
        bad = CONFIG_TEXT.replace(
            'path: "performance/discover"', 'path: "performance/unknown-surface"'
        )
        with pytest.raises(ConfigParseError, match="unknown-surface"):
            parse_legacy_cells(bad)

    def test_unknown_search_type_not_in_allowed_set_raises(self) -> None:
        bad = CONFIG_TEXT.replace('searchType: "image"', 'searchType: "pdf"')
        with pytest.raises(ConfigParseError, match="pdf"):
            parse_legacy_cells(bad)

    def test_empty_string_constant_raises(self) -> None:
        bad = CONFIG_TEXT.replace('label: "首頁"', 'label: ""')
        with pytest.raises(ConfigParseError):
            parse_legacy_cells(bad)


class TestLoadConfigText:
    def test_missing_file_raises_config_parse_error(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigParseError, match="找不到"):
            load_config_text(tmp_path / "nope.mjs")

    def test_reads_existing_file(self, tmp_path: Path) -> None:
        p = tmp_path / "config.mjs"
        p.write_text(CONFIG_TEXT, encoding="utf-8")
        assert "SEARCH_PERFORMANCE" in load_config_text(p)


# ══════════════════════════════════════════════════════════════════════
# 視窗計算
# ══════════════════════════════════════════════════════════════════════

class TestResolveWindow:
    def test_default_days_and_end_offset_matches_known_reverse_engineered_window(self) -> None:
        start, end = resolve_window(start=None, end=None, days=7, end_offset=3, run_date=date(2026, 9, 4))
        assert (start, end) == (date(2026, 8, 26), date(2026, 9, 1))

    def test_explicit_start_and_end_override(self) -> None:
        start, end = resolve_window(
            start="2026-01-01", end="2026-01-05", days=7, end_offset=3, run_date=date(2026, 9, 4)
        )
        assert (start, end) == (date(2026, 1, 1), date(2026, 1, 5))

    def test_only_start_without_end_raises(self) -> None:
        with pytest.raises(ValueError, match="同時提供"):
            resolve_window(start="2026-01-01", end=None, days=7, end_offset=3, run_date=date(2026, 9, 4))

    def test_only_end_without_start_raises(self) -> None:
        with pytest.raises(ValueError, match="同時提供"):
            resolve_window(start=None, end="2026-01-01", days=7, end_offset=3, run_date=date(2026, 9, 4))

    def test_start_after_end_raises(self) -> None:
        with pytest.raises(ValueError, match="晚於"):
            resolve_window(start="2026-01-05", end="2026-01-01", days=7, end_offset=3, run_date=date(2026, 9, 4))

    def test_days_less_than_one_raises(self) -> None:
        with pytest.raises(ValueError, match="days"):
            resolve_window(start=None, end=None, days=0, end_offset=3, run_date=date(2026, 9, 4))


# ══════════════════════════════════════════════════════════════════════
# request body 組法
# ══════════════════════════════════════════════════════════════════════

class TestBuildRequestBody:
    def test_page_cell_uses_including_regex_filter(self) -> None:
        cell = LegacyCell(cell="G20", label="首頁", kind="page", search_type="web",
                          dimension="page", pattern=r"^https://vocus\.cc/$")
        body = build_request_body(cell, date(2026, 8, 26), date(2026, 9, 1))
        assert body["type"] == "web"
        assert body["aggregationType"] == "auto"
        assert "dimensions" not in body
        assert body["dimensionFilterGroups"] == [{
            "filters": [{"dimension": "page", "operator": "includingRegex",
                        "expression": r"^https://vocus\.cc/$"}]
        }]
        assert (body["startDate"], body["endDate"]) == ("2026-08-26", "2026-09-01")

    def test_surface_cell_has_no_filter_group(self) -> None:
        cell = LegacyCell(cell="G41", label="探索", kind="surface", search_type="discover",
                          dimension=None, pattern=None)
        body = build_request_body(cell, date(2026, 8, 26), date(2026, 9, 1))
        assert body["type"] == "discover"
        assert "dimensionFilterGroups" not in body
        assert "dimensions" not in body

    def test_equals_operator_override(self) -> None:
        cell = LegacyCell(cell="G33", label="保養", kind="query", search_type="web",
                          dimension="query", pattern="保養")
        body = build_request_body(cell, date(2026, 8, 26), date(2026, 9, 1), operator="equals")
        assert body["dimensionFilterGroups"][0]["filters"][0]["operator"] == "equals"


class TestExtractClicks:
    def test_returns_zero_when_no_rows(self) -> None:
        assert extract_clicks({"rows": []}) == 0
        assert extract_clicks({}) == 0

    def test_rounds_float_clicks_to_int(self) -> None:
        assert extract_clicks({"rows": [{"clicks": 8592.0, "impressions": 1.0}]}) == 8592

    def test_rounds_half_up_like_ui_card(self) -> None:
        assert extract_clicks({"rows": [{"clicks": 419.6}]}) == 420


# ══════════════════════════════════════════════════════════════════════
# 重試 / 致命分類
# ══════════════════════════════════════════════════════════════════════

CELL = LegacyCell(cell="G20", label="首頁", kind="page", search_type="web",
                  dimension="page", pattern=r"^https://vocus\.cc/$")


class TestQueryCellRetry:
    def test_success_on_first_try(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            return 200, json.dumps({"rows": [{"clicks": 100.0}]})

        monkeypatch.setattr(mod, "_post_json", fake_post)
        assert query_cell("tok", CELL, date(2026, 8, 26), date(2026, 9, 1)) == 100
        assert len(calls) == 1

    def test_retries_on_429_then_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            if len(calls) == 1:
                return 429, "rate limited"
            return 200, json.dumps({"rows": [{"clicks": 50.0}]})

        monkeypatch.setattr(mod, "_post_json", fake_post)
        monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
        assert query_cell("tok", CELL, date(2026, 8, 26), date(2026, 9, 1)) == 50
        assert len(calls) == 2

    @pytest.mark.parametrize("status", [408, 500, 502, 503, 504])
    def test_5xx_and_408_are_retryable(self, status: int, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            if len(calls) == 1:
                return status, "unavailable"
            return 200, json.dumps({"rows": [{"clicks": 1.0}]})

        monkeypatch.setattr(mod, "_post_json", fake_post)
        monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
        assert query_cell("tok", CELL, date(2026, 8, 26), date(2026, 9, 1)) == 1
        assert len(calls) == 2

    def test_exhausted_retries_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            return 503, "unavailable"

        monkeypatch.setattr(mod, "_post_json", fake_post)
        monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
        with pytest.raises(LegacyExportError, match="503"):
            query_cell("tok", CELL, date(2026, 8, 26), date(2026, 9, 1))
        assert len(calls) == MAX_ATTEMPTS

    def test_non_retryable_400_fails_immediately(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            return 400, "bad request"

        monkeypatch.setattr(mod, "_post_json", fake_post)
        monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
        with pytest.raises(LegacyExportError, match="400"):
            query_cell("tok", CELL, date(2026, 8, 26), date(2026, 9, 1))
        assert len(calls) == 1

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_errors_are_fatal_and_not_retried(self, status: int, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            return status, '{"error": {"message": "forbidden"}}'

        monkeypatch.setattr(mod, "_post_json", fake_post)
        monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
        with pytest.raises(LegacyExportError, match="不可重試"):
            query_cell("tok", CELL, date(2026, 8, 26), date(2026, 9, 1))
        assert len(calls) == 1

    def test_daily_quota_exceeded_429_is_fatal_and_not_retried(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []
        body = json.dumps({"error": {"errors": [{"reason": "dailyLimitExceeded",
                                                  "message": "Daily Limit Exceeded"}]}})

        def fake_post(url, req_body, headers, timeout):
            calls.append(1)
            return 429, body

        monkeypatch.setattr(mod, "_post_json", fake_post)
        monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
        with pytest.raises(LegacyExportError, match="不可重試"):
            query_cell("tok", CELL, date(2026, 8, 26), date(2026, 9, 1))
        assert len(calls) == 1

    def test_plain_rate_limit_429_still_retries_to_the_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, req_body, headers, timeout):
            calls.append(1)
            return 429, '{"error": {"message": "too many requests"}}'

        monkeypatch.setattr(mod, "_post_json", fake_post)
        monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
        with pytest.raises(LegacyExportError) as exc_info:
            query_cell("tok", CELL, date(2026, 8, 26), date(2026, 9, 1))
        assert "不可重試" not in str(exc_info.value)
        assert len(calls) == MAX_ATTEMPTS

    def test_backoff_table_matches_attempt_count(self) -> None:
        assert len(RETRY_BACKOFF_SECONDS) == MAX_ATTEMPTS - 1


# ══════════════════════════════════════════════════════════════════════
# 輸出
# ══════════════════════════════════════════════════════════════════════

class TestWriteOutputs:
    def _row(self, cell: str, label: str, clicks: int) -> ResultRow:
        legacy_cell = LegacyCell(cell=cell, label=label, kind="page", search_type="web",
                                 dimension="page", pattern="/x")
        return ResultRow(cell=legacy_cell, start=date(2026, 8, 26), end=date(2026, 9, 1), clicks=clicks)

    def test_writes_json_and_csv(self, tmp_path: Path) -> None:
        rows = [self._row("G20", "首頁", 8592), self._row("G21", "/article/", 420757)]
        json_path, csv_path = write_outputs(rows, tmp_path, date(2026, 9, 1))
        assert json_path.name == "2026-09-01.json"
        assert csv_path.name == "2026-09-01.csv"

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["start"] == "2026-08-26"
        assert payload["end"] == "2026-09-01"
        assert len(payload["cells"]) == 2
        assert payload["cells"][0]["clicks"] == 8592
        assert payload["controls"] == []

        csv_text = csv_path.read_text(encoding="utf-8")
        header = csv_text.splitlines()[0]
        assert header == ",".join(CSV_FIELDS)
        assert "G20" in csv_text and "8592" in csv_text

    def test_controls_appear_only_in_json_not_csv(self, tmp_path: Path) -> None:
        rows = [self._row("G33", "保養", 3)]
        control_cell = LegacyCell(cell="G33", label="保養", kind="query", search_type="web",
                                  dimension="query", pattern="保養")
        controls = [ResultRow(cell=control_cell, start=date(2026, 8, 26), end=date(2026, 9, 1),
                              clicks=114, operator="equals")]
        json_path, csv_path = write_outputs(rows, tmp_path, date(2026, 9, 1), controls=controls)

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(payload["controls"]) == 1
        assert payload["controls"][0]["operator"] == "equals"
        assert payload["controls"][0]["clicks"] == 114

        csv_text = csv_path.read_text(encoding="utf-8")
        assert "114" not in csv_text

    def test_creates_out_dir_if_missing(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "nested" / "legacy-cells"
        json_path, _ = write_outputs([self._row("G20", "首頁", 1)], out_dir, date(2026, 9, 1))
        assert json_path.exists()


# ══════════════════════════════════════════════════════════════════════
# run_export / run_equals_control
# ══════════════════════════════════════════════════════════════════════

class TestRunExport:
    def test_dry_run_does_not_call_token_provider_or_query(self, monkeypatch: pytest.MonkeyPatch,
                                                            capsys: pytest.CaptureFixture) -> None:
        calls: list[str] = []
        monkeypatch.setattr(mod, "query_cell", lambda *a, **k: calls.append("query") or 0)
        results = run_export(cells=[CELL], start=date(2026, 8, 26), end=date(2026, 9, 1),
                             execute=False, token_provider=lambda: calls.append("token") or "tok")
        assert calls == []
        assert results[0].clicks is None
        assert "[dry-run]" in capsys.readouterr().out

    def test_execute_calls_query_cell_and_prints_clicks(self, monkeypatch: pytest.MonkeyPatch,
                                                         capsys: pytest.CaptureFixture) -> None:
        monkeypatch.setattr(mod, "query_cell", lambda *a, **k: 8592)
        results = run_export(cells=[CELL], start=date(2026, 8, 26), end=date(2026, 9, 1),
                             execute=True, token_provider=lambda: "tok")
        assert results[0].clicks == 8592
        out = capsys.readouterr().out
        assert "G20 首頁 8592" in out


class TestRunEqualsControl:
    def test_matches_label_and_uses_equals_operator(self, monkeypatch: pytest.MonkeyPatch) -> None:
        care_cell = LegacyCell(cell="G33", label="保養", kind="query", search_type="web",
                               dimension="query", pattern="保養")
        seen_operators: list[str] = []

        def fake_query_cell(token, cell, start, end, *, operator="includingRegex"):
            seen_operators.append(operator)
            return 114

        monkeypatch.setattr(mod, "query_cell", fake_query_cell)
        controls = run_equals_control(cells=[care_cell], labels=["保養"],
                                      start=date(2026, 8, 26), end=date(2026, 9, 1),
                                      token_provider=lambda: "tok")
        assert controls[0].clicks == 114
        assert seen_operators == ["equals"]

    def test_unknown_label_raises(self) -> None:
        with pytest.raises(ValueError, match="不到"):
            run_equals_control(cells=[CELL], labels=["不存在的標籤"],
                               start=date(2026, 8, 26), end=date(2026, 9, 1),
                               token_provider=lambda: "tok")

    def test_surface_cell_label_rejected(self) -> None:
        surface_cell = LegacyCell(cell="G41", label="探索", kind="surface", search_type="discover",
                                  dimension=None, pattern=None)
        with pytest.raises(ValueError, match="不到"):
            run_equals_control(cells=[surface_cell], labels=["探索"],
                               start=date(2026, 8, 26), end=date(2026, 9, 1),
                               token_provider=lambda: "tok")


# ══════════════════════════════════════════════════════════════════════
# 額外邊界分支：_js_string、_parse_cell_start、write_outputs 空清單
# ══════════════════════════════════════════════════════════════════════

class TestJsStringAndCellStartEdgeCases:
    def test_query_page_invalid_type_with_correct_count_raises(self) -> None:
        """數量對（15 筆）但某筆 type 不是 page/query——單獨測，跟『數量不對』分開。"""
        bad = CONFIG_TEXT.replace(
            '{ label: "股", type: "query", pattern: "股" },',
            '{ label: "股", type: "unknown", pattern: "股" },',
        )
        with pytest.raises(ConfigParseError, match="未知 type"):
            parse_legacy_cells(bad)

    def test_cell_block_present_but_key_missing_falls_back_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        text = CONFIG_TEXT.replace("  multiType: 38,\n", "")
        with caplog.at_level("WARNING"):
            cells = parse_legacy_cells(text)
        assert cells[0].cell == "G20"       # queryPage 鍵還在，照常解析
        assert cells[15].cell == "G38"      # multiType 鍵不見了，用預設值 38
        assert any("multiType" in r.message for r in caplog.records)

    def test_malformed_string_escape_raises_config_parse_error(self) -> None:
        from scripts.export_legacy_gsc_cells import _js_string
        with pytest.raises(ConfigParseError, match="無法解析"):
            _js_string('unterminated \\')


class TestWriteOutputsEmptyResults:
    def test_empty_results_writes_null_start(self, tmp_path: Path) -> None:
        json_path, csv_path = write_outputs([], tmp_path, date(2026, 9, 1))
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["start"] is None
        assert payload["cells"] == []
        # 只有表頭，沒有資料列
        assert len(csv_path.read_text(encoding="utf-8").splitlines()) == 1


# ══════════════════════════════════════════════════════════════════════
# _post_json —— 真的打 urllib（不繞過 module-level 函式本身）
# ══════════════════════════════════════════════════════════════════════

class _FakeResponse:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body.encode()

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None


class TestPostJson:
    def test_returns_status_and_body_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict = {}

        def fake_urlopen(request, timeout=None):
            captured["method"] = request.method
            captured["auth"] = request.headers.get("Authorization")
            return _FakeResponse(200, '{"rows": []}')

        monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
        status, body = mod._post_json("https://api.test/x", {"a": 1}, {"Authorization": "Bearer k"}, 5)
        assert (status, body) == (200, '{"rows": []}')
        assert captured["method"] == "POST" and captured["auth"] == "Bearer k"

    def test_http_error_returned_not_raised(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error as urlerror

        error = urlerror.HTTPError("u", 429, "too many", {}, None)
        error.read = lambda: b"rate limited"  # type: ignore[method-assign]

        def fake_urlopen(request, timeout=None):
            raise error

        monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
        status, body = mod._post_json("https://api.test/x", {}, {}, 5)
        assert status == 429 and "rate limited" in body

    def test_url_error_becomes_legacy_export_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error as urlerror

        def fake_urlopen(request, timeout=None):
            raise urlerror.URLError("dns fail")

        monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(LegacyExportError, match="連線失敗"):
            mod._post_json("https://api.test/x", {}, {}, 5)


# ══════════════════════════════════════════════════════════════════════
# main() CLI —— dry-run／錯誤路徑／--execute（monkeypatch 掉真的 API 呼叫）
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    p = tmp_path / "config.mjs"
    p.write_text(CONFIG_TEXT, encoding="utf-8")
    return p


class TestMainCli:
    def test_dry_run_happy_path_exits_zero(self, monkeypatch: pytest.MonkeyPatch, config_path: Path) -> None:
        argv = ["prog", "--config", str(config_path), "--start", "2026-08-26", "--end", "2026-09-01"]
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 0

    def test_config_parse_error_exits_two(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        argv = ["prog", "--config", str(tmp_path / "missing.mjs")]
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 2

    def test_invalid_window_args_exit_two(self, monkeypatch: pytest.MonkeyPatch, config_path: Path) -> None:
        argv = ["prog", "--config", str(config_path), "--start", "2026-08-26"]  # 缺 --end
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 2

    def test_legacy_export_error_exits_one(self, monkeypatch: pytest.MonkeyPatch, config_path: Path) -> None:
        monkeypatch.setattr(mod, "run_export", lambda **k: (_ for _ in ()).throw(LegacyExportError("boom")))
        argv = ["prog", "--config", str(config_path), "--start", "2026-08-26", "--end", "2026-09-01"]
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 1

    def test_execute_writes_outputs_and_runs_equals_control(self, monkeypatch: pytest.MonkeyPatch,
                                                             config_path: Path, tmp_path: Path) -> None:
        fake_cell = LegacyCell(cell="G20", label="首頁", kind="page", search_type="web",
                               dimension="page", pattern=r"^https://vocus\.cc/$")
        fake_row = ResultRow(cell=fake_cell, start=date(2026, 8, 26), end=date(2026, 9, 1), clicks=8592)
        control_calls: list[list[str]] = []

        monkeypatch.setattr(mod, "run_export", lambda **k: [fake_row])

        def fake_run_equals_control(*, cells, labels, start, end, token_provider=None):
            control_calls.append(list(labels))
            control_cell = LegacyCell(cell="G33", label="保養", kind="query", search_type="web",
                                      dimension="query", pattern="保養")
            return [ResultRow(cell=control_cell, start=start, end=end, clicks=114, operator="equals")]

        monkeypatch.setattr(mod, "run_equals_control", fake_run_equals_control)

        out_dir = tmp_path / "out"
        argv = ["prog", "--config", str(config_path), "--start", "2026-08-26", "--end", "2026-09-01",
                "--execute", "--out-dir", str(out_dir), "--equals-control", "保養"]
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 0
        assert control_calls == [["保養"]]

        json_path = out_dir / "2026-09-01.json"
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["cells"][0]["clicks"] == 8592
        assert payload["controls"][0]["clicks"] == 114
