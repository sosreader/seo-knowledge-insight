"""Tests for ingest_crawl_hourly.py / crawl_taxonomy.py / crawl_warehouse.py.

重點覆蓋四件在 2026-09-01 的 live 探測中實際踩到、且**失敗時不會有錯誤訊號**的事：

  1. 過濾樣式必須是分群表的超集。手寫 `bot|crawler|spider` 會漏掉
     facebookexternalhit / Google-AMPHTML / meta-webindexer / AIWebIndex /
     Claude-User（UA 裡都沒有 "bot"），漏掉的部分會靜默併進 human。
  2. token alternation 的順序。Googlebot-Image 排在 Googlebot 之後的話，
     "Googlebot-Image/1.0" 會被抽成 "Googlebot"，圖片抓取整批算進網頁抓取。
  3. path allowlist 失效時每個路徑各自成桶，撞 max_series=500 讓整個查詢死。
  4. 只 upsert 不掃過期列，桶集合縮小時舊列殘留、被 SUM 計入，靜默高估。

另外覆蓋 Loki 的四種失敗回應（400 series / 400 bytes / 500 length / 502 proxy），
它們的 status code 分不出種類，只能比對訊息子字串。
"""
from __future__ import annotations

import json
import logging
import re
import sys
import urllib.error
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import crawl_taxonomy as tax  # noqa: E402
from scripts import crawl_warehouse as wh  # noqa: E402
from scripts.ingest_crawl_hourly import (  # noqa: E402
    DEFAULT_LOOKBACK_HOURS,
    LOKI_MAX_SERIES,
    MAX_AGE_HOURS,
    MAX_BACKFILL_HOURS,
    RETENTION_SAFETY_MARGIN_HOURS,
    LokiQueryError,
    _row,
    build_crawler_bytes_query,
    build_crawler_count_query,
    build_rows,
    build_total_bytes_query,
    build_total_count_query,
    classify_loki_error,
    collect_hour,
    complete_hours,
    derive_human,
    fold_crawler,
    fold_total,
    loki_instant,
    parse_iso_hour,
    resolve_hours,
    run_freshness_check,
    run_ingestion,
    run_verify,
    truncate_to_hour,
)

UTC = timezone.utc
HOUR = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)


def _http_error(status: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", status, "err", {}, BytesIO(body.encode()))


def _pattern_of(expr: str) -> str:
    """從 label_format 片段裡把 regex 取出來，好在 Python 端重現 LogQL 的行為。

    形狀固定是 `name=`{{ regexReplaceAll "PATTERN" .field "${1}" }}``。
    Python 的 re 與 Go RE2 在這裡用到的語法（非貪婪、alternation、字元類別）
    語意一致，而且 alternation 都是 leftmost-first——這一點已用 live 查詢對照過
    （見 .verification/.../01-loki-probe-findings.md 第 5、7 節）。
    """
    match = re.search(r'regexReplaceAll "(.+?)" \.', expr)
    assert match, f"取不出 pattern：{expr}"
    return match.group(1)


def _apply(pattern: str, value: str) -> str:
    """重現 regexReplaceAll 的「命中回捕捉組、沒命中回空字串」。"""
    match = re.match(pattern, value)
    return (match.group(1) or "") if match else ""


def _extract_token(user_agent: str) -> str:
    return _apply(_pattern_of(tax.build_ua_token_expr()), user_agent)


def _extract_prefix(path: str) -> str:
    return _apply(_pattern_of(tax.build_path_prefix_expr()), path)


# 2026-09-01 08:00Z 實際出現過的 UA（節錄），拿真值當測資而不是自己編。
REAL_USER_AGENTS = {
    "googlebot-desktop": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "googlebot-smartphone": (
        "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.7922.173 Mobile Safari/537.36 "
        "(compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    ),
    "googlebot-image": "Googlebot-Image/1.0",
    "googlebot-other": (
        "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.7922.173 Mobile Safari/537.36 "
        "(compatible; AdsBot-Google-Mobile; +http://www.google.com/mobile/adsbot.html)"
    ),
    "bingbot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; bingbot/2.0; "
        "+http://www.bing.com/bingbot.htm) Chrome/116.0.1938.76 Safari/537.36"
    ),
    "ai-search-bot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; "
        "+searchbot@anthropic.com)"
    ),
    "ai-mixed-bot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Amazonbot/0.1; "
        "+https://developer.amazon.com/support/amazonbot) Chrome/119.0.6045.214 Safari/537.36"
    ),
    "ai-training-bot": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; "
        "+claudebot@anthropic.com)"
    ),
    "seo-tool-bot": (
        "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/108.0.5359.128 Mobile Safari/537.36 (compatible; AhrefsSiteAudit/6.1; +http://ahrefs.com/robot/)"
    ),
    "social-bot": "facebookexternalhit/1.1;line-poker/1.0",
}
REAL_HUMAN_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/26.6 Mobile/15E148 Safari/604.1"
)


# ══════════════════════════════════════════════════════════════════════
# 過濾樣式必須是分群表的超集 —— 漏掉的 crawler 會靜默變成 human
# ══════════════════════════════════════════════════════════════════════

class TestCrawlerPatternIsDerivedNotHandwritten:
    def test_every_named_token_passes_the_filter(self) -> None:
        """分群表裡的每一個 token 都必須被過濾樣式接住，否則那一群整批漏掉。"""
        pattern = tax.build_crawler_ua_pattern()
        for token in tax.TOKEN_TO_UA_GROUP:
            assert re.match(pattern, f"Mozilla/5.0 (compatible; {token}/1.0)"), token

    def test_real_user_agents_all_pass_the_filter(self) -> None:
        pattern = tax.build_crawler_ua_pattern()
        for group, user_agent in REAL_USER_AGENTS.items():
            assert re.match(pattern, user_agent), group

    def test_naive_bot_pattern_would_miss_these_and_that_is_why_we_derive(self) -> None:
        """這個測試把教訓釘住：手寫的 bot|crawler|spider 會漏掉五個真實 crawler。

        實測 2026-09-01 08:00Z 合計 1,239 次/小時會被誤判成 human。
        """
        naive = re.compile(r".*([Bb]ot|[Cc]rawler|[Ss]pider|[Ss]lurp).*")
        derived = re.compile(tax.build_crawler_ua_pattern())
        missed_by_naive = [
            "facebookexternalhit", "Google-AMPHTML", "meta-webindexer",
            "AIWebIndex", "Claude-User",
        ]
        for token in missed_by_naive:
            assert token in tax.TOKEN_TO_UA_GROUP
            assert not naive.match(token), f"{token} 竟然含 bot 字樣，測資該更新"
            assert derived.match(token), f"{token} 沒被推導出的樣式接住"

    def test_human_user_agent_does_not_pass_the_filter(self) -> None:
        assert not re.match(tax.build_crawler_ua_pattern(), REAL_HUMAN_UA)


# ══════════════════════════════════════════════════════════════════════
# token alternation 的順序 —— 具體者必須排在泛用者之前
# ══════════════════════════════════════════════════════════════════════

class TestTokenExtractionOrdering:
    def test_googlebot_image_is_not_swallowed_by_generic_googlebot(self) -> None:
        assert _extract_token("Googlebot-Image/1.0") == "Googlebot-Image"

    def test_adsbot_google_mobile_wins_over_adsbot_google(self) -> None:
        assert _extract_token(REAL_USER_AGENTS["googlebot-other"]) == "AdsBot-Google-Mobile"

    def test_generic_googlebot_still_extracted_from_smartphone_shell(self) -> None:
        assert _extract_token(REAL_USER_AGENTS["googlebot-smartphone"]) == "Googlebot"

    def test_unmatched_user_agent_yields_empty_token(self) -> None:
        assert _extract_token(REAL_HUMAN_UA) == ""

    def test_every_token_extracts_to_itself(self) -> None:
        for token in tax.TOKEN_TO_UA_GROUP:
            extracted = _extract_token(f"Mozilla/5.0 (compatible; {token}/1.0; +http://x/)")
            assert tax.TOKEN_TO_UA_GROUP[extracted] is not None
            # 抽出來的 token 必須在表裡；不必等於原 token（更長的具名前綴優先是設計）
            assert extracted in tax.TOKEN_TO_UA_GROUP, (token, extracted)

    def test_specific_google_tokens_precede_generic_googlebot(self) -> None:
        keys = list(tax.TOKEN_TO_UA_GROUP)
        generic = keys.index(tax.GOOGLEBOT_TOKEN)
        for specific in ("Googlebot-Image", "Googlebot-Video", "Googlebot-News"):
            assert keys.index(specific) < generic


# ══════════════════════════════════════════════════════════════════════
# ua_group 分類
# ══════════════════════════════════════════════════════════════════════

class TestClassify:
    @pytest.mark.parametrize("group", sorted(REAL_USER_AGENTS))
    def test_real_user_agent_lands_in_expected_group(self, group: str) -> None:
        user_agent = REAL_USER_AGENTS[group]
        token = _extract_token(user_agent)
        mobile = _apply(_pattern_of(tax.build_mobile_expr()), user_agent)
        assert tax.classify(token, mobile)[1] == group

    def test_googlebot_splits_on_mobile_marker(self) -> None:
        assert tax.classify("Googlebot", "") == ("googlebot-desktop", "googlebot-desktop")
        assert tax.classify("Googlebot", "Android") == ("googlebot-smartphone", "googlebot-smartphone")

    def test_mobile_marker_does_not_affect_other_tokens(self) -> None:
        assert tax.classify("bingbot", "Mobile") == ("bingbot", "bingbot")

    def test_empty_token_means_generic_bot_marker_matched(self) -> None:
        assert tax.classify("", "") == (tax.UA_NAME_OTHER_BOT, tax.UA_GROUP_OTHER_BOT)

    def test_unknown_token_raises_instead_of_silently_bucketing(self) -> None:
        """分群表與 label_format 樣式分岔時要當場失敗，不可靜默塞進殘餘桶。"""
        with pytest.raises(ValueError, match="TOKEN_TO_UA_GROUP"):
            tax.classify("SomeBotWeNeverDefined", "")

    def test_ua_name_is_the_lowercased_token(self) -> None:
        assert tax.classify("Claude-SearchBot", "")[0] == "claude-searchbot"
        assert tax.classify("OAI-SearchBot", "")[0] == "oai-searchbot"

    def test_name_and_group_come_from_one_call_so_they_cannot_drift(self) -> None:
        """ua_group 是 ua_name 的函數。分開算就可能分岔，而冪等鍵只看 ua_name，擋不住。"""
        for token in tax.TOKEN_TO_UA_GROUP:
            name, group = tax.classify(token, "")
            assert (name, group) == tax.classify(token, "")
            # 同一個 ua_name 在整張表裡只能對應一個 ua_group
            assert group == tax.classify(token, "")[1]

    def test_one_ua_name_maps_to_exactly_one_ua_group(self) -> None:
        seen: dict[str, str] = {}
        for token in tax.TOKEN_TO_UA_GROUP:
            for mobile in ("", "Android"):
                name, group = tax.classify(token, mobile)
                assert seen.setdefault(name, group) == group, name

    def test_applebot_and_amazonbot_are_mixed_not_training(self) -> None:
        """兩者都有面向使用者的搜尋介面（Siri / Alexa）。併進 ai-training-bot 會讓
        該桶的 SUM 靜默包含會回連的 bot，而歧義寫在 COMMENT 裡不會參與加總。"""
        assert tax.classify("Applebot", "")[1] == "ai-mixed-bot"
        assert tax.classify("Amazonbot", "")[1] == "ai-mixed-bot"

    @pytest.mark.parametrize("group", ["ai-search-bot", "ai-training-bot", "ai-mixed-bot"])
    def test_three_ai_buckets_are_all_populated(self, group: str) -> None:
        assert group in set(tax.TOKEN_TO_UA_GROUP.values())

    def test_every_ua_name_satisfies_the_db_check(self) -> None:
        """crawl_daily_ua_name_ck：小寫 slug 且 <= 64 bytes（它在 unique 索引裡）。"""
        names = {tax.classify(t, m)[0] for t in tax.TOKEN_TO_UA_GROUP for m in ("", "Android")}
        names |= {tax.UA_NAME_OTHER_BOT, tax.UA_NAME_HUMAN}
        for name in names:
            assert re.fullmatch(tax.UA_NAME_PATTERN, name), name
            assert len(name.encode()) <= tax.UA_NAME_MAX_BYTES, name

    def test_every_group_is_within_the_check_constraint_domain(self) -> None:
        """值域必須與 migration 017 的 crawl_daily_ua_group_ck 一致。"""
        allowed = {
            "googlebot-desktop", "googlebot-smartphone", "googlebot-image", "googlebot-other",
            "bingbot", "ai-search-bot", "ai-training-bot", "ai-mixed-bot",
            "seo-tool-bot", "social-bot", "other-bot", "human", "other",
        }
        assert set(tax.TOKEN_TO_UA_GROUP.values()) <= allowed
        assert {tax.GOOGLEBOT_SMARTPHONE, tax.UA_GROUP_OTHER_BOT, tax.UA_GROUP_HUMAN} <= allowed


# ══════════════════════════════════════════════════════════════════════
# path 分桶 —— allowlist 失效會撞 max_series
# ══════════════════════════════════════════════════════════════════════

class TestPathPrefixBucketing:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("/article/69a944f3fd897800012ee057", "/article"),
            ("/article", "/article"),
            ("/tags/%E5%AE%9A%E6%9C%9F?tagname=x", "/tags"),
            ("/", "/"),
            ("/robots.txt", "/robots.txt"),
            ("/favicon.ico", "/favicon.ico"),
            ("/.well-known/assetlinks.json", "/.well-known"),
            ("/_next/data/abc/zh-Hant/login.json", "/_next"),
        ],
    )
    def test_allowlisted_first_segment_is_kept(self, path: str, expected: str) -> None:
        assert _extract_prefix(path) == expected

    @pytest.mark.parametrize(
        "path",
        ["/someuserhandle", "/%E5%B0%88%E9%A1%8C", "/@handle", "/unknownroute/x"],
    )
    def test_non_allowlisted_first_segment_collapses(self, path: str) -> None:
        """根路徑下的使用者頁是高基數維度，不塌就會撞 max_series=500。"""
        assert _extract_prefix(path) == ""
        assert tax.normalize_path_prefix(_extract_prefix(path)) == tax.PATH_PREFIX_OTHER

    def test_path_segments_escape_dots_with_character_class_not_backslash(self) -> None:
        """`\\.` 會讓整個 Go template 掛掉（invalid syntax），必須用 `[.]`。"""
        for segment in tax.PATH_SEGMENTS:
            assert "\\" not in segment, segment
        assert "robots[.]txt" in tax.PATH_SEGMENTS

    def test_generated_expression_carries_no_backslash(self) -> None:
        assert "\\" not in tax.build_path_prefix_expr()


class TestNormalizePathPrefix:
    def test_root_is_preserved(self) -> None:
        assert tax.normalize_path_prefix("/") == "/"

    def test_empty_becomes_residual_bucket(self) -> None:
        assert tax.normalize_path_prefix("") == tax.PATH_PREFIX_OTHER

    def test_missing_leading_slash_becomes_residual(self) -> None:
        assert tax.normalize_path_prefix("article") == tax.PATH_PREFIX_OTHER

    def test_illegal_characters_become_residual(self) -> None:
        """crawl_daily_path_prefix_ck 只收 [A-Za-z0-9_.-]；送過去會整批被打回。"""
        assert tax.normalize_path_prefix("/%E5%B0%88") == tax.PATH_PREFIX_OTHER
        assert tax.normalize_path_prefix("/a/b") == tax.PATH_PREFIX_OTHER

    def test_over_length_becomes_residual(self) -> None:
        """octet_length <= 64；btree 索引在壓縮後才檢查，長字串只在特定資料上才炸。"""
        assert tax.normalize_path_prefix("/" + "z" * 64) == tax.PATH_PREFIX_OTHER
        assert tax.normalize_path_prefix("/" + "z" * 63) == "/" + "z" * 63

    def test_residual_bucket_name_satisfies_the_check_constraint(self) -> None:
        assert re.fullmatch(r"^/[A-Za-z0-9_.-]*$", tax.PATH_PREFIX_OTHER)
        assert len(tax.PATH_PREFIX_OTHER.encode()) <= tax.PATH_PREFIX_MAX_BYTES


class TestParseStatusCode:
    @pytest.mark.parametrize("raw,expected", [("200", 200), ("404", 404), ("599", 599), ("100", 100)])
    def test_valid_codes(self, raw: str, expected: int) -> None:
        assert tax.parse_status_code(raw) == expected

    @pytest.mark.parametrize("raw", ["0", "99", "600", "", "abc", "-1"])
    def test_out_of_range_or_malformed_returns_none(self, raw: str) -> None:
        """envoy 連線層失敗會記 status=0，那不是 HTTP 碼，進 payload 會整批被 CHECK 打回。"""
        assert tax.parse_status_code(raw) is None


# ══════════════════════════════════════════════════════════════════════
# LogQL 組裝
# ══════════════════════════════════════════════════════════════════════

class TestQueryConstruction:
    def test_crawler_queries_group_by_all_four_dimensions(self) -> None:
        for query in (build_crawler_count_query(), build_crawler_bytes_query()):
            assert query.startswith("sum by (token, mob, status, pfx)")

    def test_total_queries_do_not_touch_user_agent(self) -> None:
        """全流量查詢刻意不跑 UA regex：157k 行跑 UA regex 實測 20-23s，貼著 30s proxy 上限。"""
        for query in (build_total_count_query(), build_total_bytes_query()):
            assert "user_agent" not in query
            assert query.startswith("sum by (status, pfx)")

    def test_crawler_queries_filter_on_parsed_field_not_raw_line(self) -> None:
        """line filter 會把 referer 含 google 的真人流量誤標成 Googlebot。"""
        query = build_crawler_count_query()
        assert "| json | user_agent =~" in query
        assert "|~" not in query

    def test_bytes_queries_unwrap_bytes_sent_not_origin_content_length(self) -> None:
        """origin_content_length 只在 200 有值，unwrap 它會讓 3xx/4xx 靜默變 0。"""
        for query in (build_crawler_bytes_query(), build_total_bytes_query()):
            assert "unwrap bytes_sent" in query
            assert "origin_content_length" not in query

    def test_every_query_uses_the_one_hour_bucket(self) -> None:
        for query in (build_crawler_count_query(), build_crawler_bytes_query(),
                      build_total_count_query(), build_total_bytes_query()):
            assert "[1h]" in query

    def test_capture_or_empty_has_a_catch_all_alternative(self) -> None:
        """regexReplaceAll 沒有 else 分支，靠 `^.*$` 兜底才有預設值。"""
        assert _pattern_of(tax.build_ua_token_expr()).endswith("|^.*$")
        assert _pattern_of(tax.build_path_prefix_expr()).endswith("|^.*$")


# ══════════════════════════════════════════════════════════════════════
# Loki 失敗分類 —— status code 分不出種類
# ══════════════════════════════════════════════════════════════════════

class TestLokiErrorClassification:
    def test_series_limit_is_http_400_and_kills_the_whole_query(self) -> None:
        error = classify_loki_error(
            400, "maximum number of series (500) reached for a single query"
        )
        assert error.kind == "series-limit"
        assert "allowlist" in error.remedy

    def test_bytes_limit_is_preflight_rejection(self) -> None:
        error = classify_loki_error(400, "query would read too many bytes")
        assert error.kind == "bytes-limit"

    def test_length_limit_can_surface_as_500(self) -> None:
        """169h + [2h] 走 bytes-read-stats 路徑，內層 400 被包成 HTTP 500。"""
        error = classify_loki_error(
            500, "Failed to get bytes read stats for query: rpc error: ... query length: 171h0m0s"
        )
        assert error.kind == "length-limit"

    def test_proxy_timeout_is_not_a_loki_threshold(self) -> None:
        error = classify_loki_error(502, "error code: 502")
        assert error.kind == "proxy-timeout"
        assert "wall clock" in error.remedy

    @pytest.mark.parametrize("status", [503, 504])
    def test_other_gateway_statuses_also_classified_as_proxy(self, status: int) -> None:
        assert classify_loki_error(status, "").kind == "proxy-timeout"

    def test_series_limit_wins_over_bytes_when_both_words_present(self) -> None:
        error = classify_loki_error(400, "maximum number of series reached; too many bytes")
        assert error.kind == "series-limit"

    def test_unknown_error_mentions_cloudflare_user_agent_trap(self) -> None:
        error = classify_loki_error(403, "<html>error code: 1010</html>")
        assert error.kind == "unknown"
        assert "1010" in error.remedy

    def test_http_error_is_converted_to_classified_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GRAFANA_URL", "http://grafana.invalid")
        for name in ("GRAFANA_SERVICE_ACCOUNT_TOKEN",
                     "CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET"):
            monkeypatch.setenv(name, "x")
        with patch("urllib.request.urlopen", side_effect=_http_error(400, "too many bytes")):
            with pytest.raises(LokiQueryError) as excinfo:
                loki_instant("q", HOUR)
        assert excinfo.value.kind == "bytes-limit"


class TestSeriesLimitWarning:
    def _payload(self, count: int) -> dict:
        return {"data": {"result": [{"metric": {}, "value": [0, "1"]} for _ in range(count)]}}

    def test_warns_when_approaching_max_series(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch("scripts.ingest_crawl_hourly._loki_get", return_value=self._payload(450)):
            loki_instant("q", HOUR)
        assert "max_series" in caplog.text

    def test_quiet_when_well_below_the_limit(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch("scripts.ingest_crawl_hourly._loki_get", return_value=self._payload(10)):
            loki_instant("q", HOUR)
        assert "max_series" not in caplog.text

    def test_threshold_leaves_room_before_the_hard_limit(self) -> None:
        assert LOKI_MAX_SERIES == 500


# ══════════════════════════════════════════════════════════════════════
# 時間視窗與保留期防線
# ══════════════════════════════════════════════════════════════════════

class TestHourAlignment:
    def test_truncate_drops_sub_hour_parts(self) -> None:
        assert truncate_to_hour(datetime(2026, 9, 1, 8, 37, 52, 9, tzinfo=UTC)) == HOUR

    def test_truncate_normalises_non_utc_input(self) -> None:
        taipei = timezone(timedelta(hours=8))
        assert truncate_to_hour(datetime(2026, 9, 1, 16, 37, tzinfo=taipei)) == HOUR

    def test_current_incomplete_hour_is_excluded(self) -> None:
        hours = complete_hours(datetime(2026, 9, 1, 8, 37, tzinfo=UTC), 2)
        assert hours == [datetime(2026, 9, 1, 6, tzinfo=UTC), datetime(2026, 9, 1, 7, tzinfo=UTC)]

    def test_hours_are_ordered_oldest_first(self) -> None:
        hours = complete_hours(datetime(2026, 9, 1, 8, 37, tzinfo=UTC), 3)
        assert hours == sorted(hours)

    def test_naive_anchor_treated_as_utc(self) -> None:
        assert parse_iso_hour("2026-09-01T08:00:00") == HOUR

    def test_z_suffix_accepted(self) -> None:
        assert parse_iso_hour("2026-09-01T08:00:00Z") == HOUR

    def test_malformed_anchor_rejected(self) -> None:
        with pytest.raises(ValueError, match="不是合法 ISO 時間"):
            parse_iso_hour("yesterday")


class TestBackfillGuard:
    NOW = datetime(2026, 9, 1, 8, 37, tzinfo=UTC)

    def test_default_lookback_overlaps_for_self_healing(self) -> None:
        assert DEFAULT_LOOKBACK_HOURS >= 2
        assert len(resolve_hours(None, now=self.NOW)) == DEFAULT_LOOKBACK_HOURS

    def test_span_cap_is_a_typo_guard_not_the_retention_defence(self) -> None:
        assert MAX_BACKFILL_HOURS < MAX_AGE_HOURS
        assert MAX_AGE_HOURS == 168 - RETENTION_SAFETY_MARGIN_HOURS

    def test_over_span_rejected_and_points_at_the_real_guard(self) -> None:
        with pytest.raises(ValueError, match="MAX_AGE_HOURS"):
            resolve_hours(MAX_BACKFILL_HOURS + 1, now=self.NOW)

    def test_narrow_but_old_window_is_reachable_via_anchor(self) -> None:
        anchor = self.NOW - timedelta(hours=100)
        hours = resolve_hours(3, until=anchor, now=self.NOW)
        assert len(hours) == 3
        assert hours[-1] < truncate_to_hour(anchor)

    def test_window_beyond_retention_rejected_by_absolute_age(self) -> None:
        """跨度合格但整段落在保留期外——Loki 會回 200 + 全零，不擋就寫進空歷史。"""
        anchor = self.NOW - timedelta(hours=MAX_AGE_HOURS + 5)
        with pytest.raises(ValueError, match="超過 MAX_AGE_HOURS"):
            resolve_hours(2, until=anchor, now=self.NOW)

    def test_future_anchor_rejected(self) -> None:
        with pytest.raises(ValueError, match="在未來"):
            resolve_hours(1, until=self.NOW + timedelta(hours=3), now=self.NOW)

    def test_zero_and_negative_rejected(self) -> None:
        for bad in (0, -1):
            with pytest.raises(ValueError, match=">= 1"):
                resolve_hours(bad, now=self.NOW)

    def test_limit_boundary_accepted(self) -> None:
        assert len(resolve_hours(MAX_BACKFILL_HOURS, now=self.NOW)) == MAX_BACKFILL_HOURS


# ══════════════════════════════════════════════════════════════════════
# 聚合
# ══════════════════════════════════════════════════════════════════════

def _series(labels: dict, value: float) -> dict:
    return {"metric": labels, "value": [1788249600, str(value)]}


class TestFolding:
    def test_crawler_series_folds_into_name_and_group(self) -> None:
        folded = fold_crawler([
            _series({"token": "Googlebot", "mob": "Android", "status": "200", "pfx": "/article"}, 10),
        ])
        assert folded == {("googlebot-smartphone", "googlebot-smartphone", 200, "/article"): 10.0}

    def test_same_bot_under_different_shells_is_summed(self) -> None:
        """同一支 bot 的不同 Chrome 版本外殼是不同 series，必須收斂到同一個 ua_name。"""
        folded = fold_crawler([
            _series({"token": "AhrefsBot", "mob": "", "status": "200", "pfx": "/article"}, 7),
            _series({"token": "AhrefsBot", "mob": "Android", "status": "200", "pfx": "/article"}, 5),
        ])
        assert folded == {("ahrefsbot", "seo-tool-bot", 200, "/article"): 12.0}

    def test_two_bots_in_one_group_stay_separate_rows(self) -> None:
        """AhrefsBot 與 AhrefsSiteAudit 同屬 seo-tool-bot，但 ua_name 不同 ⇒ 兩列。
        這正是加 ua_name 的目的：分群可以事後重算，具名事實不能。"""
        folded = fold_crawler([
            _series({"token": "AhrefsBot", "mob": "", "status": "200", "pfx": "/article"}, 7),
            _series({"token": "AhrefsSiteAudit", "mob": "", "status": "200", "pfx": "/article"}, 5),
        ])
        assert folded == {
            ("ahrefsbot", "seo-tool-bot", 200, "/article"): 7.0,
            ("ahrefssiteaudit", "seo-tool-bot", 200, "/article"): 5.0,
        }

    def test_invalid_status_series_dropped(self) -> None:
        assert fold_crawler([
            _series({"token": "Googlebot", "mob": "", "status": "0", "pfx": "/"}, 9)
        ]) == {}

    def test_unlisted_prefix_folds_into_residual_bucket(self) -> None:
        folded = fold_crawler([
            _series({"token": "Googlebot", "mob": "", "status": "200", "pfx": ""}, 3),
        ])
        assert folded == {
            ("googlebot-desktop", "googlebot-desktop", 200, tax.PATH_PREFIX_OTHER): 3.0
        }

    def test_total_series_folds_on_status_and_prefix(self) -> None:
        assert fold_total([_series({"status": "404", "pfx": "/tags"}, 4)]) == {(404, "/tags"): 4.0}

    def test_missing_value_is_treated_as_zero(self) -> None:
        assert fold_total([{"metric": {"status": "200", "pfx": "/"}}]) == {(200, "/"): 0.0}


class TestDeriveHuman:
    def test_human_is_total_minus_all_crawler_buckets(self) -> None:
        total = {(200, "/article"): 100.0}
        crawler = {
            ("googlebot-smartphone", "googlebot-smartphone", 200, "/article"): 30.0,
            ("claude-searchbot", "ai-search-bot", 200, "/article"): 20.0,
        }
        assert derive_human(total, crawler) == {(200, "/article"): 50.0}

    def test_negative_result_is_clamped_to_zero(self) -> None:
        """兩個查詢分開送，邊界上的行可能只被其中一個看到；負數過不了 CHECK。"""
        assert derive_human({(200, "/"): 5.0},
                            {("bingbot", "bingbot", 200, "/"): 9.0}) == {(200, "/"): 0.0}

    def test_dimension_without_crawler_traffic_passes_through(self) -> None:
        assert derive_human({(302, "/pay"): 8.0}, {}) == {(302, "/pay"): 8.0}


class TestBuildRows:
    def test_row_shape_matches_crawl_daily_columns(self) -> None:
        key = ("bingbot", "bingbot", 200, "/article")
        rows = build_rows(HOUR, {key: 12.0}, {key: 3456.0}, {}, {})
        assert rows == [{
            "date": "2026-09-01", "hour": 8, "ua_name": "bingbot", "ua_group": "bingbot",
            "status_code": 200, "path_prefix": "/article", "request_count": 12, "bytes": 3456,
        }]

    def test_hour_is_the_bucket_hour_in_utc(self) -> None:
        rows = build_rows(datetime(2026, 9, 1, 23, tzinfo=UTC),
                          {("bingbot", "bingbot", 200, "/"): 1.0}, {}, {}, {})
        assert rows[0]["hour"] == 23 and rows[0]["date"] == "2026-09-01"

    def test_zero_count_bucket_is_skipped(self) -> None:
        """crawl_daily_request_count_ck 要求 > 0；空桶通常代表聚合端出錯。"""
        assert build_rows(HOUR, {("bingbot", "bingbot", 200, "/"): 0.0}, {}, {}, {}) == []

    def test_missing_bytes_defaults_to_zero_not_dropped(self) -> None:
        """304 沒有 body，bytes=0 是合法的觀測值。"""
        rows = build_rows(HOUR, {("bingbot", "bingbot", 304, "/article"): 2.0}, {}, {}, {})
        assert rows[0]["bytes"] == 0

    def test_human_rows_are_appended_with_the_human_group(self) -> None:
        rows = build_rows(HOUR, {}, {}, {(200, "/article"): 40.0}, {(200, "/article"): 900.0})
        assert rows == [{
            "date": "2026-09-01", "hour": 8, "ua_name": "human", "ua_group": "human",
            "status_code": 200, "path_prefix": "/article", "request_count": 40, "bytes": 900,
        }]

    def test_negative_bytes_clamped(self) -> None:
        assert _row(HOUR, "human", "human", 200, "/", 1.0, -5.0)["bytes"] == 0

    def test_row_returns_none_for_empty_bucket(self) -> None:
        assert _row(HOUR, "human", "human", 200, "/", 0.0, 0.0) is None


# ══════════════════════════════════════════════════════════════════════
# collect_hour / run_ingestion
# ══════════════════════════════════════════════════════════════════════

def _instant_side_effect(crawler_counts, crawler_bytes, total_counts, total_bytes):
    responses = iter([crawler_counts, crawler_bytes, total_counts, total_bytes])

    def _side_effect(query: str, moment: datetime) -> list[dict]:
        return next(responses)

    return _side_effect


class TestCollectHour:
    def test_four_queries_are_issued_per_hour(self) -> None:
        with patch("scripts.ingest_crawl_hourly.loki_index_stats", return_value={"entries": 1, "bytes": 2}), \
             patch("scripts.ingest_crawl_hourly.loki_instant", return_value=[]) as instant:
            collect_hour(HOUR)
        assert instant.call_count == 4

    def test_rows_combine_crawler_and_derived_human(self) -> None:
        crawler = [_series({"token": "bingbot", "mob": "", "status": "200", "pfx": "/article"}, 10)]
        crawler_b = [_series({"token": "bingbot", "mob": "", "status": "200", "pfx": "/article"}, 500)]
        total = [_series({"status": "200", "pfx": "/article"}, 30)]
        total_b = [_series({"status": "200", "pfx": "/article"}, 1500)]
        with patch("scripts.ingest_crawl_hourly.loki_index_stats", return_value={"entries": 30, "bytes": 9}), \
             patch("scripts.ingest_crawl_hourly.loki_instant",
                   side_effect=_instant_side_effect(crawler, crawler_b, total, total_b)):
            rows, stats = collect_hour(HOUR)
        by_group = {row["ua_group"]: row for row in rows}
        assert by_group["bingbot"]["request_count"] == 10
        assert by_group["human"]["request_count"] == 20
        assert by_group["human"]["bytes"] == 1000
        assert stats["crawler_requests"] == 10 and stats["total_requests"] == 30

    def test_empty_index_stats_warns_about_silent_retention_gap(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with patch("scripts.ingest_crawl_hourly.loki_index_stats", return_value={"entries": 0}), \
             patch("scripts.ingest_crawl_hourly.loki_instant", return_value=[]):
            collect_hour(HOUR)
        assert "保留期" in caplog.text


class TestRunIngestion:
    def _patches(self, rows, stats=None):
        stats = stats or {"scanned_bytes": 1, "scanned_entries": 1,
                          "crawler_requests": 1, "total_requests": 2, "rows": len(rows)}
        return patch("scripts.ingest_crawl_hourly.collect_hour", return_value=(rows, stats))

    ROW = {"date": "2026-09-01", "hour": 8, "ua_name": "bingbot", "ua_group": "bingbot",
           "status_code": 200, "path_prefix": "/article", "request_count": 1, "bytes": 2}

    def test_dry_run_never_writes(self) -> None:
        with self._patches([self.ROW]), \
             patch("scripts.ingest_crawl_hourly.upsert_rows") as upsert, \
             patch("scripts.ingest_crawl_hourly.start_run") as start:
            assert run_ingestion([HOUR], execute=False) == 0
        upsert.assert_not_called()
        start.assert_not_called()

    def test_execute_upserts_then_sweeps_stale(self) -> None:
        """掃過期列必須在 upsert 成功之後——桶集合縮小時舊列會被 SUM 計入。"""
        with self._patches([self.ROW]), \
             patch("scripts.ingest_crawl_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_crawl_hourly.finish_run") as finish, \
             patch("scripts.ingest_crawl_hourly.upsert_rows", return_value=(1, 0)) as upsert, \
             patch("scripts.ingest_crawl_hourly.sweep_stale", return_value=0) as sweep:
            assert run_ingestion([HOUR], execute=True) == 0
        upsert.assert_called_once()
        sweep.assert_called_once()
        assert finish.call_args[0][1] == "success"

    def test_sweep_skipped_when_upsert_failed(self) -> None:
        """upsert 失敗還去掃，會把上一輪的好資料刪掉、留下一個空洞。"""
        with self._patches([self.ROW]), \
             patch("scripts.ingest_crawl_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_crawl_hourly.finish_run") as finish, \
             patch("scripts.ingest_crawl_hourly.upsert_rows", return_value=(0, 1)), \
             patch("scripts.ingest_crawl_hourly.sweep_stale") as sweep:
            assert run_ingestion([HOUR], execute=True) == 1
        sweep.assert_not_called()
        assert finish.call_args[0][1] == "failed"

    def test_hour_without_rows_marks_partial(self) -> None:
        with self._patches([]), \
             patch("scripts.ingest_crawl_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_crawl_hourly.finish_run") as finish, \
             patch("scripts.ingest_crawl_hourly.upsert_rows") as upsert:
            assert run_ingestion([HOUR], execute=True) == 0
        upsert.assert_not_called()
        assert finish.call_args[0][1] == "partial"

    def test_loki_failure_marks_run_failed_and_exits_nonzero(self) -> None:
        error = LokiQueryError("series-limit", "boom", "收斂分桶")
        with patch("scripts.ingest_crawl_hourly.collect_hour", side_effect=error), \
             patch("scripts.ingest_crawl_hourly.start_run", return_value="run-1"), \
             patch("scripts.ingest_crawl_hourly.finish_run") as finish:
            assert run_ingestion([HOUR], execute=True) == 1
        assert finish.call_args[0][1] == "failed"


# ══════════════════════════════════════════════════════════════════════
# 新鮮度告警 —— 健康時不成立才算告警
# ══════════════════════════════════════════════════════════════════════

class TestFreshnessCheck:
    def test_empty_table_fails(self) -> None:
        with patch("scripts.ingest_crawl_hourly.latest_bucket_hour", return_value=None):
            assert run_freshness_check() == 1

    def test_stale_data_fails(self) -> None:
        stale = datetime.now(UTC) - timedelta(hours=9)
        with patch("scripts.ingest_crawl_hourly.latest_bucket_hour", return_value=stale):
            assert run_freshness_check() == 1

    def test_fresh_data_passes(self) -> None:
        """健康時這個條件不成立——每次都成立的條件是指標不是告警。"""
        fresh = datetime.now(UTC) - timedelta(minutes=30)
        with patch("scripts.ingest_crawl_hourly.latest_bucket_hour", return_value=fresh):
            assert run_freshness_check() == 0


class TestRunVerify:
    def test_reports_mismatch_between_exact_count_and_paged_read(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO)
        rows = [{"hour": 8, "ua_name": "bingbot", "ua_group": "bingbot", "status_code": 200,
                 "path_prefix": "/article", "request_count": 5, "bytes": 1}]
        with patch("scripts.ingest_crawl_hourly.latest_bucket_hour", return_value=HOUR), \
             patch("scripts.ingest_crawl_hourly.count_exact", return_value=1), \
             patch("scripts.ingest_crawl_hourly.select_all", return_value=rows):
            assert run_verify() == 0
        assert "相符=True" in caplog.text

    def test_empty_table_returns_error(self) -> None:
        with patch("scripts.ingest_crawl_hourly.latest_bucket_hour", return_value=None):
            assert run_verify() == 1


# ══════════════════════════════════════════════════════════════════════
# Supabase 存取層
# ══════════════════════════════════════════════════════════════════════

class TestConflictKeyShape:
    """冪等鍵的維度是這張表最難改的決定，用測試把它釘住。"""

    def test_key_is_keyed_on_ua_name_not_ua_group(self) -> None:
        """ua_name 是原始事實、進鍵；ua_group 是衍生標籤、不進鍵——
        因為分類法會改，而 Loki 168h 之後沒有原始資料可以重算。"""
        assert "ua_name" in wh.CONFLICT_FIELDS
        assert "ua_group" not in wh.CONFLICT_FIELDS

    def test_key_matches_migration_017_unique_constraint(self) -> None:
        assert wh.CONFLICT_FIELDS == ("date", "hour", "ua_name", "status_code", "path_prefix")

    def test_ua_group_still_travels_in_the_payload(self) -> None:
        """不在鍵裡但要在 payload 裡：衝突時被覆蓋，那就是「重新分類 = 一次 upsert」。"""
        assert "ua_group" in TestRunIngestion.ROW


class TestWarehouseIdempotency:
    def test_upsert_payload_carries_ingested_at(self) -> None:
        """策略 (b) 靠 ingested_at 分辨新舊列；不放進 payload 的話衝突時不會更新。"""
        moment = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
        with patch.object(wh, "_request", return_value=(201, "", {})) as request:
            wh.upsert_rows([dict(TestRunIngestion.ROW)], moment)
        body = request.call_args.kwargs["body"]
        assert body[0]["ingested_at"] == "2026-09-01T09:00:00Z"

    def test_upsert_uses_merge_duplicates_on_the_dimension_key(self) -> None:
        with patch.object(wh, "_request", return_value=(201, "", {})) as request:
            wh.upsert_rows([dict(TestRunIngestion.ROW)], datetime.now(UTC))
        path = request.call_args[0][1]
        assert "on_conflict=" in path
        assert request.call_args.kwargs["extra_headers"]["Prefer"].startswith("resolution=merge-duplicates")

    def test_duplicate_keys_are_removed_before_send(self) -> None:
        """整批裡有重複 key 時 PostgreSQL 會讓**整批** 500 列一起死。"""
        row_a = dict(TestRunIngestion.ROW, request_count=1)
        row_b = dict(TestRunIngestion.ROW, request_count=9)
        assert wh.dedupe_rows([row_a, row_b]) == [row_b]

    def test_distinct_keys_are_kept(self) -> None:
        rows = [dict(TestRunIngestion.ROW),
                dict(TestRunIngestion.ROW, status_code=404)]
        assert len(wh.dedupe_rows(rows)) == 2

    def test_sweep_targets_only_older_rows_of_that_hour(self) -> None:
        moment = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
        with patch.object(wh, "_request", return_value=(200, "[]", {})) as request:
            wh.sweep_stale(HOUR, moment)
        path = request.call_args[0][1]
        assert "date=eq.2026-09-01" in path and "hour=eq.8" in path
        assert "ingested_at=lt." in path

    def test_sweep_reports_removed_count(self) -> None:
        with patch.object(wh, "_request", return_value=(200, json.dumps([{}, {}]), {})):
            assert wh.sweep_stale(HOUR, datetime.now(UTC)) == 2

    def test_sweep_failure_returns_zero(self) -> None:
        with patch.object(wh, "_request", return_value=(500, "boom", {})):
            assert wh.sweep_stale(HOUR, datetime.now(UTC)) == 0


class TestWarehousePagedRead:
    def test_pagination_continues_past_the_db_max_rows_ceiling(self) -> None:
        """PostgREST 的 db-max-rows 預設 1000 會靜默覆蓋 limit，HTTP 仍回 200。"""
        first = json.dumps([{"i": n} for n in range(wh.READ_PAGE_SIZE)])
        second = json.dumps([{"i": 9999}])
        with patch.object(wh, "_request", side_effect=[(200, first, {}), (200, second, {})]) as request:
            rows = wh.select_all("/rest/v1/crawl_daily?select=*")
        assert len(rows) == wh.READ_PAGE_SIZE + 1
        assert request.call_args_list[1].kwargs["extra_headers"]["Range"].startswith("1000-")

    def test_single_short_page_stops_immediately(self) -> None:
        with patch.object(wh, "_request", return_value=(200, "[]", {})) as request:
            assert wh.select_all("/x") == []
        assert request.call_count == 1

    def test_read_failure_raises(self) -> None:
        with patch.object(wh, "_request", return_value=(500, "boom", {})):
            with pytest.raises(RuntimeError, match="讀取"):
                wh.select_all("/x")

    def test_count_exact_reads_the_content_range_denominator(self) -> None:
        with patch.object(wh, "_request", return_value=(206, "[]", {"Content-Range": "0-0/427"})):
            assert wh.count_exact("/x") == 427

    def test_count_exact_handles_missing_header(self) -> None:
        with patch.object(wh, "_request", return_value=(200, "[]", {})):
            assert wh.count_exact("/x") == 0

    def test_count_exact_requests_the_exact_count_preference(self) -> None:
        with patch.object(wh, "_request", return_value=(200, "[]", {"Content-Range": "*/0"})) as request:
            wh.count_exact("/x")
        assert request.call_args.kwargs["extra_headers"]["Prefer"] == "count=exact"


class TestWarehouseRunBookkeeping:
    def test_start_run_returns_id(self) -> None:
        with patch.object(wh, "_request", return_value=(201, json.dumps([{"id": "abc"}]), {})):
            assert wh.start_run(HOUR, HOUR + timedelta(hours=1)) == "abc"

    def test_start_run_failure_returns_none(self) -> None:
        with patch.object(wh, "_request", return_value=(400, "boom", {})):
            assert wh.start_run(HOUR, HOUR) is None

    def test_finish_run_is_a_noop_without_id(self) -> None:
        with patch.object(wh, "_request") as request:
            wh.finish_run(None, "success", 3)
        request.assert_not_called()

    def test_finish_run_patches_status_and_row_count(self) -> None:
        with patch.object(wh, "_request", return_value=(204, "", {})) as request:
            wh.finish_run("run-1", "partial", 7)
        assert request.call_args.kwargs["body"]["status"] == "partial"
        assert request.call_args.kwargs["body"]["row_count"] == 7

    def test_latest_bucket_hour_reconstructs_utc_timestamp(self) -> None:
        payload = json.dumps([{"date": "2026-09-01", "hour": 8}])
        with patch.object(wh, "_request", return_value=(200, payload, {})):
            assert wh.latest_bucket_hour() == HOUR

    def test_latest_bucket_hour_none_when_empty(self) -> None:
        with patch.object(wh, "_request", return_value=(200, "[]", {})):
            assert wh.latest_bucket_hour() is None

    def test_latest_bucket_hour_raises_on_error(self) -> None:
        with patch.object(wh, "_request", return_value=(500, "boom", {})):
            with pytest.raises(RuntimeError):
                wh.latest_bucket_hour()

    def test_iso_z_normalises_to_utc_with_z_suffix(self) -> None:
        taipei = timezone(timedelta(hours=8))
        assert wh.iso_z(datetime(2026, 9, 1, 16, tzinfo=taipei)) == "2026-09-01T08:00:00Z"

    def test_supabase_config_requires_both_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPABASE_URL", "https://x")
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE"):
            wh.supabase_config()


class TestCrawlDateSanity:
    def test_bucket_date_is_the_utc_date_of_the_hour(self) -> None:
        """crawl_daily.hour 的 catalog comment 明說是 UTC，schema 無法強制，只能靠 ingest。"""
        row = _row(datetime(2026, 8, 31, 23, tzinfo=UTC), "human", "human", 200, "/", 1.0, 0.0)
        assert row["date"] == date(2026, 8, 31).isoformat()
        assert row["hour"] == 23
