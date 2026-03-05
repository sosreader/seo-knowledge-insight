# /generate-report — 生成 SEO 週報（ECC 6 維度，不需要任何 API）

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

### Health Score 演算法
```
score = 100 - (ALERT_DOWN 數量 × 10)
若所有 CORE 指標同時下滑，額外扣 20
score 範圍 [0, 100]，標籤：≥80 良好 / ≥60 需關注 / <60 警示
```

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

### Step A：解析指標

若為 Google Sheets URL：
```bash
.venv/bin/python scripts/qa_tools.py load-metrics --source "<URL>" --tab vocus
```

若為 snapshot JSON，直接讀取 `metrics` 欄位。

記錄所有 CORE / ALERT_DOWN / ALERT_UP 指標，計算 Health Score。

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

### Step C：ECC 6 維度推理生成

**你直接推理生成以下 6 個 section，不套用固定模板文字。**
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

若 Step A 的輸入為 snapshot JSON 路徑（`output/metrics_snapshots/YYYYMMDD-HHMMSS.json`）：

```bash
# 取得 snapshot_id（格式 YYYYMMDD-HHMMSS）
SNAPSHOT_ID=$(basename <snapshot_path> .json)

# 呼叫 API 組裝報告（API 處理模板 + LLM 分析注入 + 儲存 + eval）
curl -s -X POST http://localhost:8002/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"snapshot_id\": \"$SNAPSHOT_ID\",
    \"situation_analysis\": \"<step_c1_situation>\",
    \"traffic_analysis\": \"<step_c1_traffic>\",
    \"technical_analysis\": \"<step_c1_technical>\",
    \"intent_analysis\": \"<step_c1_intent>\",
    \"action_analysis\": \"<step_c1_action>\"
  }"
```

若 API 成功（HTTP 200），取回 `data.filename` 和 `data.date`，作為 Step D 輸出。

**若 API 不可用或輸入為 Google Sheets URL**（fallback）：跳過 Step C2，改為繼續執行下方完整 6 section 本地生成。

---

#### （Fallback）完整本地 6 section 生成（API 不可用時）

#### 一、本週 SEO 情勢快照

- 列出 Health Score 與標籤（良好/需關注/警示）
- **5 大現象**：down 指標取前 3（🔴 高優先），up 指標取前 2（🟢 低優先）
  - 每個現象：指標名稱 + 月/週趨勢 + **你的語意解讀**（為什麼這件事重要？）
- **異常指標逐項解讀**（針對每個 ALERT_DOWN）：
  - 你對該指標下滑的推理（結合 qaMap 的 KB 知識）
  - 用知識庫引用格式輸出相關 QA（若有）

#### 二、流量信號解讀

根據 CTR / 曝光 / 點擊 / Discover / Organic Search 的實際數值，
**判斷屬於哪個象限**（你的判斷，不是預設答案）：

- 高曝光 / 低 CTR → Title 吸引力問題或 SERP Feature 搶走點擊（引用 arxiv SERP Features）
- 低曝光 / 高 CTR → 排名後退，觸及縮小
- 雙低（曝光 + 點擊同降）→ NavBoost 惡化循環（引用 NavBoost 研究）
- 雙穩或雙升 → 正常，找驅動因素

對 Discover 單獨分析（季節性 vs. 內容品質信號），引用 First Page Sage 2025。
結合 qaMap 中 CTR / 曝光相關 QA 佐證。

#### 三、技術 SEO 健康度

根據 Coverage / 檢索未索引 / AMP 類指標的實際數值：

- Coverage 有效率趨勢：是否有頁面被排除？
- 檢索未索引：比例增加代表什麼？（爬蟲預算問題 vs. 內容品質問題）
- AMP 類：`AMP Article` vs. `AMP (non-Rich)` 差異分析——兩者背離表示新聞版位問題，而非技術問題
- 結合 qaMap 中技術 SEO 相關 QA

#### 四、搜尋意圖對映

根據有資料的關鍵字 / 路徑指標（KW: xxx、/salon/、/tags/ 等），
**分析意圖位移**（Semrush 漏斗：Awareness → Consideration → Conversion）：

- 哪些意圖層正在成長？哪些在萎縮？
- 上升的路徑/KW，代表 Google 如何定位這個網站？
- E-E-A-T 信號：作者、About 頁、外部聲譽（若有相關指標）

#### 五、優先行動清單

**三級行動**，基於本週實際 down 指標和你的推理：

```
🔴 高優先（需立即處理）：針對 ALERT_DOWN，各一條具體行動 + KB 佐證連結
🟡 中優先（本週內）：CTR 優化 / 上升指標延伸，各一條
🟢 低優先（下週規劃）：E-E-A-T 強化 / 內容行事曆
```

#### 六、來源

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
