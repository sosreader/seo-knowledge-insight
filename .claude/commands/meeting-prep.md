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

### Step C-prime：前週報告差異偵測（自動執行）

在生成任何 Section 之前，先讀取最近一份已存在的 meeting-prep 報告，建立差異化基準：

```bash
Glob: output/meeting_prep_*.md  # 找出所有報告，取日期最新且早於本次的一份
```

若找到前一份報告，用 Read tool 讀取其 S2、S4、S6、S7、S8 段落，建立 `prevReport` 物件：

- `prev_s2_items`：每個動態項的 {url, title, status}（用於 SITREP 標注）
- `prev_s4_topics`：S4 表格的主題欄 + 判斷欄（用於 CF 標注）
- `prev_s6_scores`：E-E-A-T 4 維度分數 + 依據摘要
- `prev_s7_scores`：人本 7 要素分數 + 引用 citation IDs
- `prev_s8_levels`：成熟度 4 維度等級 + 依據摘要
- `prev_s9_questions`：S9 提問 ID 列表（用於 CARRY 標注）

若找不到前一份，所有項目標注 `[NEW]`，不使用 toggle 折疊。

**SITREP 標注規則（CRITICAL — 必須遵守）：**

| 元素 | 標注 | 條件 |
|------|------|------|
| S2 動態項 | `[NEW]` | URL 未出現在前週 S2 |
| S2 動態項 | `[ONGOING-W{n}]` | URL 與前週相同（n = 連續出現週數） |
| S2 動態項 | `[RESOLVED]` | 前週有但本週不再相關 |
| S4 topic | `[NEW]` | 主題名稱未出現在前週 S4 |
| S4 topic | `[CF]` | 主題與前週相同（Carry Forward） |
| S6/S7/S8 維度 | Changed | 分數與前週不同 → 展開 |
| S6/S7/S8 維度 | No Change | 分數與前週相同 → `<details>` toggle 折疊 |
| S9 提問 | `[NEW]` | 新增提問 |
| S9 提問 | `[CARRY-W{n}]` | 與前週相同指標+來源的提問 |

**Toggle 折疊模板（用於 No Change 內容）：**

```html
<details>
<summary>No Change（{N} 維度，點擊展開上週評估）</summary>

| 維度 | 分數 | 上週依據（carry forward） |
|------|------|------------------------|
| ... | ... | ... |

</details>
```

S2 的 ONGOING 項目、S4 的 CF topic 同樣使用 `<details>` toggle，只展開「本週新發展」。

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

> **三層語意模型**（源自 claude-reports 資訊架構）：
> - **Tier 1 — Signal**（S0-S2）：回答「現在有問題嗎？業界發生什麼事？」
> - **Tier 2 — Diagnosis**（S3-S8）：回答「根因是什麼？多框架交叉驗證」
> - **Tier 3 — Action**（S9-S10）：回答「會議上問什麼？會後做什麼？」
>
> Tier 1 內容應最精煉（讀者 2 分鐘內掌握），Tier 2 為按需展開的深度分析。

#### 第一批：S0-S4（Tier 1 Signal + Tier 2 前段）

**Section 0：執行摘要（5 bullets）**
從 S1-S10 蒸餾 5 個最重要的發現，每個 1 句話。最後生成（先跳過）。

**Section 1：本週異常地圖**
- 列出所有 ALERT_DOWN / ALERT_UP 指標
- 每個指標標注月趨勢 / 週趨勢
- 用表格呈現，按嚴重度排序

**Section 2：業界最新動態**

**內容密度要求**：S2 必須包含至少 **15 行**非標題、非分隔線的實質內容，並引用至少 **5 個不同來源名稱**。

**重要：所有業界動態必須附上原始來源 URL**。

**Delta 指引（若有 prevReport）**：
- `[ONGOING-W{n}]` 項用 `<details>` toggle 折疊，只寫「本週新發展」
- `[NEW]` 項完整展開
- `[RESOLVED]` 項一句帶過
- Google 官方更新若無新 incident，篇幅讓給新的業界報導

```markdown
### Google 官方更新
- [日期] [更新名稱](URL) — [狀態/影響] — [與本週異常的關聯性]

### 業界報導
- [來源] [標題](URL) — [摘要] — [與本站異常的可能關聯]

### 關鍵字市場趨勢（Google Trends）
| 關鍵字 | 本站趨勢 | 市場趨勢 | 判斷 | 來源 |
|--------|---------|---------|------|------|

### SERP Feature 偵測
| 關鍵字 | 觀察到的 SERP Feature | 對有機 CTR 的影響 | 來源 |
|--------|---------------------|-----------------|------|
```

**Section 3：深度根因假設**

**子標題格式**：`### H{N}：{S1 指標名稱}`。指標名稱**必須與 S1 表格一致**。子標題中**禁止使用括號**。

**大型 S1 集合時的分群策略**（>8 項 ALERT_DOWN）：分群數 5-7 群。

**假設生命週期標注（若有 prevReport）**：`New Hypothesis` / `Updated` / `Validated` / `Discarded`

對每群提出 3 個假設（`**假設 1（技術面）**` 格式），每個結尾標注「**可驗證**」「**需人工確認**」或「**需顧問判斷**」。

**Section 4：顧問視角交叉比對**

**Delta 指引（若有 prevReport）**：
- `[NEW]` topic ≥ 2 個；`[CF]` topic 用 `<details>` toggle，只寫「本週進展」

```markdown
| 狀態 | 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|------|---------|-------------|---------|---------|------|
```

**四欄必填規則**：每格 >5 字元實質內容。

#### 第二批：S5-S8（Tier 2 Diagnosis 後段）

**Section 5：五層審計缺口清單**

**Section 6：E-E-A-T 現況評估**

**Delta 指引（若有 prevReport）**：
- Changed 維度展開，標注 ↑↓ + 變動原因
- No Change 維度用 `<details>` toggle 折疊，carry forward 上週依據
- 若所有維度相同，**必須說明原因**

```markdown
**Changed this week:**
| 維度 | 分數 | 變化 | 原因 |
|------|------|------|------|

<details>
<summary>No Change（{N} 維度，點擊展開上週評估）</summary>

| 維度 | 分數 | 上週依據（carry forward） |
|------|------|------------------------|

</details>
```

若無 prevReport，使用原始格式（完整表格，無 toggle）。

**Section 7：人本七要素分析** — Delta 指引同 S6。

**Section 8：SEO 成熟度自評** — Delta 指引同 S6。

#### 第三批：S9-S10 + S0（Tier 3 Action + S0 回填）

**Section 9：會議提問清單（核心輸出）**

**指標名稱呼應規則**：每個問題中必須包含至少一個 S1/S3 的指標原始名稱。

**Delta 指引（若有 prevReport）**：`[NEW]` 完整展開；`[CARRY-W{n}]` 用 toggle 折疊 + 補充新 context。

四類提問（A 確認事實 3-5 題、B 探索判斷 4-6 題、C 挑戰假設 2-3 題、D 業界趨勢 2-3 題）。

**Section 10：會議後行動核查表**

每項格式：`- [ ] 在 {工具名} {動作動詞} {具體對象} — **[{維度} L{X}→L{Y}]**`

三要素必備：(1) 工具名 (2) 動作動詞 (3) 成熟度標籤。

**最後回填 Section 0**：從 S1-S10 蒸餾 5 bullets。

---

### Step E-prime：自我驗證（Self-Validation）

存檔前逐項確認（不對使用者輸出，僅內部計數並修正）：

| 項目 | 標準 | 不達標行動 |
|------|------|-----------|
| Section 完整性 | S0-S10 共 11 個 section 標題 | 補齊缺少的 section |
| Citation 密度 | ≥15 筆 [N] 標記 | 補引用 qaMap 相關 QA |
| S2 內容密度 | ≥15 行非標題實質內容、≥5 個來源名稱 | 擴展業界動態 |
| S3 指標名稱一致性 | 子標題指標名稱 = S1 表格指標名稱 | 修正不一致 |
| S4 四欄必填 | 每格 >5 字元實質內容 | 充實空格 |
| S6/S7/S8 Toggle 一致性 | No Change 維度已用 `<details>` 折疊 | 補折疊標籤 |
| S9 提問數量 | A 3-5、B 4-6、C 2-3、D 2-3 題 | 補充或精簡 |
| S10 三要素 | 每項含工具名 + 動作動詞 + 成熟度標籤 | 補充缺失要素 |
| Delta 標注完整性 | 所有新舊項正確標注 [NEW]/[CF]/[CARRY] | 補漏標 |

驗證方式：逐項計數，任何不達標項在存檔前修正。此步驟源自 claude-reports 的 `report_validate` 模式——確保輸出品質不因資料變化而劣化。

---

### Step F：存檔與文件留存

#### F1：完整報告存檔

附加 metadata JSON blocks → 計算 hash → 存至 `output/meeting_prep_YYYYMMDD_{hash8}.md`

#### F2：業界動態累積（research/11-seo-industry-updates.md）

Append 新日期 section。超過 12 sections 時移除最舊。

#### F3：評分與洞察累積（research/12-meeting-prep-insights.md）

Append 評分追蹤行 + 交叉比對新發現。

#### F4：結構化趨勢記錄（data/seo-trends.jsonl）

在 F3 的 prose append 之外，另存一行 JSONL 供跨週自動比較（源自 claude-reports `report-trends.sh` 模式）：

```bash
# 在報告中計數後，用 bash 寫入 JSONL
echo '{"date":"'$(date +%Y-%m-%d)'","report":"meeting-prep","eeat_avg":<S6平均>,"maturity_strategy":"<L>","maturity_process":"<L>","maturity_keywords":"<L>","maturity_metrics":"<L>","s9_questions":<S9總數>,"citations":<[N]計數>}' >> data/seo-trends.jsonl
```

若 `data/` 目錄不存在則先 `mkdir -p data`。此步驟讓 Step C-prime 的前週差異偵測可直接讀 JSONL，不需重新解析完整 Markdown。

---

## Citation 標記規則

Perplexity 風格 `[N]` 標記。密度目標 15-18 筆。

**Section-Citation 對應**：S3 優先引用技術SEO/索引與檢索/連結策略/演算法與趨勢/Discover與AMP/搜尋表現分析。S6 同理。

---

## 輸出摘要

完成後告訴使用者：輸入來源、ALERT_DOWN 數量、業界動態筆數、KB 引用數、顧問文章引用數、E-E-A-T 平均分、成熟度概覽、Google Trends 驗證結果、SERP Feature 偵測結果、提問清單總數、儲存路徑、research/ 更新狀態。
