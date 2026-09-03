"""Tests for gsc_surfaces.py —— surface × 維度組合設定、position 規則、totals 逐列驗證。

test_ingest_gsc_search_analytics.py 已經透過主腳本重新匯出的名稱間接跑過本模組的
`row_to_record`／`_validate_metrics`／`combo_filter`／`dedupe_by_key`（哨兵值、判別式、
分頁去重那一大塊）。本檔補三塊主腳本測試沒碰的：(1) SURFACE_COMBOS／NO_RANKING_SURFACES
的設定本身是否自洽、與 022 的 search_type_ck 值域一致；(2) position 規則對六種
surface×position 組合的完整矩陣；(3) `totals_record`／`build_totals_records`——
gsc_daily_totals 的欄位映射與去重，這條在主腳本測試裡只被間接呼叫過。
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.gsc_surfaces import (  # noqa: E402
    ALLOWED_SEARCH_TYPES,
    COMBO_DIMENSIONS,
    COMBO_PAGE,
    COMBO_QUERY,
    DEFAULT_SEARCH_TYPE,
    NO_RANKING_SURFACES,
    PROPERTY,
    REJECT_POSITION_NO_RANKING,
    REJECT_POSITION_RANKED,
    SURFACE_COMBOS,
    TOTALS_CONFLICT_FIELDS,
    _validate_metrics,
    build_totals_records,
    dedupe_by_key,
    is_position_valid,
    position_reject_reason,
    totals_record,
)

DAY = date(2026, 8, 25)


def _probe_row(day: date, *, clicks: int = 5, impressions: int = 20,
                position: float = 3.0, ctr: float | None = None) -> dict:
    return {"keys": [day.isoformat()], "clicks": clicks, "impressions": impressions,
            "ctr": clicks / impressions if ctr is None and impressions else (ctr or 0.0),
            "position": position}


# ══════════════════════════════════════════════════════════════════════
# (a) SURFACE_COMBOS／ALLOWED_SEARCH_TYPES 設定本身自洽、與 022 值域一致
# ══════════════════════════════════════════════════════════════════════

class TestSurfaceCombosConfiguration:
    @pytest.mark.parametrize("surface", list(SURFACE_COMBOS))
    def test_every_combo_is_a_known_dimension_combo(self, surface: str) -> None:
        for combo in SURFACE_COMBOS[surface]:
            assert combo in COMBO_DIMENSIONS

    def test_googlenews_has_page_combo_only(self) -> None:
        """googleNews 帶 query 維度送出去必定整個 run 400，只能是 page 組。"""
        assert SURFACE_COMBOS["googleNews"] == (COMBO_PAGE,)

    def test_discover_has_no_combos(self) -> None:
        """2026-09-03 live run（S2.5）：discover 連 page 組（帶 device 維度）也回 400
        `Requests for Discover cannot be grouped by device`——比 googleNews 更窄，
        SURFACE_COMBOS 對它是空 tuple，只收 gsc_daily_totals。"""
        assert SURFACE_COMBOS["discover"] == ()

    def test_no_ranking_surfaces_combos_are_a_subset_of_googlenews(self) -> None:
        """NO_RANKING_SURFACES 兩個成員的 combos 都不含 query 組（不論是否為空）。"""
        for surface in sorted(NO_RANKING_SURFACES):
            assert COMBO_QUERY not in SURFACE_COMBOS[surface]

    @pytest.mark.parametrize("surface", sorted(set(SURFACE_COMBOS) - NO_RANKING_SURFACES))
    def test_ranking_surfaces_have_both_combos(self, surface: str) -> None:
        assert SURFACE_COMBOS[surface] == (COMBO_PAGE, COMBO_QUERY)

    def test_allowed_search_types_matches_022_search_type_ck_domain(self) -> None:
        """022 的 gsc_daily_metrics_search_type_ck／gsc_daily_totals_search_type_ck：
        CHECK (search_type IN ('web','image','video','news','googleNews','discover'))。"""
        assert set(ALLOWED_SEARCH_TYPES) == {
            "web", "image", "video", "news", "googleNews", "discover",
        }

    def test_default_search_type_is_allowed(self) -> None:
        assert DEFAULT_SEARCH_TYPE in ALLOWED_SEARCH_TYPES

    def test_no_ranking_surfaces_are_a_subset_of_allowed_search_types(self) -> None:
        assert NO_RANKING_SURFACES <= set(ALLOWED_SEARCH_TYPES)


# ══════════════════════════════════════════════════════════════════════
# (b) is_position_valid／_validate_metrics —— surface-aware 的 position 規則
# ══════════════════════════════════════════════════════════════════════

class TestIsPositionValid:
    @pytest.mark.parametrize("search_type, position, expected", [
        ("web", 0.0, False),          # 015 position_ck 要擋的那個形狀：0-based sum_position 忘了 +1
        ("web", 1.0, True),
        ("googleNews", 0.0, True),    # 022 例外：這個 surface 沒有排名概念，0 是忠實的 API 原值
        ("googleNews", 0.5, False),   # 落在 (0,1) 開區間——仍是那個壞形狀，不因 surface 放行
        ("googleNews", 3.0, True),
        ("discover", 0.0, True),      # 與 googleNews 同一條規則
        ("discover", 0.5, False),
        ("discover", 3.0, True),
        ("news", 0.0, False),         # news 有排名概念，不在 NO_RANKING_SURFACES，0 仍要擋
    ])
    def test_matches_022_conditional_position_ck(
        self, search_type: str, position: float, expected: bool
    ) -> None:
        assert is_position_valid(search_type, position) is expected


class TestPositionRejectReason:
    def test_ranked_surface_keeps_existing_label(self) -> None:
        """既有 log 在看這個字串，改了下游解析會斷。"""
        assert position_reject_reason("web") == REJECT_POSITION_RANKED == "position<1"

    @pytest.mark.parametrize("surface", sorted(NO_RANKING_SURFACES))
    def test_no_ranking_surface_gets_distinct_label(self, surface: str) -> None:
        assert position_reject_reason(surface) == REJECT_POSITION_NO_RANKING


class TestValidateMetricsSurfaceAware:
    @pytest.mark.parametrize("search_type, position, should_pass", [
        ("web", 0.0, False),
        ("googleNews", 0.0, True),
        ("googleNews", 0.5, False),
        ("discover", 0.0, True),
    ])
    def test_position_rule_is_surface_aware(
        self, search_type: str, position: float, should_pass: bool
    ) -> None:
        rejects: dict[str, int] = {}
        row = {"clicks": 1, "impressions": 10, "ctr": 0.1, "position": position}
        result = _validate_metrics(row, rejects, search_type=search_type)
        assert (result is not None) is should_pass
        if not should_pass:
            assert any("position" in reason for reason in rejects)

    def test_default_search_type_is_the_strictest_side(self) -> None:
        """漏傳 search_type 只會多擋、不會放行髒資料——預設值是 'web'（有排名概念）。"""
        rejects: dict[str, int] = {}
        assert _validate_metrics({"clicks": 1, "impressions": 10, "ctr": 0.1, "position": 0.0},
                                  rejects) is None

    def test_non_numeric_metric_field_is_rejected_not_crashed(self) -> None:
        """探測回應少一個 metric 欄位、或欄位變成字串時，記一筆、跳過該列，不炸整個 run。"""
        rejects: dict[str, int] = {}
        row = {"clicks": "N/A", "impressions": 10, "ctr": 0.1, "position": 3.0}
        assert _validate_metrics(row, rejects, search_type="web") is None
        assert "metric 欄位缺漏或非數值" in rejects

    def test_missing_metric_field_uses_default_and_may_still_fail_other_checks(self) -> None:
        """完全缺欄位時用 .get 預設值，不是 non-numeric 那條 except 路徑。"""
        rejects: dict[str, int] = {}
        assert _validate_metrics({}, rejects, search_type="web") is None
        assert "impressions<=0" in rejects


# ══════════════════════════════════════════════════════════════════════
# (d) totals_record／build_totals_records —— gsc_daily_totals 的欄位映射與去重
# ══════════════════════════════════════════════════════════════════════

class TestTotalsRecord:
    def test_maps_probe_row_to_totals_fields(self) -> None:
        rejects: dict[str, int] = {}
        record = totals_record(_probe_row(DAY), search_type="web", rejects=rejects)
        assert rejects == {}
        assert record == {
            "date": DAY.isoformat(), "property": PROPERTY, "search_type": "web",
            "clicks": 5, "impressions": 20, "ctr": 0.25, "position": 3.0,
        }

    def test_has_no_page_query_device_country_fields(self) -> None:
        """totals 的 unique key 只有三欄，沒有哨兵問題——結果不該帶那些欄位。"""
        record = totals_record(_probe_row(DAY), search_type="web", rejects={})
        assert set(record) == {"date", "property", "search_type", "clicks",
                                "impressions", "ctr", "position"}

    def test_google_news_position_zero_passes_through(self) -> None:
        """走同一套 _validate_metrics，googleNews／discover 的 position=0 一樣通過。"""
        row = _probe_row(DAY, position=0.0)
        record = totals_record(row, search_type="googleNews", rejects={})
        assert record is not None and record["position"] == 0.0

    def test_keys_length_not_one_is_rejected(self) -> None:
        rejects: dict[str, int] = {}
        row = {"keys": [DAY.isoformat(), "extra"], "clicks": 1, "impressions": 1,
               "ctr": 1.0, "position": 1.0}
        assert totals_record(row, search_type="web", rejects=rejects) is None
        assert "探測列 keys 長度不是 1" in rejects

    def test_missing_keys_is_rejected(self) -> None:
        rejects: dict[str, int] = {}
        row = {"clicks": 1, "impressions": 1, "ctr": 1.0, "position": 1.0}
        assert totals_record(row, search_type="web", rejects=rejects) is None
        assert "探測列 keys 長度不是 1" in rejects

    def test_unparsable_date_is_rejected(self) -> None:
        rejects: dict[str, int] = {}
        row = {"keys": ["not-a-date"], "clicks": 1, "impressions": 1, "ctr": 1.0, "position": 1.0}
        assert totals_record(row, search_type="web", rejects=rejects) is None
        assert "探測列日期無法解析" in rejects

    def test_invalid_metrics_are_rejected_via_shared_validation(self) -> None:
        rejects: dict[str, int] = {}
        row = _probe_row(DAY, impressions=0, ctr=0.0)
        assert totals_record(row, search_type="web", rejects=rejects) is None
        assert "impressions<=0" in rejects


class TestBuildTotalsRecords:
    def test_empty_rows_returns_empty(self) -> None:
        assert build_totals_records([], search_type="web", warnings=[]) == []

    def test_distinct_dates_are_all_kept(self) -> None:
        rows = [_probe_row(DAY), _probe_row(date(2026, 8, 24))]
        records = build_totals_records(rows, search_type="web", warnings=[])
        assert len(records) == 2

    def test_dedupe_by_property_search_type_date(self) -> None:
        """(property, search_type, date) 撞鍵時保留最後一筆——與 dedupe_by_key 的既有語意一致。
        clicks 上限是 impressions（20），兩筆都要合法才是在測 dedupe 而不是驗證。"""
        rows = [_probe_row(DAY, clicks=1), _probe_row(DAY, clicks=15)]
        records = build_totals_records(rows, search_type="web", warnings=[])
        assert len(records) == 1 and records[0]["clicks"] == 15
        assert TOTALS_CONFLICT_FIELDS == ("property", "search_type", "date")

    def test_rejected_rows_are_recorded_as_warnings_not_dropped_silently(self) -> None:
        rows = [_probe_row(DAY), {"keys": ["bad-date"], "clicks": 1, "impressions": 1,
                                   "ctr": 1.0, "position": 1.0}]
        warnings: list[str] = []
        records = build_totals_records(rows, search_type="web", warnings=warnings)
        assert len(records) == 1
        assert len(warnings) == 1 and "totals/web" in warnings[0]

    def test_no_warnings_when_everything_is_valid(self) -> None:
        warnings: list[str] = []
        build_totals_records([_probe_row(DAY)], search_type="web", warnings=warnings)
        assert warnings == []

    def test_different_search_types_are_independent_keys(self) -> None:
        """totals 的 unique key 含 search_type——同一天 web 與 googleNews 不該互相覆蓋。"""
        web_records = build_totals_records([_probe_row(DAY)], search_type="web", warnings=[])
        news_records = build_totals_records([_probe_row(DAY, position=0.0)],
                                            search_type="googleNews", warnings=[])
        assert web_records[0]["search_type"] == "web"
        assert news_records[0]["search_type"] == "googleNews"


class TestDedupeByKeyWithTotalsFields:
    def test_uses_three_field_key_when_given_totals_fields(self) -> None:
        a = {"property": PROPERTY, "search_type": "web", "date": DAY.isoformat(), "clicks": 1}
        b = {"property": PROPERTY, "search_type": "web", "date": DAY.isoformat(), "clicks": 2}
        result = dedupe_by_key([a, b], TOTALS_CONFLICT_FIELDS)
        assert len(result) == 1 and result[0]["clicks"] == 2
