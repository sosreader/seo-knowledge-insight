# SEO QA Pipeline — 專案參考手冊

深度參考文件：架構、腳本、模型政策、資料結構。
在需要了解 pipeline 細節、查詢指令用法、確認模型選擇時載入此 skill。

---

## 專案概述

SEO Q&A 知識庫建構 Pipeline — 從 Notion 會議紀錄自動萃取結構化問答資料庫，支援去重、分類、語意搜尋與週報生成。

資料來源為超過兩年（2023-03 至今）的 SEO 顧問會議紀錄，87 份會議，產出 670 筆原始 Q&A，去重後 655 筆（v2.0，2026-03-02 防幻覺規則重跑）。

---

## 常用指令

```bash
# 安裝依賴
pip install -r requirements.txt
pip install -e ".[dev]"          # 含 pytest 開發依賴

# ── Makefile 快速入口（推薦 AI 工具使用） ──────────────
make pipeline          # 完整流程 fetch-notion→extract-qa→dedupe-classify
make fetch-notion      # Notion 擷取
make extract-qa        # Q&A 萃取
make dedupe-classify   # 去重 + 分類
make generate-report   # 週報生成
make evaluate-qa       # 品質評估
make extract-qa-test   # 只處理 3 份（快速驗證）
make dry-run           # 驗證設定（不執行）
make test              # 執行測試
make help              # 所有可用 targets

# ── 直接呼叫 Python ────────────────────────────────────
# 執行完整 pipeline（步驟 1→2→3，不含步驟 4、5）
python scripts/run_pipeline.py

# 分步驟執行
python scripts/run_pipeline.py --step fetch-notion              # Notion 擷取
python scripts/run_pipeline.py --step extract-qa              # OpenAI Q&A 萃取
python scripts/run_pipeline.py --step dedupe-classify              # 去重 + 分類
python scripts/run_pipeline.py --step generate-report              # 週報生成
python scripts/run_pipeline.py --step evaluate-qa              # 品質評估

# 常用選項
python scripts/run_pipeline.py --step fetch-notion --force      # 強制全量重抓
python scripts/run_pipeline.py --step extract-qa --limit 3    # 只處理 3 份（測試用）
python scripts/run_pipeline.py --step dedupe-classify --skip-dedup # 只分類不去重
python scripts/run_pipeline.py --step generate-report --input metrics.tsv  # 本機指標檔
python scripts/run_pipeline.py --step evaluate-qa --sample 50  # 抽樣 50 筆評估
python scripts/run_pipeline.py --step evaluate-qa --with-source # 帶原始 Markdown 驗證
python scripts/run_pipeline.py --step evaluate-qa --eval-retrieval # 評估 Retrieval 品質
python scripts/run_pipeline.py --dry-run             # 檢查設定不執行

# 測試
python -m pytest tests/ -v
python -m pytest tests/test_core.py::TestExtractDate -v  # 單一測試類別
```

---

## 架構：知識蒸餞 + RAG 混合架構

```
Notion API → [步驟1] fetch → raw_data/notion_json/ + markdown/
                                    ↓
                              [步驟2] extract → output/qa_per_meeting/ → qa_all_raw.json
                                    ↓
                              [步驟3] dedupe + classify → qa_final.json + qa_embeddings.npy
                                    ↓
                   Google Sheets → [步驟4] Hybrid Search + RAG → report_YYYYMMDD.md
                                    ↓
                              [步驟5] evaluate → eval_report.json + eval_report.md
```

- Steps 1–3 = **離線知識蒸餞**（從原始文檔提煉結構化知識庫）
- Step 4 = **RAG 流程**（Hybrid Search：語意檢索 + 關鍵字 boost → 上下文增強生成）
- Step 5 = **評估層**（Q&A 品質 + 分類 + Retrieval 品質）

### 步驟對應腳本

| 步驟 | 腳本                            | 功能                                                | 使用的模型                                  |
| ---- | ------------------------------- | --------------------------------------------------- | ------------------------------------------- |
| 1    | `scripts/01_fetch_notion.py`    | Notion 擷取 + Markdown 轉換                         | —                                           |
| 2    | `scripts/02_extract_qa.py`      | 會議紀錄 → Q&A pairs                                | gpt-5.2                                     |
| 3    | `scripts/03_dedupe_classify.py` | embedding 去重 + LLM 合併 + 分類 + embedding 持久化 | text-embedding-3-small, gpt-5.2, gpt-5-mini |
| 4    | `scripts/04_generate_report.py` | 指標異常偵測 + Hybrid Search + RAG 週報             | text-embedding-3-small, gpt-5.2             |
| 5    | `scripts/05_evaluate.py`        | Q&A 品質 + 分類 + Retrieval 評估                    | gpt-5.2, gpt-5-mini                         |

### 工具模組（utils/）

- `openai_helper.py` — OpenAI API 封裝：萃取 Q&A、embedding、合併、分類。所有 prompt 定義在此。
- `notion_client.py` — Notion API 封裝：含 rate limit 重試與增量同步。
- `block_to_markdown.py` — Notion block → Markdown 轉換。

### Helper 純邏輯函式

- `scripts/extract_qa_helpers.py` — 日期提取、長文分段
- `scripts/dedupe_helpers.py` — cosine similarity 矩陣計算

---

## 關鍵設定（config.py）

所有 API key 從 `.env` 讀取（參考 `.env.example`）。重要參數：

- `OPENAI_MODEL`: gpt-5.2（萃取與合併）
- `OPENAI_EMBEDDING_MODEL`: text-embedding-3-small
- `MAX_TOKENS_PER_CHUNK`: 6000（長文分段閾值）
- `SIMILARITY_THRESHOLD`: 0.88（去重 cosine similarity 閾值）
- `KW_BOOST`: 0.10（完整關鍵字命中的 boost 分數）
- `KW_BOOST_PARTIAL`: 0.05（弱命中 boost 分數）
- `KW_BOOST_MAX_HITS`: 3（最多計入幾個關鍵字命中）

---

## 模型使用政策

**一律使用 GPT-5 系列模型，禁止使用 GPT-4 系列（gpt-4o、gpt-4o-mini 等已淘汰）。**

| 用途      | 模型                     | 說明                               |
| --------- | ------------------------ | ---------------------------------- |
| Q&A 萃取  | `gpt-5.2`                | 主力模型，需要高品質理解與生成     |
| Q&A 合併  | `gpt-5.2`                | 合併多源資訊需要強推理             |
| 分類標籤  | `gpt-5-mini`             | 結構化輸出，省成本                 |
| 週報生成  | `gpt-5.2`                | 需要深度分析與知識引用             |
| 品質評估  | `gpt-5.2` + `gpt-5-mini` | Judge 用主力模型，分類驗證用小模型 |
| Embedding | `text-embedding-3-small` | 去重與語意搜尋                     |

---

## 資料目錄

- `raw_data/notion_json/` — Notion API 原始 JSON
- `raw_data/markdown/` — 轉換後的會議 Markdown
- `raw_data/images/` — 下載的圖片
- `raw_data/meetings_index.json` — 會議索引（含 last_edited_time）
- `output/qa_per_meeting/` — 每份會議的 Q&A JSON
- `output/qa_all_raw.json` — 合併後原始 Q&A（去重前）
- `output/qa_final.json` — 最終資料庫（含分類標籤）
- `output/qa_embeddings.npy` — 持久化 embedding 向量（Step 3 產出，Step 4/5 載入）
- `eval/golden_qa.json` — 分類評估 golden set
- `eval/golden_retrieval.json` — Retrieval 評估 golden set

---

## Q&A 資料結構

每筆 Q&A 包含：`question`, `answer`, `keywords`, `confidence`, `source_file`, `source_title`, `source_date`。

經步驟 3 後新增：`id`, `category`（10 分類）, `difficulty`（基礎/進階）, `evergreen`（true/false）。

合併的筆數另有 `merged_from` 來源列表。

---

## 增量處理機制

- 步驟 1：比對 `last_edited_time`，只抓新增或更新的頁面
- 步驟 2：檢查 `qa_per_meeting/` 已存在就跳過（`--force` 強制重跑）
- 所有步驟支援中途中斷後接續執行

---

## Python 版本

需要 Python ≥ 3.11。

---

## Claude Code 模式 — qa_tools.py CLI（Layer 2 資料介面）

### 架構總覽（三層）

```
Layer 3：Slash Commands（/search / /chat / /generate-report / /pipeline-local / /evaluate-qa-local / /evaluate-provider）
        （OpenAI 版本：/run-pipeline / /evaluate-qa）
Layer 2：scripts/qa_tools.py（I/O 操作，無 OpenAI 依賴）
Layer 1：.claude/skills/seo-qa-pipeline.md（此文件，規則與 schema）
```

### qa_tools.py 子命令速查

```bash
# 狀態查詢
python scripts/qa_tools.py pipeline-status          # pipeline 各步驟狀態
python scripts/qa_tools.py list-unprocessed         # 待萃取的 Markdown 檔
python scripts/qa_tools.py list-needs-review        # needs_review=true 的 merged Q&A

# 資料操作（無 OpenAI）
python scripts/qa_tools.py merge-qa                 # per-meeting JSON → qa_all_raw.json
python scripts/qa_tools.py add-meeting --file <path>       # 增量加入新會議（情境 A）
python scripts/qa_tools.py fix-meeting --source-file <f>   # 目標性刪除/標記（情境 B）
python scripts/qa_tools.py fix-meeting --source-file <f> --dry-run  # 預覽影響範圍
python scripts/qa_tools.py diff-snapshot --before <snapshot>        # 與快照比對

# 搜尋（無 OpenAI）
python scripts/qa_tools.py search --query "canonical 索引"     # 關鍵字加權搜尋
python scripts/qa_tools.py search --query "Discover" --top-k 10     # 回傳更多筆
python scripts/qa_tools.py search --query "AMP" --category "Discover與AMP"  # 限定分類

# 指標解析（無 OpenAI）
python scripts/qa_tools.py load-metrics --source "https://docs.google.com/..."
python scripts/qa_tools.py load-metrics --source metrics.tsv  # 本機 TSV 檔

# Eval（無 OpenAI）
python scripts/qa_tools.py eval-sample --size 20 --seed 42 --with-golden  # 抽樣 Q&A
python scripts/qa_tools.py eval-retrieval-local     # 規則式 Retrieval 評估
python scripts/qa_tools.py eval-save --input <json> --extraction-engine claude-code  # 儲存結果
python scripts/qa_tools.py eval-compare             # 跨 provider eval 比較表
```

### stable_id 說明

每筆 Q&A 的確定性 ID：`sha256(source_file::question[:120])[:16]`

- 重跑 Step 3 後 `stable_id` 不變（不同於 `id` 流水號）
- 合併後的 Q&A：`sha256(sorted([src_id1, src_id2, ...]))[:16]`
- `output/qa_embeddings_index.json`：`{stable_id: npy_row_index}` 映射

### output/evals/ 結構

```
output/
├── evals/                          # 版本化 eval 結果（.gitignore 忽略）
│   └── {date}_{provider}_{engine}.json
└── eval_baseline.json              # 受保護基準線（需 --update-baseline 才更新）
```

---

## 最近改動

### v2.0 Pipeline 全量重跑 + 統一清理（2026-03-02）

- 87 場會議完整重萃取（防幻覺規則），670 筆原始 → 655 筆去重後
- Embeddings 重建：(655, 1536) + 655 筆 index 映射
- `_persist_embeddings()` 修正：支援 `id` 欄位 fallback（原只認 `stable_id`）
- Registry latest 指針修正至 v2.0 條目
- v1 殘留報告歸檔至 `output/archive_v1/`（10 個檔案）
- `qa_final.md` 重建為 655 筆版本

### Dead Code Cleanup（2026-02-28）

- `config.py` 中的 `BATCH_CONCURRENCY` 常數（已棄用）
- `app/config.py` 中的 `SEARCH_TOP_K` 常數（已棄用）
- `utils/block_to_markdown.py` 中的 `list_counter` 參數與 `blocks_to_markdown_sync()` 函式
- `scripts/05_evaluate.py` 中的 `load_golden_set()` 函式（未使用）
- `scripts/04_generate_report.py` 中的舊版 `find_relevant_qas()` backward-compat wrapper
