"""Tests for ingest_gsc_url_inspection.py.

重點覆蓋六件本腳本特有、且錯了不會有訊號的事：

1. **配額守門** —— 本地滾動視窗分類帳、達閾值即停止且視為成功、即時 429 中途停止也是成功。
2. **抽樣三層優先序** —— 對照組固定不變（hash 排序）、零曝光新舊頁分層、tags 被排除。
3. **sitemap 抓取** —— index → 子 sitemap 的兩層抓取、部分失敗容忍、全部失敗才是硬失敗。
4. **indexing_state 值域** —— 未知值進 errors（不是 warnings），coverage_state 只驗長度。
5. **0 筆的三種樣貌** —— 母體全空＝失敗；配額不足或中途配額用盡＝成功。
6. **新鮮度門檻** —— 無 GSC 固有延遲，但配額擠占可能連續數天零寫入，門檻要容忍這個情境。
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.error
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ingest_gsc_url_inspection import (  # noqa: E402
    CONTROL_SET_SIZE,
    DEFAULT_QUOTA_BUDGET,
    DEFAULT_SAMPLE_SIZE,
    FRESHNESS_MAX_AGE_HOURS,
    INDEXING_STATE_ALLOWED,
    MAX_SAMPLE_SIZE,
    PROPERTY,
    QUOTA_HARD_CEILING,
    QUOTA_LEDGER_TABLE_NAME,
    RECENT_THRESHOLD_DAYS,
    TABLE_RUN,
    TABLE_URL_INSPECTION,
    GscQueryError,
    QuotaExhaustedError,
    SitemapFetchError,
    _attach_last_crawl,
    _finalize_run,
    _http_get_xml,
    _inspect_post,
    _quota_gate,
    build_control_set,
    build_sample,
    classify_sub_sitemap,
    collect_inspections,
    count_url_inspection_rows,
    fetch_pages_with_any_impressions,
    fetch_sitemap_pool,
    finish_url_inspection_run,
    inspect_url,
    latest_inspected_at,
    list_sub_sitemaps,
    list_url_entries,
    main,
    quota_used_last_24h,
    record_quota_usage,
    resolve_quota_budget,
    resolve_sample_size,
    result_to_record,
    run_freshness_check,
    run_ingestion,
    run_verify,
    split_zero_impression_tiers,
    start_url_inspection_run,
    upsert_url_inspections,
)

MODULE = "scripts.ingest_gsc_url_inspection"
UTC = timezone.utc
TODAY = date(2026, 9, 2)
INSPECTED_AT = "2026-09-02T00:00:00Z"
SUPABASE_ENV = {"SUPABASE_URL": "https://db.example/", "SUPABASE_SERVICE_KEY": "k"}


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


def _index_status(
    *, indexing_state: str = "INDEXING_ALLOWED", coverage_state: str = "Crawled - currently not indexed",
    last_crawl: str | None = None,
) -> dict:
    result: dict = {"coverageState": coverage_state, "indexingState": indexing_state}
    if last_crawl:
        result["lastCrawlTime"] = last_crawl
    return result


def _sitemap_index_xml(sub_urls: list[str]) -> str:
    sitemaps = "".join(f"<sitemap><loc>{u}</loc></sitemap>" for u in sub_urls)
    return (f'<?xml version="1.0"?><sitemapindex '
            f'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sitemaps}</sitemapindex>')


def _urlset_xml(entries: list[tuple[str, str | None]]) -> str:
    urls = "".join(
        f"<url><loc>{u}</loc>{f'<lastmod>{lm}</lastmod>' if lm else ''}</url>" for u, lm in entries
    )
    return (f'<?xml version="1.0"?><urlset '
            f'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')


# ══════════════════════════════════════════════════════════════════════
# URL Inspection API 呼叫與 429 分流
# ══════════════════════════════════════════════════════════════════════

class TestInspectPost:
    def test_success_returns_parsed_json(self) -> None:
        response = _FakeResponse('{"inspectionResult": {"indexStatusResult": {"indexingState": "INDEXING_ALLOWED"}}}')
        with patch("urllib.request.urlopen", return_value=response):
            assert _inspect_post("token", "https://vocus.cc/a") == {
                "inspectionResult": {"indexStatusResult": {"indexingState": "INDEXING_ALLOWED"}}
            }

    def test_429_becomes_quota_exhausted_not_generic_error(self) -> None:
        """規則 (a) 的分流起點：429 要能被上層識別為配額停止，不是系統性中止。"""
        with patch("urllib.request.urlopen", side_effect=_http_error(429, "quota")):
            with pytest.raises(QuotaExhaustedError):
                _inspect_post("token", "https://vocus.cc/a")

    def test_401_becomes_generic_gsc_query_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_http_error(401, "no access")):
            with pytest.raises(GscQueryError) as excinfo:
                _inspect_post("token", "https://vocus.cc/a")
        assert not isinstance(excinfo.value, QuotaExhaustedError)

    def test_url_error_becomes_gsc_query_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            with pytest.raises(GscQueryError):
                _inspect_post("token", "https://vocus.cc/a")


class TestInspectUrl:
    def test_extracts_index_status_result(self) -> None:
        payload = {"inspectionResult": {"indexStatusResult": {"indexingState": "INDEXING_ALLOWED"}}}
        with patch(f"{MODULE}._inspect_post", return_value=payload):
            assert inspect_url("token", "https://vocus.cc/a")["indexingState"] == "INDEXING_ALLOWED"

    def test_missing_index_status_result_is_empty_dict(self) -> None:
        """Google 從未見過的 URL：inspectionResult 存在但沒有 indexStatusResult。"""
        with patch(f"{MODULE}._inspect_post", return_value={"inspectionResult": {}}):
            assert inspect_url("token", "https://vocus.cc/never-seen") == {}


# ══════════════════════════════════════════════════════════════════════
# indexing_state 值域 —— 未知值是 errors，不是 warnings
# ══════════════════════════════════════════════════════════════════════

class TestIndexingStateEnum:
    def test_matches_migration_015_enum(self) -> None:
        assert INDEXING_STATE_ALLOWED == {
            "INDEXING_STATE_UNSPECIFIED", "INDEXING_ALLOWED", "BLOCKED_BY_META_TAG",
            "BLOCKED_BY_HTTP_HEADER", "BLOCKED_BY_ROBOTS_TXT",
        }


class TestResultToRecord:
    def test_maps_valid_result(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        record = result_to_record(
            "https://vocus.cc/a", _index_status(), inspected_at=INSPECTED_AT,
            errors=errors, warnings=warnings,
        )
        assert record == {
            "property": PROPERTY, "url": "https://vocus.cc/a", "inspected_at": INSPECTED_AT,
            "coverage_state": "Crawled - currently not indexed", "indexing_state": "INDEXING_ALLOWED",
            "ingested_at": INSPECTED_AT, "last_crawl": None,
        }
        assert not errors and not warnings

    def test_empty_index_status_is_a_warning_not_an_error(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        assert result_to_record("https://vocus.cc/a", {}, inspected_at=INSPECTED_AT,
                                errors=errors, warnings=warnings) is None
        assert not errors and warnings

    def test_unknown_indexing_state_is_an_error_not_a_warning(self) -> None:
        """migration 015 的原文：新分類需要人看一眼，不能靜默丟進 unknown 桶。"""
        errors: list[str] = []
        warnings: list[str] = []
        status = _index_status(indexing_state="INDEXING_STATE_BRAND_NEW")
        assert result_to_record("https://vocus.cc/a", status, inspected_at=INSPECTED_AT,
                                errors=errors, warnings=warnings) is None
        assert errors and not warnings
        assert "INDEXING_STATE_BRAND_NEW" in errors[0]

    def test_oversized_coverage_state_is_a_warning(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        status = _index_status(coverage_state="x" * 201)
        assert result_to_record("https://vocus.cc/a", status, inspected_at=INSPECTED_AT,
                                errors=errors, warnings=warnings) is None
        assert warnings and not errors

    def test_empty_coverage_state_is_a_warning(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        status = _index_status(coverage_state="")
        assert result_to_record("https://vocus.cc/a", status, inspected_at=INSPECTED_AT,
                                errors=errors, warnings=warnings) is None
        assert warnings

    def test_malformed_url_is_a_warning(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        assert result_to_record("not-a-url", _index_status(), inspected_at=INSPECTED_AT,
                                errors=errors, warnings=warnings) is None
        assert warnings


class TestAttachLastCrawl:
    """live 事故（run 33609190700）：省略 last_crawl 鍵導致同批物件鍵集合不一致，
    PostgREST 回 PGRST102 "All object keys must match"，20 筆全滅。修法是缺席時
    明確填 None，鍵永遠存在——以下測試釘住「鍵永遠在」這件事，不只測值。"""

    def test_valid_last_crawl_is_attached(self) -> None:
        record: dict = {}
        _attach_last_crawl(record, "2026-08-20T10:00:00Z", INSPECTED_AT, "https://vocus.cc/a", [])
        assert record["last_crawl"] == "2026-08-20T10:00:00Z"

    def test_missing_last_crawl_key_is_still_present_as_none(self) -> None:
        record: dict = {}
        _attach_last_crawl(record, None, INSPECTED_AT, "https://vocus.cc/a", [])
        assert "last_crawl" in record
        assert record["last_crawl"] is None

    def test_last_crawl_after_inspection_is_dropped_to_none_not_omitted(self) -> None:
        """CHECK last_crawl <= inspected_at：Google 不可能在查詢之後才抓取。"""
        record: dict = {}
        warnings: list[str] = []
        _attach_last_crawl(record, "2099-01-01T00:00:00Z", INSPECTED_AT, "https://vocus.cc/a", warnings)
        assert "last_crawl" in record
        assert record["last_crawl"] is None
        assert warnings

    def test_unparseable_last_crawl_is_dropped_to_none_not_omitted(self) -> None:
        record: dict = {}
        warnings: list[str] = []
        _attach_last_crawl(record, "not-a-timestamp", INSPECTED_AT, "https://vocus.cc/a", warnings)
        assert "last_crawl" in record
        assert record["last_crawl"] is None
        assert warnings


class TestBatchKeyConsistency:
    """regression test for PGRST102（run 33609190700 的實際成因）：一個 batch 裡
    混合「Google 爬過」與「Google 從沒爬過」兩種 URL，upsert 送出的每筆物件鍵集合
    必須完全一致，否則 PostgREST 批次 upsert 整批 400。這個測試在修正前會失敗
    （crawled 那筆多一個 last_crawl 鍵）。"""

    def test_mixed_crawled_and_never_crawled_urls_produce_identical_key_sets(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        crawled = result_to_record(
            "https://vocus.cc/crawled", _index_status(last_crawl="2026-08-20T10:00:00Z"),
            inspected_at=INSPECTED_AT, errors=errors, warnings=warnings,
        )
        never_crawled = result_to_record(
            "https://vocus.cc/never-crawled", _index_status(last_crawl=None),
            inspected_at=INSPECTED_AT, errors=errors, warnings=warnings,
        )
        assert crawled is not None and never_crawled is not None
        assert set(crawled.keys()) == set(never_crawled.keys())
        assert not errors and not warnings

    def test_batch_of_records_all_share_one_key_set(self) -> None:
        """模擬真實抽樣批次：部分 URL 有 lastCrawlTime、部分沒有。"""
        errors: list[str] = []
        warnings: list[str] = []
        records = [
            result_to_record(
                f"https://vocus.cc/{i}",
                _index_status(last_crawl="2026-08-20T10:00:00Z" if i % 2 == 0 else None),
                inspected_at=INSPECTED_AT, errors=errors, warnings=warnings,
            )
            for i in range(10)
        ]
        key_sets = {frozenset(r.keys()) for r in records if r is not None}
        assert len(key_sets) == 1, f"批次內鍵集合不一致，會觸發 PGRST102：{key_sets}"


# ══════════════════════════════════════════════════════════════════════
# sitemap 抓取
# ══════════════════════════════════════════════════════════════════════

class TestClassifySubSitemap:
    def test_structural_pool(self) -> None:
        assert classify_sub_sitemap("https://vocus.cc/sitemap-0.xml") == "structural"

    def test_tags_excluded(self) -> None:
        assert classify_sub_sitemap("https://vocus.cc/tags/sitemap.xml") is None

    @pytest.mark.parametrize("url", [
        "https://vocus.cc/sitemap-articles-0.xml",
        "https://vocus.cc/sitemap-articles-11.xml",
        "https://vocus.cc/article-news.xml",
    ])
    def test_article_pool(self, url: str) -> None:
        assert classify_sub_sitemap(url) == "article"


class TestListSubSitemaps:
    def test_parses_loc_entries(self) -> None:
        xml = _sitemap_index_xml(["https://vocus.cc/sitemap-0.xml", "https://vocus.cc/sitemap-articles-0.xml"])
        with patch("urllib.request.urlopen", return_value=_FakeResponse(xml)):
            assert list_sub_sitemaps() == [
                "https://vocus.cc/sitemap-0.xml", "https://vocus.cc/sitemap-articles-0.xml",
            ]

    def test_empty_index_is_a_hard_failure(self) -> None:
        xml = '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>'
        with patch("urllib.request.urlopen", return_value=_FakeResponse(xml)):
            with pytest.raises(SitemapFetchError):
                list_sub_sitemaps()

    def test_http_error_is_a_hard_failure(self) -> None:
        with patch("urllib.request.urlopen", side_effect=_http_error(500, "boom")):
            with pytest.raises(SitemapFetchError):
                list_sub_sitemaps()

    def test_connection_error_is_a_hard_failure(self) -> None:
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            with pytest.raises(SitemapFetchError):
                list_sub_sitemaps()

    def test_malformed_xml_is_a_hard_failure(self) -> None:
        with patch("urllib.request.urlopen", return_value=_FakeResponse("not xml at all <<<")):
            with pytest.raises(SitemapFetchError):
                _http_get_xml("https://vocus.cc/sitemap-index.xml")

    def test_exceeding_safety_cap_only_takes_the_first_n(self) -> None:
        many = [f"https://vocus.cc/sitemap-articles-{i}.xml" for i in range(30)]
        xml = _sitemap_index_xml(many)
        with patch("urllib.request.urlopen", return_value=_FakeResponse(xml)):
            result = list_sub_sitemaps()
        assert len(result) <= 20


class TestListUrlEntries:
    def test_parses_loc_and_lastmod(self) -> None:
        xml = _urlset_xml([("https://vocus.cc/a", "2026-08-01"), ("https://vocus.cc/b", None)])
        from defusedxml.ElementTree import fromstring
        entries = list_url_entries(fromstring(xml))
        assert entries == [("https://vocus.cc/a", date(2026, 8, 1)), ("https://vocus.cc/b", None)]

    def test_entry_without_loc_is_skipped(self) -> None:
        xml = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               '<url><lastmod>2026-08-01</lastmod></url></urlset>')
        from defusedxml.ElementTree import fromstring
        assert list_url_entries(fromstring(xml)) == []


class TestFetchSitemapPool:
    def test_splits_into_article_and_structural_pools(self) -> None:
        sub_urls = ["https://vocus.cc/sitemap-0.xml", "https://vocus.cc/sitemap-articles-0.xml",
                    "https://vocus.cc/tags/sitemap.xml"]
        structural_xml = _urlset_xml([("https://vocus.cc/", None)])
        article_xml = _urlset_xml([("https://vocus.cc/a", "2026-08-01")])
        from defusedxml.ElementTree import fromstring
        with patch(f"{MODULE}.list_sub_sitemaps", return_value=sub_urls), \
             patch(f"{MODULE}._http_get_xml", side_effect=[fromstring(structural_xml), fromstring(article_xml)]):
            articles, structural = fetch_sitemap_pool()
        assert articles == [("https://vocus.cc/a", date(2026, 8, 1))]
        assert structural == [("https://vocus.cc/", None)]

    def test_one_failed_sub_sitemap_is_tolerated(self) -> None:
        sub_urls = ["https://vocus.cc/sitemap-articles-0.xml", "https://vocus.cc/sitemap-articles-1.xml"]
        from defusedxml.ElementTree import fromstring
        ok_xml = fromstring(_urlset_xml([("https://vocus.cc/a", None)]))
        with patch(f"{MODULE}.list_sub_sitemaps", return_value=sub_urls), \
             patch(f"{MODULE}._http_get_xml", side_effect=[SitemapFetchError("boom"), ok_xml]):
            articles, _structural = fetch_sitemap_pool()
        assert articles == [("https://vocus.cc/a", None)]

    def test_all_sub_sitemaps_failing_is_a_hard_failure(self) -> None:
        sub_urls = ["https://vocus.cc/sitemap-articles-0.xml"]
        with patch(f"{MODULE}.list_sub_sitemaps", return_value=sub_urls), \
             patch(f"{MODULE}._http_get_xml", side_effect=SitemapFetchError("boom")):
            with pytest.raises(SitemapFetchError):
                fetch_sitemap_pool()


# ══════════════════════════════════════════════════════════════════════
# 零曝光比對與抽樣三層
# ══════════════════════════════════════════════════════════════════════

class TestFetchPagesWithAnyImpressions:
    def test_single_page_of_results(self) -> None:
        response = _FakeResponse('[{"page": "https://vocus.cc/a"}, {"page": "https://vocus.cc/b"}]')
        with patch.dict("os.environ", SUPABASE_ENV), patch("urllib.request.urlopen", return_value=response):
            assert fetch_pages_with_any_impressions() == {"https://vocus.cc/a", "https://vocus.cc/b"}

    def test_paginates_until_short_page(self) -> None:
        full_page = json.dumps([{"page": f"https://vocus.cc/{i}"} for i in range(5000)])
        short_page = '[{"page": "https://vocus.cc/last"}]'
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen",
                   side_effect=[_FakeResponse(full_page), _FakeResponse(short_page)]) as opener:
            result = fetch_pages_with_any_impressions()
        assert "https://vocus.cc/last" in result
        assert opener.call_count == 2

    def test_http_error_raises(self) -> None:
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(500, "boom")):
            with pytest.raises(RuntimeError):
                fetch_pages_with_any_impressions()


class TestBuildControlSet:
    def test_returns_at_most_control_set_size(self) -> None:
        entries = [(f"https://vocus.cc/s{i}", None) for i in range(CONTROL_SET_SIZE + 10)]
        assert len(build_control_set(entries)) == CONTROL_SET_SIZE

    def test_is_deterministic_across_calls(self) -> None:
        entries = [(f"https://vocus.cc/s{i}", None) for i in range(50)]
        assert build_control_set(entries) == build_control_set(list(reversed(entries)))

    def test_deduplicates(self) -> None:
        entries = [("https://vocus.cc/a", None)] * 5
        assert build_control_set(entries) == ["https://vocus.cc/a"]


class TestSplitZeroImpressionTiers:
    def test_url_with_impressions_is_excluded_from_both_tiers(self) -> None:
        tier1, tier2 = split_zero_impression_tiers(
            [("https://vocus.cc/a", None)], {"https://vocus.cc/a"}, TODAY,
        )
        assert tier1 == [] and tier2 == []

    def test_recent_lastmod_goes_to_tier2(self) -> None:
        recent = (TODAY - timedelta(days=1)).isoformat()
        tier1, tier2 = split_zero_impression_tiers(
            [("https://vocus.cc/new", date.fromisoformat(recent))], set(), TODAY,
        )
        assert tier2 == ["https://vocus.cc/new"] and tier1 == []

    def test_old_lastmod_goes_to_tier1(self) -> None:
        old = TODAY - timedelta(days=RECENT_THRESHOLD_DAYS + 1)
        tier1, tier2 = split_zero_impression_tiers([("https://vocus.cc/old", old)], set(), TODAY)
        assert tier1 == ["https://vocus.cc/old"] and tier2 == []

    def test_missing_lastmod_is_conservatively_tier1(self) -> None:
        tier1, tier2 = split_zero_impression_tiers([("https://vocus.cc/unknown", None)], set(), TODAY)
        assert tier1 == ["https://vocus.cc/unknown"] and tier2 == []

    def test_boundary_day_is_tier2(self) -> None:
        boundary = TODAY - timedelta(days=RECENT_THRESHOLD_DAYS)
        tier1, tier2 = split_zero_impression_tiers([("https://vocus.cc/edge", boundary)], set(), TODAY)
        assert tier2 == ["https://vocus.cc/edge"]

    def test_duplicate_urls_in_pool_are_deduplicated(self) -> None:
        tier1, _tier2 = split_zero_impression_tiers(
            [("https://vocus.cc/a", None), ("https://vocus.cc/a", None)], set(), TODAY,
        )
        assert tier1 == ["https://vocus.cc/a"]


class TestBuildSample:
    def test_control_set_has_priority(self) -> None:
        sample = build_sample(["c1", "c2"], ["t1a", "t1b"], ["t2a"], budget=2)
        assert sample == ["c1", "c2"]

    def test_fills_remaining_budget_from_tier1_then_tier2(self) -> None:
        sample = build_sample(["c1"], ["t1a", "t1b"], ["t2a"], budget=3)
        assert sample == ["c1", "t1a", "t1b"]

    def test_never_exceeds_budget(self) -> None:
        sample = build_sample(["c1", "c2", "c3"], ["t1a"] * 10, ["t2a"] * 10, budget=5)
        assert len(sample) == 5

    def test_deduplicates_across_pools(self) -> None:
        sample = build_sample(["x"], ["x"], ["x"], budget=10)
        assert sample == ["x"]

    def test_zero_budget_returns_empty(self) -> None:
        assert build_sample(["c1"], ["t1"], ["t2"], budget=0) == []


# ══════════════════════════════════════════════════════════════════════
# 配額分類帳
# ══════════════════════════════════════════════════════════════════════

class TestQuotaLedger:
    def test_used_sums_row_counts_within_window(self) -> None:
        body = json.dumps([{"row_count": 100}, {"row_count": 50}])
        with patch(f"{MODULE}._supabase_request", return_value=(200, body)):
            assert quota_used_last_24h() == 150

    def test_used_queries_the_ledger_table_name_not_the_data_table(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")) as request:
            quota_used_last_24h()
        path = request.call_args.args[1]
        assert f"table_name=eq.{QUOTA_LEDGER_TABLE_NAME}" in path

    def test_used_raises_on_error(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            with pytest.raises(RuntimeError):
                quota_used_last_24h()

    def test_record_usage_writes_calls_made_as_row_count(self) -> None:
        now = datetime(2026, 9, 2, tzinfo=UTC)
        with patch(f"{MODULE}._supabase_request", return_value=(201, "")) as request:
            record_quota_usage(7, now, now + timedelta(seconds=1))
        payload = request.call_args.kwargs["body"][0]
        assert payload["row_count"] == 7
        assert payload["table_name"] == QUOTA_LEDGER_TABLE_NAME
        assert payload["status"] == "success"

    def test_record_usage_is_a_noop_for_zero_calls(self) -> None:
        with patch(f"{MODULE}._supabase_request") as request:
            record_quota_usage(0, datetime.now(UTC), datetime.now(UTC) + timedelta(seconds=1))
        request.assert_not_called()


class TestQuotaGate:
    def test_remaining_is_budget_minus_used(self) -> None:
        with patch(f"{MODULE}.quota_used_last_24h", return_value=300):
            assert _quota_gate(500) == 200

    def test_remaining_can_go_negative_when_over_budget(self) -> None:
        with patch(f"{MODULE}.quota_used_last_24h", return_value=600):
            assert _quota_gate(500) == -100


# ══════════════════════════════════════════════════════════════════════
# 逐一 inspect —— 429 提前停止 vs 系統性錯誤中止
# ══════════════════════════════════════════════════════════════════════

class TestCollectInspections:
    def test_happy_path_all_urls_inspected(self) -> None:
        with patch(f"{MODULE}.inspect_url", return_value=_index_status()):
            records, quota_stopped = collect_inspections(
                "token", ["https://vocus.cc/a", "https://vocus.cc/b"], INSPECTED_AT, [0], [], [],
            )
        assert len(records) == 2 and quota_stopped is False

    def test_quota_exhausted_stops_early_without_raising(self) -> None:
        calls_counter = [0]
        with patch(f"{MODULE}.inspect_url", side_effect=QuotaExhaustedError("429")):
            records, quota_stopped = collect_inspections(
                "token", ["https://vocus.cc/a", "https://vocus.cc/b"], INSPECTED_AT, calls_counter, [], [],
            )
        assert records == [] and quota_stopped is True
        assert calls_counter[0] == 1  # 只打了第一個就停，第二個 URL 沒被消耗

    def test_quota_exhausted_after_some_successes_keeps_partial_records(self) -> None:
        with patch(f"{MODULE}.inspect_url",
                   side_effect=[_index_status(), QuotaExhaustedError("429")]):
            records, quota_stopped = collect_inspections(
                "token", ["https://vocus.cc/a", "https://vocus.cc/b"], INSPECTED_AT, [0], [], [],
            )
        assert len(records) == 1 and quota_stopped is True

    def test_systemic_error_propagates_not_swallowed(self) -> None:
        with patch(f"{MODULE}.inspect_url", side_effect=GscQueryError("401")):
            with pytest.raises(GscQueryError):
                collect_inspections("token", ["https://vocus.cc/a"], INSPECTED_AT, [0], [], [])

    def test_calls_counter_increments_even_on_rejected_rows(self) -> None:
        calls_counter = [0]
        with patch(f"{MODULE}.inspect_url", return_value={}):
            collect_inspections("token", ["https://vocus.cc/a"], INSPECTED_AT, calls_counter, [], [])
        assert calls_counter[0] == 1


# ══════════════════════════════════════════════════════════════════════
# Supabase 存取（gsc_url_inspection 本體）
# ══════════════════════════════════════════════════════════════════════

class TestIngestionRunLifecycle:
    def test_start_run_records_url_inspection_table_name(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(201, '[{"id": "abc"}]')) as request:
            run_id = start_url_inspection_run(datetime(2026, 9, 2, tzinfo=UTC), datetime(2026, 9, 2, 0, 0, 1, tzinfo=UTC))
        assert run_id == "abc"
        payload = request.call_args.kwargs["body"][0]
        assert payload["table_name"] == TABLE_URL_INSPECTION
        assert payload["status"] == "running"

    def test_start_run_failure_returns_none(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            assert start_url_inspection_run(datetime.now(UTC), datetime.now(UTC) + timedelta(seconds=1)) is None

    def test_finish_run_sets_terminal_status(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(204, "")) as request:
            finish_url_inspection_run("abc", "success", 20)
        payload = request.call_args.kwargs["body"]
        assert payload["status"] == "success" and payload["row_count"] == 20

    def test_finish_run_without_id_is_noop(self) -> None:
        with patch(f"{MODULE}._supabase_request") as request:
            finish_url_inspection_run(None, "success", 0)
        request.assert_not_called()

    def test_finish_run_logs_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            finish_url_inspection_run("abc", "failed", 0)
        assert "收尾 ingestion_run 失敗" in caplog.text


class TestUpsert:
    ROW = {"property": PROPERTY, "url": "https://vocus.cc/a", "inspected_at": INSPECTED_AT,
           "coverage_state": "Submitted and indexed", "indexing_state": "INDEXING_ALLOWED",
           "ingested_at": INSPECTED_AT}

    def test_all_succeed(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(201, "")):
            assert upsert_url_inspections([self.ROW] * 3) == (3, 0)

    def test_batch_failure_counts_as_failed(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            assert upsert_url_inspections([self.ROW]) == (0, 1)

    def test_conflict_key_matches_unique_constraint(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "")) as request:
            upsert_url_inspections([self.ROW])
        path = request.call_args.args[1]
        assert "on_conflict=property%2Curl%2Cinspected_on" in path

    def test_rows_are_sent_in_batches(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(201, "")) as request:
            upsert_url_inspections([self.ROW] * 1200)
        assert request.call_count == 3

    def test_empty_input_makes_no_request(self) -> None:
        with patch(f"{MODULE}._supabase_request") as request:
            assert upsert_url_inspections([]) == (0, 0)
        request.assert_not_called()


class TestCountAndLatest:
    def test_count_reads_content_range(self) -> None:
        response = _FakeResponse("[]", status=206, headers={"Content-Range": "0-0/42"})
        with patch.dict("os.environ", SUPABASE_ENV), patch("urllib.request.urlopen", return_value=response):
            assert count_url_inspection_rows() == 42

    def test_count_raises_on_http_error(self) -> None:
        with patch.dict("os.environ", SUPABASE_ENV), \
             patch("urllib.request.urlopen", side_effect=_http_error(500, "boom")):
            with pytest.raises(RuntimeError):
                count_url_inspection_rows()

    def test_count_raises_on_malformed_content_range(self) -> None:
        response = _FakeResponse("[]", headers={"Content-Range": "nope"})
        with patch.dict("os.environ", SUPABASE_ENV), patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(RuntimeError):
                count_url_inspection_rows()

    def test_latest_inspected_at_returns_parsed_datetime(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, '[{"inspected_at": "2026-09-01T10:00:00Z"}]')):
            assert latest_inspected_at() == datetime(2026, 9, 1, 10, 0, tzinfo=UTC)

    def test_latest_inspected_at_empty_table_returns_none(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(200, "[]")):
            assert latest_inspected_at() is None

    def test_latest_inspected_at_error_raises(self) -> None:
        with patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            with pytest.raises(RuntimeError):
                latest_inspected_at()


# ══════════════════════════════════════════════════════════════════════
# 執行模式 —— 0 筆的三種樣貌
# ══════════════════════════════════════════════════════════════════════

class TestFinalizeRun:
    def test_dry_run_with_records_and_no_errors_succeeds(self) -> None:
        assert _finalize_run([{"url": "a"}], [], [], quota_stopped=False, execute=False) == 0

    def test_dry_run_zero_records_without_quota_stop_fails(self) -> None:
        """規則 (c)：查不到資料一律是失敗，不能以 0 呈現成功。"""
        assert _finalize_run([], [], [], quota_stopped=False, execute=False) == 1

    def test_dry_run_zero_records_with_quota_stop_succeeds(self) -> None:
        """規則 (a)：配額停止是成功結束，即使可寫入 0 列。"""
        assert _finalize_run([], [], [], quota_stopped=True, execute=False) == 0

    def test_dry_run_errors_fail_even_with_quota_stop(self) -> None:
        assert _finalize_run([], ["bad row"], [], quota_stopped=True, execute=False) == 1

    def test_execute_writes_and_reports_success(self) -> None:
        with patch(f"{MODULE}.start_url_inspection_run", return_value="run-1"), \
             patch(f"{MODULE}.upsert_url_inspections", return_value=(2, 0)), \
             patch(f"{MODULE}.finish_url_inspection_run") as finish:
            code = _finalize_run([{"url": "a"}, {"url": "b"}], [], [], quota_stopped=False, execute=True)
        assert code == 0
        assert finish.call_args.args[1] == "success"

    def test_execute_zero_written_without_quota_stop_fails(self) -> None:
        with patch(f"{MODULE}.start_url_inspection_run", return_value="run-1"), \
             patch(f"{MODULE}.upsert_url_inspections", return_value=(0, 0)), \
             patch(f"{MODULE}.finish_url_inspection_run") as finish:
            code = _finalize_run([], [], [], quota_stopped=False, execute=True)
        assert code == 1
        assert finish.call_args.args[1] == "failed"

    def test_execute_quota_stop_with_zero_written_succeeds(self) -> None:
        """規則 (a) 在 execute 模式下同樣成立。"""
        with patch(f"{MODULE}.start_url_inspection_run", return_value="run-1"), \
             patch(f"{MODULE}.upsert_url_inspections", return_value=(0, 0)), \
             patch(f"{MODULE}.finish_url_inspection_run") as finish:
            code = _finalize_run([], [], [], quota_stopped=True, execute=True)
        assert code == 0
        assert finish.call_args.args[1] == "success"

    def test_execute_partial_write_failure_is_partial_status(self) -> None:
        with patch(f"{MODULE}.start_url_inspection_run", return_value="run-1"), \
             patch(f"{MODULE}.upsert_url_inspections", return_value=(1, 1)), \
             patch(f"{MODULE}.finish_url_inspection_run") as finish:
            code = _finalize_run([{"url": "a"}, {"url": "b"}], [], [], quota_stopped=False, execute=True)
        assert code == 1
        assert finish.call_args.args[1] == "partial"


class TestRunIngestion:
    def test_quota_exhausted_before_any_call_is_success_with_zero_calls(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="token"), \
             patch(f"{MODULE}._quota_gate", return_value=0), \
             patch(f"{MODULE}._build_candidates") as build_candidates:
            assert run_ingestion(execute=True, sample_size=DEFAULT_SAMPLE_SIZE, quota_budget=DEFAULT_QUOTA_BUDGET) == 0
        build_candidates.assert_not_called()

    def test_empty_candidate_pool_is_a_hard_failure(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="token"), \
             patch(f"{MODULE}._quota_gate", return_value=100), \
             patch(f"{MODULE}._build_candidates", return_value=([], [], [])):
            assert run_ingestion(execute=True, sample_size=DEFAULT_SAMPLE_SIZE, quota_budget=DEFAULT_QUOTA_BUDGET) == 1

    def test_dry_run_execute_writes_when_records_found(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="token"), \
             patch(f"{MODULE}._quota_gate", return_value=100), \
             patch(f"{MODULE}._build_candidates", return_value=(["c1"], [], [])), \
             patch(f"{MODULE}.collect_inspections", return_value=([{"url": "c1"}], False)), \
             patch(f"{MODULE}.record_quota_usage"), \
             patch(f"{MODULE}.start_url_inspection_run", return_value="run-1"), \
             patch(f"{MODULE}.upsert_url_inspections", return_value=(1, 0)), \
             patch(f"{MODULE}.finish_url_inspection_run"):
            assert run_ingestion(execute=True, sample_size=10, quota_budget=DEFAULT_QUOTA_BUDGET) == 0

    def test_systemic_error_mid_run_aborts_with_failure(self) -> None:
        with patch(f"{MODULE}.gsc_access_token", return_value="token"), \
             patch(f"{MODULE}._quota_gate", return_value=100), \
             patch(f"{MODULE}._build_candidates", return_value=(["c1"], [], [])), \
             patch(f"{MODULE}.collect_inspections", side_effect=GscQueryError("401")), \
             patch(f"{MODULE}.record_quota_usage"):
            assert run_ingestion(execute=True, sample_size=10, quota_budget=DEFAULT_QUOTA_BUDGET) == 1

    def test_quota_recorded_even_when_run_aborts(self) -> None:
        """配額是打 API 就算數，即使中途系統性錯誤中止也要記到分類帳。"""
        with patch(f"{MODULE}.gsc_access_token", return_value="token"), \
             patch(f"{MODULE}._quota_gate", return_value=100), \
             patch(f"{MODULE}._build_candidates", return_value=(["c1"], [], [])), \
             patch(f"{MODULE}.collect_inspections", side_effect=GscQueryError("401")), \
             patch(f"{MODULE}.record_quota_usage") as record:
            run_ingestion(execute=True, sample_size=10, quota_budget=DEFAULT_QUOTA_BUDGET)
        record.assert_called_once()

    def test_sample_size_caps_the_target_regardless_of_quota_headroom(self) -> None:
        many_tier1 = [f"https://vocus.cc/{i}" for i in range(50)]
        with patch(f"{MODULE}.gsc_access_token", return_value="token"), \
             patch(f"{MODULE}._quota_gate", return_value=500), \
             patch(f"{MODULE}._build_candidates", return_value=([], many_tier1, [])), \
             patch(f"{MODULE}.collect_inspections", return_value=([], False)) as collect, \
             patch(f"{MODULE}.record_quota_usage"):
            run_ingestion(execute=False, sample_size=5, quota_budget=DEFAULT_QUOTA_BUDGET)
        assert len(collect.call_args.args[1]) == 5


# ══════════════════════════════════════════════════════════════════════
# 新鮮度告警
# ══════════════════════════════════════════════════════════════════════

class TestFreshnessCheck:
    def test_threshold_is_wider_than_two_schedule_periods(self) -> None:
        """配額被別的呼叫方擠占時可能連續數天零寫入，24h×2 會誤報。"""
        assert FRESHNESS_MAX_AGE_HOURS >= 24 * 3

    def test_empty_table_fails(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch(f"{MODULE}.latest_inspected_at", return_value=None):
            assert run_freshness_check() == 1
        assert "從未成功寫入" in caplog.text

    def test_fresh_data_passes(self, caplog: pytest.LogCaptureFixture) -> None:
        recent = datetime.now(UTC) - timedelta(hours=2)
        with caplog.at_level(logging.INFO, logger="ingest_gsc_url_inspection"), \
             patch(f"{MODULE}.latest_inspected_at", return_value=recent):
            assert run_freshness_check() == 0
        assert "PASS" in caplog.text

    def test_stale_data_fails(self, caplog: pytest.LogCaptureFixture) -> None:
        stale = datetime.now(UTC) - timedelta(hours=FRESHNESS_MAX_AGE_HOURS + 1)
        with patch(f"{MODULE}.latest_inspected_at", return_value=stale):
            assert run_freshness_check() == 1
        assert "FAIL" in caplog.text

    def test_two_day_quota_contention_gap_does_not_false_alarm(self) -> None:
        """規則 (a) 的連帶效果：連續兩天配額停止（0 寫入）不該觸發告警。"""
        two_days_stale = datetime.now(UTC) - timedelta(hours=48)
        with patch(f"{MODULE}.latest_inspected_at", return_value=two_days_stale):
            assert run_freshness_check() == 0


# ══════════════════════════════════════════════════════════════════════
# 參數與 CLI
# ══════════════════════════════════════════════════════════════════════

class TestArgumentResolution:
    def test_default_sample_size(self) -> None:
        assert resolve_sample_size(None) == DEFAULT_SAMPLE_SIZE

    @pytest.mark.parametrize("value", [0, -1, MAX_SAMPLE_SIZE + 1])
    def test_out_of_range_sample_size_rejected(self, value: int) -> None:
        with pytest.raises(ValueError):
            resolve_sample_size(value)

    def test_default_quota_budget(self) -> None:
        assert resolve_quota_budget(None) == DEFAULT_QUOTA_BUDGET

    def test_quota_budget_cannot_exceed_hard_ceiling(self) -> None:
        with pytest.raises(ValueError, match="上限"):
            resolve_quota_budget(QUOTA_HARD_CEILING + 1)

    def test_quota_budget_at_hard_ceiling_is_accepted(self) -> None:
        assert resolve_quota_budget(QUOTA_HARD_CEILING) == QUOTA_HARD_CEILING

    def test_zero_quota_budget_rejected(self) -> None:
        with pytest.raises(ValueError):
            resolve_quota_budget(0)


class TestCli:
    def _run(self, argv: list[str]) -> int:
        with patch("sys.argv", ["ingest_gsc_url_inspection.py", *argv]):
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

    def test_execute_flag_and_options_pass_through(self) -> None:
        with patch(f"{MODULE}.run_ingestion", return_value=0) as ingest:
            self._run(["--execute", "--sample-size", "20", "--quota-budget", "300"])
        assert ingest.call_args.kwargs == {"execute": True, "sample_size": 20, "quota_budget": 300}

    def test_invalid_sample_size_exits_two(self) -> None:
        assert self._run(["--sample-size", "9999"]) == 2

    def test_invalid_quota_budget_exits_two(self) -> None:
        assert self._run(["--quota-budget", "5000"]) == 2


class TestRunVerify:
    def test_reports_total_and_recent_rows(self) -> None:
        with patch(f"{MODULE}.count_url_inspection_rows", return_value=20), \
             patch(f"{MODULE}._supabase_request", side_effect=[
                 (200, '[{"url": "https://vocus.cc/a", "inspected_on": "2026-09-01", '
                       '"coverage_state": "Submitted and indexed", "indexing_state": "INDEXING_ALLOWED", '
                       '"last_crawl": null}]'),
                 (200, '[{"id": "run-1", "window_start": "2026-09-01T00:00:00Z", '
                       '"window_end": "2026-09-01T00:00:01Z", "row_count": 20, "status": "success", '
                       '"finished_at": "2026-09-01T00:00:02Z"}]'),
             ]):
            assert run_verify() == 0

    def test_empty_table_fails(self) -> None:
        with patch(f"{MODULE}.count_url_inspection_rows", return_value=0), \
             patch(f"{MODULE}._supabase_request", return_value=(200, "[]")):
            assert run_verify() == 1

    def test_read_failure_returns_one(self) -> None:
        with patch(f"{MODULE}.count_url_inspection_rows", return_value=20), \
             patch(f"{MODULE}._supabase_request", return_value=(500, "boom")):
            assert run_verify() == 1
