done
# /generate-report — 執行 Step 4 週報生成

直接執行 [scripts/04_generate_report.py](scripts/04_generate_report.py)，使用 OpenAI 產生報告內容。

## 實際行為

- 報告內容由 OpenAI 產生，使用 `config.REPORT_MODEL`
- 若啟用知識庫檢索，候選 Q&A 的 rerank 也會呼叫 OpenAI
- 主要輸入支援三種：Google Sheets URL、metrics snapshot JSON、本機 TSV
- 預設輸出為 `output/report_YYYYMMDD_<hash8>.md`
- 會使用 `output/qa_final.json`、`output/qa_embeddings.npy`、`output/qa_embeddings_index.json` 做知識庫檢索
- 生成後會做內建驗證、寫入 report cache、trend memory 與 artifact version registry

## 必要條件

- `OPENAI_API_KEY`
- 至少一種 metrics 來源：
  - Google Sheets URL
  - `output/metrics_snapshots/*.json`
  - 本機 TSV
- 若不使用 `--no-qa`，建議先確認 Step 3 artifacts 存在且一致：
  - `output/qa_final.json`
  - `output/qa_embeddings.npy`
  - `output/qa_embeddings_index.json`

## 硬性 Checklist（autoresearch 驗證，存檔前必達）

報告寫完、存檔前**逐項計數**，未達標的必須回頭修正再存檔。
這些規則的權重佔 composite_v3 的 44%，漏掉任一項都會顯著拉低分數。

| # | 規則 | eval 如何判定 | 目標 |
|---|------|--------------|------|
| 1 | Section 一：≥**5 個**結構化區塊，每塊含 `**現象**` + `**原因**` + `**行動**`（粗體關鍵字必須精確） | `causal_chain` = regex 匹配 `**現象**....**原因**....**行動**` 區塊數 ÷ 5 | ≥ 1.0 |
| 2 | Section 六：含一行 `💡 **最值得投入**：{具體動作}，因為{理由}` | `top_recommendation` = grep「最值得投入」或「💡」，300 字內需含因果詞（因為/由於/導致/所以/因此） | ≥ 1.0 |
| 3 | **每條** `- ` 行動項含具體工具名 + 動詞 | `action_specificity` = 含 pattern 的行動行數 ÷ 總行動行數 | ≥ 0.8 |
|   | 工具名：`GSC` `Search Console` `Screaming Frog` `Ahrefs` `Semrush` `PageSpeed` `GA4` `Chrome` | | |
|   | 動詞：`檢查` `驗證` `篩選` `設定` `修復` `排查` `測試` `重寫` `補上` `移除` `加入` `優化 title` `優化 description` | | |
| 4 | 含數據段落 ≥ **70**（每段含 `%` 或絕對數值） | `data_evidence_ratio` = 含數據段落 ÷ 70 | ≥ 1.0 |
| 5 | Section 三、四、五 **各 ≥4 分析段落**（與 Section 一、六 字數差距 < 3x） | `section_depth_variance` = 1 − (max_len − min_len) ÷ max_len | ≥ 0.6 |

> **失敗教訓**（autoresearch Round 6/10/11）：壓縮 Section 一來平衡深度會犧牲 causal_chain。正確做法是只擴展短 section，不壓縮長的。

---

## 用法

```bash
/generate-report <Google Sheets URL>
/generate-report output/metrics_snapshots/20260306-184745.json
```

對應 CLI 範例：

```bash
.venv/bin/python scripts/04_generate_report.py --input "https://docs.google.com/spreadsheets/d/..." --tab vocus
.venv/bin/python scripts/04_generate_report.py --snapshot output/metrics_snapshots/20260306-184745.json
.venv/bin/python scripts/04_generate_report.py --input metrics.tsv
```

若沒有提供參數，腳本會依序使用：

1. `--input`
2. `config.SHEETS_URL`
3. `utils.metrics_parser.DEFAULT_SHEETS_URL`

## 常用參數

- `--tab vocus`：指定 Google Sheets 分頁
- `--top-k 15`：最終保留的相關 Q&A 數量
- `--weeks 2`：解析最近 N 週指標
- `--output path/to/report.md`：指定輸出檔案路徑
- `--snapshot path/to/snapshot.json`：直接從 metrics snapshot 生成
- `--no-qa`：跳過知識庫檢索
- `--no-cache`：跳過報告 cache，強制重新生成
- `--check`：只做 preflight，不實際生成

## 實際流程

1. Preflight 檢查：確認 `OPENAI_API_KEY`，以及在 QA 模式下檢查 Step 3 artifacts。
2. 解析 metrics：從 snapshot JSON、Google Sheets 或 TSV 載入指標。
3. 偵測異常：依月/週趨勢標記 `CORE`、`ALERT_DOWN`、`ALERT_UP`。
4. 搜尋 Q&A：
   - 優先載入持久化的 `qa_embeddings.npy`
   - 若 embeddings 與當前 query provider 維度不一致，Step 4 會記 warning，並在必要時暫時改用 local query embeddings 相容
   - 正式修復方式是重建 embeddings，不是長期依賴 fallback
5. Rerank 候選：用 OpenAI 從候選池選出最相關的 Q&A。
6. 生成 Markdown：用 OpenAI 根據 metrics summary 與 Q&A context 產生完整週報。
7. 寫檔與驗證：
   - 執行 `_validate_report()`
   - 寫入 `output/report_YYYYMMDD_<hash8>.md`
   - 更新 trend memory 與 artifact version registry

## Embeddings 維護

如果 Step 3 曾在沒有 OpenAI key 的情況下產生 256 維 local embeddings，而現在 Step 4 用的是 1536 維 OpenAI embeddings，建議先重建：

```bash
.venv/bin/python scripts/03_dedupe_classify.py --rebuild-embeddings
```

重建後，`qa_embeddings.npy` 應與目前 provider 維度一致。這次正常狀態應是 `1869 x 1536`。

## 輸出與驗證

- 預設檔名：`output/report_YYYYMMDD_<hash8>.md`
- 若指定 `--output`，會直接寫到指定路徑
- 成功時終端會印出最終報告路徑與版本記錄 ID

### Report meta（前端顯示副標的關鍵）

報告**必須**在檔尾 append `<!-- report_meta {...} -->` HTML 註解，否則前端列表只會顯示 date + hash + KB，**不會出現「週報/雙週報」label、生成方式、模型**等副標。

腳本生成時自動 append；**Claude Code as LLM 模式（手動撰寫）時不可遺漏**。位置在 citations 區塊之後：

```
<!-- citations [...] -->

<!-- report_meta {"weeks":1,"generated_at":"2026-04-27T03:36:23.000Z","generation_mode":"claude-code","generation_label":"Claude Code 語意推理","model":null} -->
```

欄位定義：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `weeks` | number | 1 = 週報、2 = 雙週報 |
| `generated_at` | ISO8601 | 生成時間 |
| `generation_mode` | string | `"claude-code"` / `"openai"` / `"template"` |
| `generation_label` | string | 顯示用標籤：`"Claude Code 語意推理"` / `"OpenAI 生成"` |
| `model` | string \| null | OpenAI 模式填 `"gpt-5.4"`，Claude Code 模式填 `null` |
| `snapshot_id` | string? | 對應 `output/metrics_snapshots/<id>.json`（選填）|
| `experiment_tag` | string? | autoresearch 實驗標籤（選填）|

驗證：`grep -c "report_meta" output/report_*.md` 應 = 1，缺者用 force-sync 補上後重推。

## 常見問題

### 1. `OPENAI_API_KEY` 未設定

Step 4 腳本路徑（`scripts/04_generate_report.py`）強制要求 OPENAI_API_KEY。

但本 skill 也支援「**Claude Code as LLM 模式**」——當 OPENAI_API_KEY 未設定時，由 Claude Code 直接做語意推理組稿（不呼叫任何外部 LLM API），詳見下方「Claude Code as LLM 模式」章節。

### 2. `size 256 is different from 1536`

這表示 `qa_embeddings.npy` 和當前 query embedding provider 維度不一致。先執行：

```bash
.venv/bin/python scripts/03_dedupe_classify.py --rebuild-embeddings
```

### 3. 想快速確認依賴是否就緒

```bash
.venv/bin/python scripts/04_generate_report.py --check
```

會檢查 `OPENAI_API_KEY` 與 Step 4 需要的 artifacts，不實際生成報告。

---

## Claude Code as LLM 模式

當 `.env` 沒有 OPENAI_API_KEY、但仍要產出週報時，由 Claude Code 直接當語意判斷引擎，不呼叫任何外部 LLM API。WebFetch / WebSearch 是 built-in tools，不算外部 LLM 呼叫。

跨 session 一致狀態：4/20、4/27、5/1 三次週報均走此模式（`.env` 第 7 / 9 行 OPENAI_API_KEY 持續被註解）。

### 流程

1. **抓 metrics**：
   ```bash
   .venv/bin/python scripts/qa_tools.py load-metrics --source "<URL>" --tab vocus --json
   ```
   解析輸出時注意：含 stderr-like header 兩行（`Mode: ...` 與 `從 Google Sheets 下載：...`），用 `re.search(r'^\{', text, re.MULTILINE)` 找 JSON 起點。

2. **異常分群**：純 Python 排序 weekly delta，按 CORE / ALERT_DOWN / ALERT_UP 分組，top-30 整理為「現象→原因→行動→依據」。

3. **KB 搜尋**：
   ```bash
   .venv/bin/python scripts/qa_tools.py search --query "<主題>" --top-k 3
   ```
   多輪查詢萃取 30+ citations，無 OpenAI 限制。

4. **直接組稿**：對齊既有報告 7 段結構（情勢 / 流量 / 技術 / 意圖 / 跨週 / 行動 / 來源）。

5. **必補 report_meta**：
   ```
   <!-- report_meta {"weeks":1,"generated_at":"<ISO8601>","generation_mode":"claude-code","generation_label":"Claude Code 語意推理","model":null} -->
   ```
   遺漏會導致前端列表 subtitle 顯示異常。

### 與 OpenAI 模式的範圍差異

| 項目 | OpenAI 模式 | Claude Code as LLM 模式 |
|------|------------|----------------------|
| Off-page Authority 指標（DA/DR/AS/TF/CF/MT/AI Visibility） | 不含 | **不含**（屬 `/meeting-prep` S6/S7 範疇，月度追蹤，避免稀釋週訊號） |
| Health Score 計算 | LLM 自評 | 透明化算式（accumulating 累進式） |
| Citation 編號 | 自動分配 | 跨週 trace 保留跳號（避免重編） |
| 因果歸因 | 單一假設 | 多假設並列（給人工核查空間） |

> **設計原則**：authority metrics（DA/DR/AS）變化緩慢（月度級別），加進週報會稀釋訊號。週報專注 GSC + GA4 內部數據；外部權威指標由 `/meeting-prep` 在 S6/S7 評分依據中引用，並寫入 `data/off-page-authority.jsonl` 跨週追蹤。
