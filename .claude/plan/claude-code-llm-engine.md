# 計畫：Claude Code 作為 LLM 引擎（整合版）

> 日期：2026-02-28
> 狀態：v4 — 整合增量更新策略、研究佐證、架構審查修正
> 審查來源：everything-claude-code:architect（x2）+ 增量更新研究（LSHBloom、SemHash、LiveVectorLake）

---

## 一、目標

讓所有目前依賴 OpenAI API 的操作，都能透過 Claude Code CLI 完成，且：

1. **無需 OpenAI API key** 即可執行 Step 2/3/4 及搜尋/對話
2. **Eval（Step 5）保留 OpenAI** 作為獨立 judge，維持基準線可比性
3. **跨 provider 追蹤 eval 分數**，能比較 OpenAI vs 其他方案，並保護最高分基準線
4. **Context Window 風險** 每步有明確預算與分批策略
5. **增量更新**：單份會議修正或新會議加入，不觸發全量重算

---

## 二、架構總覽

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3：Slash Commands（便捷捷徑，瘦包裝）                          │
│  /extract-qa  /dedupe-classify  /generate-report                    │
│  /evaluate-qa  /pipeline-local  /search  /chat                      │
│  → 每個 command 只描述任務意圖，規則 reference Layer 1               │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ Bash 工具呼叫
┌──────────────────────────────────▼──────────────────────────────────┐
│  Layer 2：scripts/qa_tools.py（輕量 CLI 資料工具）                    │
│  • pipeline-status / list-unprocessed / merge-qa                    │
│  • search --query（qa_embeddings.npy + numpy cosine，無 API）        │
│  • load-metrics --source（Google Sheets / TSV，無 API）              │
│  • sample-eval --n / eval-compare                                   │
│  → 所有 I/O 操作集中於此，Claude Code 不直接讀寫 JSON/npy            │
│  → 重用現有邏輯，不重寫：list_pipeline_state.py、metrics_parser.py   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ import
┌──────────────────────────────────▼──────────────────────────────────┐
│  Layer 1：.claude/skills/seo-qa-pipeline.md（共用規則）               │
│  → Q&A schema、category 定義、萃取規則、週報模板、評估維度             │
│  → 所有 commands 唯一參考來源，不再各自內嵌規則                        │
└─────────────────────────────────────────────────────────────────────┘

Phase 2（未來升級路徑）：
  scripts/mcp_server.py → 將 Layer 2 工具暴露為 MCP tools
  → 使用者可用自然語言觸發，無須記憶 slash command 名稱
```

### Phase 1 vs Phase 2 觸發條件

Phase 2 升級時機（任一滿足即可考慮）：
- 使用者頻繁用自然語言描述複雜跨步工作流
- `qa_tools.py` CLI 介面出現明顯瓶頸
- 需要工具之間的動態組合呼叫

---

## 三、OpenAI API → Claude Code 替代對照表

| OpenAI 呼叫 | 替代方式 | 工具 | Step |
|------------|---------|------|------|
| `extract_qa_from_text()` gpt-5.2 | Claude Code 直接推理 | `qa_tools.py merge-qa` 後儲存 | 2 |
| `get_embeddings()` 建索引 | **保留 OpenAI**（已有 qa_embeddings.npy）| — | 3 |
| `merge_similar_qas()` gpt-5.2 | Claude Code 直接推理 | — | 3 |
| `classify_qa()` gpt-5-mini | Claude Code 直接推理 | — | 3 |
| `get_embeddings()` 查詢 | `qa_tools.py search`（本地向量搜尋） | numpy cosine on .npy | 4 |
| `_llm_rerank_report_qa()` gpt-5-mini | Claude Code 直接推理 | `qa_tools.py search` 候選集 | 4 |
| `evaluate_qa_quality()` gpt-5.2 | **保留 OpenAI**（避免 self-eval bias） | `05_evaluate.py` | 5 |
| `_llm_judge_retrieval_relevance()` gpt-5-mini | **保留 OpenAI** | `05_evaluate.py` | 5 |
| `rag_chat()` gpt-5.2 | Claude Code 直接推理 | `qa_tools.py search` | chat |
| `get_embedding()` query | `qa_tools.py search`（本地向量搜尋） | numpy cosine on .npy | search |

> **關鍵設計決策**：
> - `qa_embeddings.npy` 已存在（1536 維，703 筆），直接用於本地向量搜尋，不需 OpenAI
> - Step 5 必須保留 OpenAI 作為獨立 judge，確保 eval 基準線可比性
> - `get_embeddings()` 建索引（Step 3）繼續用 OpenAI，因為現有 .npy 可直接用

---

## 四、增量更新策略

### 4.1 現況診斷（架構審查發現）

**問題：目前 Step 3 爆炸半徑 = 100%**

```
修正 1 份會議（~8 筆 Q&A）→ 觸發：
  712 次 embedding API 呼叫（全量重算）
  725 次 LLM 分類呼叫（全量重算）
  所有 id 流水號重新編號（下游全斷）
```

**三個根本缺陷**（架構審查確認）：

| 缺陷 | 位置 | 影響 |
|------|------|------|
| `id` 是不穩定流水號 | `03_dedupe_classify.py:196` | golden set、audit trail 每次重跑後全部失效 |
| `merged_from` 缺 `source_file` | `openai_helper.py:371-377` | 無法反查哪些 merged Q&A 受影響 |
| `qa_embeddings.npy` 用位置耦合 | `app/core/store.py` | 插入/刪除任何 Q&A 導致 index 位移，搜尋結果全錯 |

---

### 4.2 基礎修正（其他所有功能的前提）

**必須先做，再實作 qa_tools.py 和增量邏輯：**

#### 修正 A：穩定 ID（`stable_id`）

```python
# 基於內容的確定性 ID，跨次執行不變
def compute_stable_id(source_file: str, question: str) -> str:
    content = f"{source_file}::{question[:120]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

- `stable_id` 加入 `qa_final.json` 每筆 Q&A 的 schema
- 保留 `id`（流水號）供顯示用，但所有跨系統引用改用 `stable_id`
- 合併後的 Q&A：`stable_id = sha256(sorted([src_id1, src_id2, ...]))[:16]`

研究佐證：LlamaIndex、LangChain 的 document 追蹤都基於 `doc_id`（等同 `stable_id`），不用位置 index（[LlamaIndex docs](https://docs.llamaindex.ai/)）

#### 修正 B：補齊 `merged_from.source_file`

修改 `utils/openai_helper.py:371-377`，`merged_from` 結構加入 `source_file`：

```json
"merged_from": [
  {"source_title": "...", "source_date": "2024-01-15", "source_file": "meeting_20240115.md", "stable_id": "abc123"},
  {"source_title": "...", "source_date": "2024-02-10", "source_file": "meeting_20240210.md", "stable_id": "def456"}
]
```

#### 修正 C：Embedding 以 `stable_id` 為 key

用 `dict[stable_id → vector]` 取代位置耦合的 `.npy`：

```python
# output/qa_embeddings_index.json  → {stable_id: embedding_row_index}
# output/qa_embeddings.npy         → 仍為 numpy array（效能不變）
# 查詢：先查 index 得到 row，再切 npy 的對應行
```

或更徹底：儲存為 `{stable_id: list[float]}` 的 JSON（搜尋效能稍降，但完全解除耦合）。選擇取決於知識庫規模，700-1000 筆 JSON 格式仍在接受範圍（~10 MB）。

研究佐證：pgvector、Milvus 2.6+、Chroma 都使用文件 ID 作為向量查詢 key，不依賴位置順序（[pgvector embedding versioning](https://www.dbi-services.com/blog/rag-series-embedding-versioning-with-pgvector/)）

---

### 4.3 三種更新情境與策略

#### 情境 A：新會議加入（最常見）

```
觸發：Step 1 fetch 到新 Markdown，Step 2 萃取出新的 *_qa.json

增量去重流程：
  1. 計算新 Q&A 的 embeddings（N 筆，N ≈ 5-15）
  2. 與現有 qa_final.json 的 embeddings 做 cosine similarity
     （N × 725 次 dot product，numpy，< 0.1 秒）
  3. similarity ≥ 0.88 → LLM 判斷是否合併（僅候選對，通常 0-5 組）
  4. 無重複 → 直接 append，賦予新 stable_id
  5. 更新 qa_embeddings_index.json（append，不重建）

API 呼叫量：N × embedding + 0-5 × LLM merge（vs. 700+ × 全量）
```

研究佐證：SemHash cosine similarity threshold 0.88-0.90 適合 Q&A 去重（[SemHash paper](https://medium.com/@sreeprad99/how-semhash-simplifies-semantic-deduplication-for-llm-data-a0b1a53e84fe)）

#### 情境 B：單份會議資料異常，需修正並重新萃取

```
觸發：發現 meeting_X.md 的萃取結果有誤，修正後重跑

目標性替換流程：
  1. 查找所有受影響的 Q&A（不需全量 scan，只需查 stable_id 前綴）：
     - source_file = meeting_X.md  AND  is_merged = false  → 直接刪除
     - source_file in merged_from   AND  is_merged = true  → 標記 needs_review
  2. 執行修正後的 Step 2：重新萃取 meeting_X.md → 新的 *_qa.json
  3. 對新 Q&A 執行情境 A 的增量去重流程
  4. needs_review 的 merged Q&A：呈現給使用者，由 Claude Code 判斷是否重新合併

爆炸半徑：僅影響 meeting_X 的 N 筆（N ≈ 5-15）+ needs_review 的 merged 筆數（通常 0-3）
vs. 舊方案：全量 700+ 筆
```

#### 情境 C：定期全量重算（維護用）

```
觸發：embedding model 更換、重大 prompt 調整、季度品質審查

全量重算時機（研究建議每季一次）：
  make step3 --force   （現有機制，保留不變）

保護措施：
  - 重算前自動建立 snapshot：output/snapshots/qa_final_{date}.json
  - 重算完成後比對 stable_id 集合，列出新增/刪除/變更的 Q&A
  - eval 基準線不自動更新，需手動 --update-baseline
```

研究佐證：Hybrid update 策略——週增量 + 月優化 + 季全量（[Incremental Updates in RAG](https://dasroot.net/posts/2026/01/incremental-updates-rag-dynamic-documents/)）

---

### 4.4 `qa_tools.py` 增量更新子命令

```bash
# 情境 A：新會議增量加入
python scripts/qa_tools.py add-meeting --file output/qa_per_meeting/new_meeting_qa.json

# 情境 B：修正異常會議
python scripts/qa_tools.py fix-meeting --source-file meeting_20240115.md
  # 輸出：列出將被刪除/標記的 Q&A，確認後執行

# 情境 C：查看待複審的 merged Q&A
python scripts/qa_tools.py list-needs-review

# 全量 diff：重算前後比對
python scripts/qa_tools.py diff-snapshot --before snapshots/qa_final_20260215.json
```

---

### 4.5 Data Integrity 護欄

| 風險 | 護欄 |
|------|------|
| embedding index 位移 | `qa_embeddings_index.json` 以 `stable_id` 為 key，不依賴位置 |
| golden set id 斷裂 | eval golden set 改用 `stable_id` 引用；舊 `id` 欄位保留但廢棄 |
| 增量去重漏合併 | add-meeting 後自動提示：`已新增 N 筆，建議執行 /evaluate-qa 驗證品質` |
| 部分更新中途失敗 | `qa_tools.py` 所有寫入操作先寫 `.tmp` 再 rename（atomic write） |
| 合併來源遺失 | `merged_from` 補齊 `source_file` 和 `stable_id`（修正 B） |

---

## 五、Context Window 預算與分批策略

每步操作的 token 預算（以 Claude Sonnet 4.6 200k context 為基準）：

### Step 2：Q&A 萃取（每個 sub-agent 獨立 context）

```
單一會議 Markdown：    3,000 – 10,000 tokens
萃取規則 system：      ~1,500 tokens
輸出 Q&A（預估）：     ~3,000 tokens
─────────────────────────────────────
單 agent 峰值：        ~15,000 tokens  ✅ 安全
```

策略：parallel sub-agent（已實作），每個檔案獨立 agent，context 自動隔離。

### Step 3：去重 + 分類（依增量 vs 全量分路）

**路徑 A — 增量（新會議 / 修正單份）**：

```
新 Q&A 筆數 N（通常 5-15 筆）：
  embedding 計算：N 筆，不進 context
  相似度比對：N × 725 dot product（numpy，0.1 秒，不進 context）
  LLM 合併候選（0-5 對）× 2 筆完整 Q&A = ~5,000 tokens  ✅

分類：
  N 筆 × 200 tokens = ~3,000 tokens  ✅
```

**路徑 B — 全量重算（季度維護、--force）**：

```
全量 Q&A × 400 tokens/筆 × 703 筆 = ~280,000 tokens  ❌ 需分批
```

**全量時的兩階段分批策略（Claude Code 執行）**：

```
Stage A — 去重候選識別（只看 question 文字）：
  703 筆 question × 50 tokens/筆 = ~35,000 tokens  ✅
  → 輸出 duplicate_groups 清單（只含 stable_id + question）

Stage B — 合併（只載入候選群組的完整 Q&A）：
  平均 3 筆/群 × 500 tokens/筆 × N 群
  若 N ≤ 20 群 = ~30,000 tokens  ✅
  → 每群合併，不全量載入

分類（按 category 分批）：
  每次一個 category ~70 筆 × 200 tokens = ~14,000 tokens  ✅
  共 10 個 category，分 10 批
```

### Step 4：週報生成（分段執行）

```
指標資料（異常指標清單）：    ~5,000 tokens
每指標搜尋結果 top-5：       5 × 400 = 2,000 tokens
同時處理指標數（分批 10 個）：~20,000 tokens/批  ✅
最終報告組裝（摘要 + 精選）： ~15,000 tokens  ✅
```

策略：`qa_tools.py search` 按指標逐一查詢，只有搜尋結果進入 context，不全量載入知識庫。

### Step 5：Eval（OpenAI API，Claude Code 只解讀結果）

```
OpenAI judge 負責評分（context 在 OpenAI 側）
Claude Code 接收 eval_report.json：~5,000 tokens  ✅
負責：解讀趨勢、對比基準線、建議改善方向
```

### Chat / Search（互動式，每輪有界）

```
search 結果 top-5：           5 × 400 = ~2,000 tokens
對話歷史（最多 20 輪）：       ~10,000 tokens
system prompt：               ~500 tokens
─────────────────────────────────────────────
單輪峰值：                     ~13,000 tokens  ✅
```

---

## 五、Eval 跨 Provider 追蹤設計

### 5.1 目標

- 比較 **OpenAI vs 其他 provider** 的萃取/分類品質差異
- 保護歷史最高分，不被低品質 run 覆蓋
- 在 Laminar 看到跨時間、跨 provider 的分數趨勢

### 5.2 版本化輸出結構

```
output/
├── evals/                                   ← 新增目錄
│   ├── 20260227_openai_gpt-5.2.json         ← 歷史 run
│   ├── 20260228_openai_gpt-5.2.json
│   └── 20260228_claude-code.json            ← Claude Code 萃取後用 OpenAI judge
├── eval_baseline.json                        ← 受保護的最高分基準線（唯讀，需 --update-baseline 才改）
├── eval_report.json                          → 符號連結到最新 run（向下相容）
└── eval_report.md                            → 最新 run 的 Markdown（向下相容）
```

### 5.3 eval_baseline.json 結構

```json
{
  "locked": true,
  "note": "只有 --update-baseline 且新分數超過閾值才更新",
  "provider": "openai",
  "model": "gpt-5.2",
  "extraction_engine": "openai",
  "run_date": "2026-02-27",
  "scores": {
    "relevance":    4.80,
    "accuracy":     3.95,
    "completeness": 3.85,
    "granularity":  4.75
  },
  "retrieval": {
    "kw_hit_rate":       0.78,
    "mrr":               0.75,
    "llm_top1_precision": 1.0
  },
  "classification": {
    "category_accuracy": 0.68
  }
}
```

### 5.4 05_evaluate.py 修改（不重寫，只加功能）

新增 CLI flags：
```bash
# 現有用法不變（向下相容）
python scripts/05_evaluate.py

# 新增：標記 provider 和萃取引擎
python scripts/05_evaluate.py \
  --provider openai \
  --extraction-engine claude-code \
  --model gpt-5.2 \
  --sample 30

# 比較並考慮更新基準線
python scripts/05_evaluate.py \
  --provider openai \
  --extraction-engine openai \
  --update-baseline
```

新增邏輯（在現有主流程末尾加入，不改 judge 邏輯）：

```python
# 1. 版本化輸出
run_id = f"{today}_{provider}_{extraction_engine}"
versioned_path = OUTPUT_DIR / "evals" / f"{run_id}.json"
save_to(versioned_path, results_with_metadata)

# 2. 與基準線比較
baseline = load_baseline()
if baseline:
    print_comparison_table(new=results, baseline=baseline)
    if args.update_baseline:
        if beats_baseline(results, baseline, threshold=0.05):
            update_baseline(results)
            print("✅ 基準線已更新")
        else:
            print("⚠️  分數未超過基準線閾值，保留原有基準線")

# 3. Laminar 追蹤（新增）
Laminar.initialize(project_api_key=os.getenv("LMNR_PROJECT_API_KEY"))
# @observe 已在各 evaluate_* 函式加 metadata
```

### 5.5 Laminar metadata 標記（05_evaluate.py）

```python
from lmnr import Laminar, observe

@observe(
    name="evaluate_qa_quality",
    metadata={
        "provider": os.getenv("EVAL_PROVIDER", "openai"),
        "model": os.getenv("EVAL_MODEL", config.OPENAI_MODEL),
        "extraction_engine": os.getenv("EXTRACTION_ENGINE", "openai"),
        "step": "step5_quality_eval",
    }
)
def evaluate_qa_quality(qa: dict, source_text: str = "") -> dict:
    ...  # 現有邏輯不變
```

### 5.6 qa_tools.py eval-compare 子命令

```bash
python scripts/qa_tools.py eval-compare
```

輸出範例：
```
Eval 比較報告（output/evals/ 下 5 個 run）

provider          model      extraction_engine  avg_score  relevance  accuracy  completeness  granularity
─────────────────────────────────────────────────────────────────────────────────────────────────────
★ BASELINE        openai     gpt-5.2            openai     4.34       4.80      3.95          3.85       4.75
  20260228        openai     gpt-5.2            claude-code 4.20      4.75      3.90          3.80       4.35
  20260227        openai     gpt-5-mini         openai     3.95       4.60      3.70          3.65       3.85

★ = 受保護的基準線，需 --update-baseline 才能覆寫
```

### 5.7 基準線更新規則

```python
def beats_baseline(new: dict, baseline: dict, threshold: float = 0.05) -> bool:
    """所有核心維度平均分須超過基準線 threshold 分才更新"""
    dims = ["relevance", "accuracy", "completeness", "granularity"]
    new_avg = sum(new["scores"][d] for d in dims) / len(dims)
    baseline_avg = sum(baseline["scores"][d] for d in dims) / len(dims)
    return new_avg >= baseline_avg + threshold
```

---

## 六、重用現有程式碼（避免重工）

| 現有程式碼 | qa_tools.py 的處理方式 |
|-----------|----------------------|
| `scripts/list_pipeline_state.py` | 直接 import `PipelineState` 類別，不重寫 |
| `04_generate_report.py` 的 `fetch_from_sheets()` / `parse_metrics_tsv()` / `detect_anomalies()` | 抽取到 `utils/metrics_parser.py`（無 OpenAI 依賴），兩者都 import |
| `05_evaluate.py` 的完整 judge 邏輯 | 不動，只在末尾加 provider flags + 版本化輸出 + Laminar |
| `qa_embeddings.npy` (1536 維) | 直接用於 `search` 子命令的本地向量搜尋 |

> **關鍵約束**：`qa_tools.py` 禁止 `import config`，避免 `_require_env("OPENAI_API_KEY")` 在啟動時觸發。
> 所有路徑使用相對於專案根目錄的 `pathlib.Path`，不依賴 `config.OUTPUT_DIR`。

---

## 七、新增 / 修改的 Slash Commands

### 現有（只精簡，不重寫）

| Command | 修改內容 |
|---------|---------|
| `/extract-qa` | 移除內嵌規則 → reference `seo-qa-pipeline.md`；加入 qa_tools.py 呼叫說明 |
| `/dedupe-classify` | 同上；加入兩階段策略說明（Stage A 只比 question，Stage B 合併群組） |
| `/pipeline-local` | 加入 Step 4 流程；更新工具呼叫方式 |

### 新增

| Command | 功能 |
|---------|------|
| `/generate-report` | 呼叫 qa_tools.py load-metrics + search，生成週報 |
| `/evaluate-qa` | 呼叫 05_evaluate.py（需 OpenAI），解讀結果並與基準線比較 |
| `/search` | 呼叫 qa_tools.py search，Claude Code 格式化輸出 |
| `/chat` | 互動式 RAG：每輪呼叫 qa_tools.py search，Claude Code 推理回答 |

---

## 八、實作步驟

### Step 0：基礎修正（阻斷項，必須先做）

**這三項是所有後續工作的前提。不先修正，增量邏輯和 eval 追蹤都無法正常運作。**

**0.1 修正 `utils/openai_helper.py`：補齊 `merged_from.source_file`**
- 第 371-377 行，`merged_from` 結構加入 `source_file` 和 `stable_id` 欄位
- 對現有 `qa_final.json` 中 `is_merged=true` 的記錄，可從 `source_title + source_date` 反查補填 `source_file`（一次性 migration script）

**0.2 修正 `scripts/03_dedupe_classify.py`：引入 `stable_id`**
- 加入 `compute_stable_id(source_file, question)` 函式
- 每筆 Q&A 在寫入 `qa_final.json` 時同時生成 `stable_id`
- 保留 `id`（流水號）但所有跨系統引用（golden set、audit trail）改用 `stable_id`

**0.3 修正 `qa_embeddings.npy` 的耦合問題**
- 新增 `output/qa_embeddings_index.json`：`{stable_id: row_index}` 映射
- 修改 `app/core/store.py` 的 `search()` 方法：改用 `stable_id` 查詢而非位置 index
- 修改 `scripts/05_evaluate.py` 的 `_load_persisted_embeddings()` 同步更新

---

### Step 1：抽取共用邏輯（避免後續重工）

**1.1 新增 `utils/metrics_parser.py`**
- 從 `04_generate_report.py` 抽取：`fetch_from_sheets()`、`parse_metrics_tsv()`、`detect_anomalies()`、`METRIC_QUERY_MAP`、`CORE_METRICS`、`ALERT_THRESHOLD_*`
- 修改 `04_generate_report.py`：改為 `from utils.metrics_parser import ...`
- 不改任何邏輯，純搬移

**1.2 建立 `output/evals/` 目錄**
- `mkdir -p output/evals`
- 將現有 `output/eval_report.json`（若存在）複製為 `output/evals/20260227_openai_gpt-5.2.json`

**1.3 建立初始 `output/eval_baseline.json`**
- 從 MEMORY.md 的基準線數值填入（Relevance 4.80、Accuracy 3.95 等）

### Step 2：建立 scripts/qa_tools.py

子命令清單：

```
# 狀態查詢
pipeline-status          重用 list_pipeline_state.py
list-unprocessed         重用 list_pipeline_state.py
list-needs-review        列出 is_merged=true 且 needs_review=true 的 Q&A

# 資料操作
merge-qa                 重用 list_pipeline_state.py 的 merge logic
add-meeting              增量加入新會議 Q&A（情境 A）
fix-meeting              目標性替換異常會議的 Q&A（情境 B）
diff-snapshot            與快照比對，列出變更

# 搜尋與 eval
search                   qa_embeddings.npy + index.json + numpy cosine（無 OpenAI）
load-metrics             from utils.metrics_parser import fetch_from_sheets
eval-compare             掃描 output/evals/*.json，輸出跨 provider 比較表
```

行數目標：300–400 行（因加入增量邏輯）。禁止 `import config`。

### Step 3：修改 scripts/05_evaluate.py

修改範圍（最小改動原則）：

1. 加入 `--provider`、`--extraction-engine`、`--model`、`--update-baseline` flags
2. 在主流程末尾加入版本化儲存邏輯
3. 在主流程末尾加入基準線比較邏輯
4. 加入 `Laminar.initialize()` 和 `@observe` metadata
5. 不改任何 judge 邏輯或評分計算

### Step 4：補完 .claude/skills/seo-qa-pipeline.md

從現有 commands 抽取重複規則，加入：
- 週報 Markdown 模板
- qa_tools.py CLI 速查表
- Context Window 預算速查

### Step 5：新增 / 更新 Slash Commands

依序：
1. 更新 `/extract-qa`（精簡規則 → reference skill）
2. 更新 `/dedupe-classify`（加入兩階段策略）
3. 新增 `/generate-report`
4. 新增 `/evaluate-qa`
5. 新增 `/search`
6. 新增 `/chat`
7. 更新 `/pipeline-local`（加 Step 4）

### Step 6：更新 CLAUDE.md

- 加入完整命令清單
- 加入「Claude Code 模式 vs OpenAI 模式」功能對照表

---

## 九、檔案清單

### Step 0：基礎修正（阻斷項）
| 檔案 | 修改內容 | 風險 |
|------|---------|------|
| `utils/openai_helper.py` | `merged_from` 加 `source_file` + `stable_id` | 低（只加欄位） |
| `scripts/03_dedupe_classify.py` | 加 `compute_stable_id()`，寫入 `stable_id` 欄位 | 中（需 migration） |
| `output/qa_embeddings_index.json` | 新增 `{stable_id: row_index}` 映射（由 03 生成） | — |
| `app/core/store.py` | search() 改用 stable_id index 查詢 | 中（需測試） |
| `scripts/05_evaluate.py` | `_load_persisted_embeddings()` 用 index.json | 低 |

### Step 1：共用邏輯抽取
| 檔案 | 說明 | 約行數 |
|------|------|--------|
| `utils/metrics_parser.py` | 從 04 抽取，無 OpenAI 依賴 | ~300 |
| `output/evals/` | 版本化 eval 結果目錄 | — |
| `output/eval_baseline.json` | 受保護基準線（從 MEMORY.md 填入） | — |

### Step 2：`scripts/qa_tools.py`（新增）
| 說明 | 約行數 |
|------|--------|
| 輕量 CLI 工具（含增量更新子命令） | ~350 |

### Step 3：Eval 追蹤（修改 `scripts/05_evaluate.py`）
| 修改內容 |
|---------|
| 加 `--provider`、`--extraction-engine`、`--update-baseline` flags |
| 版本化輸出到 `output/evals/` |
| 基準線比較與保護邏輯 |
| Laminar `@observe` metadata |

### Step 4：補完 Shared Skill 與 Commands
| 檔案 | 說明 |
|------|------|
| `.claude/skills/seo-qa-pipeline.md` | 補完規則 + qa_tools.py CLI 速查 |
| `.claude/commands/generate-report.md` | 新增 |
| `.claude/commands/evaluate-qa.md` | 新增 |
| `.claude/commands/search.md` | 新增 |
| `.claude/commands/chat.md` | 新增 |
| `.claude/commands/extract-qa.md` | 精簡（reference skill） |
| `.claude/commands/dedupe-classify.md` | 精簡 + 兩路徑說明（增量/全量） |
| `.claude/commands/pipeline-local.md` | 加 Step 4、說明增量模式 |
| `CLAUDE.md` | 更新命令清單 |

### 不修改
| 檔案 | 原因 |
|------|------|
| `scripts/list_pipeline_state.py` | `qa_tools.py` 直接 import |
| `scripts/02_extract_qa.py` | Step 2 增量機制已完整 |
| `scripts/04_generate_report.py` 邏輯 | 純搬移 import，不改邏輯 |
| `config.py` / `utils/openai_helper.py` 其他邏輯 | OpenAI 模式雙軌保留 |
| `app/` 其他檔案 | FastAPI 服務獨立 |

---

## 十、成功標準

### Step 0 基礎修正
- [ ] `qa_final.json` 每筆都有 `stable_id`，重跑 Step 3 後 `stable_id` 不變（確定性）
- [ ] `merged_from` 每筆含 `source_file` + `stable_id`
- [ ] `output/qa_embeddings_index.json` 存在且與 `.npy` 行數一致
- [ ] `app/core/store.py` 搜尋在插入新 Q&A 後結果不漂移

### 增量更新
- [ ] `python scripts/qa_tools.py add-meeting --file <new_qa.json>` 只新增 N 筆，不觸發全量重算
- [ ] `python scripts/qa_tools.py fix-meeting --source-file meeting_X.md` 只刪除/替換 meeting_X 相關的 Q&A
- [ ] 修正單份會議後，golden set 中引用其他會議的 `stable_id` 全部仍有效
- [ ] `list-needs-review` 能列出受影響的 merged Q&A

### Claude Code 模式功能
- [ ] `python scripts/qa_tools.py search --query "canonical"` 回傳相關 Q&A（本地向量）
- [ ] `python scripts/qa_tools.py load-metrics --source <url>` 無 OpenAI key 成功解析
- [ ] `/generate-report <url>` 生成完整 Markdown 週報
- [ ] `/chat` 多輪對話，正確引用知識庫來源
- [ ] 無 `OPENAI_API_KEY` 時，Step 2/3/4/search/chat 正常；Step 5 明確提示需要 key

### Eval 追蹤
- [ ] `python scripts/05_evaluate.py --extraction-engine claude-code` 輸出版本化結果到 `output/evals/`
- [ ] `python scripts/qa_tools.py eval-compare` 顯示跨 provider 比較表（含 baseline 標記）
- [ ] Laminar dashboard 可依 `extraction_engine` 篩選 eval 分數趨勢
- [ ] `output/eval_baseline.json` 未被低分 run 覆寫（須 `--update-baseline` 且平均分 +0.05 以上）
