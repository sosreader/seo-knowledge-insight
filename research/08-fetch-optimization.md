# Fetch 流程優化

## 現狀分析

### 痛點

- 每次 fetch 掃 3103 個 block（即使大多數不是 child_page）
- 完整增量比對在「列舉步驟」後，已經浪費 API
- max_depth=10 導致不必要的遞迴
- 逐個頁面等待 blocks，未充分並發

### 成本

- **API 調用**：列舉子頁面 ~40-50 次（3103÷100），每個頁面再額外調用 5-10 次（遞迴）
- **時間**：單次 full fetch ~15-30 分鐘
- **Rate limit 風險**：容易觸發 429

---

## 改進方案

### Phase 1：增量索引與時間戳

**目標**：支持只 fetch 近期更新的頁面

**改動**：

1. `meetings_index.json` 新增 `"last_checked_time": "2026-02-28T10:00:00.000Z"`
2. 支持 `--since` 參數（例如 `--since 2026-02-27`）
3. 在 list_child_pages 前篩選：只列舉滿足條件的頁面

**預期效果**：

- 日常增量 fetch：從 3103→~50-100 個 block 掃描
- 減少 80% 的列舉成本

### Phase 2：Blocks 遞迴深度優化

**目標**：減少不必要的遞迴

**改動**：

1. 將 `max_depth=10` 改為 `--block-depth 2` 可配置
2. 對於表格、列表等常見結構，手動控制深度
3. Skip 已知「不含實質內容」的 block 類型（separator, divider 等）

**預期效果**：

- 減少 30-40% 的遞迴 API 調用
- 加快 blocks 讀取 20%

### Phase 3：並發與智能列舉

**目標**：加速頁面 blocks 抓取 & 優化列舉

**改動**：

1. `fetch_blocks_recursive()` 改為並發（semaphore 限制併發數 ≤5）
2. `_list_page_children()` 改為「快速掃一遍找 child_page，然後 break」
3. 支持 Notion 資料庫模式（如果改為資料庫，直接用 query API）

**預期效果**：

- 並發 5 個頁面：從 15 分鐘→3-5 分鐘
- 列舉步驟完全跳過（對增量 fetch）

---

## 優先級排序

1. **立即** — Phase 1（增量索引）✅ — 低風險，效果最大
2. **次優** — Phase 2（深度優化）✅ — 容易測試
3. **後續** — Phase 3（並發）✅ — 需要更多測試

---

## 配置建議

新增 `.env` 參數：

```bash
# 最大 block 遞迴深度（預設 3）
NOTION_BLOCK_MAX_DEPTH=3

# 並發抓取 blocks 數（預設 5）
NOTION_FETCH_CONCURRENCY=5

# 列舉超時（秒）
NOTION_LIST_TIMEOUT=10
```

---

## CLI 用法擴展

```bash
# 完整 fetch（全量）
python scripts/01_fetch_notion.py

# 增量：只抓最近 7 天更新的
python scripts/01_fetch_notion.py --since 2026-02-21

# 控制遞迴深度（測試用）
python scripts/01_fetch_notion.py --block-depth 1 --limit 5

# 強制全量（保留舊用法）
python scripts/01_fetch_notion.py --force
```

---

## 多來源爬取架構（v2.6+，2026-03-05）

v2.6 起擴展至 4 個獨立 fetcher，各來源有不同的爬取策略和優化手段。

### 來源對照表

| Fetcher | 腳本 | 來源格式 | 輸出目錄 | 策略 |
|---------|------|---------|---------|------|
| Notion | `01_fetch_notion.py` | API（blocks 遞迴） | `raw_data/markdown/` | 增量索引 + ETag |
| Medium | `01b_fetch_medium.py` | RSS + HTML（Scrapling） | `raw_data/medium_markdown/` | StealthyFetcher + DynamicFetcher fallback |
| iThome | `01c_fetch_ithelp.py` | HTML scraping | `raw_data/ithelp_markdown/` | 靜態 HTML 解析 |
| Google Cases | `01d_fetch_google_cases.py` | HTML scraping | `raw_data/google_cases_markdown/` | 靜態 HTML 解析 |

### Medium 爬取優化（v2.15 + v2.19）

**挑戰**：Medium 有反爬機制（JavaScript shell、rate limiting）。

**解法**：

```python
# 主路徑：StealthyFetcher（~4s/篇，不需 browser）
page = StealthyFetcher.fetch(url)

# Fallback：DynamicFetcher（JS shell 偵測後，啟動 headless browser）
if _is_js_shell(page):
    page = DynamicFetcher.fetch(url)
```

**v2.19 Noise 清除**：Medium 文章轉 Markdown 後包含大量 UI 噪音。雙層清除機制：

1. `_MEDIUM_NOISE_INLINE`：regex 移除內嵌 UI 文字（如 "Sign up"、"Follow" 等）
2. `_MEDIUM_UI_TEXTS`：frozenset 比對整行匹配的 UI 元素

### 分頁重複文件處理

Medium 文章分頁抓取會產生 `_10`~`_19` suffix 的 chunk 檔案。這些是同一篇文章的重複片段。

**處理方式**：在 `extract-qa` 步驟建立空佔位符（`{}`），讓 pipeline 跳過萃取，避免重複 Q&A。

### `--force` 覆寫修復（v2.19）

```python
# 修正前：force 模式下 while 迴圈無限自增 suffix
# 修正後：force 模式直接覆寫，不進入 while md_path.exists() 迴圈
if force:
    md_path.write_text(content, encoding="utf-8")
else:
    while md_path.exists():
        md_path = md_path.with_stem(f"{stem}_{suffix}")
        suffix += 1
```

### CLI 用法

```bash
make fetch-medium        # Medium 文章擷取
make fetch-ithelp        # iThome 鐵人賽擷取
make fetch-google-cases  # Google Case Studies 擷取
make fetch-articles      # 以上全部（Medium + iThome + Google Cases）
make fetch-all           # Notion + 所有外部文章
```
