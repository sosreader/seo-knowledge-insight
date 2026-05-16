# Indexing Health — Coverage 與已檢索未索引研究

> 本檔歸納 vocus.cc 站索引健康度的判讀框架、根因分析、修復路徑。
> 觸發本檔建立的事件：2026-05-08 已檢索未索引 95.3 萬筆 + 未索引/有效比 0.7944 逼近警戒線 0.80。

---

## 1. 三條核心判讀指標

| 指標 | 定義 | 健康區間 | 危險區間 | 紅線 |
|------|------|----------|----------|------|
| 已檢索但未索引（Crawled, currently not indexed）| Googlebot 已抓取但未納入索引 | < Coverage × 0.30 | > Coverage × 0.65 | > 100 萬絕對量 |
| Coverage（有效頁面） | Google 已索引的頁面數 | 月變動 ±5% 內 | 月跌 > 15% | 月跌 > 25% |
| 未索引 / 有效比 | 上述兩者比值 | < 0.30 | > 0.65 | **0.80** |

**vocus.cc 2026-05-08 現況**：未索引 95.3 萬 / Coverage 120.0 萬 / 比值 **0.7944**（距紅線 0.0056）。

## 2. KB 13/14：「正向排除」vs「結構性收縮」辨識指南

引用 KB [`81c32da0e940147b`](../output/qa_final.json)（SEO 會議 20260223）+ KB [`163263b13edaaabb`]（20260309）：

> 有效頁面數下降本身**不代表**索引惡化，需搭配「流量頁面數」（GSC 指標 112）同步觀察。

### 辨識規則

| Coverage 走向 | 流量頁面/有效 比率 | 流量頁面絕對量 | 判讀 | 行動 |
|--------------|-------------------|----------------|------|------|
| ↓ | ↑ | 持平 | **正向排除**（低品質頁被 Google 主動排除） | 觀察，不急著反應 |
| ↓ | ↑ | ↓ | 結構性收縮第一階段 | 對比相同頁型 4 週走勢 |
| ↓ | ↓ | ↓ | **結構性收縮第二階段** | 啟動 Plan B 緊急應對 |

**vocus.cc 5/8 現況**：Coverage M -29.46%、流量頁面/有效 W +10.54%（41.30%）、流量頁面絕對量**未驗證**——目前判讀為「**待 5/15 確認**」狀態。

## 3. KB 22：「已檢索未索引」5 大根因族群

引用 KB [`b82545d945ee0f56`](../output/qa_final.json)（SC 內部指標討論 20260920）+ 業界 2026 共識（[aivisibility.systeme.io](https://aivisibility.systeme.io/google-indexing-survival-guide-2026) / [speedindex.pro](https://speedindex.pro/blog/crawled-currently-not-indexed-the-complete-fix-guide)）：

| 根因 | 預估占比（vocus.cc）| 主要影響頁型 | 修復槓桿 |
|------|---------------------|--------------|----------|
| A. 連結密度不足 | ~40% | /tag、/user、舊 /article | 模板加「同 tag/作者推薦」區塊 |
| B. 內容稀薄 | ~30% | /salon 廣告頁、空 /tag、佔位 /user | noindex（KB 13 正向排除）或重寫 |
| C. Canonical 衝突 | ~20% | /article 帶參數、/post AMP | KB 10：canonical hint + 內鏈一致 |
| D. AMP 配對缺失 | ~10% | /article ↔ /post | KB 16：補 `<link rel="amphtml">` |
| E. robots.txt 誤擋 | < 5% | 自定義網址段 | KB 17：移除過寬 Disallow |

> 詳細修復路徑：[`plans/active/crawled-not-indexed-fix-20260508.md`](../plans/active/crawled-not-indexed-fix-20260508.md)

## 4. KB 15：減半未索引的流量增益預期

引用 KB [`80e67d0329557d54`](../output/qa_final.json)（SEO 會議 20230320）：

> 若能將目前「已檢索但未索引」的頁面數量降低一半，流量有機會進一步成長。

**機械式試算**（修復 50% 假設 60% 表現）：

| 修復比例 | 釋放未索引數 | 預期月新增曝光 | 預期月新增點擊 |
|---------|-------------|---------------|----------------|
| 30% | 28.6 萬 | ~6.5M | ~17 萬 |
| 50% | 47.6 萬 | ~10.97M | ~28.3 萬 |
| 70% | 66.7 萬 | ~15.4M | ~39.6 萬 |

> 本估算公式詳見 [`~/Documents/knowledge-base/reports/seo-crawled-not-indexed-deepdive-20260508.md`](file:///Users/shiun/Documents/knowledge-base/reports/seo-crawled-not-indexed-deepdive-20260508.md) 第 8 章。

## 5. 6 週軌跡（線性 → 指數式轉折）

| 日期 | 已檢索未索引 | 未索引/有效比 | 模式 |
|------|-------------|---------------|------|
| 2026-03-22 | 39.4 萬 | 0.2767 | 線性 |
| 2026-04-13 | 50.2 萬 | 0.3215 | 線性 |
| 2026-04-20 | 52.8 萬 | 0.3478 | 線性 |
| **2026-04-27** | **59.6 萬** | **0.3754** | **轉折點** |
| 2026-05-01 | 80.4 萬 | 0.5943 | 指數式 |
| 2026-05-08 | 95.3 萬 | 0.7944 | 指數式 |

**6 週累積 +141.6%**——4/27 後從線性轉為指數式升溫，意味本站正在被 Google 大規模批次重新評估。

## 6. vocus.cc 站特殊性放大因子

1. **UGC 平台內容離散度大**：作者層級內容深度不一，broad coverage 觸發 Discover Feb 2026 niche reclassification
2. **雙網址表達**：`/article/<id>` vs `/@user/<slug>` 增加 canonical 衝突機率
3. **/salon/ 子網域**：對 Googlebot 顯示登入提示，部分頁無法被正確 render
4. **Tag 自動匯集**：產生 near-duplicate 頁面，KB 11 重覆網頁三類典型 case

## 7. 5/15 Plan A vs Plan B 切換條件

本期建立的條件觸發決策框架（見 [`plans/active/crawled-not-indexed-fix-20260508.md`](../plans/active/crawled-not-indexed-fix-20260508.md) 第五章 + 本檔附件）：

| # | 條件 | 5/8 現況 | 5/15 達標門檻 |
|---|------|---------|--------------|
| 1 | Discover 月跌幅 | -55.32% | ≤ -30% |
| 2 | 已檢索未索引絕對量 | 95.3 萬 | < 100 萬（守住紅線） |
| 3 | Coverage 月跌幅 | -29.46% | 止跌 |
| 4 | Organic Search 月跌幅 | -43.50% | ≤ -30% |

**規則**：≥ 2 項未達 → 啟動 Plan B（推薦主軸 α：本檔第 3 章 5 大根因修復 + Information Gain 內容深度化）。

## 8. 業界 2026 共識

- **#1 cause = quality gaps + information gain**（aivisibility.systeme.io / speedindex.pro / searchengineland.com）
- 健康站點索引率基準 **85–95%**（vocus.cc 約 51%）
- 未索引/有效比 **> 0.80** 屬危險區
- 月增幅可承受 **< 15%**（vocus.cc +73.41% M 超出 4.9 倍）

## 9. 相關文件

- 本期執行 plan：[`plans/active/crawled-not-indexed-fix-20260508.md`](../plans/active/crawled-not-indexed-fix-20260508.md)
- 深度根因分析：`~/Documents/knowledge-base/reports/seo-crawled-not-indexed-deepdive-20260508.md`
- 5/8 週報：`output/report_20260508_c734a2de.md`（local）+ Supabase
- 5/8 meeting-prep：`output/meeting_prep_20260508_0fd5f190.md`（local）+ Supabase
- 既有觀測 plan：`plans/active/crawled-not-indexed-observability.md`
- 業界動態快照：[`research/11-seo-industry-updates.md`](./11-seo-industry-updates.md) 5/8 段落
