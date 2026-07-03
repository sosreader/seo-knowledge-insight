# Plans Index

## Active（進行中）— 2 個計畫

| 計畫 | 優先級 | 摘要 |
|------|--------|------|
| [seo-knowledge-insight-iteration-roadmap-2026h2](active/seo-knowledge-insight-iteration-roadmap-2026h2.md) | P1 | H2 2026 產品迭代路線圖：eval 框架完善、meeting-prep 結構規範化、retrieval 多維對齊 |
| [crawled-not-indexed-fix-20260508](active/crawled-not-indexed-fix-20260508.md) | P2 | GSC 檢索未索引異常診斷與修復（2026-05-08 起追蹤） |

## Deprecated（已棄用，存檔參考）— 4 個計畫

> 2026-07-03 triage 判定以下計畫為已飽和或優先級下調，移入 deprecated/ 供未來參考。

| 計畫 | 棄用原因 | 摘要 |
|------|---------|------|
| [multi-domain-analysis](deprecated/multi-domain-analysis.md) | 4 個月未動；純架構分析未實作，泛化他領域非現行主線 | 系統從 SEO 擴增到多領域的架構分析（擱置） |
| [cache-redis](deprecated/cache-redis.md) | 4 個月未動；本文自述「目前不需要 Redis」，保留作升級觸發條件設計參考 | Redis/Valkey 升級觸發條件與模式分析 |
| [phase2-learning-query](deprecated/phase2-learning-query.md) | 4 個月未動；前置時間閘從未執行，依賴元件（usage_aggregator 等）不存在 | Learning Store 深化 + Query Understanding |
| [multi-layer-context](deprecated/multi-layer-context.md) | 4 個月未動；僅 L3 learning_store 落地，RAG 線依 roadmap S2.4 暫緩 | 多層知識庫架構改進（Phase 2 待做） |

## Completed（已完成）— 32 個計畫

| 計畫 | 摘要 |
|------|------|
| [retrieval-quality-data-dimensions](completed/retrieval-quality-data-dimensions.md) | 提升 retrieval 評分、top-k purity 與 QA 多維 metadata |
| [mvp](completed/mvp.md) | FastAPI in-memory MVP |
| [api-security](completed/api-security.md) | API 認證 + 限流 + 安全 envelope |
| [pipeline-memory](completed/pipeline-memory.md) | Content-addressed cache + version registry |
| [eval-fix](completed/eval-fix.md) | 評估 BUG-001/002 修復 |
| [version-registry-multilayer](completed/version-registry-multilayer.md) | Version Registry 增強 + Multi-Layer Phase 1 |
| *（其他 26 份已完成計畫）* | *（詳見 completed/ 目錄）* |

---

## Deprecated 目錄說明

`deprecated/` 目錄收集已審查但優先級下調的計畫，保留以供：
- 未來條件改善時重新啟動
- 架構決策參考
- 相關計畫延伸時查閱

本次整理（2026-07-03）將 19 個 active/in-progress 計畫（active 17 + in-progress 2）精簡至 2 個核心 active，其餘根據成熟度狀態分類到 completed（32 個）或 deprecated（4 個）。
