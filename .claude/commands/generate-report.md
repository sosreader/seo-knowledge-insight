# /generate-report — 生成 SEO 週報（ECC 7 維度，不需要任何 API）

**你（Claude Code）就是語意判斷引擎**——直接推理，不呼叫任何外部 LLM API。
指標資料和知識庫搜尋結果由工具提供，報告內容完全由你的語意理解生成。

---

## 用法

```
/generate-report <Google Sheets URL 或 snapshot JSON 路徑>
/generate-report https://docs.google.com/spreadsheets/d/...
/generate-report output/metrics_snapshots/20260305-081902.json
```

---

## 分析框架（你的推理依據）

### Health Score v2 演算法
```
# Step 1：CORE 指標中觸發 ALERT_DOWN 的（高衝擊）
core_penalty = core_alert_down_count × 10

# Step 2：非 CORE 的 ALERT_DOWN（衍生/次要指標）
non_core_penalty = non_core_alert_down_count × 3

# Step 3：CORE 健康加分（月趨勢 > 0% 的 CORE 指標）
core_bonus = min(core_healthy_count × 2, 20)

# Step 4：全面崩盤懲罰（所有 CORE 月趨勢皆為負時）
all_core_penalty = 15 if ALL core monthly < 0% else 0

score = clamp(100 - core_penalty - non_core_penalty + core_bonus - all_core_penalty, 0, 100)
標籤：≥80 良好 / ≥60 需關注 / <60 警示
```
> 設計原理：CORE ALERT_DOWN 每個扣 10 分（核心流量信號），非 CORE 每個僅扣 3 分（避免衍生指標灌水），
> 健康的 CORE 指標提供正面抵銷（cap 20），確保「核心流量上揚但次要警報多」不會被誤判為嚴重警示。

### 異常閾值
- `ALERT_DOWN`：月趨勢 < -15% 或週趨勢 < -20%
- `ALERT_UP`：月趨勢 > +15% 或週趨勢 > +20%
- `CORE`：曝光、點擊、CTR、有效(Coverage)、檢索未索引、工作階段總數、Organic Search、Discover、AMP(non-Rich)、AMP Article、Google News、News(new)、Image

### 業界研究參考（推理時引用）
- **CTR 基準**：Backlinko 2024（67K 關鍵字）：Position 1 平均 CTR 27.6%，Position 2 降至 15.8%
- **SERP Features**：arxiv 2306.01785：Knowledge Panel 使目標頁 CTR 降低 ~8pp；Featured Snippet 可提升 CTR ~20%
- **NavBoost**：Google 排名洩露（2024）：以 13 個月滾動視窗聚合用戶點擊，為核心排名信號
- **因果歸因**：SEOCausal / CausalImpact（Bayesian）：SEO 無法 A/B 測試，貝氏時間序列為業界標準
- **E-E-A-T**：Google 2024 更新：Experience = 作者署名 + About 頁 + 可查核外部聲譽
- **Discover**：First Page Sage 2025：持續發佈高品質內容為首要因素；搜尋者參與度為第 5 大信號
- **搜尋意圖**：Semrush 2025：Awareness / Consideration / Conversion 漏斗，各自對應不同 CTR 基準

### Citation 標記規則（Perplexity 風格）

每次在 body text 引用知識庫 Q&A 後，**在句末加上 plain text `[N]`**（同一 QA 重複引用時用同一 N）：

```
成人牆進站前遮蔽正文的做法，對內容檢索的影響目前不確定 [1]。
CTR 下滑時，建議優先檢查 Title/Description 吸引力是否因 SERP Feature 被稀釋 [2]。
```

維護一個 citation map：`{qa_id → N}`，依首次出現順序遞增。

### 知識庫引用格式
QA 答案若含 `[What]`/`[Why]`/`[How]`/`[Evidence]` 標籤，依以下格式輸出：

```markdown
> **現象** {What 內容}
> **原因** {Why 內容}
> **行動** {How 內容}

— {source_title}、{source_date}  [知識庫 →](/admin/seoInsight/{id})  [N]
```

無標籤時，節錄前 350 字作為 blockquote，attribution 在框外（含 `[N]`）。

---

## 執行步驟

### Step 0：模式偵測（API-first + Local fallback）

在所有步驟之前，偵測並顯示執行環境。

**Priority 1：嘗試呼叫 API**
```bash
curl -s --max-time 3 http://localhost:8002/health
```

若 HTTP 200 且 JSON 包含 `capabilities`：
- 設定 `api_available = true`
- 顯示：`Mode（API）: [runtime:<X> | llm:<Y> | store:<Z> | agent:<W>]`

**Human-in-the-loop（僅 snapshot JSON + `llm: "none"` 時觸發）**：

若輸入為 snapshot JSON **且** `llm: "none"`，使用 AskUserQuestion 詢問：

> API server 已連線，但 server 自身無 LLM 能力（`llm: "none"`）。
> 你（Claude Code）將作為 LLM 引擎生成分析內容。請選擇報告組裝方式：
>
> 1. **API 模板模式** — 我生成 5 段分析文字，傳給 API 組裝完整報告（Step C2）
> 2. **完全本地生成** — 我直接生成完整 7 section 報告（Fallback 路徑）

根據使用者回答設定 `use_api_template`（預設 true）。

不詢問的情境（直接決定）：
- `llm: "openai"` → `use_api_template = true`
- 輸入為 Google Sheets URL → `use_api_template = false`（Step C2 不支援 URL 輸入）

**Priority 2：Local fallback（API 不可用時）**
- 設定 `api_available = false`，`use_api_template = false`
- 顯示：`Mode（Local）: [runtime:cli | llm:claude-code | store:<Z> | agent:disabled]`

**決策影響**：
- `api_available = true` + `use_api_template = true` + snapshot JSON → Step C2 呼叫 API 組裝報告
- `api_available = true` + Google Sheets URL → Step A2 可呼叫 API 擷取路徑分段資料，Step C2 走 Fallback 本地生成
- `api_available = false` → Step A2 + C2 皆走 Fallback 本地生成（避免 30s hang）

### Step A：解析指標

若為 Google Sheets URL：
```bash
.venv/bin/python scripts/qa_tools.py load-metrics --source "<URL>" --tab vocus
```

若為 snapshot JSON，直接讀取 `metrics` 欄位。

記錄所有 CORE / ALERT_DOWN / ALERT_UP 指標，計算 Health Score。

#### Step A1b：自動儲存指標快照（Report-Snapshot 關聯）

**目的**：確保每份報告都能追溯原始指標資料。

若 `api_available = true` 且輸入為 Google Sheets URL（尚未有 snapshot_id）：
```bash
# 先用 API parse + save，取得 snapshot_id
curl -s -X POST http://localhost:8002/api/v1/pipeline/metrics/save \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <key>" \
  -d '{"source":"<URL>","tab":"vocus","weeks":1,"label":"auto-<YYYYMMDD>"}'
```
記錄回傳的 `snapshot_id`，在 Step F 存檔時寫入 `report_meta`。

若輸入為 snapshot JSON，`snapshot_id` 從檔名或 JSON 的 `id` 欄位取得。

若 `api_available = false`，跳過此步驟（report_meta 不含 snapshot_id）。

> **查看關聯資料**：`GET /api/v1/reports/<date>/metrics` 會自動查 report meta 中的 `snapshot_id` 並回傳完整 162 個指標。

#### Step A3：自動偵測 Meeting-Prep 成熟度分數

讀取最新的 `output/meeting_prep_*.md`（若存在），解析 `<!-- meeting_prep_meta -->` 中的 `scores.maturity`。
建立 `maturity_context` 物件供 Step C2 使用。

```bash
# 找最新的 meeting-prep 報告
LATEST_MP=$(ls -t output/meeting_prep_*.md 2>/dev/null | head -1)
```

若找到且解析成功，`maturity_context` 範例：`{ "strategy": "L2", "process": "L2", "keywords": "L3", "metrics": "L2" }`

支援覆寫：
- `--maturity L2` — 所有維度設為指定等級
- `--no-maturity` — 強制跳過成熟度感知

若無 meeting-prep 報告且未指定 `--maturity`，`maturity_context` 為 null（行為不變）。

#### Step A2：擷取檢索未索引路徑分段資料

同一張 Google Sheet 的底部包含「檢索未索引」路徑分段表（全網域、/article/、/salon/ 等）。
若 API 可用，呼叫 API 自動擷取：

```bash
curl -s -X POST http://localhost:8002/api/v1/pipeline/crawled-not-indexed \
  -H "Content-Type: application/json" \
  -d '{"source": "<Google Sheets URL>"}'
```

回傳 `data.insight` 包含 `overall_severity`、`worsening_paths`、`improving_paths`、`summary_text`。
回傳 `data.markdown` 包含格式化的分析區塊。

若 API 不可用：直接讀取 Sheet 原始資料中的路徑分段（全網域 → 差距），用你的語意理解分析。

### Step B：建立 qaMap（每個指標搜尋 KB）

對每個 CORE + ALERT 指標，以指標名稱搜尋知識庫（各取 top-3）：
```bash
.venv/bin/python scripts/qa_tools.py search --query "<指標名稱>" --top-k 3
```

另外搜尋廣域主題詞（各取 top-2）：
```bash
for query in "CTR 下降 改善" "AMP Article" "Discover 演算法" "索引覆蓋 問題" "AI 流量 搜尋"; do
  .venv/bin/python scripts/qa_tools.py search --query "$query" --top-k 2
done
```

建立 `qaMap`：`{指標名稱 → [QAItem, ...]}`，去重後保留 top-8 作為全域 `topQas`。

### Step C：ECC 7 維度推理生成

**你直接推理生成以下 7 個 section（含檢索未索引分析），不套用固定模板文字。**
每個 section 的分析框架是指引，不是填空題。根據本週實際指標組合，判斷哪些洞察有意義、哪些研究引用適用。

---

#### Step C1：語意推理生成 5 段分析（儲存為變數，稍後傳入 API）

生成以下 5 段分析文字，**儲存備用**，不直接輸出為最終報告。
每段都要展示你的**思考過程**——不只是描述數字，而是「我看到 X，所以判斷 Y，因為 Z」的推理鏈。

**`situation_analysis`**（Section 1 跨指標關聯，2-3 句）：
- 針對本週 ALERT_DOWN + ALERT_UP 指標組合，分析最重要的**跨指標因果關聯**
- 不要重複 Health Score 數字（模板已有），聚焦在你觀察到的**非顯而易見關聯**
- 範例推理鏈：「AMP Article 崩跌同時 /salon/ 暴漲 → 判斷：新聞版位流量重新分配至長尾頁，而非整體需求萎縮」

**`traffic_analysis`**（Section 2 流量象限判讀，2-3 句 + 1 個行動建議）：
- 判斷本週屬於哪個象限（高曝光低CTR / 雙低 / 雙升等），**解釋為什麼**
- 結尾給出 1 個最具體的行動建議（「應優先做 X，因為 Y」）

**`technical_analysis`**（Section 3 技術面判讀，2-3 句）：
- 根據 Coverage / 檢索未索引 / AMP 類指標的實際數值，判斷技術健康度
- 重點：檢索未索引上升是爬蟲預算問題還是內容品質問題？AMP Article vs AMP (non-Rich) 背離代表什麼？
- 結合 qaMap 中技術相關 QA 的 [How] 建議

**`crawled_not_indexed_analysis`**（Section 3.5 檢索未索引路徑分段判讀，2-3 句）：
- 根據 Step A2 擷取的路徑分段資料（全網域、/article/、/salon/、/tag/、/user/、/en/ 等），分析哪些路徑惡化最嚴重
- 判斷惡化原因：爬蟲預算浪費（/tag/ 大量低品質頁）vs. 內容品質問題（/article/ 核心內容被排除）vs. 國際化設定（/en/ hreflang 缺失）
- 結合知識庫中「檢索未索引」「索引覆蓋」相關 QA 佐證
- 若 Step A2 無資料，輸出空字串

**`intent_analysis`**（Section 4 意圖位移判讀，2-3 句）：
- 根據路徑指標（/salon/、/tags/、/article/）和關鍵字（影評、電影、評價、攻略）的升降
- 判斷 Google 如何重新定位這個網站（娛樂媒體？UGC 平台？）
- 哪些意圖層（Awareness / Consideration / Conversion）正在成長或萎縮？

**`action_analysis`**（Section 5 行動優先序判讀，2-3 句）：
- 解釋你為什麼認為某些行動比其他行動更緊急
- 例：「雖然 AMP Article 跌幅最大（-166%），但其絕對流量僅 187，對總流量影響 < 0.01%。Organic Search 雖僅 -15%，但代表 164 萬 sessions 的基數，應優先處理。」
- 點出模板行動清單中**最值得投入時間的 1 項**

---

#### Step C2：呼叫 API 組裝完整報告

**前提**：`api_available = true` 且 `use_api_template = true` 且輸入為 snapshot JSON。
若任一條件不滿足，跳過本步驟，直接走 Fallback 本地生成。

若 Step A 的輸入為 snapshot JSON 路徑（`output/metrics_snapshots/YYYYMMDD-HHMMSS.json`）：

```bash
# 取得 snapshot_id（格式 YYYYMMDD-HHMMSS）
SNAPSHOT_ID=$(basename <snapshot_path> .json)

# 呼叫 API 組裝報告（API 處理模板 + LLM 分析注入 + 儲存 + eval）
# maturity_context 來自 Step A3（若為 null 則省略此欄位）
curl -s -X POST http://localhost:8002/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"snapshot_id\": \"$SNAPSHOT_ID\",
    \"situation_analysis\": \"<step_c1_situation>\",
    \"traffic_analysis\": \"<step_c1_traffic>\",
    \"technical_analysis\": \"<step_c1_technical>\",
    \"crawled_not_indexed_analysis\": \"<step_c1_crawled_not_indexed>\",
    \"intent_analysis\": \"<step_c1_intent>\",
    \"action_analysis\": \"<step_c1_action>\",
    \"maturity_context\": <step_a3_maturity_or_null>
  }"
```

> **優先序**：snapshot 內建的 `maturity` 欄位 > request `maturity_context` > null

若 API 成功（HTTP 200），取回 `data.filename` 和 `data.date`，作為 Step D 輸出。

**若前提不滿足**（`api_available = false`、`use_api_template = false`、或輸入為 Google Sheets URL）：跳過 Step C2，改為繼續執行下方完整 7 section 本地生成。

---

#### （Fallback）完整本地 7 section 生成（API 不可用時）

**行動項目用詞規範**：所有 `- ` 開頭的行動建議都應使用具體動詞（檢查、驗證、排查、修復、設定、加入、移除、重寫、篩選、測試、補上、優化 title/description）搭配具體工具名（GSC、Search Console、PageSpeed、GA4、Screaming Frog）。避免模糊用詞（持續觀察、注意、關注、留意）。分析性段落盡量用段落文字而非 `- ` 列表。

#### 一、本週 SEO 情勢快照

列出 Health Score 與標籤（良好/需關注/警示）。5 大現象：down 指標取前 3（🔴 高優先），up 指標取前 2（🟢 低優先），每個現象用段落描述指標名稱 + 月/週趨勢 + 語意解讀。
- **異常指標逐項解讀**（針對每個 ALERT_DOWN，使用結構化因果分析格式）：
  - 每個主要異常指標用以下格式分析（至少 5 個區塊）：

    **現象** {指標名稱}月趨勢 {X}%、週環比 {Y}%（latest {數值}）
    **原因** {你的推理 + KB 知識佐證}
    **行動** {具體建議 + KB 引用}

  - 用知識庫引用格式輸出相關 QA（若有）

**格式要求**：每個指標描述行必須同時包含月趨勢和週環比百分比（例：「月趨勢 -5.5%、週環比 +20.3%」），確保雙時間框架對照。

#### 二、流量信號解讀

根據 CTR / 曝光 / 點擊 / Discover / Organic Search 的實際數值，
**判斷屬於哪個象限**（你的判斷，不是預設答案）。

**必須在報告中明確寫出象限名稱**（使用以下四字格式之一），並在同一段落內解釋判斷理由：

- **高曝光低點擊** → 表示 Title 吸引力問題或 SERP Feature 搶走點擊（引用 arxiv SERP Features），建議優先檢查 Title/Description
- **低曝光高點擊** → 代表排名後退但既有訪客忠誠度高，需要擴大觸及
- **低曝光低點擊** → 意味 NavBoost 惡化循環（引用 NavBoost 研究），應該優先處理排名基礎
- **高曝光高點擊** → 表示正向循環，找出驅動因素並強化

對 Discover 單獨分析（季節性 vs. 內容品質信號），引用 First Page Sage 2025。
結合 qaMap 中 CTR / 曝光相關 QA 佐證。

#### 三、技術 SEO 健康度

根據 Coverage / 檢索未索引 / AMP 類指標的實際數值：

- Coverage 有效率趨勢：是否有頁面被排除？
- 檢索未索引：比例增加代表什麼？（爬蟲預算問題 vs. 內容品質問題）
- AMP 類：`AMP Article` vs. `AMP (non-Rich)` 差異分析——兩者背離表示新聞版位問題，而非技術問題
- 結合 qaMap 中技術 SEO 相關 QA

#### 四、檢索未索引路徑分段分析

根據 Step A2 的路徑分段資料（全網域 → 各路徑 → 差距），分析「已檢索未索引」覆蓋率：

- **全網域概覽**：檢索未索引佔比趨勢（上升/穩定/改善）
- **惡化路徑**（change_pct > 15%）：逐一分析惡化原因
  - `/tag/`：低品質頁面大量被爬取但不被索引 → 建議 noindex
  - `/article/`：核心內容被排除 → 內容品質 or thin content 問題
  - `/salon/`：UGC 品質不穩定 → 審核機制
  - `/user/`：thin content → robots.txt 或 noindex
  - `/en/`：hreflang 設定問題 → 檢查語系標籤
- **改善路徑**（change_pct < -10%）：點出哪些路徑正在恢復、可能原因
- **整體判讀**：問題主要是爬蟲預算浪費、內容品質、還是技術設定？

結合 qaMap 中「索引覆蓋」「檢索未索引」相關 QA 佐證。

若 Step A2 無資料，本段落省略。

#### 五、搜尋意圖對映

根據有資料的關鍵字 / 路徑指標（KW: xxx、/salon/、/tags/ 等），
**分析意圖位移**（Semrush 漏斗：Awareness → Consideration → Conversion）：

- 哪些意圖層正在成長？哪些在萎縮？
- 上升的路徑/KW，代表 Google 如何定位這個網站？
- E-E-A-T 信號：作者、About 頁、外部聲譽（若有相關指標）

#### 六、優先行動清單

##### Step E 補充：成熟度感知行動建議

在生成本 section 前，使用 Step A3 取得的 `maturity_context`（若有）：
1. ~~讀取最新的 `output/meeting_prep_*.md`~~ → 已由 Step A3 自動偵測
2. 行動建議依成熟度等級分層：
   - L1 維度：建議「建立基礎」（例：建立 SOP、開始追蹤基本指標）
   - L2 維度：建議「系統化」（例：自動化流程、多維度追蹤）
   - L3 維度：建議「進階優化」（例：預測性分析、意圖分群）
   - L4 維度：建議「維持領先」（例：持續改進循環、歸因分析）

若無 meeting-prep 報告，跳過成熟度脈絡，行為不變。

**三級行動**，基於本週實際 down 指標和你的推理：

**ALERT_DOWN 覆蓋規則（重要）**：每個 ALERT_DOWN 指標名稱必須至少在本 section 的行動項目中出現一次。
評估腳本會計算 `alert_coverage = 被提及的 ALERT 數 / 總 ALERT 數`，目標 ≥ 0.5。
若某 ALERT_DOWN 指標沒有對應的具體行動，也應在行動項目中提及該指標名稱並說明為何暫不處理。

若有成熟度脈絡，先輸出參考行：

```markdown
> 成熟度參考：策略 L2 / 流程 L2 / 關鍵字 L3 / 指標 L2（來源：最近一次會議準備報告）
```

**每個行動項目前加對應 emoji**（不只是標題，每一條 `-` 項目都要有）。目標分佈：🔴 ≥ 4 條、🟡 ≥ 3 條、🟢 ≥ 2 條。

```
🔴 高優先（需立即處理）：
- 🔴 {行動 1} + KB 佐證連結 + 成熟度升級標籤
- 🔴 {行動 2} ...
- 🔴 {行動 3} ...
- 🔴 {行動 4} ...
🟡 中優先（本週內）：
- 🟡 {行動 1} CTR 優化 / 上升指標延伸
- 🟡 {行動 2} ...
- 🟡 {行動 3} ...
🟢 低優先（下週規劃）：
- 🟢 {行動 1} E-E-A-T 強化
- 🟢 {行動 2} 內容行事曆
```

每個與成熟度直接相關的行動項目標注升級標籤：
```markdown
- 建立內部連結自動 SOP — **[流程 L2→L3]**
- 建立預警閾值 + 即時儀表板 — **[指標 L2→L3]**
```

只有與成熟度直接相關的行動項目才加標籤，不強制所有項目都加。

#### 七、來源

列出 `topQas` 中最相關的 8 筆，格式為簡潔的 numbered list（CitationsPanel 已有完整卡片，不重複 blockquote）：

```markdown
[1] **{source_title}、{source_date}** — {answer 前 80 字}… [→](/admin/seoInsight/{id})
[2] **{source_title}、{source_date}** — ...
```

---

### Step D：存檔與輸出

**若 Step C2 呼叫 API 成功**：
- 報告已由 API 儲存（content-addressed 檔名），eval 已自動推 Laminar
- 跳至 Step E，使用 API 回傳的 `data.filename` 與 `data.date`

**若為 Fallback 本地生成**：
報告正文生成完畢後，**在結尾附加 citations JSON block**（供前端 CitationsPanel 解析）：

```
<!-- citations [{"n":1,"id":"abc123","title":"SEO 會議_20250623","category":"技術SEO","date":"2025-06-23","snippet":"訪客進入成人文章時...","chunk_url":"/admin/seoInsight/abc123","source_url":null},{"n":2,...}] -->
```

citation map 收錄所有本次 body text 中引用過的 QA（依 N 排序），每筆欄位：
- `n`：引用序號（int）
- `id`：qa.id（stable_id）
- `title`：source_title + source_date 組合，或 question 前 40 字
- `category`：qa.category
- `date`：qa.source_date
- `snippet`：answer 去標籤後前 120 字
- `chunk_url`：`/admin/seoInsight/{id}`
- `source_url`：qa.source_url 或 null

接著在 citations block 之後附加 `report_meta` JSON（供前端辨識生成模式）：

```
<!-- report_meta {"weeks":1,"generated_at":"2026-03-06T12:00:00.000Z","generation_mode":"claude-code","generation_label":"Claude Code 語意推理","model":null,"snapshot_id":"20260306-081902"} -->
```

- `weeks`：快照的 weeks 值（整數）
- `generated_at`：當前 ISO 時間
- `generation_mode`：固定 `"claude-code"`
- `generation_label`：固定 `"Claude Code 語意推理"`

接著計算 hash（在 bash 中執行）：

```bash
# 計算 hash（在 bash 中執行）
echo "<報告內容>" | shasum | cut -c1-8
```

使用 Write tool 存至：`output/report_{YYYYMMDD}_{hash8}.md`

存檔完成後，**推送 Laminar eval trace**（與 API mode 對齊）：

```bash
# ALERT_DOWN 指標名稱逗號連接（例如 "AMP Article,Google News,Organic Search"）
ALERT_NAMES="<本次 ALERT_DOWN 指標逗號清單>"
.venv/bin/python scripts/_eval_report.py \
  --report "output/report_{YYYYMMDD}_{hash8}.md" \
  --alert-names "$ALERT_NAMES"
```

此步驟將 7 個維度（`report_overall`、`report_section_coverage` 等）推送至 Laminar `report-quality` group。若 `LMNR_PROJECT_API_KEY` 未設定則靜默跳過，不影響存檔。

### Step E：輸出摘要

告訴使用者：
- 解析指標數量 / 關注指標數量（CORE / DOWN / UP）
- Health Score 與標籤
- 引用 KB 條目筆數
- 儲存路徑與檔案大小

### Step F：同步至 Supabase（HITL）

報告存檔完成後，使用 AskUserQuestion 詢問：

> 報告已儲存至 `output/report_{YYYYMMDD}_{hash8}.md`。
> 是否同步至 Supabase？
>
> 1. **Yes** — 執行 `make sync-db`
> 2. **No** — 僅保留本地檔案

若使用者選擇 Yes：
```bash
make sync-db
```
顯示上傳結果（uploaded / skipped / errors）。

若使用者選擇 No 或不回應，跳過此步驟。

---

## 與 API Template 模式的本質差異

| 項目 | API Template Mode | Claude Code as LLM |
|------|------------------|--------------------|
| 生成主體 | TypeScript 模板字串 | 你的語意推理 |
| 每週文字 | 固定框架填入數字 | 針對本週指標組合推理 |
| 指標間關聯 | 無（各 section 獨立） | 你可以發現跨 section 關聯 |
| 研究引用 | 硬編碼常數 | 你判斷哪條引用適用 |
| 外部 API | 無 | 無 |
| 需要 API key | 否 | 否 |
