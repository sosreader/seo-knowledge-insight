"""URL Inspection 曝光比對與分層；GSC top rows 缺席不等於真實零曝光。"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from collections.abc import Iterator, Sequence

from scripts.crawl_warehouse import HTTP_TIMEOUT_SECONDS, supabase_config
from scripts.gsc_surfaces import PROPERTY

IMPRESSION_LOOKUP_PAGE_SIZE = 1000
IMPRESSION_LOOKBACK_DAYS = 28
MAX_CANDIDATE_URLS = 40
MAX_PAGE_FILTER_BYTES = 3500
USER_AGENT = "seo-knowledge-insight-gsc-url-inspection/1.0"


def _page_filter(pages: Sequence[str]) -> str:
    return "in.(" + ",".join(json.dumps(page, ensure_ascii=False) for page in pages) + ")"


def _candidate_batches(pages: Sequence[str]) -> Iterator[list[str]]:
    """page/date 已有索引；限定候選與 query 長度，避免全表掃描或 HTTP 414。"""
    if any(not isinstance(page, str) or not page.strip() for page in pages):
        raise ValueError("曝光候選必須是非空 URL 字串")
    batch: list[str] = []
    for page in sorted(set(pages)):
        proposed = [*batch, page]
        if len(proposed) > MAX_CANDIDATE_URLS or len(urllib.parse.urlencode({"page": _page_filter(proposed)})) > MAX_PAGE_FILTER_BYTES:
            if batch:
                yield batch
            proposed = [page]
        if len(urllib.parse.urlencode({"page": _page_filter(proposed)})) > MAX_PAGE_FILTER_BYTES:
            raise ValueError("曝光候選 URL 超過查詢長度上限")
        batch = proposed
    if batch:
        yield batch


def fetch_pages_with_any_impressions(
    *, pages: Sequence[str], today: date | None = None, property: str = PROPERTY,
) -> set[str]:
    """只查 sitemap 候選的固定日期窗 Web 明細；不掃整個 28 天資料表。"""
    if not pages:
        return set()
    end = today or datetime.now(timezone.utc).date()
    filters = [
        ("select", "page"), ("property", f"eq.{property}"), ("search_type", "eq.web"),
        ("date", f"gte.{end - timedelta(days=IMPRESSION_LOOKBACK_DAYS)}"),
        ("date", f"lt.{end}"), ("impressions", "gt.0"),
        ("order", "date.asc,page.asc,device.asc"),
    ]
    url, key = supabase_config()
    seen: set[str] = set()
    for batch in _candidate_batches(pages):
        query = urllib.parse.urlencode([*filters, ("page", _page_filter(batch))])
        seen.update(_fetch_batch(f"{url}/rest/v1/gsc_page_daily?{query}", key))
    return seen


def _fetch_batch(url: str, key: str) -> set[str]:
    seen: set[str] = set()
    offset = 0
    while True:
        request = urllib.request.Request(url, headers={
            "apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT,
            "Range-Unit": "items", "Range": f"{offset}-{offset + IMPRESSION_LOOKUP_PAGE_SIZE - 1}",
        })
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                batch = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"查詢曝光資料失敗：HTTP {exc.code}") from exc
        if not isinstance(batch, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("page"), str) or not row["page"].strip()
            for row in batch
        ):
            raise ValueError("曝光查詢回應必須是含有效 page 字串的列陣列")
        seen.update(row["page"] for row in batch)
        if len(batch) < IMPRESSION_LOOKUP_PAGE_SIZE:
            return seen
        offset += len(batch)


def build_sample(
    control_set: list[str], tier1: list[str], tier2: list[str], budget: int,
    *, today: date | None = None,
) -> list[str]:
    """20% 對照／60% 舊頁／20% 新頁；空席遞補、文章每日穩定洗牌。

    budget=20 為 4/12/4；budget=1/2 優先對照、再舊頁。不增加配額。
    同日同候選集可重現；固定對照不輪替，文章不依 sitemap 讀取順序決定。
    """
    if budget <= 0:
        return []
    control_slots = max(1, budget // 5)
    recent_slots = max(1, budget // 5) if budget >= 3 else 0
    quotas = (control_slots, budget - control_slots - recent_slots, recent_slots)
    pools = [list(dict.fromkeys(pool)) for pool in (control_set, tier1, tier2)]
    if today is not None:
        pools = [pools[0], *[
            sorted(pool, key=lambda url: hashlib.sha256(f"{today}:{url}".encode()).digest())
            for pool in pools[1:]
        ]]
    selected: list[str] = []
    seen: set[str] = set()

    def take(pool: list[str], count: int) -> None:
        for url in pool:
            if count <= 0 or len(selected) >= budget:
                break
            if url not in seen:
                selected.append(url)
                seen.add(url)
                count -= 1

    for pool, quota in zip(pools, quotas):
        take(pool, quota)
    for pool in (pools[1], pools[2], pools[0]):
        take(pool, budget - len(selected))
    return selected
