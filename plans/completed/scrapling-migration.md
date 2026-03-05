# 遷移至 Scrapling：Medium 文章抓取升級

**狀態：✅ 完成（2026-03-05）**
**版本：v2.14**

---

## Context

現況：`01b_fetch_medium.py` 用 `httpx.get()` 抓 Medium，遇到 403 才 fallback Playwright（~5-10s/篇）。
Scrapling 的 `StealthyFetcher` 內建 TLS 指紋偽裝、fingerprint 隨機化，可直接繞過 Medium 403，不需啟動 headless browser（~1-2s/篇）。

**前提：Python 3.10+**（Scrapling 硬性限制）。目前 `.venv` 是 Python 3.9.6，需先升級至 3.12。
Note: `pyproject.toml` 已聲明 `requires-python = ">=3.11"`，代表 .venv 版本本來就不對。

---

## Phase 1：升級 Python 3.9 → 3.12 ✅

```bash
brew install python@3.12
rm -rf .venv
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python --version   # → Python 3.12.13
```

同步修正 `pyproject.toml`：`requires-python = ">=3.11"` → `">=3.12"`

---

## Phase 2：安裝 Scrapling ✅

```bash
.venv/bin/pip install "scrapling[fetchers]>=0.3.0"
.venv/bin/scrapling install   # 下載 Chromium（DynamicFetcher fallback 用）
```

新增到 `requirements.txt`：
```
scrapling[fetchers]>=0.3.0
```

安裝版本：scrapling-0.4.1（含 curl_cffi、patchright、playwright）

---

## Phase 3：修改 `scripts/01b_fetch_medium.py` ✅

### 替換兩個 fetch 函式，其餘完全不動

| 函式 | 修改 |
|------|------|
| `_fetch_single_url()` | httpx → `StealthyFetcher`；失敗才 fallback |
| `_fetch_single_url_playwright()` | Playwright sync_api → `DynamicFetcher` |
| `_scrape_article_urls_sitemap()` | httpx 改為局部 import `import httpx as _httpx` |
| `_strip_medium_ui_elements()` | 不動 |
| `_parse_article_html()` | 不動 |
| `_is_paywalled()` | 不動 |
| `_validate_medium_url()` | 不動 |
| `fetch_medium_articles()` | exception 捕捉從 `httpx.HTTPError` → `(ValueError, RuntimeError)` |

### 核心設計

```python
from scrapling.fetchers import StealthyFetcher, DynamicFetcher

def _fetch_single_url(url: str, use_playwright: bool = False) -> dict:
    _validate_medium_url(url)
    if use_playwright:
        return _fetch_single_url_playwright(url)
    try:
        page = StealthyFetcher(auto_match=False).fetch(url, timeout=30)
        if page.status != 200:
            raise ValueError(f"HTTP {page.status}")
        return _parse_article_html(url, page.html_content)
    except Exception as e:
        logger.info("  StealthyFetcher 失敗 (%s)，改用 DynamicFetcher: %s", e, url)
        return _fetch_single_url_playwright(url)

def _fetch_single_url_playwright(url: str) -> dict:
    """Fallback: DynamicFetcher (Scrapling's Playwright wrapper)."""
    page = DynamicFetcher(auto_match=False).fetch(
        url, timeout=30000, wait_selector="article",
    )
    return _parse_article_html(url, page.html_content)
```

---

## Phase 4：更新 `tests/test_fetch_medium.py` ✅

新增 `TestFetchSingleUrl` class，4 個測試：

- `test_fetch_single_url_uses_stealth_fetcher` — StealthyFetcher 正常路徑
- `test_fetch_single_url_fallback_to_dynamic_on_failure` — RuntimeError 觸發 fallback
- `test_fetch_single_url_validates_url` — SSRF 防護仍有效
- `test_fetch_single_url_non_200_falls_back` — HTTP 403 觸發 fallback

---

## 驗證結果

```
.venv/bin/python --version   # Python 3.12.13 ✅
tests/test_fetch_medium.py   # 28 passed ✅（+4 新增）
cd api && pnpm test          # 216 passed ✅
```

## 關鍵檔案

| 檔案 | 修改 |
|------|------|
| `scripts/01b_fetch_medium.py` | Scrapling 替換 |
| `requirements.txt` | scrapling[fetchers]>=0.3.0 |
| `pyproject.toml` | requires-python = ">=3.12" |
| `tests/test_fetch_medium.py` | +4 fetch 測試，28 passed |
