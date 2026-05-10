# Plan: crawled-not-indexed-fix-20260508

**Status**: active
**Created**: 2026-05-11
**Source**: `output/report_20260508_c734a2de.md`（vocus.cc 站 5/8 週報，唯一週+月雙惡化指標）
**KB Evidence**: KB 10–17, 21, 22, 26（hex stable_id 對應 `output/qa_final.json`）
**Owner**: SEO 團隊（內容/前端/RD 三方協作）

---

## 一、問題與目標

### 問題快照（2026-05-08）

| 指標 | 本週值 | 週變動 | 月變動 | 警戒線 |
|------|--------|--------|--------|--------|
| 已檢索但未索引 | **95.3 萬** | +18.54% | +73.41% | 100 萬（紅線） |
| Coverage（有效頁面） | **120.0 萬** | -11.32% | -29.46% | 100 萬（紅線） |
| 未索引 / 有效比 | **0.7944** | +33.67% | +106.32% | **0.80**（剩 0.0056 緩衝） |
| 點擊（月線） | 119.46 萬 | -2.74% | **-18.75%** | -10% |
| 曝光（月線） | 46.06M | -3.60% | -25.35% | -15% |

**核心結論**：當前唯一週線+月線雙惡化的核心指標。一旦未索引突破 100 萬 + Coverage 跌破 100 萬 → 比值 > 1.0，意味著「Google 抓進來的頁面有一半以上連索引都進不去」，下週曝光連動再跌一階。

### 量化驗收門檻

| 時點 | 未索引絕對量 | 未索引/有效比 | 來源依據 |
|------|--------------|---------------|----------|
| 本週末（5/15） | **不破 100 萬** | < 0.85 | 守住紅線 |
| 兩週後（5/22） | **≤ 80 萬** | < 0.65 | 階段 2 修復生效 |
| 一個月後（6/08） | **≤ 48 萬**（-50%） | **≤ 0.40** | KB 15「降一半即可帶流量增量」 |
| Coverage | 120 萬 → **130 萬+** | — | 排除式上升（非衝量） |
| 點擊月跌幅 | -18.75% → **-10% 內** | — | 連動回升 |

**北極星指標**：未索引/有效比 ≤ 0.40（業界健康站台 < 0.30）

---

## 二、根因假設分群

依 KB 證據與 vocus.cc 過往技術盤點推估占比（修復後再校準）：

| 根因 | 預估占比 | 主要 KB 證據 | 主要影響頁型 |
|------|----------|--------------|--------------|
| **A. 連結密度不足** | ~40% | KB 22 / KB 26 | /tag、/user、舊 /article |
| **B. 內容稀薄** | ~30% | KB 22（內容豐富性） | /salon 廣告頁、空 /tag、佔位 /user |
| **C. Canonical 衝突** | ~20% | KB 10 / KB 11 / KB 12 | /article 帶參數、/post AMP |
| **D. AMP 配對缺失** | ~10% | KB 16 / KB 21 | /article ↔ /post 對 |
| **E. robots.txt 誤擋** | < 5% | KB 17 | 自定義網址段 |

**反例證據（KB 13）**：若 Coverage 下降搭配「流量頁面（impressions/clicks 來源）穩定」，是**正向訊號**（排除低品質頁），不是壞事。診斷階段必須區分「死頁排除」與「核心頁掉索引」。

---

## 三、4 階段執行計畫

### 階段 1：診斷分群（Day 1–2，2026-05-11 → 05-12）

**目標**：把 95.3 萬未索引 URL 歸位到 5 大根因桶 + 5 大頁型，量化每桶占比。

#### Task 1.1 — GSC 匯出 1,000 URL 樣本

- **工具**：Google Search Console > Pages > 「已檢索但未索引」報表
- **動作**：匯出最近 7 天新增的 1,000 URL（CSV）
- **產出**：`data/cni_sample_20260511.csv`
- **量化目標**：樣本覆蓋 5 頁型各 ≥ 150 URL（不足則補抓至滿）
- **預估時間**：2 小時

#### Task 1.2 — 5 頁型分流標記

- **工具**：Python pandas（regex 比對 URL pattern）
- **動作**：依 URL pattern 標記 `page_type`：
  - `/article/{id}` → article
  - `/tag/{slug}` → tag
  - `/user/{id}` 或 `/{username}` → user
  - `/post/{id}` → post（AMP 對）
  - `/salon/{slug}` → salon
- **產出**：`data/cni_sample_20260511_typed.csv`（含 page_type 欄）
- **量化目標**：每頁型計數 + 占比表（預期 article 50%+，tag/user 各 15%+）
- **預估時間**：1 小時

#### Task 1.3 — 5 維度自動化判定

逐 URL 跑以下檢查（可平行）：

| 維度 | 工具 | 判定條件 | 對應根因 |
|------|------|----------|----------|
| 1. noindex tag | Screaming Frog SEO Spider | `<meta name="robots" content="noindex">` 存在 | F. 主動排除（合理） |
| 2. canonical 衝突 | Screaming Frog | canonical URL ≠ 自身 URL 且非 `?utm_*` 變體 | C. Canonical |
| 3. 內部連結密度 | Screaming Frog `Inlinks` 報表 | 內鏈數 < 3 | A. 連結密度 |
| 4. 內容字數 | Screaming Frog `Word Count` | 內容主體 < 300 字 | B. 內容稀薄 |
| 5. robots.txt 阻擋 | URL Inspection API | `crawlAllowed: false` | E. robots 誤擋 |

- **產出**：`data/cni_sample_20260511_diagnosed.csv`（5 個 boolean 欄 + `primary_cause` 欄）
- **量化目標**：每個根因桶占比 ± 5%（與本 plan 預估比對）
- **預估時間**：4 小時（含 Screaming Frog 抓取）

#### Task 1.4 — 流量價值分層

- **工具**：GSC > Performance > Pages（最近 28 天）
- **動作**：對 1,000 URL 標記過去 28 天 `clicks`：
  - `value_tier_A`：clicks ≥ 10（不可丟）
  - `value_tier_B`：clicks 1–9（可救）
  - `value_tier_C`：clicks = 0（可 noindex 或重寫）
- **產出**：`data/cni_sample_20260511_final.csv`（含 value_tier 欄）
- **量化目標**：A+B 占比 ≥ 60%（KB 13 反例：若 ≤ 30% 表示多為死頁，反而是正向）
- **預估時間**：1 小時

#### Task 1.5 — 階段 1 報告

- **產出**：`output/cni_diagnosis_20260512.md`
- **內容**：
  - 5 頁型 × 5 根因 矩陣表
  - 流量價值分層比例
  - 修復優先序建議（依「占比 × 流量價值」排序）
- **驗收**：交付給 SEO + RD lead，1 小時內口頭確認分群結論

---

### 階段 2：依族群分流修復（Day 3–7，2026-05-13 → 05-17）

5 大頁型優先序（按流量貢獻 × 修復槓桿）：

| 排序 | 頁型 | 為何優先 | KB 依據 |
|------|------|----------|---------|
| 1 | **/article** | 流量最大、修復影響最廣 | — |
| 2 | **/tag** | 高 ROI（佔搜尋流量 10–15%） | KB 21 |
| 3 | **/user** | 連結中樞，修好連帶救 article | KB 22 / KB 26 |
| 4 | **/post** | AMP 連動（修好帶 Top Stories） | KB 16 / KB 21 |
| 5 | **/salon** | 流量低但 noise 大，可大量 noindex | KB 13 |

#### Task 2.1 — /article 修復（根因 A + C，Day 3–4）

**A. 連結密度（KB 22 / KB 26）**：

- **工具**：Screaming Frog `Inlinks` 報表 + `vocus-web-ui` 模板
- **動作**：
  - 識別內鏈 < 3 的 article（預估 30 萬+）
  - 在 article 模板加「同 tag 推薦 5 篇」+「同作者其他文章 3 篇」區塊
  - 確保推薦來自**內容頁**而非 nav/footer（KB 26：分布相關性 > 總數）
- **量化目標**：所有 article 內鏈 ≥ 5（從內容頁來源）
- **驗收**：Screaming Frog 重抓樣本，內鏈分布 P50 ≥ 7

**C. Canonical 衝突（KB 10 / KB 11 / KB 12）**：

- **工具**：Screaming Frog + 手動 GSC URL Inspection
- **動作**：
  - 列出 canonical ≠ 自身 URL 的 article（預估 5–10 萬）
  - 子類型分群：
    - 「使用者未選取標準網頁」→ 補 `<link rel="canonical">` 指向自身
    - 「Google 選擇與使用者不同」→ 檢查內部連結是否一致指向 canonical
    - 「已提交未獲選」→ 補強內容差異化
  - **內部連結同步修正**（KB 10）：所有指向變體的內鏈改指 canonical URL
- **量化目標**：canonical 衝突 article 比例由 X% 降至 < 2%
- **驗收**：URL Inspection API 抽 50 筆，`googleSelectedCanonical == userCanonical` 比例 ≥ 95%

#### Task 2.2 — /tag 修復（根因 B + A，Day 3–4，與 article 平行）

- **工具**：`vocus-web-ui` tag 模板
- **動作**（KB 21 + KB 22）：
  - 空 tag 頁（< 5 篇文章）→ noindex（避免內容稀薄）
  - 5–20 篇 tag 頁 → 保留但加「相關 tag 推薦」+「tag 簡介 200 字」
  - 20+ 篇 tag 頁 → 加分頁 SEO（`rel="next/prev"` + canonical）
  - **AMP 配對**：tag 頁加 `<link rel="amphtml">`（KB 16）
- **量化目標**：tag 頁索引率由 Y% 升至 ≥ 70%
- **驗收**：抽 30 個 20+ 篇 tag 頁，URL Inspection 全部 `indexingState == "INDEXING_ALLOWED"`

#### Task 2.3 — /user 修復（根因 A + B，Day 5）

- **工具**：`vocus-web-ui` user profile 模板
- **動作**（KB 22）：
  - 空 user（< 3 篇文章）→ noindex
  - 活躍 user 加「最新 5 篇」+「熱門 5 篇」+「相關作者 3 位」（連結中樞）
  - 加 author schema（已在 `vocus-author-schema-hotfix.md` 推進，本任務跟進）
- **量化目標**：活躍 user 頁內鏈導出 ≥ 13 條（5+5+3）
- **驗收**：Screaming Frog 抽 50 個活躍 user，外鏈計數 P50 ≥ 13

#### Task 2.4 — /post + AMP 修復（根因 D + E，Day 6）

**D. AMP 配對（KB 16）**：

- **工具**：Screaming Frog 自訂 extraction
- **動作**：
  - 找出原始 /post 缺 `<link rel="amphtml">` 的頁（預估 3–5 萬）
  - RD 修補模板，所有 /post 自動帶 amphtml link
  - AMP 頁面同步補 `<link rel="canonical">` 指向原始 /post
- **量化目標**：/post amphtml 覆蓋率 ≥ 99%
- **驗收**：48 小時後（KB 注：AMP 修復後 Top Stories 配給驗證視窗）查 Discover/Top Stories 流量

**E. robots.txt 誤擋（KB 17）**：

- **工具**：robots.txt + URL Inspection API
- **動作**：
  - 比對自定義網址段是否被 `Disallow`
  - 移除誤擋規則（特別檢查 `Disallow: /post/` 之類過寬規則）
- **量化目標**：< 5 條 Disallow 規則影響核心頁型
- **驗收**：URL Inspection 抽 100 筆 /post，`robotsTxtState == "ALLOW"` 100%

#### Task 2.5 — /salon 修復（根因 B，Day 7）

- **工具**：GSC + 內部廣告系統
- **動作**（KB 13 反例）：
  - 過去 28 天 0 點擊 + 字數 < 200 的 /salon → **noindex**（不要救，認賠）
  - 點擊 ≥ 1 但字數 < 500 → 重寫(補充內容至 1,000 字+)
  - 高品質 salon → 加 article 推薦區塊
- **量化目標**：/salon 索引總量降 30%（健康收縮，KB 13 正向訊號）
- **驗收**：兩週後 Coverage 不再下跌而 /salon 索引下降 → 屬正向收縮

---

### 階段 3：批次 sitemap 重新提交（Week 2，2026-05-18 → 05-22）

#### Task 3.1 — Sitemap 拆分

- **工具**：`vocus-web-ui` sitemap 產生器
- **動作**：
  - 拆 5 個獨立 sitemap：`sitemap-article.xml` / `sitemap-tag.xml` / `sitemap-user.xml` / `sitemap-post.xml` / `sitemap-salon.xml`
  - 每個 sitemap 上限 50,000 URL（Google 規範）
  - 加 `lastmod` 欄位反映階段 2 修復時間（觸發 Google 重抓）
- **產出**：`/sitemap.xml`（index）+ 5 個子 sitemap
- **驗收**：GSC > Sitemaps 5 份全部 `Success` 狀態

#### Task 3.2 — URL Inspection API 批次催索引

- **工具**：URL Inspection API（quota 2,000/day）
- **動作**：
  - 對階段 2 已修復的高價值 URL（value_tier_A）批次 `requestIndexing`
  - 優先序：article > tag > post > user > salon
  - 連續 5 天，每天 2,000 筆，共 1 萬筆
- **量化目標**：高價值 URL 100% 提交完畢
- **驗收**：每天 GSC 「已要求索引」計數 += 2,000

#### Task 3.3 — 內部連結重生成

- **工具**：`vocus-web-ui` 後台批次任務
- **動作**：
  - 重跑全站「相關推薦」演算法，套用階段 2 模板
  - 確保 KB 26：推薦來自內容頁而非 nav/footer
- **量化目標**：全站平均內鏈度 +30%（從基準線）

---

### 階段 4：驗收（Week 3–4，2026-05-25 → 06-08）

#### Task 4.1 — 每週指標追蹤

每週一上午 10:00 跑 `make generate-report`，比對：

| 週次 | 預期未索引 | 預期 Coverage | 預期比值 |
|------|------------|---------------|----------|
| 5/15（W1） | < 100 萬 | ≥ 120 萬 | < 0.85 |
| 5/22（W2） | ≤ 80 萬 | ≥ 125 萬 | < 0.65 |
| 5/29（W3） | ≤ 60 萬 | ≥ 130 萬 | < 0.50 |
| 6/05（W4） | ≤ 48 萬 | ≥ 130 萬 | ≤ 0.40 |

#### Task 4.2 — 5 頁型修復成效抽樣

每週對 5 頁型各抽 50 URL（共 250），跑 URL Inspection，記錄：

- `indexingState` 分布
- `googleCanonical` 一致性
- `crawlAllowed` 比例

**產出**：`output/cni_progress_W{1,2,3,4}.md`

#### Task 4.3 — KB 15 驗證

階段 4 結束時，比對：

- 未索引降 50% 是否真的帶來流量增量（KB 15 預期效益）
- 點擊月跌幅是否從 -18.75% 收斂至 -10% 內

---

## 四、5 大頁型修復優先序總覽

| 排序 | 頁型 | 主要根因 | 修復人天 | 預期未索引降量 | KB 依據 |
|------|------|----------|----------|----------------|---------|
| 1 | /article | A + C | 4 | -30 萬 | KB 22 / KB 10 |
| 2 | /tag | B + A | 2 | -10 萬 | KB 21 / KB 22 |
| 3 | /user | A + B | 1 | -5 萬 | KB 22 / KB 26 |
| 4 | /post | D + E | 1 | -5 萬 | KB 16 / KB 17 |
| 5 | /salon | B（noindex） | 1 | -7 萬 | KB 13 |
| **合計** | — | — | **9** | **-57 萬** | — |

預期一個月後未索引 95.3 萬 - 57 萬 = **38.3 萬**（優於目標 48 萬，留 ~10 萬緩衝）。

---

## 五、Definition of Done

### 量化驗收（必須全達標）

- [ ] **本週末（5/15）**：未索引絕對量 **不破 100 萬**
- [ ] **兩週後（5/22）**：未索引 ≤ **80 萬**，未索引/有效比 < 0.65
- [ ] **一個月後（6/08）**：未索引 ≤ **48 萬**（-50%，KB 15 預期）
- [ ] **Coverage** 從 120 萬升回 **≥ 130 萬**
- [ ] **未索引/有效比** ≤ **0.40**
- [ ] **點擊月跌幅** 由 -18.75% 收斂到 **-10% 內**

### 流程驗收

- [ ] 階段 1 診斷報告 `output/cni_diagnosis_20260512.md` 交付
- [ ] 階段 2 五頁型修復 PR 全部 merge（vocus-web-ui）
- [ ] 階段 3 sitemap 5 份 GSC `Success`
- [ ] 階段 4 W1–W4 每週進度報告 `output/cni_progress_W*.md` 完成
- [ ] 一個月後抽 250 URL（5 頁型 × 50）URL Inspection，索引率 ≥ 70%
- [ ] MEMORY.md 更新「已驗證 KB 15 預期效益」段落

---

## 六、風險與監控

### 風險清單

| 風險 | 等級 | 對應 KB | 監控指標 | Mitigation |
|------|------|---------|----------|------------|
| **過度 noindex 致 Coverage 崩** | 高 | KB 13 反例 | Coverage 週跌 > 5% | 階段 2 每天監控；單日 noindex < 5 萬筆，分批執行 |
| **canonical 修復未同步內鏈** | 高 | KB 10 / KB 11 | `googleSelectedCanonical` 不一致率 | 修 canonical 必須同時跑內鏈重生（Task 3.3） |
| **AMP 修復後 Top Stories 配給未提升** | 中 | KB 21 | 48 小時後 Discover/Top Stories 流量 | 48 小時驗證視窗，未提升則檢查 schema validation |
| **修復觸發 Google 重抓 → 短期未索引上升** | 中 | — | 5/15 未索引 > 100 萬 | 預期前 3–5 天可能上升 5–10%，紅線守 105 萬而非 100 萬 |
| **/salon noindex 影響 PageRank 流動** | 低 | — | 全站平均排名 | 只 noindex 0 點擊頁，保留高品質 salon |
| **GSC 報表延遲 2–3 天** | 低 | — | 報表更新時間 | 用 URL Inspection API 即時驗證 |

### 監控頻率

| 指標 | 頻率 | 工具 | 觸發行動 |
|------|------|------|----------|
| 未索引絕對量 | 每日 | GSC + `make generate-report` | > 100 萬 → 暫停 noindex 操作 |
| Coverage | 每日 | GSC | 週跌 > 5% → 緊急 review |
| 未索引/有效比 | 每週一 | 週報自動計算 | > 0.85 → escalate |
| 5 頁型索引率 | 每週 | URL Inspection 抽樣 250 | 任一頁型 < 50% → 加診斷 |
| 點擊/曝光 | 每日 | GSC | 月跌幅擴大 → 對照修復進度 |
| AMP Top Stories 配給 | 修復後 48h | GSC > Top Stories | 未提升 → schema validate |

---

## 七、每階段所需工具

| 階段 | 必要工具 | 用途 |
|------|----------|------|
| 1 診斷 | GSC、Screaming Frog SEO Spider、URL Inspection API、pandas | URL 匯出、5 維度判定、流量分層 |
| 2 修復 | `vocus-web-ui`（前端模板）、Screaming Frog（驗收）、URL Inspection API | 模板改動、驗證內鏈/canonical |
| 3 sitemap | `vocus-web-ui` sitemap 產生器、GSC Sitemaps、URL Inspection API（批次） | 拆分提交、催索引 |
| 4 驗收 | GSC、`make generate-report`、URL Inspection API、Ahrefs（外鏈交叉比對） | 每週指標追蹤、抽樣驗收 |

### 工具 quota 規劃

- **URL Inspection API**：2,000/day × 30 天 = 60,000 次（足夠 1 萬批次催索引 + 抽樣驗收）
- **Screaming Frog**：免費版 500 URL，需專業版（unlimited）
- **GSC API**：未限額但有 rate limit（10 QPS）

---

## 八、追蹤指標清單

### 每日指標（自動化）

- 未索引絕對量（GSC > Pages > Crawled, currently not indexed）
- Coverage（GSC > Pages > Indexed）
- 未索引/有效比（計算欄）
- 點擊、曝光、CTR（GSC > Performance）
- URL Inspection API 已用 quota

### 每週指標（每週一報告）

- 未索引/有效比 W/W、M/M
- 5 頁型分桶占比變化
- 5 大根因桶占比變化
- 250 URL 抽樣 indexing state 分布
- AMP 配對覆蓋率
- Canonical 一致性比例
- 全站平均內鏈度

### 每月指標（驗收用）

- 未索引絕對量月降幅（目標 -50%）
- Coverage 月升幅（目標 +8%）
- 點擊月跌幅收斂度（-18.75% → -10% 內）
- KB 15 預期效益達成度（流量增量）

---

## Out of Scope

- 跨站修復（只處理 vocus.cc，不含其他 properties）
- 全站重新抓取（只批次催索引，不觸發全站 recrawl）
- Schema 修復除外（已在 `vocus-author-schema-hotfix.md` 處理）
- 國際化 SEO（hreflang）— 本次未涉及多語站
- Core Web Vitals（CWV）— 未索引主因不在效能，獨立議題
- Discover 演算法調整 — 屬內容策略，非 indexing 議題

---

## References

- 來源報告：`output/report_20260508_c734a2de.md`
- 對應深度分析 report：`~/Documents/knowledge-base/reports/seo-crawled-not-indexed-deepdive-20260508.md`
- KB Q&A 資料庫：`output/qa_final.json`（hex stable_id 對應）
- KB 證據（依本 plan 引用順序）：
  - KB 22 (`b82545d945ee0f56`) — 連結結構與內容豐富性根因
  - KB 15 (`80e67d0329557d54`) — 降一半帶流量增量（量化效益）
  - KB 13 (`81c32da0e940147b`) — Coverage 下降 + 流量穩定為正向訊號
  - KB 10 (`5c302d663e820183`) — Canonical 是 hint，需內鏈一致
  - KB 11 (`8bb43c1c09668ffb`) — 使用者選取標準網址數字升 = 設定未生效
  - KB 12 (`1aa84d68b5d5065d`) — 重覆網頁三種子類型
  - KB 16 (`94e8cb17a2ed0e67`) — /post 缺 amphtml 直接導致 AMP 不收錄
  - KB 17 (`cbb4b0398dc81a35`) — robots.txt 阻擋自定義網址同步壓低 AMP + 原始頁
  - KB 21 (`b9d41bca61f51e5c`) — Tag 頁佔流量 10–15%，AMP 配套 +20–30%
  - KB 26 (`275a9dea8f216354`) — 內部連結分布相關性 > 總數
- 相關 plans：
  - `plans/active/vocus-author-schema-hotfix.md`（user/article schema 配套）
  - `plans/active/crawled-not-indexed-observability.md`（觀測能力強化）
- 工具文件：
  - GSC URL Inspection API: <https://developers.google.com/webmaster-tools/v1/urlInspection.index>
  - Screaming Frog SEO Spider: <https://www.screamingfrog.co.uk/seo-spider/>
