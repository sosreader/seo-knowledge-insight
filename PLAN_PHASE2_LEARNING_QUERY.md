# Phase 2：Learning Store 深化 + Query Understanding 計畫

**狀態：待執行（前置條件未滿足）**
**前置計畫：** `PLAN_VERSION_REGISTRY_MULTILAYER.md`（已完成）

---

## 延遲原因

以下功能因時序或驗證門檻問題，在 Phase 1 刻意推遲。

---

## 待執行項目

### E2-1：`utils/usage_aggregator.py`

**前置條件：** 需積累 2 週含 `top_score` 欄位的新格式 access log

**背景：** `utils/audit_logger.py` 在 2026-03-02（Phase B B0）已加入 `top_score` 欄位。
新格式記錄從今天開始產生，14 天後（約 2026-03-16）可執行。

**功能：**
- 聚合 `access_logs/*.jsonl` 中含 `top_score` 的記錄
- 統計每筆 Q&A 的 `search_hit_count`（含分數加權）
- 輸出供 `scripts/enrich_qa.py` 使用的 usage stats JSON

**執行時機：** 2026-03-16 後，執行 `make enrich` 時自動引入

---

### E2-2：Query Understanding 層

**前置條件：** `evals/eval_enrichment.py` 顯示 KW Hit Rate ≥ 85%

**背景：** 目前 synonym + freshness 效果需先透過 Laminar eval 確認才值得增加複雜度。
若 KW Hit Rate 仍低，優先改善 synonym_dict 覆蓋率。

**功能：**
- Query intent classification（查詢意圖分類：索引問題 / 搜尋表現 / 技術 SEO...）
- Query rewriting（非 LLM，規則式：簡寫展開 → 標準術語）
- Multi-hop retrieval（複合問題拆解 → 多次搜尋再合併）

**依賴：** `utils/synonym_dict.py` 的 `expand_keywords()` 已就緒

---

### E2-3：`qa_tools.py analyze-access` 子命令

**前置條件：** `utils/usage_aggregator.py` 完成（E2-1）

**功能：**
- 顯示 Top 20 最常被搜尋的 Q&A
- 顯示 Top 20 搜尋失敗查詢（無 hit / top_score < 0.35）
- 識別知識庫涵蓋缺口

```bash
python scripts/qa_tools.py analyze-access [--days 14] [--show-misses]
```

---

### E2-4：`qa_tools.py annotate-category` 子命令

**前置條件：** 可獨立執行，但建議先確認 Category 分類準確率問題的根因

**背景：** 目前 Category 正確率 68%（評估基準線）。先確認是評估邏輯問題還是分類品質問題，
再決定是否需要 Human Annotation 回饋路徑。

**功能：**
- 互動式逐筆確認/修正 category
- 寫入 `_category_annotation` 欄位（不覆蓋原始 category）
- 支援 --dry-run 模式

---

### E2-5：Source Snippet Index

**前置條件：** `scripts/enrich_qa.py` Phase 2 加入（Phase 1 只做 synonym + freshness）

**功能：**
- 為每筆 Q&A 預計算 `source_snippet`：來源會議記錄的關鍵段落（前 200 字）
- 作為 RAG context 的補充（目前只有 Q&A 本身）
- 改善回答的具體性（可引用原始會議討論）

---

### E2-6：向量資料庫引入評估

**前置條件：** 知識庫規模超過 10,000 筆 Q&A

**背景：** 目前 655 筆 numpy in-memory search < 1ms，不需要向量資料庫。
此條目作為規模監測觸發點。

**評估門檻：**
- > 10,000 筆 Q&A：評估 Qdrant / Chroma 引入成本
- > 50,000 筆 Q&A：強烈建議引入

---

## 執行順序建議

```
2026-03-16（+14 天）
  → 執行 make enrich（包含 usage_aggregator.py 整合）
  → 執行 evals/eval_enrichment.py 確認 KW Hit Rate ≥ 85%

確認 ≥ 85% 後：
  → E2-3（analyze-access）：理解知識庫使用模式
  → E2-2（Query Understanding）：若仍有長尾失敗

優先順序較低（待評估後決定）：
  → E2-4（annotate-category）
  → E2-5（Source Snippet Index）
  → E2-6（向量資料庫）
```

---

## 成功指標

| 指標 | Phase 1 當前 | Phase 2 目標 |
|------|-------------|-------------|
| KW Hit Rate | **79.67%**（make enrich 後，+9.27pp）| ≥ 85%（差 5.33pp）|
| MRR | 0.75 | ≥ 0.80 |
| Search Miss Rate | 建立 baseline | < 15% |
| Category 正確率 | 68% | ≥ 75% |
