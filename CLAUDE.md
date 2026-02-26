# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

SEO Q&A 知識庫建構 Pipeline — 從 Notion 會議紀錄自動萃取結構化問答資料庫，支援去重、分類、語意搜尋與週報生成。

資料來源為超過兩年（2023-03 至今）的 SEO 顧問會議紀錄，目前約 87 份，產出 699 筆 Q&A。

## 常用指令

```bash
# 安裝依賴
pip install -r requirements.txt
pip install -e ".[dev]"          # 含 pytest 開發依賴

# 執行完整 pipeline（步驟 1→2→3，不含步驟 4、5）
python scripts/run_pipeline.py

# 分步驟執行
python scripts/run_pipeline.py --step 1              # Notion 擷取
python scripts/run_pipeline.py --step 2              # OpenAI Q&A 萃取
python scripts/run_pipeline.py --step 3              # 去重 + 分類
python scripts/run_pipeline.py --step 4              # 週報生成
python scripts/run_pipeline.py --step 5              # 品質評估

# 常用選項
python scripts/run_pipeline.py --step 1 --force      # 強制全量重抓
python scripts/run_pipeline.py --step 2 --limit 3    # 只處理 3 份（測試用）
python scripts/run_pipeline.py --step 3 --skip-dedup # 只分類不去重
python scripts/run_pipeline.py --step 4 --input metrics.tsv  # 本機指標檔
python scripts/run_pipeline.py --step 5 --sample 50  # 抽樣 50 筆評估
python scripts/run_pipeline.py --step 5 --with-source # 帶原始 Markdown 驗證
python scripts/run_pipeline.py --step 5 --eval-retrieval # 評估 Retrieval 品質
python scripts/run_pipeline.py --dry-run             # 檢查設定不執行

# 測試
python -m pytest tests/ -v
python -m pytest tests/test_core.py::TestExtractDate -v  # 單一測試類別
```

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

## 關鍵設定（config.py）

所有 API key 從 `.env` 讀取（參考 `.env.example`）。重要參數：

- `OPENAI_MODEL`: gpt-5.2（萃取與合併）
- `OPENAI_EMBEDDING_MODEL`: text-embedding-3-small
- `MAX_TOKENS_PER_CHUNK`: 6000（長文分段閾值）
- `SIMILARITY_THRESHOLD`: 0.88（去重 cosine similarity 閾值）
- `BATCH_CONCURRENCY`: 5

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

## Q&A 資料結構

每筆 Q&A 包含：`question`, `answer`, `keywords`, `confidence`, `source_file`, `source_title`, `source_date`。經步驟 3 後新增：`id`, `category`（10 分類）, `difficulty`（基礎/進階）, `evergreen`（true/false）。合併的筆數另有 `merged_from` 來源列表。

## 增量處理機制

- 步驟 1：比對 `last_edited_time`，只抓新增或更新的頁面
- 步驟 2：檢查 `qa_per_meeting/` 已存在就跳過（`--force` 強制重跑）
- 所有步驟支援中途中斷後接續執行

## Python 版本

需要 Python ≥ 3.11。
