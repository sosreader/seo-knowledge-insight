"""probe_gsc_sitemaps_api.py — 一次性探測 GSC Sitemaps API 的真實回應長相

不寫資料庫，只印出 GET .../sitemaps 的原始 JSON（拿掉不需要的雜訊）。
用途：在動手蓋 ingestion 管線 / migration 之前，先確認 `contents[].indexed`
欄位在這個 property 上到底回不回得出非零值——Google 多年前已在 Search Console UI
拿掉 sitemap 報表的「已編入索引」數字，這個欄位很可能一律是 0 或不存在。
若是，整條「以 indexed 為核心指標」的管線就不值得建，要先回報再决定替代方案。

認證沿用 ingest_gsc_search_analytics.py 的 service account 路徑
（GSC_READONLY_KEY 環境變數，非檔案路徑）。scope 先用既有的
webmasters.readonly 試——Sitemaps API 讀取理論上這個 scope 夠用，
若回 403 才代表要 webmasters 完整 scope，那需要使用者去 GCP 那邊授權，
不是本腳本能自己解決的事。

用法：python scripts/probe_gsc_sitemaps_api.py
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingest_gsc_search_analytics import (  # noqa: E402
    HTTP_TIMEOUT_SECONDS,
    PROPERTY,
    USER_AGENT,
    _service_account_info,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("probe_gsc_sitemaps_api")

SITEMAPS_URL = "https://www.googleapis.com/webmasters/v3/sites/{site}/sitemaps"
SITEMAPS_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


def sitemaps_access_token() -> str:
    """換一張只帶 webmasters.readonly scope 的 token，供 Sitemaps API 用。"""
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_info(
        _service_account_info(), scopes=[SITEMAPS_SCOPE]
    )
    credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise RuntimeError("取得 GSC access token 失敗（refresh 後 token 為空）")
    return credentials.token


def fetch_sitemaps(token: str) -> dict:
    url = SITEMAPS_URL.format(site=urllib.parse.quote(PROPERTY, safe=""))
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        logger.error("HTTP %s：%s", exc.code, body[:500])
        raise
    except urllib.error.URLError as exc:
        logger.error("連線失敗：%s", exc.reason)
        raise


def main() -> None:
    logger.info("property=%s", PROPERTY)
    token = sitemaps_access_token()
    payload = fetch_sitemaps(token)

    entries = payload.get("sitemap", [])
    logger.info("raw keys=%s，sitemap 分片數=%d", list(payload.keys()), len(entries))
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    # 每個分片底下 contents[] 才是 {type, submitted, indexed} 所在——不是分片本身的欄位。
    indexed_values: set = set()
    submitted_values: set = set()
    for entry in entries:
        for content in entry.get("contents", []):
            indexed_values.add(content.get("indexed"))
            submitted_values.add(content.get("submitted"))
    logger.info("contents[].indexed 出現的相異值集合：%s", indexed_values)
    logger.info("contents[].submitted 出現的相異值集合：%s", submitted_values)


if __name__ == "__main__":
    main()
