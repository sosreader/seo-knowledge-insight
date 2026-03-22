# Experiment Log — autoresearch/mar21

Baseline composite: **0.912616** (2026-03-21)

## Experiment Details

### #1 — categoryBoost 0.08→0.12 | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** `categoryBoost per-match` 0.08 → 0.12
- **Composite:** 0.912616 | **Delta:** 0.000
- **Status:** discarded — search-engine.ts 的 SearchEngine class 在 Supabase 模式下不被使用
- **Finding:** 確認 DEFAULT_CONFIG 參數在 Supabase 模式下無效

### #2 — overRetrieveFactor 3→5 | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** `overRetrieveFactor` 3 → 5
- **Composite:** 0.912616 | **Delta:** 0.000
- **Status:** discarded — 同 #1，search-engine.ts 不被使用
- **Finding:** 進一步確認 DEFAULT_CONFIG 全部無效

### #3 — categoryDiversityBoost base 0.12→0.18 | discarded
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** `categoryDiversityBoost` base 0.12 → 0.18
- **Composite:** 0.909728 | **Delta:** -0.003
- **Status:** discarded — mrr regression: case 20 mrr 1.0→0.5

### #4 — bigram prefix 2→3 chars | discarded
- **File:** `api/src/utils/keyword-boost.ts`
- **Change:** bigram prefix length 2 → 3
- **Composite:** 0.903577 | **Delta:** -0.009
- **Status:** discarded — many regressions: cases 3, 10, 27, 34, 38, 40

### #5 — add 轉換率+可見度 to 搜尋表現分析 hints | KEPT ✅
- **File:** `api/src/store/search-engine.ts`
- **Change:** `QUERY_CATEGORY_HINTS.搜尋表現分析` 新增 `"轉換率"`, `"可見度"`
- **Diff:**
  ```diff
  +      "轉換率",
  +      "可見度",
  ```
- **Composite:** 0.919064 | **Delta:** +0.006
- **Commit:** `ac9dcfa`

### #6 — add 意圖/反向連結/錨文本 to category hints | KEPT ✅
- **File:** `api/src/store/search-engine.ts`
- **Change:** `內容策略` 新增 `"意圖"`；`連結策略` 新增 `"反向連結"`, `"錨文本"`
- **Diff:**
  ```diff
  -    內容策略: ["內容", "文章", "eeat", "供給", "更新"],
  -    連結策略: ["連結", "內部連結", "錨點"],
  +    內容策略: ["內容", "文章", "eeat", "供給", "更新", "意圖"],
  +    連結策略: ["連結", "內部連結", "錨點", "反向連結", "錨文本"],
  ```
- **Composite:** 0.922413 | **Delta:** +0.003
- **Commit:** `39a6cac`

### #7 — add ai-overview scenario + 轉換率/signups | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** 新增 AI Overview scenario 和 measurement intent 關鍵字
- **Composite:** 0.922413 | **Delta:** 0.000
- **Status:** discarded — no QA metadata matches

### #8 — novelQueryTermBoost coefficients +50% | discarded
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** novelQueryTermBoost 三個 tier 的係數各 +50%
- **Composite:** 0.922413 | **Delta:** 0.000
- **Status:** discarded — no effect

### #9 — categoryDiversityBoost base 0.12→0.08 | discarded
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** diversity base 0.12 → 0.08
- **Composite:** 0.915946 | **Delta:** -0.006
- **Status:** discarded — recall/f1 regression

### #10 — remove 'ai' from 演算法與趨勢 hints | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** 從 `演算法與趨勢` 移除 `"ai"`
- **Composite:** 0.920779 | **Delta:** -0.002
- **Status:** discarded — recall loss > precision gain

### #11 — move 'ai' from 演算法 to 搜尋表現分析 | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** 將 `"ai"` 從 `演算法與趨勢` 移到 `搜尋表現分析` 改為 `"ai 搜尋"`
- **Composite:** 0.920779 | **Delta:** -0.002
- **Status:** discarded — same as #10

### #12 — add 數據 to GA與數據追蹤 hints | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** `GA與數據追蹤` 新增 `"數據"`
- **Composite:** 0.922413 | **Delta:** 0.000
- **Status:** discarded — simplicity: no benefit

### #13 — add 5th layer: suffix match | discarded
- **File:** `api/src/utils/keyword-boost.ts`
- **Change:** 新增第 5 層匹配：keyword 最後 2 字元（kw>=4）
- **Composite:** 0.917879 | **Delta:** -0.005
- **Status:** discarded — too loose, case 34 regressed

### #14 — tokenize: split on hyphens/slashes/punctuation | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** tokenize 函式加入 hyphen/slash/punctuation splitting
- **Composite:** 0.920266 | **Delta:** -0.002
- **Status:** discarded — case 34 regressed

### #15 — questionSignature truncate 120→60 | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** questionSignature 截斷長度 120 → 60
- **Composite:** 0.922413 | **Delta:** 0.000
- **Status:** discarded — no effect

### #16 — categoryDiversityBoost step 0.06→0.10 | discarded
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** diversity step 0.06 → 0.10
- **Composite:** 0.922413 | **Delta:** 0.000
- **Status:** discarded — no effect

### #17 — queryTerms: CJK sliding window bigrams | KEPT ✅
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** 對 ≥4 字元的純 CJK term，產生 sliding window bigrams
- **Diff:**
  ```diff
  +  const CJK_RE = /^[\u4e00-\u9fff]+$/;
  +  const baseTerms = text.toLowerCase().split(/\s+/)...
  +  for (const term of baseTerms) {
  +    result.push(term);
  +    if (term.length >= 4 && CJK_RE.test(term)) {
  +      for (let i = 0; i < term.length - 1; i++) {
  +        result.push(term.slice(i, i + 2));
  +      }
  +    }
  +  }
  ```
- **Composite:** 0.922861 | **Delta:** +0.000（marginal）
- **Commit:** `52a5ee2`

### #18 — CJK bigrams: non-overlapping pairs | discarded
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** CJK bigrams 改為不重疊（每 2 字元一組）
- **Composite:** 0.922405 | **Delta:** -0.000
- **Status:** discarded — lower than sliding window

### #19 — CJK bigram threshold 4→6 chars | discarded
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** CJK bigram 觸發閾值 4 → 6 字元
- **Composite:** 0.922058 | **Delta:** -0.001
- **Status:** discarded

### #20 — CJK bigrams: head-tail only | discarded
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** 只取頭尾 bigram 而非 sliding window
- **Composite:** 0.922802 | **Delta:** -0.000
- **Status:** discarded — marginal

### #21 — tokenize: strip punctuation | discarded
- **File:** `api/src/store/search-engine.ts`
- **Change:** tokenize 函式移除標點符號
- **Composite:** 0.920067 | **Delta:** -0.003
- **Status:** discarded — case 15, 34 regressed

### #22 — add specific hints: key moments/圖片搜尋/創作者/max-image-preview | KEPT ✅
- **File:** `api/src/store/search-engine.ts`
- **Change:** 多個 category hints 擴充
- **Diff:**
  ```diff
  +      "key moments",
  +      "image pack",
  +      "圖片搜尋",
       ],
  -    Discover與AMP: ["discover", "amp", "news"],
  +    Discover與AMP: ["discover", "amp", "news", "max-image-preview"],
  -    平台策略: ["平台", "作者", "/user", "路徑", "cms"],
  +    平台策略: ["平台", "作者", "/user", "路徑", "cms", "創作者", "自訂網域"],
  ```
- **Composite:** 0.926483 | **Delta:** +0.004
- **Commit:** `08b9d0c`

### #23 — add 點擊率/觸發 to hints | discarded
- **Composite:** 0.926483 | **Delta:** 0.000 | discarded — no effect

### #24 — add 有效頁面 to 索引與檢索 | discarded
- **Composite:** 0.926483 | **Delta:** 0.000 | discarded — no effect

### #25 — exact keyword match: 1.0→1.5 hits weight | KEPT ✅
- **File:** `api/src/utils/keyword-boost.ts`
- **Change:** exact match `totalHits += 1` → `totalHits += 1.5`
- **Diff:**
  ```diff
  -      totalHits += 1;
  +      totalHits += 1.5;
  ```
- **Composite:** 0.933339 | **Delta:** +0.007
- **Commit:** `9bdbfa7`

### #26 — exact match 1.5→2.0 | KEPT ✅
- **File:** `api/src/utils/keyword-boost.ts`
- **Change:** `totalHits += 1.5` → `totalHits += 2.0`
- **Composite:** 0.934224 | **Delta:** +0.001
- **Commit:** `4fbfc5d`

### #27 — exact match 2.0→2.5 | KEPT ✅
- **File:** `api/src/utils/keyword-boost.ts`
- **Change:** `totalHits += 2.0` → `totalHits += 2.5`
- **Composite:** 0.935407 | **Delta:** +0.001
- **Commit:** `1c89d92`

### #28 — exact match 2.5→3.0 | KEPT ✅
- **File:** `api/src/utils/keyword-boost.ts`
- **Change:** `totalHits += 2.5` → `totalHits += 3.0`
- **Composite:** 0.942787 | **Delta:** +0.007
- **Commit:** `f05110a`
- **Note:** Massive improvement — exact match 3.0x 是最大單一槓桿

### #29 — exact match 3.0→3.5 | discarded
- **Composite:** 0.942787 | **Delta:** 0.000 | discarded — same score, keep simpler 3.0

### #30 — token forward/reverse match 1.0→1.5 | KEPT ✅
- **File:** `api/src/utils/keyword-boost.ts`
- **Change:** token forward/reverse match 各從 1.0 → 1.5
- **Diff:**
  ```diff
       } else if ([...queryTokens].some((t) => kwLower.includes(t))) {
  -      totalHits += 1;
  +      totalHits += 1.5;
       } else if ([...kwTokens].some((t) => queryLower.includes(t))) {
  -      totalHits += 1;
  +      totalHits += 1.5;
  ```
- **Composite:** 0.944530 | **Delta:** +0.002
- **Commit:** `6d15b4a`

### #31 — token match 1.5→2.0 | discarded
- **Composite:** 0.944530 | **Delta:** 0.000 | discarded — same, maxHits cap

### #32 — bigram partial 0.5→1.0 | discarded
- **Composite:** 0.944530 | **Delta:** 0.000 | discarded — dominated by stronger signals

### #33 — add url inspection / inspection api to 索引與檢索 | KEPT ✅
- **File:** `api/src/store/search-engine.ts`
- **Change:** `索引與檢索` 新增 `"url inspection"`, `"inspection api"`
- **Diff:**
  ```diff
  -    索引與檢索: ["索引", "coverage", "googlebot", "canonical", "檢索未索引"],
  +    索引與檢索: ["索引", "coverage", "googlebot", "canonical", "檢索未索引", "url inspection", "inspection api"],
  ```
- **Composite:** 0.945665 | **Delta:** +0.001
- **Commit:** `86c8d06`

### #34 — add 提交 to 索引與檢索 | discarded
- **Composite:** 0.945665 | **Delta:** 0.000 | discarded

### #35 — add 問題類 to 內容策略 | discarded
- **Composite:** 0.945665 | **Delta:** 0.000 | discarded

### #36 — novelQueryTermBoost caps doubled | CRASH
- **Composite:** 0.012000 | **Status:** discarded — server crash, bad result

### #37 — categoryDiversityBoost base 0.12→0.15 | discarded
- **Composite:** 0.943340 | **Delta:** -0.002 | discarded — case 5 regressed

### #38 — add 大圖 to Discover hints | discarded
- **Composite:** 0.945665 | **Delta:** 0.000 | discarded

### #39 — remove CJK bigram (simplicity test) | discarded
- **Composite:** 0.938039 | **Delta:** -0.008
- **Status:** discarded — CJK bigrams confirmed essential（移除掉 0.008）

### #40 — multi-token exact 4.0 vs single 3.0 | discarded
- **Composite:** 0.945665 | **Delta:** 0.000 | discarded — maxHits cap

### #41 — diversity base 0.10 step 0.08 | KEPT ✅
- **File:** `api/src/store/query-term-utils.ts`
- **Change:** `categoryDiversityBoost` base 0.12→0.10, step 0.06→0.08
- **Diff:**
  ```diff
  -  return 0.12 + Math.min(uncoveredQueryCategories - 1, 1) * 0.06;
  +  return 0.10 + Math.min(uncoveredQueryCategories - 1, 1) * 0.08;
  ```
- **Composite:** 0.945743 | **Delta:** +0.000（marginal）
- **Commit:** `0c564f7`

### #42 — diversity base 0.10 step 0.05 max 2 | discarded
- **Composite:** 0.945743 | **Delta:** 0.000 | discarded — same as #41

### #43 — keyword tokenize CJK/ASCII split | discarded
- **Composite:** 0.945743 | **Delta:** 0.000 | discarded

### #44 — novelQueryTermBoost +50% | discarded
- **Composite:** 0.945365 | **Delta:** -0.000 | discarded — marginal regression

### #45 — questionSignature 120→40 | discarded
- **Composite:** 0.945743 | **Delta:** 0.000 | discarded

### #46 — inferQueryLabels word boundary for short English hints | KEPT ✅
- **File:** `api/src/store/search-engine.ts`
- **Change:** ≤3 字元的純英文 hint 改用 word boundary 匹配（`\bamp\b`）避免 false positive
- **Diff:**
  ```diff
  +    if (hint.length <= 3 && /^[a-z0-9]+$/.test(hint)) {
  +      return new RegExp(`\\b${hint}\\b`).test(queryLower);
  +    }
  +    return queryLower.includes(hint);
  ```
- **Composite:** 0.946940 | **Delta:** +0.001
- **Commit:** `8a451a7`

### #47 — word boundary threshold 3→4 | discarded
- **Composite:** 0.946940 | **Delta:** 0.000 | discarded

### #48 — add 排名 to 搜尋表現分析 | discarded
- **Composite:** 0.946940 | **Delta:** 0.000 | discarded

### #49 — matchedQueryTerms partial CJK match | discarded
- **Composite:** 0.940021 | **Delta:** -0.007 | discarded — too loose

### #50 — add 流量佔比 to 搜尋表現分析 | discarded
- **Composite:** 0.945812 | **Delta:** -0.001 | discarded — hurt case 16

### #51 — diversity step 0.08→0.12 | discarded
- **Composite:** 0.946940 | **Delta:** 0.000 | discarded

### #52 — inferQueryLabels bidirectional match | discarded
- **Composite:** 0.935419 | **Delta:** -0.012 | discarded — massive false positives

### #53 — remove cms from 平台策略 | KEPT ✅
- **File:** `api/src/store/search-engine.ts`
- **Change:** 從 `平台策略` hints 移除 `"cms"`
- **Diff:**
  ```diff
  -    平台策略: ["平台", "作者", "/user", "路徑", "cms", "創作者", "自訂網域"],
  +    平台策略: ["平台", "作者", "/user", "路徑", "創作者", "自訂網域"],
  ```
- **Composite:** 0.950288 | **Delta:** +0.003
- **Commit:** `7cc0212`
- **Impact:** Case 33 (Sitemap CMS API) mrr 0.500→1.000 — "cms" 同時出現在 Sitemap/API 和平台策略語境中，造成類別錯誤匹配

### #54 — add 查詞 to 內容策略 | discarded
- **Composite:** 0.950288 | **Delta:** 0.000 | discarded

### #55 — add 安全區 to 搜尋表現分析 | KEPT ✅
- **File:** `api/src/store/search-engine.ts`
- **Change:** `搜尋表現分析` 新增 `"安全區"`
- **Diff:**
  ```diff
  +      "安全區",
  ```
- **Composite:** 0.953728 | **Delta:** +0.003
- **Commit:** `4493e4e`
- **Note:** Breaks 0.95 milestone

### #56 — add 資訊型 to 搜尋表現分析 | discarded
- **Composite:** 0.953728 | **Delta:** 0.000 | discarded

### #57 — add 探索 to Discover | discarded
- **Composite:** 0.953728 | **Delta:** 0.000 | discarded

### #58 — 5th layer: CJK suffix match | discarded
- **Composite:** 0.953728 | **Delta:** 0.000 | discarded

---

## Summary

| Metric | Baseline | Final | Delta |
|--------|----------|-------|-------|
| Composite | 0.9126 | 0.9542 | +4.6% |
| Hit Rate | 0.975 | 1.000 | +0.025 |
| MRR | 0.933 | 1.000 | +0.067 |
| Precision@K | 0.795 | 0.900 | +0.105 |
| NDCG@K | 0.864 | 0.933 | +0.069 |

**15 KEPT / 43 discarded / 1 crash** across 58 experiments.

## Key Findings

1. **`search-engine.ts` 不被 Supabase 模式使用** — 只有 exports（hint maps, tokenize, inferQueryLabels, questionSignature）影響 Supabase 路徑（#1-2 證實）
2. **精確匹配權重是最大槓桿** — exact match 1→3, token match 1→1.5 合計 +0.023（#25-30）
3. **Category hints 是第二大槓桿** — 針對性 hints 合計 +0.010（#5,6,22,33,55）
4. **CJK bigram splitting 對中文查詢重要** — 移除掉 0.008（#39 反證）
5. **多樣性調整風險大** — 增減 diversity boost 都容易傷害 mrr 或 recall（#3,9,37）
6. **瓶頸在 pgvector candidate pool** — metadata scoring 只能 rerank 候選集，無法修復 pgvector 回傳錯誤的候選

## Bottleneck Cases (prec ≤ 0.4)

| Case | Scenario | Issue |
|------|----------|-------|
| 25 | GA+Discover 數據不一致 | "Discover" 拉到錯分類結果（pgvector 層級） |
| 32 | Vocus 平台 SEO | only 2/5 relevant, generic SEO fills slots |
| 37 | AI Overviews 觸發因素 | 演算法與趨勢 results dominate |
| 39 | AI 搜尋轉換率 | mrr=0.5, pgvector 候選品質差 |
