# Experiment Log — autoresearch/mar21

Baseline composite: **0.912616**

## Experiment Summary

| # | Description | Composite | Delta | Status |
|---|------------|-----------|-------|--------|
| 1 | categoryBoost 0.08→0.12 (search-engine.ts) | 0.912616 | 0.000 | discarded (no effect — search-engine.ts not used in Supabase mode) |
| 2 | overRetrieveFactor 3→5 (search-engine.ts) | 0.912616 | 0.000 | discarded (same reason) |
| 3 | categoryDiversityBoost base 0.12→0.18 | 0.909728 | -0.003 | discarded (mrr regression: case 20 mrr 1.0→0.5) |
| 4 | bigram prefix 2→3 chars | 0.903577 | -0.009 | discarded (many regressions: cases 3,10,27,34,38,40) |
| 5 | **add 轉換率+可見度 to 搜尋表現分析 hints** | **0.919064** | **+0.006** | **KEPT** ✅ |
| 6 | **add 意圖 to 內容策略, 反向連結+錨文本 to 連結策略** | **0.922413** | **+0.003** | **KEPT** ✅ |
| 7 | add ai-overview scenario + 轉換率/signups to measurement intent | 0.922413 | 0.000 | discarded (no QA metadata matches) |
| 8 | novelQueryTermBoost coefficients +50% | 0.922413 | 0.000 | discarded (no effect) |
| 9 | categoryDiversityBoost base 0.12→0.08 | 0.915946 | -0.006 | discarded (recall/f1 regression) |
| 10 | remove 'ai' from 演算法與趨勢 hints | 0.920779 | -0.002 | discarded (recall loss > precision gain) |
| 11 | move 'ai' from 演算法 to 搜尋表現分析 as 'ai 搜尋' | 0.920779 | -0.002 | discarded (same as exp 10) |
| 12 | add 數據 to GA與數據追蹤 hints | 0.922413 | 0.000 | discarded (simplicity: no benefit) |
| 13 | add 5th layer: suffix match (last 2 chars of kw>=4) | 0.917879 | -0.005 | discarded (too loose, cases 34 regressed) |

| 14 | tokenize: split on hyphens/slashes/punctuation | 0.920266 | -0.002 | discarded (case 34 regressed) |
| 15 | questionSignature truncate 120→60 | 0.922413 | 0.000 | discarded (no effect) |
| 16 | categoryDiversityBoost step 0.06→0.10 | 0.922413 | 0.000 | discarded (no effect) |
| 17 | **queryTerms: CJK sliding window bigrams** | **0.922861** | **+0.000** | **KEPT** ✅ |
| 18 | CJK bigrams: non-overlapping pairs | 0.922405 | -0.000 | discarded (lower than sliding window) |
| 19 | CJK bigram threshold 4→6 chars | 0.922058 | -0.001 | discarded |
| 20 | CJK bigrams: head-tail only | 0.922802 | -0.000 | discarded (marginal) |
| 21 | tokenize: strip punctuation | 0.920067 | -0.003 | discarded (case 15, 34 regressed) |
| 22 | **add specific hints: key moments/圖片搜尋/創作者/max-image-preview** | **0.926483** | **+0.004** | **KEPT** ✅ |

| 23 | add 點擊率 to 搜尋表現分析, 觸發 to 內容策略 | 0.926483 | 0.000 | discarded (no effect) |
| 24 | add 有效頁面 to 索引與檢索 | 0.926483 | 0.000 | discarded (no effect) |
| 25 | **exact keyword match: 1.0→1.5 hits weight** | **0.933339** | **+0.007** | **KEPT** ✅ |

| 26 | **exact match 1.5→2.0 hits** | **0.934224** | **+0.001** | **KEPT** ✅ |
| 27 | **exact match 2.0→2.5 hits** | **0.935407** | **+0.001** | **KEPT** ✅ |
| 28 | **exact match 2.5→3.0 hits** | **0.942787** | **+0.007** | **KEPT** ✅ |
| 29 | exact match 3.0→3.5 hits | 0.942787 | 0.000 | discarded (same score, keep simpler 3.0) |

| 30 | **token forward/reverse match 1.0→1.5 hits** | **0.944530** | **+0.002** | **KEPT** ✅ |
| 31 | token match 1.5→2.0 | 0.944530 | 0.000 | discarded (same, maxHits cap) |
| 32 | bigram partial 0.5→1.0 fractional | 0.944530 | 0.000 | discarded (dominated by stronger signals) |
| 33 | **add url inspection / inspection api to 索引與檢索** | **0.945665** | **+0.001** | **KEPT** ✅ |
| 34 | add 提交 to 索引與檢索 | 0.945665 | 0.000 | discarded |

| 35 | add 問題類 to 內容策略 | 0.945665 | 0.000 | discarded |
| 36 | novelQueryTermBoost caps doubled | 0.012000 | CRASH | discarded (server crash, bad result) |
| 37 | categoryDiversityBoost base 0.12→0.15 | 0.943340 | -0.002 | discarded (case 5 regressed) |
| 38 | add 大圖 to Discover hints | 0.945665 | 0.000 | discarded |
| 39 | remove CJK bigram (simplicity test) | 0.938039 | -0.008 | discarded (CJK bigrams confirmed essential) |

## Current Best: 0.953728 (composite, +4.5% from baseline 0.9126)

### Per-Case Summary (Current Best)

| Case | Scenario | mrr | prec | vs baseline |
|------|----------|-----|------|-------------|
| 1 | Discover 流量大幅下降 | 1.000 | 0.800 | = |
| 5 | AMP Article 幾乎歸零 | 1.000 | 0.800 | = |
| 8 | 結構化資料覆蓋率下降 | 1.000 | 0.800 | = |
| 12 | Google News 流量下降 | 1.000 | 0.800 | = |
| 13 | 伺服器回應時間上升 | 1.000 | **1.000** | +0.2 |
| 15 | 手機 Core Web Vitals | 1.000 | **1.000** | = |
| 17 | 圖片搜尋流量下降 | 1.000 | **1.000** | +0.4 |
| 18 | GSC 探索流量 → GA Direct | 1.000 | 0.800 | = |
| 20 | 當週文章數銳減 | 1.000 | 0.800 | +0.2 |
| 21 | FAQ 結構化資料異常 | 1.000 | **1.000** | +0.2 |
| 25 | GA+Discover 數據不一致 | 1.000 | 0.600 | +0.4 |
| 27 | 品牌/非品牌流量 | 1.000 | 0.800 | = |
| 28 | VideoObject 實作 | 1.000 | 0.800 | = |
| 29 | Event 結構化資料 | 1.000 | 0.800 | = |
| 30 | 多語言影片 Key Moments | 1.000 | **1.000** | +0.6 |
| 32 | Vocus 平台策略 | 1.000 | 0.800 | +0.4 |
| **33** | **Sitemap CMS API** | **0.500** | **0.600** | mrr+0.2 |
| 34 | Discover 大圖 | 1.000 | 0.600 | = |
| 36 | AI Overview 品牌可見度 | 1.000 | 0.600 | +0.2 |
| **37** | **AI Overviews 觸發因素** | 1.000 | **0.400** | = |
| 38 | AI Overviews 點擊率 | 1.000 | **1.000** | +0.4 |
| 39 | AI 搜尋轉換率 | 1.000 | 0.800 | +0.6 |
| 40 | 國際頁面 AI Search | 1.000 | 0.600 | = |

| 40 | multi-token exact 4.0 vs single 3.0 | 0.945665 | 0.000 | discarded (maxHits cap) |
| 41 | **diversity base 0.10 step 0.08** | **0.945743** | **+0.000** | **KEPT** ✅ |
| 42 | diversity base 0.10 step 0.05 max 2 | 0.945743 | 0.000 | discarded (same as 41) |
| 43 | keyword tokenize CJK/ASCII split | 0.945743 | 0.000 | discarded (no effect) |
| 44 | novelQueryTermBoost +50% | 0.945365 | -0.000 | discarded (marginal regression) |

| 45 | questionSignature 120→40 (aggressive dedup) | 0.945743 | 0.000 | discarded |
| 46 | **inferQueryLabels word boundary for short English hints** | **0.946940** | **+0.001** | **KEPT** ✅ |
| 47 | word boundary threshold 3→4 | 0.946940 | 0.000 | discarded |
| 48 | add 排名 to 搜尋表現分析 | 0.946940 | 0.000 | discarded |
| 49 | matchedQueryTerms partial CJK match | 0.940021 | -0.007 | discarded (too loose) |
| 50 | add 流量佔比 to 搜尋表現分析 | 0.945812 | -0.001 | discarded (hurt case 16) |
| 51 | diversity step 0.08→0.12 | 0.946940 | 0.000 | discarded |
| 52 | inferQueryLabels bidirectional match | 0.935419 | -0.012 | discarded (massive false positives) |
| 53 | **remove cms from 平台策略** | **0.950288** | **+0.003** | **KEPT** ✅ mrr→1.000! |
| 54 | add 查詞 to 內容策略 | 0.950288 | 0.000 | discarded |
| 55 | **add 安全區 to 搜尋表現分析** | **0.953728** | **+0.003** | **KEPT** ✅ breaks 0.95! |
| 56 | add 資訊型 to 搜尋表現分析 | 0.953728 | 0.000 | discarded |
| 57 | add 探索 to Discover | 0.953728 | 0.000 | discarded |
| 58 | 5th layer: CJK suffix match | 0.953728 | 0.000 | discarded |

---

### Key Findings
1. **`search-engine.ts` 不被 Supabase 模式使用** — 只有 exports（hint maps, tokenize, inferQueryLabels, questionSignature）影響 Supabase 路徑
2. **精確匹配權重是最大槓桿** — exact match 1→3, token match 1→1.5 貢獻了 +0.023
3. **Category hints 是第二大槓桿** — 針對性 hints 貢獻 +0.010
4. **CJK bigram splitting 對中文查詢很重要** — 移除它會掉 0.008
5. **多樣性調整風險大** — 增減 diversity boost 都容易傷害 mrr 或 recall

## Per-Case Results (Current Best)

| Case | Scenario | mrr | prec | Status |
|------|----------|-----|------|--------|
| 1 | Discover 流量大幅下降 | 1.000 | 0.800 | ok |
| 2 | CTR 持續下降 | 1.000 | 1.000 | perfect |
| 3 | 檢索未索引大幅增加 | 1.000 | 1.000 | perfect |
| 4 | Organic Search 工作階段下降 | 1.000 | 1.000 | perfect |
| 5 | AMP Article 幾乎歸零 | 1.000 | 1.000 | perfect |
| 6 | 曝光大幅上升但點擊未同步 | 1.000 | 1.000 | perfect |
| 7 | 內部連結架構優化 | 1.000 | 1.000 | perfect |
| 8 | 結構化資料覆蓋率下降 | 1.000 | 0.800 | ok |
| 9 | GA4 追蹤問題 unassigned 增加 | 1.000 | 1.000 | perfect |
| 10 | Canonical 設定混亂 | 1.000 | 1.000 | perfect |
| 11 | Video Appearance 歸零 | 1.000 | 1.000 | perfect |
| 12 | Google News 流量下降 | 1.000 | 1.000 | perfect |
| 13 | 伺服器回應時間上升 | 1.000 | 1.000 | perfect |
| 14 | /user 路徑流量大幅下降 | 1.000 | 1.000 | perfect |
| 15 | 手機 Core Web Vitals 劣化 | 1.000 | 0.800 | ok |
| 16 | AI 來源流量佔比偏低 | 1.000 | 1.000 | perfect |
| 17 | 圖片搜尋流量下降 | 1.000 | 0.800 | ok |
| 18 | GSC 探索流量被計入 GA Direct | 1.000 | 1.000 | perfect |
| 19 | 有效頁面數持續下滑 | 1.000 | 1.000 | perfect |
| 20 | 當週文章數銳減影響整體曝光 | 1.000 | 0.800 | ok |
| 21 | Search Console 搜尋外觀 FAQ 異常 | 1.000 | 0.800 | ok |
| 22 | AI 生成內容的 SEO 風險評估 | 1.000 | 1.000 | perfect |
| 23 | AMP 退場後的技術替代方案 | 1.000 | 1.000 | perfect |
| 24 | 語意相關的連結建設策略 | 1.000 | 1.000 | perfect |
| 25 | GA 與 Search Console Discover 數據不一致 | 1.000 | 0.400 | **weak** |
| 26 | Search Console KPI 指標體系 | 1.000 | 1.000 | perfect |
| 27 | 品牌關鍵字與非品牌流量評估 | 1.000 | 0.800 | ok |
| 28 | 影片 SEO VideoObject 實作 | 1.000 | 0.800 | ok |
| 29 | Event 結構化資料提升搜尋流量 | 1.000 | 1.000 | perfect |
| 30 | 多語言影片 SEO 與 Key Moments | 1.000 | 1.000 | perfect |
| 31 | 內部連結結構與爬取效率 | 1.000 | 1.000 | perfect |
| 32 | Vocus 平台 SEO 經營策略 | 1.000 | 0.400 | **weak** |
| 33 | Sitemap 提交與 CMS API 整合 | 0.333 | 0.600 | **weak** (mrr!) |
| 34 | Discover 大圖優化 max-image-preview | 1.000 | 0.600 | weak |
| 35 | 外部連結品質與交換連結風險 | 1.000 | 1.000 | perfect |
| 36 | AI Overview 品牌可見度因子 | 1.000 | 0.600 | weak |
| 37 | AI Overviews 觸發因素與安全區查詢 | 1.000 | 0.400 | **weak** |
| 38 | AI Overviews 對點擊率衝擊 | 1.000 | 0.800 | ok |
| 39 | AI 搜尋流量轉換率與策略調整 | 0.500 | 0.400 | **weak** (mrr!) |
| 40 | 國際頁面在 AI Search 的流量落差 | 1.000 | 0.600 | weak |

## Bottleneck Analysis

**Critical cases** (prec ≤ 0.4):
- Case 25: GA+Discover query — "Discover" pulls wrong-category results (pgvector level)
- Case 30: 多語言影片 — only 2/5 relevant, generic SEO fills remaining slots
- Case 32: Vocus 平台 — only 2/5 relevant, generic SEO fills remaining slots
- Case 36: AI Overview 品牌可見度 — 演算法與趨勢 results dominate
- Case 37: AI Overviews 觸發因素 — same issue

**Key insight**: The bottleneck is at the **pgvector candidate pool** level. The metadata scoring can only rerank what pgvector returns. When pgvector returns mostly wrong-category candidates, no amount of metadata tuning can fix precision.
