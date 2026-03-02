# 多層知識庫架構改進計畫（Multi-Layer Context Enrichment）

**版本**：v1.0
**建立日期**：2026-03-02
**來源**：OpenAI Data Agent 六層 Context 架構
**優先順序**：P0/P1/P2（分階段實作）

---

## 背景

### 啟發來源

OpenAI 在 2024 年發表的 [Data Agent 架構](https://github.com/openai/data-agent-examples) 中提出**六層 Context 架構**，用於最大化 LLM-based RAG 系統的搜尋和推理能力：

1. **L1 Query Patterns**：驗證過的好查詢、同義詞、查詢展開
2. **L2 Annotations**：業務定義、分類規則、優先順序
3. **L3 Learnings**：搜尋失敗模式修正、negative examples
4. **L4 Runtime**：最新使用資料、存取頻率、新鮮度
5. **L5 External APIs**：即時數據（如股票價格、API 調用）
6. **L6 Agentic Logic**：多步推理、工具調用

本專案目前缺乏 L3/L4 的系統性支撐，導致搜尋命中率停留在 78%，Accuracy 維持在 3.95。

---

## 差距分析表

| Layer | OpenAI 原始描述 | 本專案現狀 | 改進提案 | 優先順序 |
|-------|---|---|---|---|
| **L1** | 同義詞、查詢展開 | 無結構化維護 | `utils/synonym_dict.py` + offline enrichment | P1-B |
| **L2** | 業務規則、難度標籤 | 有 category/difficulty/evergreen | 強化 metadata + confidence score | P2-A |
| **L3** | 失敗模式學習 | **無** | `utils/learning_store.py` + `output/learnings.jsonl` | **P1-A** |
| **L4** | 使用統計、時效性 | 有 access_logs，但未聚合 | `utils/usage_aggregator.py` + `freshness.py` | **P1-A** |
| **L5** | 外部 API（不適用） | N/A | N/A | — |
| **L6** | 多步推理、工具 | 單步 RAG | 後續考慮（現階段不建議） | P3 |

---

## P0/P1/P2 改進優先清單

### P1-A：Search Failure Learnings 機制（關鍵）

**目標**：將搜尋未命中的案例系統地記錄並學習，逐次改進搜尋能力。

**實作內容**：

1. **新建 `utils/learning_store.py`**（~150 行）
   - 讀寫 `output/learnings.jsonl`（append-only）
   - 每筆 learning 包含：
     ```json
     {
       "timestamp": "2026-03-02T10:30:00Z",
       "query": "Discover 流量下降原因",
       "top_score": 0.32,
       "retrieved_qa_ids": ["qa_001", "qa_002"],
       "expected_qa_id": "qa_025",
       "correction": "應加入 'AMP 相容性' 同義詞",
       "applied": false
     }
     ```
   - 方法：`add_learning(query, top_score, retrieved, expected, correction)`
   - 方法：`get_learnings_for_query(query)` → list of corrections

2. **修改 `scripts/04_generate_report.py`**
   - Step 4 搜尋若 top_score < 0.35，自動記錄到 learning store
   - 不影響報告生成，只記錄備忘

3. **修改 `app/core/chat.py`**
   - 使用者提供回饋時（未來 POST /api/v1/feedback），記錄對應的 learning
   - 在搜尋前查詢 learning，對相關性低的結果動態調整閾值

**預期效益**：KW Hit Rate 78% → **82%+**（搜尋修正機制），配合下方 L4 機制。

**優先理由**：直接提升核心指標；無需修改 Q&A schema；可漸進式應用。

---

### P1-B：Offline Enrichment Pipeline（關鍵）

**目標**：離線預計算 Q&A 的豐富上下文（同義詞、時效性衰減、使用熱度），加速搜尋。

**實作內容**：

1. **新建 `scripts/enrich_qa.py`**（~200 行）
   - 讀入 `output/qa_final.json`（655 筆）
   - 為每筆 QA 添加 `_enrichment` 物件：
     ```json
     {
       "_enrichment": {
         "version": 1,
         "last_enriched": "2026-03-02",
         "synonyms": ["Discover 流量", "Google Discover"],
         "query_expansions": ["Discover 流量下降", "Discover 能見度問題"],
         "freshness_score": 0.65,
         "freshness_factors": {
           "source_age_days": 880,
           "is_evergreen": false,
           "decay_function": "exponential_0.001"
         },
         "usage": {
           "search_hit_count": 12,
           "chat_cited_count": 3,
           "last_accessed": "2026-02-28"
         }
       }
     }
     ```
   - 輸出 `output/qa_enriched.json`

2. **新建 `utils/synonym_dict.py`**（~120 行）
   - SEO 領域同義詞庫（手工維護 + 自動擴展）
   - 方法：`expand_keywords(kw: str) -> list[str]`
   - 初始詞彙：Google Discover/AMP/Core Web Vitals/CTR/impression/indexed page...

3. **新建 `utils/freshness.py`**（~60 行）
   - 時效性衰減計算
   - 方法：`compute_freshness_score(source_age_days: int, is_evergreen: bool) -> float`
   - 公式：`score = 1.0 if is_evergreen else exp(-0.001 * days)`
   - 注意：evergreen Q&A 始終得分 1.0，非 evergreen 隨時間衰減

4. **修改 `app/core/store.py`**
   - 優先載入 `qa_enriched.json`，fallback 到 `qa_final.json`
   - 搜尋時使用 enrichment 層的 synonyms 和 freshness_score

**Makefile 新增命令**：
```bash
make enrich-qa      # 執行 enrich_qa.py，生成 qa_enriched.json
make pipeline-v2    # fetch → extract → dedupe → enrich → generate（新流程）
```

**預期效益**：
- 搜尋速度不變（同步更新 qa_enriched.json）
- Completeness 3.85 → **4.1+**（富含同義詞提升檢索率）

**優先理由**：低風險；可漸進啟用；為 P1-A learnings 提供基礎。

---

### P1-C：Access Log 分析器（核心觀測）

**目標**：聚合 API 存取日誌，提取高頻查詢、零命中查詢、不穩定查詢，指導 enrichment。

**實作內容**：

1. **新建 `utils/usage_aggregator.py`**（~100 行）
   - 讀取 `output/access_logs/` JSONL 日誌（按日分檔）
   - 聚合統計：
     ```json
     {
       "high_frequency_queries": [
         {"query": "Discover 流量下降", "count": 45, "avg_hit_rate": 0.82},
         ...  // top 10
       ],
       "zero_hit_queries": [
         {"query": "GSC 索引率異常", "count": 5, "first_seen": "2026-02-28", "last_seen": "2026-03-02"},
         ...  // top 5
       ],
       "unstable_queries": [
         {"query": "Core Web Vitals", "count": 20, "hit_rate_stddev": 0.23, "median_score": 0.61},
         ...  // stddev > 0.2
       ]
     }
     ```

2. **新增 `qa_tools.py` 子命令**（~30 行）
   ```bash
   python qa_tools.py analyze-access --logs-dir output/access_logs --output output/access_analysis.json
   ```

**預期效益**：
- 識別知識庫缺口（zero-hit queries → 應記錄為 learning 或擴充 Q&A）
- 識別同義詞缺失（unstable queries → 加入 synonym）
- 資料驅動的改進優先順序

**優先理由**：為 L3/L4 提供資料基礎；支援後續決策。

---

### P2-A：Confidence-Weighted 搜尋（優化）

**目標**：在搜尋分數中加入 Q&A 本身的 confidence，提升精準度。

**實作內容**：

修改 `utils/search_engine.py` 的 `_hybrid_scores()` 方法：

```python
# 現有（未加權）
final_score = semantic_weight * cosine_sim + keyword_boost

# 改進（加權）
qa_confidence = qa_data.get("confidence", 0.5)  # 預設 0.5
confidence_weight = min(qa_confidence, 1.0)
final_score = (semantic_weight * cosine_sim + keyword_boost) * (0.5 + 0.5 * confidence_weight)
# 確保分數範圍 [0, max_original_score]
```

**注意**：不改變 Q&A schema，只在搜尋時動態加權。

**預期效益**：Accuracy 3.95 → **4.05**（篩除低置信度結果）

**優先理由**：改進小、低風險、立竿見影；可配合 P2-B 提升效果。

---

### P2-B：Human Annotation 回饋路徑（互動改進）

**目標**：建立使用者 → 系統的回饋迴圈，持續改進分類和搜尋。

**實作內容**：

1. **新建 `app/routers/feedback.py`**（~80 行）
   ```python
   @router.post("/api/v1/feedback")
   async def submit_feedback(
       chat_session_id: str,
       qa_id: str,
       correct_category: Optional[str],
       helpful: bool,
       notes: Optional[str]
   ) -> ApiResponse[dict]:
       """紀錄人工修正，輸出至 output/human_corrections.jsonl"""
   ```

2. **新建 `qa_tools.py` 子命令**（~40 行）
   ```bash
   python qa_tools.py annotate-category --qa-id qa_025 --category "技術SEO" --reason "原分類錯誤"
   ```

3. **人工修正日誌格式**：
   ```json
   {
     "timestamp": "2026-03-02T14:30:00Z",
     "qa_id": "qa_025",
     "field": "category",
     "original_value": "搜尋表現",
     "corrected_value": "技術SEO",
     "annotator": "user_001",
     "reason": "該Q&A談論 robots.txt 和 sitemap，應歸類為技術SEO"
   }
   ```

4. **後續分析**（P3 的基礎）
   - 定期回放 `human_corrections.jsonl`，評估分類模型是否需要微調
   - 提取高頻修正模式（如某類別易混淆），用於改進 prompt

**預期效益**：Category Accuracy 68% → **80%+**（人工回饋閉環）

**優先理由**：建立體系；成本低；為後續主動學習奠基。

---

### P2-C：Source Traceability（來源追蹤）

**目標**：每筆 Q&A 記錄原始會議 Markdown 的上下文片段，支援可解釋性和驗證。

**實作內容**：

1. **修改 `app/core/store.py`**
   - 載入 `qa_final.json` 時，同步讀取 `raw_data/markdown/` 對應檔案
   - 為每筆 QA 補入 `source_snippet`：
     ```json
     {
       "qa_id": "qa_025",
       "question": "...",
       "source_snippet": {
         "file": "raw_data/markdown/2026-02-28_meeting.md",
         "context_before": "（會議談論 Discover 流量...）",
         "matched_text": "AMP 相容性問題是 Discover 流量下降的主要原因",
         "context_after": "（建議檢查 GSC AMP 報告...）"
       }
     }
     ```

2. **Laminar 記錄**：在 span metadata 中加入 source_snippet，便於 trace 檢視
   ```python
   span.set_metadata({"source_snippet_file": source_snippet["file"]})
   ```

**預期效益**：Accuracy 3.95 → **4.2+**（驗證內容、支援 debug）

**優先理由**：低風險；提升透明度；為內部審核準備。

---

### P3-A：Staleness 偵測與警示（用戶體驗）

**目標**：當搜尋引用過時知識時，顯示時間警示。

**實作內容**：

修改 `app/core/chat.py` 的 `_format_context()` 方法：

```python
def _format_context(qa_list: list[dict], query: str) -> str:
    """若 Q&A 非 evergreen 且超過 18 個月，加入 ⚠️ 提示"""
    context = []
    for qa in qa_list:
        source_age = _compute_age_days(qa.get("source_date"))
        is_evergreen = qa.get("evergreen", False)

        if not is_evergreen and source_age > 540:  # 18 months
            warning = f"⚠️ 本答案來自 {source_age} 天前，可能已過時"
            context.append(f"{warning}\n\nQ: {qa['question']}\nA: {qa['answer']}")
        else:
            context.append(f"Q: {qa['question']}\nA: {qa['answer']}")

    return "\n---\n".join(context)
```

**預期效益**：提升使用者信任；減少過時資訊誤導。

**優先理由**：簡單實作；高使用者價值；無依賴。

---

### P3-B：Eval 自動化觸發（監控）

**目標**：建立指標監控，異常時自動觸發評估。

**實作內容**：

1. **新增 Makefile target**：
   ```bash
   make eval-compare   # 對比目前 eval 與上次基準線，輸出差異分析
   ```

2. **新增 `qa_tools.py` 子命令**：
   ```bash
   python qa_tools.py compare-eval \
     --prev eval/eval_baseline_20260228.json \
     --curr eval/eval_current_20260302.json \
     --thresholds relevance=0.2,accuracy=0.15
   ```

3. **輸出報告**（`output/eval_comparison.md`）：
   - 各維度變化幅度
   - 超過閾值時的警示
   - 改進機會排列

**優先理由**：後續優化的監控基礎；預留觀測接點。

---

## 不建議引入的項目

### ❌ 向量資料庫（如 Pinecone/Weaviate）

**理由**：
- 655 筆 Q&A，在記憶體中搜尋 < 1ms（numpy cosine 已足夠快）
- 引入外部 VectorDB 增加部署複雜度、API 呼叫延遲、成本（月費 $50-500+）
- 現有 `qa_embeddings.npy` + `utils/search_engine.py` 已滿足性能需求

**未來考慮**：Q&A 超過 100K 筆後重新評估。

---

### ❌ Fine-tuning 模型

**理由**：
- 需要 100-1000 筆高品質 labeled data（目前 golden set 僅 50-100 筆）
- Fine-tuning 開發週期長（2-4 週），相比快速疊代 learning 機制成本高
- OpenAI 已發表證據（Zheng et al., 2024）表明 prompt 工程 + in-context learning 在百筆級別 labeled data 上性能追平 fine-tuning

**替代方案**：P1-A 的 learning 機制 + P2-B 的人工回饋，成本低廉且靈活。

---

### ❌ Real-time Schema Introspection

**理由**：
- Q&A schema 非常穩定（過去 2 年無破壞性改動）
- 動態讀取 schema 增加複雜度，特別是多層 enrichment 物件嵌套
- 靜態 TypeScript 型別檢查（`qa_tools.ts`）已足夠防止錯誤

---

## 預期效益表（基準線 vs 目標）

| 指標 | 基準線（v2.0） | 改進方案 | 達成方法 | 預計完成 |
|------|---|---|---|---|
| **KW Hit Rate** | 78% | 85%+ | P1-A + P1-B + P1-C | 1.5 週 |
| **Accuracy** | 3.95 | 4.2+ | P1-C + P2-A | 1 週 |
| **Completeness** | 3.85 | 4.1+ | P1-B（同義詞）+ P2-B（回饋） | 2 週 |
| **Category Acc.** | 68% | 80%+ | P2-B（人工回饋）| 3-4 週 |
| **搜尋延遲** | ~50ms | 30ms | P1-B（預計算） | 1 週 |

---

## 實作時序

### Phase 1（1-2 週，P1 優先級）

1. **Day 1-2**：
   - 新建 `utils/synonym_dict.py` + `utils/freshness.py` + `utils/learning_store.py`
   - 修改 `utils/search_engine.py` 整合 freshness_score + synonym_boost

2. **Day 2-3**：
   - 新建 `scripts/enrich_qa.py`，生成 `qa_enriched.json`
   - 修改 `app/core/store.py` 支援 enriched 版本
   - 更新 `config.py` 新增 SYNONYM_BOOST、FRESHNESS_MIN 常數

3. **Day 3-4**：
   - 修改 `scripts/04_generate_report.py` 和 `app/core/chat.py`，記錄 learnings（top_score < 0.35）
   - 新增 `qa_tools.py analyze-access` 子命令

4. **Day 4-5**：
   - 測試 + Makefile 更新
   - 基準線評估（eval-compare）

### Phase 2（2-3 週，P2 優先級）

1. **Week 2-1**：
   - 新建 `app/routers/feedback.py` 和 feedback 處理邏輯
   - 新增 `qa_tools.py annotate-category` 和 `qa_tools.py compare-eval` 子命令

2. **Week 2-2**：
   - 修改 `app/core/store.py` 加入 source_snippet 追蹤
   - 修改 `app/core/chat.py` 加入 P3-A staleness 警示（可先實作）

3. **Week 2-3**：
   - 回放 `human_corrections.jsonl`，統計分類誤差模式
   - 準備 Phase 3 規劃

### Phase 3（後續，P3 及觀測層）

- Query Understanding 高階特徵提取
- Metric 監控（Prometheus + Grafana）
- 多步推理 Agent（可選）

---

## 模組清單與估算

### 新增模組

| 檔案 | 行數估算 | 職責 |
|------|---------|------|
| `utils/synonym_dict.py` | ~120 | SEO 同義詞辭典 + expand_keywords() |
| `utils/freshness.py` | ~60 | 時效性衰減函數 |
| `utils/learning_store.py` | ~150 | Learning JSONL 讀寫 + 索引 |
| `utils/usage_aggregator.py` | ~100 | Access log 聚合統計 |
| `scripts/enrich_qa.py` | ~200 | Offline enrichment 主控 |
| `app/routers/feedback.py` | ~80 | POST /api/v1/feedback endpoint |
| | **合計** | **~710 行** |

### 修改模組

| 檔案 | 修改項目 | 影響 |
|------|---------|------|
| `utils/search_engine.py` | `_hybrid_scores()` 加入 freshness_mod + synonym_boost + learning_boost + usage_boost | 搜尋邏輯擴展，向下相容 |
| `app/core/store.py` | 優先載入 qa_enriched.json，fallback 到 qa_final.json | 無破壞性 |
| `scripts/04_generate_report.py` | Step 4 搜尋失敗記錄 learning | 副作用：僅記錄，不影響報告 |
| `app/core/chat.py` | 整合 learning + P3-A staleness 警示 | 副作用：加入提示文字 |
| `config.py` | 新增 5 個常數：SYNONYM_BOOST、FRESHNESS_MIN、LEARNING_BOOST、USAGE_WEIGHT | 擴展，向下相容 |
| `qa_tools.py` | 新增子命令：analyze-access、annotate-category、compare-eval | 工具擴展 |
| `Makefile` | 新增 make target：enrich-qa、pipeline-v2、eval-compare | CI/CD 擴展 |
| | **合計修改** | **8 檔案** |

---

## 風險與依賴

### 依賴關係

```
P1-A (Learnings) ← P1-B (Enrichment) + P1-C (Usage Agg)
                     ↓
P2-A (Confidence) ← P1-A/B
P2-B (Feedback) ← Access Logs + Learnings
P2-C (Traceability) ← Q&A 需有 source_date
P3-A (Staleness) ← source_date enrichment
```

**關鍵依賴**：
- `source_date` 欄位：確認 `qa_final.json` 每筆 Q&A 是否有 source_date；如無需從 `qa_per_meeting/` 中回填
- Access logs：確認 `output/access_logs/` 持續記錄（FastAPI `audit_logger` 實作）

### 風險

| 風險 | 衝擊 | 緩解策略 |
|------|------|---------|
| Enrichment 檔案過大 | 記憶體溢出 | 分塊載入（千筆級批次）；使用 generator |
| Learning JSONL 無限增長 | 搜尋性能降低 | 定期輪轉檔案（按月）；保留最近 12 個月 |
| 同義詞詞典維護負擔高 | 人工成本 | 初始 100+ 詞彙後，基本穩定；後續靠 P1-C zero-hit 自動識別 |
| Source 追蹤路徑錯誤 | 資料不一致 | 單元測試 + 驗證 file 存在 |

---

## 成功指標

- [ ] KW Hit Rate 78% → 85%+
- [ ] Accuracy 3.95 → 4.2+
- [ ] Search Latency 50ms → 30ms
- [ ] P1-A/B/C 完全實作 + 單元測試 80%+ 覆蓋
- [ ] P2-A/B/C 完全實作 + E2E 驗證
- [ ] Makefile targets (enrich-qa, eval-compare) 可用
- [ ] 無回歸（既有評估指標不下降）

---

## 後續研究方向（未來階段）

1. **Query Understanding**（L1 進階）：自動從 zero-hit queries 生成新同義詞
2. **Active Learning**（L3 進階）：自動選取最具信息量的樣本，用於人工標記
3. **Multi-hop Reasoning**（L6）：支援多步查詢（如「Discover 流量下降的原因」→「AMP 兼容性」→「GSC 檢查方法」）
4. **Reranking with LLM**（L2 進階）：在 top-5 結果上用 gpt-5-mini 執行精確再排序
