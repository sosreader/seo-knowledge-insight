"""ingest_gsc_url_inspection.py — 用 GSC URL Inspection API 抽樣查索引狀態，寫進 Supabase gsc_url_inspection

資料流：sitemap（vocus.cc）+ gsc_daily_metrics（既有曝光資料）→ 抽樣挑 URL →
urlInspection.index.inspect API（Google）→ Supabase upsert。取代 CrawledNotIndexedPanel
目前「人工從 GSC 介面複製 TSV 貼上」的流程。

用法（旗標細節見 --help）：--dry-run（預設，仍會打真的 API，只是不寫庫）／
--execute [--sample-size N] [--quota-budget N]／--verify（唯讀檢查）／
--check-freshness（新鮮度告警，stale 則 exit 1）。環境變數：GSC_READONLY_KEY（service
account 的 JSON **字串**，與 ingest_gsc_search_analytics.py 共用同一把唯讀 SA）、
SUPABASE_URL / SUPABASE_SERVICE_KEY。

倉儲只知道每頁拿到多少曝光，不知道零曝光的頁是「沒人搜」還是「Google 根本沒收錄」——
兩者處置相反（內容/關鍵字問題 vs 技術 SEO 問題）。本管線補的是這個判別力，抽樣策略
因此要服務這個目的，不是「隨機抽一些」，見下方「抽樣優先序」。

═══ 配額：2,000 QPD 綁在 property 本身（不是我們的 GCP 專案），重置機制未經證實 ═══

來源：`.verification/2026-08-29-seo-capability/S1.2-gsc-api-facts.md` 第 3 節 + team-lead
對官方 limits 頁的複驗（原文「calls querying the same site」）。**這 2,000
是 property 級共用桶，任何呼叫這個 property 的人都共用它**（不同 SA／專案皆算），
API 不回傳剩餘額度，只在超限回 429。因此「本地計數 < 上限」**不等於**「還打得動」
——本地計數只是我們對自己的自我克制，真正剩多少取決於看不到的其他呼叫方。429 是
一等公民：立刻停止、記錄、回報「因外部配額壓力停止」，**不重試**
（`QuotaExhaustedError`）。`sitemaps.*`（gsc-sitemap-ops 用的）是不同 resource、獨立
配額桶，**不吃這 2,000**；真正共用這桶的是「誰在呼叫這個 property 的 URL
Inspection」，程式端無法得知，需人去 GSC 後台「設定→使用者和權限」查。

重置機制官方**沒有明文寫**（S1.2 第 94 行標記未查證），因此不假設 UTC 午夜歸零，
改用「本地滾動視窗」：每次呼叫的次數持久化進 ingestion_run 的獨立分類帳列
（table_name='gsc_url_inspection_quota'，非真實資料表，借用既有「一次作業一列」
結構），過去 24 小時加總＝保守估計已用量。兩種真實情況都安全：真是午夜歸零，滾動
視窗只是保守；真是滾動窗，寫死午夜歸零會在錯的時間點放行——**程式裡沒有任何「今天
過了就重置」的邏輯**。DEFAULT_QUOTA_BUDGET=500 遠低於硬限制 2,000，留給看不到的
其他呼叫方安全邊界；QUOTA_HARD_CEILING=2000 是 CLI 也蓋不過的天花板。配額是「打
API 就算數」不是「寫庫才算數」——連 --dry-run 都會打真的 inspect API，分類帳紀錄
因此不因 execute 與否而跳過。達到本地自我設限或撞到即時 429 都是**成功結束**：
回報「因配額上限停止，已處理 N 筆」，exit 0。

═══ 抽樣優先序 —— 為什麼這樣抽 ═══

三層，依序遞補到 sample-size 或配額用完為止（① 保留優先席次，不被配額排擠掉）：

  ① 對照組（固定不變）：從 sitemap-0.xml（vocus.cc 站台結構頁，實測 180 筆，見 KB
     S1.7 內鏈基線）取固定子集，**每次都查同一批**——沒有它就無法區分「這頁狀態
     變了」與「抽樣抽到不同頁」。子集用 URL 的 sha256 排序取前 N，不用字母序／
     抓取順序：字母序在 sitemap 增刪項目時會整批位移，hash 排序更穩固。

  ② 零曝光舊頁：sitemap-articles-*.xml / article-news.xml（真實內容頁）裡 lastmod
     超過 RECENT_THRESHOLD_DAYS 天、但 gsc_daily_metrics 從未出現過的 URL——頁面
     存在夠久理應被爬過卻零曝光，是本管線要解答的核心問題。

  ③ 零曝光新頁：同上頁池但 lastmod 在門檻天數內，優先序排在②之後（剛發布還沒曝光
     本來就正常）。lastmod 缺失視為「無法確認是最近的」，保守歸進②。

  tags/sitemap.xml **刻意排除**：KB S1.7 實測死鏈率 50%，對診斷沒有價值，只會浪費配額。

═══ vocus.cc sitemap 結構與站台影響／dry-run 也是真的呼叫 ═══

來源：KB S1.7 00-sampling-plan.md（2026-08-29 實測）。`/sitemap.xml` 404，正解是
`/sitemap-index.xml`（200，15 個子 sitemap，合計 12,630 筆 URL，「近期滾動視窗」非
全站清單，不影響本管線——只要「sitemap 有列、但零曝光」的子集）。不寫死 15 個子
sitemap 檔名：先抓 index 拿 `<loc>` 清單再逐一抓（MAX_SUB_SITEMAPS 安全上限）。
**唯一**會直接打 vocus.cc 的是這段抓 sitemap 樹（至多 1+MAX_SUB_SITEMAPS 次請求，
對比 KB S1.7 實測 Envoy 24h 平均 98.44 RPS 不構成站台負擔）——URL Inspection 本身
打的是 Google 的 API，Google 代替我們看 vocus.cc。

沿用 search analytics 那支腳本的慣例：--dry-run 一樣走完配額檢查、抓 sitemap、算候選、
打 urlInspection API，只最後一步不寫 Supabase，這樣才是對「認證通過、API 可解析、
抽樣清單合理」的真實驗證，配額分類帳紀錄因此不能因 --dry-run 而跳過。

═══ 索引狀態的值域處理 —— 未知值是錯誤，不是警告 ═══

indexing_state 綁死 migration 015 定義的官方 enum（5 個值）。Google 新增新值時本檔
**拒絕該筆並記進 errors**（不是 warnings，也不讓它直接撞 DB 的 CHECK，PostgREST
批次一筆違規會讓整批一起死）——migration 015 原文：「新分類需要人看一眼，不該靠
'unknown' 桶藏起來」。coverage_state 刻意不綁 enum（會隨介面文案改動），只驗長度
1-200，超界算 warnings。可選欄位（如 last_crawl）一律補 None 而非省略鍵，理由同上：
省略鍵在批次 upsert 時會讓 PostgREST 因鍵集合不一致整批 400（見 _attach_last_crawl）。

═══ 0 筆的三種樣貌 —— 只有一種是真的失敗 ═══

  (1) sitemap 母體整批是空的（含對照組）→ 硬失敗（三層抽樣池同時掛零不合理，多半抓取或曝光比對邏輯本身壞了）。
  (2) 配額一開始就不夠（本地帳本已用滿）→ 不查任何 URL，**成功**。
  (3) 配額在查詢途中被打光（即時 429）→ 提前停止，已處理的部分照常寫入，**成功**。
  (2)(3) 與 (1) 不可混為一談：前者是「該有的資料生不出來」，後兩者是「配額守門正常運作」，判別式見 run_ingestion / _finalize_run。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

# defusedxml 延遲 import 進 _http_get_xml()（同範本 gsc_access_token() 對 google-auth
# 的處理）：--verify／--check-freshness 不碰 sitemap，模組層 import 會逼它們也要裝這個
# 套件——CI 上真的踩過（freshness job 只裝 python-dotenv）。型別仍從 stdlib 取。
from xml.etree.ElementTree import Element, ParseError

# 直接重用 ingest_gsc_search_analytics.py 的認證／傳輸層。直接執行本檔時 Python 只會
# 把 scripts/ 本身放進 sys.path，找不到 `scripts.` 套件層級，故先插入 repo 根目錄。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ingest_gsc_search_analytics import (
    HTTP_TIMEOUT_SECONDS,
    PAGE_NOT_REQUESTED as PAGE_COMBO_SENTINEL,
    PROPERTY,
    GscQueryError,
    _supabase_request,
    classify_gsc_error,
    gsc_access_token,
    supabase_config,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest_gsc_url_inspection")

# ══════════════════════════════════════════════════════════════════════
# GSC URL Inspection API
# ══════════════════════════════════════════════════════════════════════

GSC_INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
USER_AGENT = "seo-knowledge-insight-gsc-url-inspection/1.0"
# property 是參數不是寫死的事實（vocus.cc 有兩個已驗證 property，若配額各自獨立可能是
# 槓桿，未證實）；下游函式一律吃 property 參數不直接引用模組層常數，多一呼叫端就能分流。
DEFAULT_PROPERTY = PROPERTY

# 官方文件確認的 indexingState 值域（migration 015 同步照抄，兩邊必須一致）。
INDEXING_STATE_ALLOWED = frozenset({
    "INDEXING_STATE_UNSPECIFIED",
    "INDEXING_ALLOWED",
    "BLOCKED_BY_META_TAG",
    "BLOCKED_BY_HTTP_HEADER",
    "BLOCKED_BY_ROBOTS_TXT",
})
MAX_COVERAGE_STATE_CHARS = 200
MIN_URL_OCTETS = 8
MAX_URL_OCTETS = 1024


class QuotaExhaustedError(GscQueryError):
    """Google 端即時回報 429。與本地配額帳本的 remaining 是兩件事——本地帳本是保守
    估計，即時 429 是最終真相（可能是同 property 的其他呼叫方先用掉了配額）。"""


def _inspect_post(token: str, url: str, *, property: str = DEFAULT_PROPERTY) -> dict:
    request = urllib.request.Request(
        GSC_INSPECT_URL,
        data=json.dumps({"inspectionUrl": url, "siteUrl": property}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        if exc.code == 429:
            raise QuotaExhaustedError(f"HTTP 429：超出 QPS/QPD 配額。{body[:200]}") from exc
        raise classify_gsc_error(exc.code, body) from exc
    except urllib.error.URLError as exc:
        raise GscQueryError(f"連線失敗：{exc.reason}") from exc


def inspect_url(token: str, url: str, *, property: str = DEFAULT_PROPERTY) -> dict:
    """呼叫一次 inspect，回傳 indexStatusResult（可能是空 dict——Google 從未見過該 URL 時）。"""
    payload = _inspect_post(token, url, property=property)
    return payload.get("inspectionResult", {}).get("indexStatusResult", {})


def _parse_gsc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def result_to_record(
    url: str, index_status: Mapping[str, Any], *, inspected_at: str,
    errors: list[str], warnings: list[str], property: str = DEFAULT_PROPERTY,
) -> dict | None:
    """indexStatusResult → gsc_url_inspection 的一列。不合法回 None。理由見模組 docstring
    「索引狀態的值域處理」：indexing_state 未知值進 errors，其餘資料形狀問題進 warnings。
    """
    if not index_status:
        warnings.append(f"{url}：回應沒有 indexStatusResult（Google 從未見過這個 URL）")
        return None
    coverage_state = str(index_status.get("coverageState", "")).strip()
    indexing_state = str(index_status.get("indexingState", "")).strip()

    if indexing_state not in INDEXING_STATE_ALLOWED:
        errors.append(f"{url}：indexingState 出現未知值 {indexing_state!r}，需要人工確認新分類")
        return None
    if not (1 <= len(coverage_state) <= MAX_COVERAGE_STATE_CHARS):
        warnings.append(f"{url}：coverageState 長度 {len(coverage_state)} 不在 1-200 範圍")
        return None
    if not url.startswith(("http://", "https://")) or not (MIN_URL_OCTETS <= len(url.encode()) <= MAX_URL_OCTETS):
        warnings.append(f"{url}：url 不合法或長度超界")
        return None

    record: dict = {
        "property": property, "url": url, "inspected_at": inspected_at,
        "coverage_state": coverage_state, "indexing_state": indexing_state,
        "ingested_at": inspected_at,
    }
    _attach_last_crawl(record, index_status.get("lastCrawlTime"), inspected_at, url, warnings)
    return record


def _attach_last_crawl(
    record: dict, last_crawl: str | None, inspected_at: str, url: str, warnings: list[str],
) -> None:
    """last_crawl 一律寫進 record（缺席或不合法時明確填 None），絕不省略這個鍵：
    upsert 整批送出，PostgREST 要求同批每個物件鍵集合完全一致（PGRST102 "All
    object keys must match"），省略鍵讓「Google 從未爬過」（本管線最想找到的那類）
    整批 400（live 事故：run 33609190700，20 筆全滅）。last_crawl 的 CHECK 是
    `last_crawl <= inspected_at`，違反代表時區處理寫錯，丟棄值（設 None）而非
    讓它撞 CHECK 拖垮整批。"""
    record["last_crawl"] = None
    if not last_crawl:
        return
    try:
        crawl_dt = _parse_gsc_timestamp(last_crawl)
        inspected_dt = _parse_gsc_timestamp(inspected_at)
    except ValueError:
        warnings.append(f"{url}：lastCrawlTime {last_crawl!r} 格式無法解析，丟棄該欄位")
        return
    if crawl_dt > inspected_dt:
        warnings.append(f"{url}：lastCrawlTime 晚於本次查詢時間，時區處理可能有誤，丟棄該欄位")
        return
    record["last_crawl"] = last_crawl


# ══════════════════════════════════════════════════════════════════════
# sitemap 抽樣母體
# ══════════════════════════════════════════════════════════════════════

SITEMAP_INDEX_URL = "https://vocus.cc/sitemap-index.xml"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_SUB_SITEMAPS = 20  # 見模組 docstring「唯一會直接打 vocus.cc 的地方」


class SitemapFetchError(RuntimeError):
    """抓 sitemap 失敗，與 GscQueryError 同一等級的系統性硬失敗（規則 (c)）。"""


def _http_get_xml(url: str) -> Element:
    import defusedxml.ElementTree as DefusedET  # 延遲 import，理由見模組頂部註解
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return DefusedET.fromstring(response.read())
    except urllib.error.HTTPError as exc:
        raise SitemapFetchError(f"HTTP {exc.code} 取得 {url} 失敗") from exc
    except urllib.error.URLError as exc:
        raise SitemapFetchError(f"連線失敗 {url}：{exc.reason}") from exc
    except ParseError as exc:
        raise SitemapFetchError(f"{url} 回傳的內容不是合法 XML：{exc}") from exc


def list_sub_sitemaps(index_url: str = SITEMAP_INDEX_URL) -> list[str]:
    root = _http_get_xml(index_url)
    locs = [el.text.strip() for el in root.iter(f"{SITEMAP_NS}loc") if el.text]
    if not locs:
        raise SitemapFetchError(f"{index_url} 沒有任何 <sitemap><loc>——sitemap 結構可能變了")
    if len(locs) > MAX_SUB_SITEMAPS:
        logger.warning("sitemap index 有 %d 個子 sitemap，超過安全上限 %d，只取前 %d 個",
                       len(locs), MAX_SUB_SITEMAPS, MAX_SUB_SITEMAPS)
    return locs[:MAX_SUB_SITEMAPS]


def classify_sub_sitemap(url: str) -> str | None:
    """回傳 'structural' / 'article' / None（None＝排除）。判準見模組 docstring
    「抽樣優先序」：tags/sitemap.xml 死鏈率 50%，排除；sitemap-0.xml 是站台結構頁，
    其餘視為真實內容頁。"""
    if url.endswith("/tags/sitemap.xml"):
        return None
    if url.rsplit("/", 1)[-1] == "sitemap-0.xml":
        return "structural"
    return "article"


def _parse_lastmod(text: str | None) -> date | None:
    if not text:
        return None
    try:
        return date.fromisoformat(text.strip()[:10])
    except ValueError:
        return None


def list_url_entries(root: Element) -> list[tuple[str, date | None]]:
    entries: list[tuple[str, date | None]] = []
    for url_el in root.iter(f"{SITEMAP_NS}url"):
        loc_el = url_el.find(f"{SITEMAP_NS}loc")
        if loc_el is None or not loc_el.text:
            continue
        lastmod_el = url_el.find(f"{SITEMAP_NS}lastmod")
        lastmod = _parse_lastmod(lastmod_el.text if lastmod_el is not None else None)
        entries.append((loc_el.text.strip(), lastmod))
    return entries


def fetch_sitemap_pool() -> tuple[list[tuple[str, date | None]], list[tuple[str, date | None]]]:
    """回傳 (article_entries, structural_entries)。任一子 sitemap 抓失敗只跳過該檔並警告；
    全部都失敗才是硬失敗（規則 (c)：抓不到不能靜默呈現成 0）。"""
    sub_urls = list_sub_sitemaps()
    articles: list[tuple[str, date | None]] = []
    structural: list[tuple[str, date | None]] = []
    attempted = ok = excluded = 0
    for sub_url in sub_urls:
        kind = classify_sub_sitemap(sub_url)
        if kind is None:
            excluded += 1
            continue
        attempted += 1
        try:
            root = _http_get_xml(sub_url)
        except SitemapFetchError as exc:
            logger.warning("略過子 sitemap %s：%s", sub_url, exc)
            continue
        ok += 1
        entries = list_url_entries(root)
        (articles if kind == "article" else structural).extend(entries)
    if attempted and ok == 0:
        raise SitemapFetchError("全部子 sitemap 抓取失敗，視為硬失敗（規則 (c)）")
    logger.info("sitemap 母體：%d 篇文章頁 / %d 個結構頁（%d/%d 個子 sitemap 成功抓取，%d 個依規則排除）",
               len(articles), len(structural), ok, attempted, excluded)
    return articles, structural


# ══════════════════════════════════════════════════════════════════════
# 零曝光比對與抽樣分層
# ══════════════════════════════════════════════════════════════════════

GSC_DAILY_METRICS_TABLE = "gsc_daily_metrics"
IMPRESSION_LOOKUP_PAGE_SIZE = 5000
RECENT_THRESHOLD_DAYS = 14
CONTROL_SET_SIZE = 20


def fetch_pages_with_any_impressions() -> set[str]:
    """gsc_daily_metrics 裡曾經出現過（page 組合）的全部 page 值，用來反推「從沒出現過」
    的 sitemap URL。分頁抓 page 欄，本地用 set 去重——PostgREST 沒有 DISTINCT 關鍵字，
    這張表目前資料量還小，可負擔用這個方式取代寫一支 RPC。"""
    seen: set[str] = set()
    offset = 0
    url, key = supabase_config()
    while True:
        headers = {
            "apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT,
            "Range-Unit": "items", "Range": f"{offset}-{offset + IMPRESSION_LOOKUP_PAGE_SIZE - 1}",
        }
        path = (f"/rest/v1/{GSC_DAILY_METRICS_TABLE}?select=page"
                f"&page=neq.{urllib.parse.quote(PAGE_COMBO_SENTINEL, safe='')}")
        request = urllib.request.Request(url + path, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                batch = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"查詢 {GSC_DAILY_METRICS_TABLE} 失敗：{exc.code} {exc.read().decode(errors='replace')[:200]}"
            ) from exc
        if not batch:
            break
        seen.update(row["page"] for row in batch)
        if len(batch) < IMPRESSION_LOOKUP_PAGE_SIZE:
            break
        offset += IMPRESSION_LOOKUP_PAGE_SIZE
    return seen


def build_control_set(structural_entries: list[tuple[str, date | None]]) -> list[str]:
    """固定對照組。用 URL 的 sha256 排序取前 N，不用字母序或抓取順序——
    理由見模組 docstring「抽樣優先序」①。"""
    unique_urls = sorted(
        {u for u, _ in structural_entries},
        key=lambda u: hashlib.sha256(u.encode()).hexdigest(),
    )
    return unique_urls[:CONTROL_SET_SIZE]


def split_zero_impression_tiers(
    article_entries: list[tuple[str, date | None]], has_impressions: set[str], today: date,
) -> tuple[list[str], list[str]]:
    """回傳 (tier1_older_zero_impression, tier2_recent_zero_impression)。
    lastmod 缺失視為「無法確認是最近的」，保守歸進 tier1（見模組 docstring ②③）。"""
    tier1: list[str] = []
    tier2: list[str] = []
    seen_in_pool: set[str] = set()
    for url, lastmod in article_entries:
        if url in seen_in_pool or url in has_impressions:
            continue
        seen_in_pool.add(url)
        if lastmod is not None and (today - lastmod).days <= RECENT_THRESHOLD_DAYS:
            tier2.append(url)
        else:
            tier1.append(url)
    return tier1, tier2


def build_sample(control_set: list[str], tier1: list[str], tier2: list[str], budget: int) -> list[str]:
    """依優先序組出本次要查的 URL 清單，總數不超過 budget。對照組保留優先席次
    （見模組 docstring ①：不能被配額排擠掉），其餘依 ②→③ 順序遞補。"""
    sample: list[str] = []
    seen: set[str] = set()
    for pool in (control_set, tier1, tier2):
        for candidate_url in pool:
            if len(sample) >= budget:
                return sample
            if candidate_url in seen:
                continue
            seen.add(candidate_url)
            sample.append(candidate_url)
    return sample


# ══════════════════════════════════════════════════════════════════════
# 配額分類帳（見模組 docstring「配額」）
# ══════════════════════════════════════════════════════════════════════

TABLE_RUN = "ingestion_run"
TABLE_URL_INSPECTION = "gsc_url_inspection"
QUOTA_LEDGER_TABLE_NAME = "gsc_url_inspection_quota"

QUOTA_HARD_CEILING = 2000    # Google 官方 2,000 QPD／property，CLI 不可蓋過
DEFAULT_QUOTA_BUDGET = 500   # 自我設限，留給同 property 上看不到的其他呼叫方安全邊界
MIN_QUOTA_BUDGET = 1
QUOTA_ROLLING_WINDOW_HOURS = 24


def quota_used_last_24h() -> int:
    """過去 24 小時（以我們自己 ledger 的 started_at 為準的滾動視窗，非 UTC 午夜）
    已消耗的配額。理由見模組 docstring「配額」。分類帳目前是單一全域桶，未依 property
    分——預設只用一個 property；未來若真啟用第二個，這裡要先改成依 property 分桶，
    否則兩個 property 的用量會被誤算成同一份。"""
    since = datetime.now(timezone.utc) - timedelta(hours=QUOTA_ROLLING_WINDOW_HOURS)
    since_str = urllib.parse.quote(since.isoformat().replace("+00:00", "Z"), safe="")
    status, body = _supabase_request(
        "GET",
        f"/rest/v1/{TABLE_RUN}?select=row_count&table_name=eq.{QUOTA_LEDGER_TABLE_NAME}"
        f"&started_at=gte.{since_str}",
    )
    if status != 200:
        raise RuntimeError(f"查詢配額分類帳失敗：{status} {body[:200]}")
    return sum(row["row_count"] for row in json.loads(body))


def record_quota_usage(calls_made: int, window_start: datetime, window_end: datetime) -> None:
    """把本次實際打了幾次 inspect API 寫進分類帳——無論這些呼叫有沒有成功寫進
    gsc_url_inspection，也無論這次是不是 --dry-run（配額是打 API 就算數）。"""
    if calls_made <= 0:
        return
    _supabase_request(
        "POST", f"/rest/v1/{TABLE_RUN}",
        body=[{
            "table_name": QUOTA_LEDGER_TABLE_NAME,
            "window_start": window_start.isoformat().replace("+00:00", "Z"),
            "window_end": window_end.isoformat().replace("+00:00", "Z"),
            "row_count": calls_made,
            "status": "success",
            "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }],
        extra_headers={"Prefer": "return=minimal"},
    )


# ══════════════════════════════════════════════════════════════════════
# 逐一 inspect
# ══════════════════════════════════════════════════════════════════════

def collect_inspections(
    token: str, urls: Sequence[str], inspected_at: str, calls_counter: list[int],
    errors: list[str], warnings: list[str], *, property: str = DEFAULT_PROPERTY,
) -> tuple[list[dict], bool]:
    """逐一 inspect，回傳 (可寫入的列, 是否因配額提前停止)。calls_counter[0] 由呼叫端
    在 finally 讀出，即使中途丟例外也能記到配額分類帳。429（QuotaExhaustedError）→
    停止但不算錯誤、不重試（規則 (a)，見模組 docstring「配額」）；其他 GscQueryError
    直接往外拋，交給呼叫端中止整個 run（同範本對系統性錯誤的處理）。"""
    records: list[dict] = []
    quota_stopped = False
    for url in urls:
        calls_counter[0] += 1
        try:
            index_status = inspect_url(token, url, property=property)
        except QuotaExhaustedError:
            logger.warning("即時撞到 Google 端配額（429，因外部配額壓力停止，不重試，已打 %d 次）", calls_counter[0])
            quota_stopped = True
            break
        record = result_to_record(url, index_status, inspected_at=inspected_at,
                                   errors=errors, warnings=warnings, property=property)
        if record is not None:
            records.append(record)
    return records, quota_stopped


# ══════════════════════════════════════════════════════════════════════
# Supabase 存取（gsc_url_inspection 本體）
# ══════════════════════════════════════════════════════════════════════

CONFLICT_KEY = "property,url,inspected_on"
UPSERT_BATCH_SIZE = 500


def start_url_inspection_run(window_start: datetime, window_end: datetime) -> str | None:
    status, body = _supabase_request(
        "POST", f"/rest/v1/{TABLE_RUN}",
        body=[{
            "table_name": TABLE_URL_INSPECTION,
            "window_start": window_start.isoformat().replace("+00:00", "Z"),
            "window_end": window_end.isoformat().replace("+00:00", "Z"),
            "row_count": 0, "status": "running",
        }],
        extra_headers={"Prefer": "return=representation"},
    )
    if status not in (200, 201):
        logger.error("建立 ingestion_run 失敗：%s %s", status, body[:300])
        return None
    return json.loads(body)[0]["id"]


def finish_url_inspection_run(run_id: str | None, run_status: str, row_count: int) -> None:
    if not run_id:
        return
    status, body = _supabase_request(
        "PATCH", f"/rest/v1/{TABLE_RUN}?id=eq.{urllib.parse.quote(run_id)}",
        body={
            "status": run_status, "row_count": row_count,
            "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        extra_headers={"Prefer": "return=minimal"},
    )
    if status not in (200, 204):
        logger.error("收尾 ingestion_run 失敗：%s %s", status, body[:300])


def upsert_url_inspections(rows: Sequence[dict]) -> tuple[int, int]:
    """冪等 upsert（on_conflict 對到 gsc_url_inspection_uniq：property,url,inspected_on）。
    inspected_on 是 GENERATED 欄位，不在 payload 裡，Postgres 會從 inspected_at 算出來
    再判斷衝突。回傳 (成功列數, 失敗列數)。"""
    succeeded = failed = 0
    for offset in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[offset: offset + UPSERT_BATCH_SIZE]
        status, body = _supabase_request(
            "POST", f"/rest/v1/{TABLE_URL_INSPECTION}?on_conflict={urllib.parse.quote(CONFLICT_KEY)}",
            body=list(batch),
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        if status in (200, 201, 204):
            succeeded += len(batch)
        else:
            failed += len(batch)
            logger.error("upsert 失敗：%s %s", status, body[:400])
    return succeeded, failed


def count_url_inspection_rows() -> int:
    url, key = supabase_config()
    headers = {
        "apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT,
        "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0",
    }
    request = urllib.request.Request(
        url + f"/rest/v1/{TABLE_URL_INSPECTION}?select=url", headers=headers, method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            content_range = response.headers.get("Content-Range", "")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"count 查詢失敗：{exc.code} {exc.read().decode(errors='replace')[:200]}"
        ) from exc
    total = content_range.rsplit("/", 1)[-1]
    if not total.isdigit():
        raise RuntimeError(f"count 查詢的 Content-Range 格式異常：{content_range!r}")
    return int(total)


def latest_inspected_at() -> datetime | None:
    status, body = _supabase_request(
        "GET", f"/rest/v1/{TABLE_URL_INSPECTION}?select=inspected_at&order=inspected_at.desc&limit=1",
    )
    if status != 200:
        raise RuntimeError(f"查詢 {TABLE_URL_INSPECTION} 失敗：{status} {body[:200]}")
    payload = json.loads(body)
    return _parse_gsc_timestamp(payload[0]["inspected_at"]) if payload else None


# ══════════════════════════════════════════════════════════════════════
# 執行模式
# ══════════════════════════════════════════════════════════════════════

def _quota_gate(quota_budget: int) -> int:
    """回傳本次還能打幾次；<=0 代表本次不查（成功結束，見規則 (a)）。"""
    used = quota_used_last_24h()
    remaining = quota_budget - used
    logger.info("配額：過去 %dh 已用 %d/%d，剩餘 %d", QUOTA_ROLLING_WINDOW_HOURS, used, quota_budget, max(remaining, 0))
    return remaining


def _build_candidates(today: date) -> tuple[list[str], list[str], list[str]]:
    """回傳 (control_set, tier1, tier2)。三者皆空代表硬失敗，由呼叫端判斷（規則 (c)）。"""
    articles, structural = fetch_sitemap_pool()
    has_impressions = fetch_pages_with_any_impressions()
    control_set = build_control_set(structural)
    tier1, tier2 = split_zero_impression_tiers(articles, has_impressions, today)
    return control_set, tier1, tier2


def _finalize_run(
    records: list[dict], errors: list[str], warnings: list[str], quota_stopped: bool, execute: bool,
) -> int:
    """execute 模式收尾：寫庫、記 ingestion_run、判斷 status；dry-run 只印摘要。"""
    if not execute:
        if quota_stopped:
            logger.info("[DRY RUN] 因配額上限提前停止：可寫入 %d 列（%d 個硬問題）。", len(records), len(errors))
            return 1 if errors else 0
        logger.info("[DRY RUN] 不寫入：可寫入 %d 列（%d 個硬問題 / %d 個資料品質提醒）。加 --execute 才會 upsert。",
                    len(records), len(errors), len(warnings))
        return 1 if (errors or not records) else 0

    now = datetime.now(timezone.utc)
    run_id = start_url_inspection_run(now, now + timedelta(seconds=1))
    succeeded, failed = upsert_url_inspections(records) if records else (0, 0)
    if quota_stopped and not errors and not failed:
        run_status = "success"
        logger.info("SUCCESS（因配額上限停止）：已處理 %d 筆（寫入成功 %d）。", len(records), succeeded)
    else:
        run_status = "success" if not errors and not failed and succeeded else (
            "failed" if not succeeded else "partial"
        )
    finish_url_inspection_run(run_id, run_status, succeeded)
    logger.info("寫入完成：%d 列成功 / %d 列失敗，run status=%s（%d 個資料品質提醒）",
               succeeded, failed, run_status, len(warnings))
    return 0 if run_status == "success" else 1


def run_ingestion(
    *, execute: bool, sample_size: int, quota_budget: int, property: str = DEFAULT_PROPERTY,
) -> int:
    now = datetime.now(timezone.utc)
    run_started_at = now.isoformat().replace("+00:00", "Z")
    token = gsc_access_token()

    remaining = _quota_gate(quota_budget)
    if remaining <= 0:
        logger.info("SUCCESS（配額停止）：本次不再送出任何查詢，配額由過去 %dh 的分類帳決定。",
                    QUOTA_ROLLING_WINDOW_HOURS)
        return 0

    control_set, tier1, tier2 = _build_candidates(now.date())
    if not (control_set or tier1 or tier2):
        logger.error("FAIL：sitemap 抽樣母體是空的，視為硬失敗（規則 (c)）。")
        return 1

    target_n = min(sample_size, remaining)
    sample = build_sample(control_set, tier1, tier2, target_n)
    logger.info("本次抽樣 %d 筆（對照組池 %d／零曝光舊頁池 %d／零曝光新頁池 %d，配額剩餘 %d，sample-size 上限 %d）",
               len(sample), len(control_set), len(tier1), len(tier2), remaining, sample_size)

    errors: list[str] = []
    warnings: list[str] = []
    calls_counter = [0]
    try:
        try:
            records, quota_stopped = collect_inspections(
                token, sample, run_started_at, calls_counter, errors, warnings, property=property)
        finally:
            record_quota_usage(calls_counter[0], now, now + timedelta(seconds=1))
    except GscQueryError as exc:
        logger.error("URL Inspection 查詢失敗（系統性，中止整個 run）：%s", exc)
        return 1

    for message in warnings:
        logger.warning("  資料品質：%s", message)
    for message in errors:
        logger.error("  問題：%s", message)

    return _finalize_run(records, errors, warnings, quota_stopped, execute)


def run_verify() -> int:
    """唯讀檢查。"""
    total = count_url_inspection_rows()
    logger.info("gsc_url_inspection 總列數：%d", total)
    status, body = _supabase_request(
        "GET",
        f"/rest/v1/{TABLE_URL_INSPECTION}?select=url,inspected_on,coverage_state,indexing_state,last_crawl"
        "&order=inspected_on.desc&limit=8",
    )
    if status != 200:
        logger.error("讀取 %s 失敗：%s %s", TABLE_URL_INSPECTION, status, body[:300])
        return 1
    for row in json.loads(body):
        logger.info("  %s [%s] %s / crawl=%s", row["inspected_on"], row["indexing_state"],
                   row["url"][:70], row.get("last_crawl") or "從未")

    status, body = _supabase_request(
        "GET",
        f"/rest/v1/{TABLE_RUN}?select=id,window_start,window_end,row_count,status,finished_at"
        f"&table_name=eq.{TABLE_URL_INSPECTION}&order=started_at.desc&limit=3",
    )
    if status != 200:
        logger.error("讀取 %s 失敗：%s %s", TABLE_RUN, status, body[:300])
        return 1
    for run in json.loads(body):
        logger.info("  run %s %s..%s status=%s rows=%d finished=%s",
                   run["id"][:8], run["window_start"], run["window_end"],
                   run["status"], run["row_count"], run["finished_at"])
    return 0 if total else 1


# 見模組 docstring：inspect 是即時查詢，沒有 search analytics 那種 2-3 天固有延遲，但
# 配額可能被同 property 上看不到的其他呼叫方擠占，導致連續數天寫入 0 筆（仍是「成功」
# 的 run，見規則 (a)）。24h×2 的緩衝會誤報，抓寬到 24h×4，仍能在真的停擺時抓到。
FRESHNESS_MAX_AGE_HOURS = 24 * 4


def run_freshness_check() -> int:
    """新鮮度告警。條件是「表裡最新 inspected_at 太舊」，不是「作業有沒有回報失敗」——
    理由與範本一致：排程沒被觸發時不會產生任何失敗事件。"""
    latest = latest_inspected_at()
    if latest is None:
        logger.error("FAIL: %s 是空的，ingestion 從未成功寫入。", TABLE_URL_INSPECTION)
        return 1
    age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
    if age_hours > FRESHNESS_MAX_AGE_HOURS:
        logger.error("FAIL: %s 最新 inspected_at %s，已 %.1f 小時（門檻 %dh）。",
                     TABLE_URL_INSPECTION, latest.isoformat(), age_hours, FRESHNESS_MAX_AGE_HOURS)
        return 1
    logger.info("PASS: %s 最新 inspected_at %s（%.1f 小時前，門檻 %dh）。",
               TABLE_URL_INSPECTION, latest.isoformat(), age_hours, FRESHNESS_MAX_AGE_HOURS)
    return 0


def resolve_sample_size(value: int | None) -> int:
    size = value if value is not None else DEFAULT_SAMPLE_SIZE
    if not (MIN_SAMPLE_SIZE <= size <= MAX_SAMPLE_SIZE):
        raise ValueError(f"--sample-size {size} 超出範圍 [{MIN_SAMPLE_SIZE}, {MAX_SAMPLE_SIZE}]")
    return size


def resolve_quota_budget(value: int | None) -> int:
    budget = value if value is not None else DEFAULT_QUOTA_BUDGET
    if not (MIN_QUOTA_BUDGET <= budget <= QUOTA_HARD_CEILING):
        raise ValueError(
            f"--quota-budget {budget} 超出範圍 [{MIN_QUOTA_BUDGET}, {QUOTA_HARD_CEILING}]"
            "（上限硬釘在 Google 官方每日配額，CLI 不能蓋過）"
        )
    return budget


DEFAULT_SAMPLE_SIZE = 100
MIN_SAMPLE_SIZE = 1
MAX_SAMPLE_SIZE = 500


def main() -> None:
    parser = argparse.ArgumentParser(
        description="用 GSC URL Inspection API 抽樣查索引狀態，寫進 Supabase gsc_url_inspection"
    )
    parser.add_argument("--dry-run", action="store_true", help="打真的 API、算完、印摘要但不寫庫（預設）")
    parser.add_argument("--execute", action="store_true", help="實際 upsert 進 Supabase")
    parser.add_argument("--verify", action="store_true", help="唯讀檢查最近寫入狀態")
    parser.add_argument("--check-freshness", action="store_true",
                        help=f"新鮮度告警：最新資料超過 {FRESHNESS_MAX_AGE_HOURS}h 則 exit 1")
    parser.add_argument("--sample-size", type=int, default=None,
                        help=f"本次最多查幾個 URL（預設 {DEFAULT_SAMPLE_SIZE}，上限 {MAX_SAMPLE_SIZE}）")
    parser.add_argument("--quota-budget", type=int, default=None,
                        help=f"24 小時滾動配額自我上限（預設 {DEFAULT_QUOTA_BUDGET}，硬上限 {QUOTA_HARD_CEILING}）")
    args = parser.parse_args()

    if args.verify:
        sys.exit(run_verify())
    if args.check_freshness:
        sys.exit(run_freshness_check())

    try:
        sample_size = resolve_sample_size(args.sample_size)
        quota_budget = resolve_quota_budget(args.quota_budget)
    except ValueError as exc:
        logger.error("%s", exc)
        sys.exit(2)

    logger.info("sample-size=%d quota-budget=%d（硬上限 %d，property=%s）",
               sample_size, quota_budget, QUOTA_HARD_CEILING, DEFAULT_PROPERTY)
    if not args.execute:
        logger.info("預設為 dry-run（仍會打真的 API），加 --execute 才會寫入。")
    sys.exit(run_ingestion(execute=args.execute, sample_size=sample_size, quota_budget=quota_budget))


if __name__ == "__main__":
    main()
