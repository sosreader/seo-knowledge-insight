# /meeting-prep — 顧問會議準備深度研究報告

**你（Claude Code）就是語意判斷引擎**——直接推理，不呼叫任何外部 LLM API。
WebFetch/WebSearch 是你的 built-in tools，用來取得最新網路資料，不算外部 LLM 呼叫。

---

## 用法

```
/meeting-prep <snapshot JSON 路徑>
/meeting-prep output/metrics_snapshots/20260306-184735.json
/meeting-prep --report output/report_20260309_f4d6dcb9.md
```

輸入三選一：
- **snapshot JSON 路徑**：直接讀取指標快照
- **Google Sheets URL**：下載並解析指標
- **--report <路徑>**：從已生成的週報萃取異常，跳過指標解析

---

## 與 /generate-report 的差異

| 項目 | /generate-report | /meeting-prep |
|------|-----------------|---------------|
| 回答 | 「本週 SEO 怎麼了？」 | 「我該在會議上問什麼？為什麼？」 |
| 用途 | 閱讀 / 歸檔 | 對話 / 核查 / 深度研究 |
| 業界動態 | 無 | 自動抓取（WebFetch + WebSearch） |
| 框架 | Health Score + 7 維度 | 5-Layer Audit + E-E-A-T + 人本要素 + SEO 成熟度 |
| 顧問文章 | 無 | 交叉比對 Gene Hong Medium 文章 |

典型工作流：先跑 `/generate-report` → 再跑 `/meeting-prep --report <路徑>`

---

## 分析框架定義

### 5-Layer SEO Audit 框架

| 層 | 英文 | 檢查重點 |
|----|------|---------|
| L1 | Technical Foundation | Crawlability, Indexability, Core Web Vitals, Structured Data |
| L2 | Content Architecture | Site structure, Internal linking, URL hierarchy |
| L3 | Content Quality | E-E-A-T signals, Topical authority, Content freshness |
| L4 | Off-Page & Authority | Backlink profile, Brand mentions, Social signals |
| L5 | User Experience | Engagement metrics, Search intent alignment, Conversion paths |

### E-E-A-T 評分框架（Google Quality Rater Guidelines）

| 維度 | 定義 | 1分（弱） | 5分（強） |
|------|------|----------|----------|
| Experience | 作者/品牌的第一手經驗 | 無可辨識作者 | 明確署名 + 實作案例 |
| Expertise | 領域專業深度 | 泛泛之談 | 深度技術分析 + 獨到見解 |
| Authoritativeness | 外部認可與引用 | 無外部提及 | 業界引用 + 媒體報導 |
| Trustworthiness | 資訊可信度 | 過時/有誤 | 有來源引用 + 定期更新 |

### 人本七要素框架（Gene Hong SEO 方法論）

| # | 要素 | 說明 |
|---|------|------|
| 1 | 網站人格（Brand Persona） | 網站在搜尋生態中的角色定位 |
| 2 | 內容靈魂（Content Soul） | 內容是否有獨特觀點、不只是聚合 |
| 3 | 使用者旅程（User Journey） | 從搜尋到轉換的路徑是否順暢 |
| 4 | 技術體質（Technical Health） | 爬取效率、渲染正確性、效能 |
| 5 | 連結生態（Link Ecosystem） | 內外連結結構是否合理 |
| 6 | 資料敘事（Data Storytelling） | 能否從數據中發現有意義的故事 |
| 7 | 趨勢敏銳度（Trend Sensitivity） | 對演算法變動和業界趨勢的反應速度 |

### SEO 成熟度模型（Demand Metric 改編）

| 維度 | L1 起步 | L2 發展 | L3 成熟 | L4 領先 |
|------|---------|---------|---------|---------|
| 策略（Strategy） | 無明確策略 | 有基本計畫 | 數據驅動決策 | 預測性優化 |
| 流程（Process） | 臨時處理 | 有 SOP 但執行不一 | 自動化流程 | 持續改進循環 |
| 關鍵字（Keywords） | 直覺選詞 | 有研究但零散 | 系統化追蹤 | 意圖分群 + 競爭分析 |
| 指標（Metrics） | 不看數據 | 看基本指標 | 多維度追蹤 | 預警 + 歸因分析 |

---

## 執行步驟

### Step A：取得異常摘要 → ALERT_DOWN 清單

**若輸入為 snapshot JSON 路徑**：
```bash
# 讀取 snapshot，解析 metrics 欄位中 flag 為 ALERT_DOWN 的指標
```
直接用 Read tool 讀取 JSON，從 `metrics` 欄位中找出所有 `flag === "ALERT_DOWN"` 的指標名稱，建立 `ALERT_DOWN` 清單。

**若輸入為 Google Sheets URL**：
```bash
.venv/bin/python scripts/qa_tools.py load-metrics --source "<URL>" --tab vocus --json
```
解析輸出的 `anomalies` 陣列，篩選 `flag === "ALERT_DOWN"` 建立清單。

**若輸入為 --report <路徑>**：
用 Read tool 讀取週報 markdown，從 Section 1（情勢快照）中萃取帶有 ALERT_DOWN / 下降標記的指標名稱。

---

### Step B：網路研究（6 路並行，自動抓取）

SEO 沒有新資料開會沒意義。**自動執行，不留給使用者處理。**

**B1：Google Search Status Dashboard**
```
WebFetch: https://status.search.google.com/incidents.json
```
解析 JSON，篩選最近 30 天的 incidents。若 fetch 失敗，標記「無法取得 Google 官方更新」並繼續。

**B2：Search Engine Roundtable 近期報導**
```
WebFetch: https://www.seroundtable.com/
```
從 HTML 中擷取最新 5 篇文章的標題 + 日期 + 摘要（首段）。若 fetch 失敗，降級跳過。

**B3：針對 ALERT_DOWN 指標搜尋業界報導**
對每個 ALERT_DOWN 指標（最多 3 個最嚴重的），執行：
```
WebSearch: "<指標英文名> site:searchengineland.com OR site:developers.google.com 2026"
```
收集搜尋結果的標題 + URL + 摘要。若搜尋失敗，降級跳過。

**B4：Google Search Central Blog（官方公告）**
```
WebFetch: https://developers.google.com/search/blog
```
擷取最近 30 天的文章標題 + 日期。比 SER 二手報導更權威——Google 官方的索引/排名變更公告。若 fetch 失敗，降級跳過。

**B5：Google Trends 驗證（針對 ALERT_DOWN 關鍵字）**
對 ALERT_DOWN 中的**關鍵字類指標**（如 KW「電影」、KW「影評」），最多取 3 個最嚴重的，執行：
```
WebSearch: "<關鍵字> Google Trends 2026" OR "search interest <關鍵字> decline"
```
目的：區分「全市場下降」vs「只有本站下降」。
- 若 Google Trends 也在降 → 標記「外部因素」，降低 S3 假設中本站問題的權重
- 若 Google Trends 持平或上升 → 標記「本站問題」，提升診斷優先序
若搜尋失敗，標記「無法取得趨勢資料」並繼續。

**B6：SERP Feature 偵測（針對 ALERT_DOWN 關鍵字）**
對 top 2 流失最嚴重的關鍵字，執行：
```
WebSearch: "<關鍵字> SERP feature AI Overview Knowledge Panel 2026"
```
記錄 SERP 組成變化（AI Overview 佔比、Knowledge Panel、Video Carousel、Featured Snippet 等）。
目的：量化 SERP Feature 搶佔有機 CTR 的程度，直接支撐 S3 技術面假設。
若搜尋失敗，降級跳過。

將 B1-B6 結果匯集為 `industryMap`（15-20 筆動態）。

**降級策略**：任何一路 fetch 失敗都不中斷流程，在報告中標記「無法取得」，用 KB 已有資料繼續。

---

### Step C：多主題 KB 搜尋（7-10 輪）→ qaMap

對每個 ALERT_DOWN 指標 + 廣域主題詞搜尋知識庫：

```bash
# 每個 ALERT_DOWN 指標
.venv/bin/python scripts/qa_tools.py search --query "<指標名稱>" --top-k 3

# 廣域主題詞（固定 + 動態）
.venv/bin/python scripts/qa_tools.py search --query "E-E-A-T 作者 經驗" --top-k 3
.venv/bin/python scripts/qa_tools.py search --query "SEO 成熟度 策略" --top-k 3
.venv/bin/python scripts/qa_tools.py search --query "人本 SEO 網站人格" --top-k 3
.venv/bin/python scripts/qa_tools.py search --query "CTR 下降 改善" --top-k 2
.venv/bin/python scripts/qa_tools.py search --query "Discover 演算法" --top-k 2
.venv/bin/python scripts/qa_tools.py search --query "索引覆蓋 問題" --top-k 2
.venv/bin/python scripts/qa_tools.py search --query "AI 流量 搜尋" --top-k 2
```

建立 `qaMap`：`{主題 → [QAItem, ...]}`，去重後保留整體 top-20。

---

### Step D：顧問文章定向讀取

用 helper 腳本找出顧問文章清單（去重）：
```bash
.venv/bin/python scripts/meeting_prep_helper.py list-consultant-articles
```

根據 ALERT_DOWN 指標，用 Grep 搜尋最相關的文章：
```bash
# 排除重複版本（_1.md, _2.md 等）
Grep: pattern="<指標關鍵字>" glob="raw_data/medium_markdown/*.md" --glob "!*_[0-9].md"
```

對找到的最相關 3 篇文章，各 Read 前 120 行，摘錄顧問觀點。

---

### Step E：分段推理生成 11 Sections

**Context window 管理**：分三批生成，避免 context 溢出。

#### 第一批：S0-S4

**Section 0：執行摘要（5 bullets）**
從 S1-S10 蒸餾 5 個最重要的發現，每個 1 句話。最後生成（先跳過）。

**Section 1：本週異常地圖**
- 列出所有 ALERT_DOWN / ALERT_UP 指標
- 每個指標標注月趨勢 / 週趨勢
- 用表格呈現，按嚴重度排序

**Section 2：業界最新動態**

**內容密度要求**：S2 必須包含至少 **15 行**非標題、非分隔線的實質內容，並引用至少 **5 個不同來源名稱**（如 SearchEngineLand、SearchEngineJournal、Google Search Central、Search Engine Roundtable、Google Trends、Ahrefs、Semrush 等）。

**重要：所有業界動態必須附上原始來源 URL**。WebFetch/WebSearch 結果自帶 URL，S2 中以 markdown hyperlink 格式保留：`[標題](URL)`。若 URL 不可取得（如 JSON API），標注「來源：<描述>」。

```markdown
### Google 官方更新
<!-- 從 B1 industryMap 填入 -->
- [日期] [更新名稱](URL) — [狀態/影響] — [與本週異常的關聯性]

### Google Search Central 官方公告
<!-- 從 B4 填入 -->
- [日期] [標題](URL) — [與本週異常的關聯性]

### 業界報導
<!-- 從 B3 搜尋結果填入 -->
- [來源] [標題](URL) — [摘要] — [與本站異常的可能關聯]

### Search Engine Roundtable 近期重點
<!-- 從 B2 填入，每篇附上 SER 原文 URL -->
- [日期] [標題](URL) — [摘要]

### 關鍵字市場趨勢（Google Trends）
<!-- 從 B5 填入，來源欄附 WebSearch 結果 URL -->
| 關鍵字 | 本站趨勢 | 市場趨勢（Google Trends） | 判斷 | 來源 |
|--------|---------|--------------------------|------|------|
| <KW> | -XX.X% | ↓ 全市場下降 / → 持平 / ↑ 上升 | 外部因素 / 本站問題 | [來源標題](URL) |

### SERP Feature 偵測
<!-- 從 B6 填入，來源欄附 WebSearch 結果 URL -->
| 關鍵字 | 觀察到的 SERP Feature | 對有機 CTR 的影響 | 來源 |
|--------|---------------------|-----------------|------|
| <KW> | AI Overview / Knowledge Panel / Video Carousel | 高 / 中 / 低 | [來源標題](URL) |
```

**Section 3：深度根因假設**

**子標題格式**：將相關 ALERT_DOWN 指標分群，每群使用 `### H{N}：{S1 指標名稱}` 子標題。指標名稱**必須與 Section 1 表格第一欄完全一致**（如 `### H1：AMP Article`、`### H2：CTR`、`### H3：Discover 月趨勢`）。可將高度相關的指標合併為一群，但每個 S1 ALERT_DOWN 名稱至少出現一次。

**大型 S1 集合時的分群策略**（>8 項 ALERT_DOWN）：分群數控制在 5-7 群。優先使用 S9 eval 可辨識的指標名稱作為群組主標題（Discover、AMP、外部連結、檢索未索引、Coverage、CTR、KW: {關鍵字}、營運 KW: {關鍵字}）。非 S9 可辨識的指標（如 GPT、Gemini、Video、/salon/、News(new)）歸入相關的 S9 可辨識群組下方討論，**不另立獨立子標題**。

對每群 ALERT_DOWN 指標，提出 3 個假設（使用 `**假設 1（技術面）**` 格式）：
- 假設 1：技術面（L1-L2）
- 假設 2：內容面（L3）
- 假設 3：外部面（L4-L5 或業界動態）——**必須引用 B5 Google Trends 和/或 B6 SERP Feature 數據**。若 Google Trends 顯示全市場下降，應在假設中標注「外部因素」以降低本站問題的權重。
每個假設結尾標注「**可驗證**」「**需人工確認**」或「**需顧問判斷**」。

**Section 4：顧問視角交叉比對**
交叉比對 4 個資料來源，找出矛盾與一致：
- KB 知識庫觀點
- 顧問 Medium 文章觀點
- 本週指標數據
- 業界最新動態

格式：
```markdown
| 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|---------|-------------|---------|---------|------|
| ... | ... | ... | ... | ... | 一致/矛盾/缺口 |
```

**四欄必填規則**：KB 觀點、顧問文章觀點、指標數據、業界動態四個來源欄位**每格必須有 >5 個字元的實質內容**。若該來源無直接對應資訊，寫「目前無直接觀點，需進一步研究」而非留空或寫「—」。

#### 第二批：S5-S8

**Section 5：五層審計缺口清單**
基於 S3-S4 的分析，列出 5-Layer Audit 中的缺口：
```markdown
| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical | ... | ... | ... | 高/中/低 |
```

**Section 6：E-E-A-T 現況評估**
對 4 個維度各給 1-5 分，並說明評分依據：
```markdown
| 維度 | 分數 | 依據 |
|------|------|------|
| Experience | 3 | KB 搜尋發現作者署名不一致... |
| Expertise | 4 | 有深度技術文章但... |
| Authoritativeness | 3 | ... |
| Trustworthiness | 4 | ... |
```

**Section 7：人本七要素分析**
對 7 個維度各給 1-5 分，引用顧問文章佐證：
```markdown
| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | 網站人格 | 3 | ... | [文章標題] 提到... |
```

**Section 8：SEO 成熟度自評**
4 維度 × 4 級，標注當前等級 + 下一步：
```markdown
| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| 策略 | L2 | ... | ... |
```

#### 第三批：S9-S10 + S0

**Section 9：會議提問清單（核心輸出）**

四類提問，每類都要標注來源 section。

**指標名稱呼應規則**：每個問題中**必須包含至少一個 S1/S3 的指標原始名稱**，以確保問題與前文分析的跨 Section 一致性。

**可用的指標名稱格式**（eval 可辨識的 pattern，優先使用這些）：
- `Discover`、`CTR`、`AMP`、`Coverage`、`外部連結`、`檢索未索引`
- `KW: {關鍵字}`（如 `KW: 電影`、`KW: 影評`）——關鍵字類指標**必須使用 `KW:` 前綴**，且**關鍵字後必須有空格**再接其他文字（如 `KW: 電影 +56%`，不寫 `KW: 電影和`）
- `營運 KW: {關鍵字}`（如 `營運 KW: 保養`）——同樣規則，關鍵字後加空格（如 `營運 KW: 保養 等商業 KW`）
- `AMP Ratio`、`探索比例`、`結構化 Ratio`、`新網頁`

**A 類：確認事實（3-5 題）**
從 S3 根因假設中「需人工確認」的項目推導。
格式：`- [ ] [A1] <問題> （來源：S3 假設 X）`

**B 類：探索判斷（4-6 題）**
從 S7 人本七要素評分 ≤ 2 的維度推導。
格式：`- [ ] [B1] <問題> （來源：S7 <要素名>，評分 N/5）`

**C 類：挑戰假設（2-3 題）**
從 S4 交叉比對中「矛盾」項推導，引用顧問文章反問。
格式：`- [ ] [C1] <問題> （來源：S4，矛盾點：<描述>）`

**D 類：業界趨勢（2-3 題）**
從 S2 業界動態中與本站相關的項目推導。
格式：`- [ ] [D1] <問題> （來源：S2 <動態標題>）`

**Section 10：會議後行動核查表**
從 S5（缺口）和 S9（提問）推導。

**每個行動項目格式**：`- [ ] 在 {工具名} {動作動詞} {具體對象} — **[{維度} L{X}→L{Y}]**`

**必備要素**：
- **工具名**（至少一個）：GSC / Search Console / PageSpeed / Ahrefs / Screaming Frog / GA4 / Google Trends / Semrush / Moz / Chrome DevTools / Lighthouse
- **動作動詞**（至少一個）：排查 / 篩選 / 檢查 / 驗證 / 監控 / 建立 / 設定 / 測試 / 分析 / 規劃 / 導入

**三要素必備**：每個行動項目**必須同時包含** (1) 工具名、(2) 動作動詞、(3) 成熟度升級標籤 `[{維度} LX→LY]`。不符合三要素的 meta-item（如「更新假設」「回寫知識庫」）**不列入 S10**。

```markdown
- [ ] 在 GA4 排查 AMP 頁面追蹤完整性 — **[流程 L2→L3]**
- [ ] 在 Ahrefs 分析主要關鍵字 SERP Feature 變化 — **[策略 L2→L3]**
- [ ] 在 GSC 監控索引覆蓋率趨勢 — **[指標 L2→L3]**
```

**最後回填 Section 0**：從 S1-S10 蒸餾 5 bullets。

---

### Step F：存檔與文件留存

#### F1：完整報告存檔

在報告末尾附加 metadata JSON blocks：

```markdown
<!-- citations [{"n":1,"id":"abc123","title":"...","category":"...","snippet":"..."},...] -->
<!-- meeting_prep_meta {"date":"2026-03-12","scores":{"eeat":{"experience":3,"expertise":4,"authoritativeness":3,"trustworthiness":4},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":5,"question_count":15,"generation_mode":"claude-code","web_sources":{"google_status":true,"ser":true,"web_search":3,"google_blog":2,"google_trends":3,"serp_feature":2},"web_source_count":13} -->
```

計算 content hash：
```bash
echo "<報告內容前 500 字>" | shasum | cut -c1-8
```

存至：`output/meeting_prep_YYYYMMDD_{hash8}.md`

#### F2：業界動態累積（research/11-seo-industry-updates.md）

在檔案末尾 append 一個新的日期 section：
```markdown
## YYYY-MM-DD

### Google 官方
- ...

### 業界報導
- ...

### SER 重點
- ...
```

若檔案超過 12 個 dated sections（約 6 個月），移除最舊的 section。

#### F3：評分與洞察累積（research/12-meeting-prep-insights.md）

在評分追蹤表 append 一行：
```markdown
| YYYY-MM-DD | E:3 E:4 A:3 T:4 | 策略:L2 流程:L2 KW:L3 指標:L2 | 重要發現摘要 |
```

在交叉比對發現區 append 新發現（若有矛盾或重要一致性）。

---

## Citation 標記規則

與 `/generate-report` 相同的 Perplexity 風格 `[N]` 標記。
維護 citation map：`{qa_id → N}`，依首次出現順序遞增。

**Citation 密度目標**：整篇報告應引用 **15-18 筆** KB 來源（Step C 搜尋 7-10 輪，每輪 top-k 3，去重後保留 top-20，目標使用其中 15-18 筆）。在 S3（根因假設）、S5（審計缺口）、S6（E-E-A-T）中密集引用。

**Section-Citation 對應**：為確保引用與 section 脈絡一致，在 S3 中優先引用 category 為「技術SEO」「索引與檢索」「連結策略」「演算法與趨勢」「Discover與AMP」「搜尋表現分析」的 KB 來源。在 S6 中優先引用 category 為「技術SEO」「Discover與AMP」「連結策略」「搜尋表現分析」「演算法與趨勢」的 KB 來源。「GA與數據追蹤」等非 SEO 核心類別的引用應放在 S1 或 S5，而非 S3/S6。

報告末尾的 `<!-- citations [...] -->` JSON block 格式同 `/generate-report`。

---

## 輸出摘要

完成後告訴使用者：
- 輸入來源類型（snapshot / sheets / report）
- ALERT_DOWN 指標數量
- 業界動態筆數（B1 + B2 + B3 + B4 + B5 + B6）
- KB 引用筆數
- 顧問文章引用數
- E-E-A-T 平均分
- SEO 成熟度概覽
- Google Trends 驗證結果（幾個為外部因素 vs 本站問題）
- SERP Feature 偵測結果（哪些關鍵字被 AI Overview / Knowledge Panel 搶佔）
- 提問清單總數（A + B + C + D 各幾題）
- 儲存路徑
- research/ 更新狀態
