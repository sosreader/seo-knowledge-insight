# Autoresearch: Meeting-Prep 品質自主優化

## Context

Meeting-Prep eval 已從 30 指標擴增至 35 指標（+5 coherence），鑑別度從「全部 1.0」改善至「0.37-1.0 分佈」。Rule-based composite baseline = 0.831（4 golden fixtures 平均）。

現在要建立 autoresearch loop，讓 Claude Code 自主修改 `meeting-prep.md` prompt → 生成報告 → eval → keep/discard，持續迭代提升 composite 分數。

**與 report autoresearch 的關鍵差異**：
- Meeting-prep 有 web research（非確定性）→ 用 `--report` 模式跳過
- Eval 有 5 層但 L3 需要 LLM 自評 → autoresearch 只用 rule-based（L1+L2+L2.5+L4）
- 生成時間較長（~3-5 分鐘 vs report ~2 分鐘）

**迭代空間**（低分指標 = 改善目標）：

| 指標 | 當前 | 目標 | prompt 可控性 |
|------|------|------|-------------|
| `cross_section_coherence` | 0.50 | 0.80 | 高：要求 S3 heading 包含 S1 alert 名稱 |
| `action_specificity` | 0.37 | 0.70 | 高：要求 S10 每項有工具名+動詞 |
| `hypothesis_falsifiability` | 0.82 | 0.90 | 中：已接近飽和 |
| `s2_content_density` | 0.75 | 0.90 | 高：要求 S2 有更多內容行 |
| `source_diversity` | 0.80 | 1.0 | 中：受 web research 結果限制 |

---

## 實作內容

### 1. 建立 `autoresearch/meeting-prep/program.md`

**新增檔案**，遵循 `autoresearch/report/program.md` 的驗證過的 14 步 loop 結構。

關鍵差異：

| 項目 | Report Autoresearch | Meeting-Prep Autoresearch |
|------|-------------------|--------------------------|
| 修改目標 | `.claude/commands/generate-report.md` | `.claude/commands/meeting-prep.md` |
| 生成模式 | snapshot → 報告 | **`--report` 模式**（固定週報輸入，跳過 web research） |
| 輸入輪替 | snapshot rotation | **週報 rotation**（4 份 golden fixture 對應的週報） |
| Eval | `autoresearch/report/eval_local.py` | `autoresearch/meeting-prep/eval_local.py` |
| Composite | `REPORT_COMPOSITE` | `MEETING_PREP_COMPOSITE` |
| Baseline | 0.6383 | 0.8305 |

**輸入來源**：用 `--report` 模式讀取已存在的週報（非 live snapshot），確保確定性：
```
eval/fixtures/meeting_prep/meeting_prep_20260306_ea576a4f.md → 對應週報
eval/fixtures/meeting_prep/meeting_prep_20260220_25caf520.md → 對應週報
...
```

**問題**：`--report` 模式仍會跑 web research（Step B）。需在 program.md 中指示跳過 B 或 mock。
**解法**：autoresearch loop 直接生成報告（Claude 本身是 LLM），不透過 `/meeting-prep` 指令。直接讀取週報 → 執行 Step A（萃取 alerts）→ Step C-E（KB search + 推理生成 11 sections）→ 跳過 Step B（web research）。Web research 結果對 rule-based eval 的影響僅限 L4（`s2_content_density`, `source_diversity`, `date_freshness_rate`），佔 composite 25%。**可在 S2 中放固定的業界動態模板**以確保 L4 不歸零。

### 2. 建立支援檔案

| 檔案 | 內容 |
|------|------|
| `autoresearch/meeting-prep/program.md` | 14 步 loop 定義（新增） |
| `autoresearch/meeting-prep/results.tsv` | TSV header（新增） |
| `autoresearch/meeting-prep/experiment_log.md` | 實驗紀錄模板（新增） |
| `autoresearch/meeting-prep/snapshots.md` | 可用週報 + fixture registry（新增） |
| `autoresearch/meeting-prep/reports/` | 生成報告目錄（mkdir） |
| `autoresearch/meeting-prep/eval_local.py` | **已存在** |
| `autoresearch/meeting-prep/baseline.json` | **已存在** |

### 3. `program.md` 核心結構

```markdown
# autoresearch: Meeting-Prep Quality Optimization

## 你只能修改：`.claude/commands/meeting-prep.md`

## 你不能修改：eval_local.py, baseline.json, evals/*, eval/golden_*, api/*, test files

## The experiment loop (LOOP FOREVER)

1. Read results.tsv + experiment_log.md
2. Read .claude/commands/meeting-prep.md (only sections you plan to modify)
3. Choose ONE hypothesis
4. Modify meeting-prep.md → git commit → record hash
5. Select input: round % 4 → rotate through 4 golden fixture reports
   (用 --report 模式的對應週報路徑)
6. Extract ALERT_DOWN from selected fixture
7. Generate meeting-prep report:
   - Skip Step B (web research) — 用固定 S2 模板
   - Execute Step A, C, D, E as normal
   - Write to autoresearch/meeting-prep/reports/<round>_<fixture_id>_pending_<hash>.md
8. Run eval:
   python autoresearch/meeting-prep/eval_local.py \
     --report autoresearch/meeting-prep/reports/<file>
9. Parse: MEETING_PREP_COMPOSITE=X.XXXXXX
10. Compare: DELTA = current - best_keep_in_TSV
11. DELTA > 0 → keep; DELTA ≤ 0 → discard + revert
12. Rename _pending_ → _keep_/_discard_
13. Append results.tsv + experiment_log.md
14. Go back to 1

## Diagnostic hints
| Metric | Adjust in meeting-prep.md |
|--------|--------------------------|
| cross_section_coherence < 0.6 | S3 heading 必須包含 S1 alert 指標名稱 |
| action_specificity < 0.5 | S10 每項要求工具名(GSC/Ahrefs/...) + 動作動詞 |
| hypothesis_falsifiability < 0.8 | S3 每假設加「可驗證/需人工確認/需顧問判斷」標籤 |
| s2_content_density < 0.7 | S2 要求每個子 section ≥3 行內容 |
| citation_relevance < 0.7 | 引用 KB 時確保 category 與 section 主題一致 |

## NEVER STOP — 人類不在，你是自主的
## Context management — compact every 5 rounds
```

### 4. `results.tsv` Header

```
timestamp	composite	l1_avg	l2g_avg	l2c_cross_section	l2c_action_spec	l2c_hypo_falsif	l2c_temporal	l2c_citation_rel	l4_avg	fixture_id	git_hash	status	description
```

### 5. `snapshots.md`（可用的輸入 fixture）

列出 4 份 golden meeting-prep fixture + 對應的原始週報路徑（用於 `--report` 模式），標記哪些可用。

---

## 修改檔案清單

| 檔案 | 動作 | 說明 |
|------|------|------|
| `autoresearch/meeting-prep/program.md` | **新增** | 14 步 loop 定義（~170 行） |
| `autoresearch/meeting-prep/results.tsv` | **新增** | TSV header（1 行） |
| `autoresearch/meeting-prep/experiment_log.md` | **新增** | 紀錄模板（~20 行） |
| `autoresearch/meeting-prep/snapshots.md` | **新增** | 4 fixture registry（~20 行） |
| `Makefile` | 修改 | 新增 `autoresearch-meeting-prep-baseline` target（已完成） |

**不修改**：`eval_local.py`、`baseline.json`、`meeting-prep.md`（loop 才會改）

---

## Verification

```bash
# 1. 確認 eval_local.py 能跑
make autoresearch-meeting-prep-baseline
# 期望：MEETING_PREP_COMPOSITE=0.809549

# 2. 確認 program.md 結構完整
cat autoresearch/meeting-prep/program.md | head -5
# 期望：# autoresearch: Meeting-Prep Quality Optimization

# 3. 確認 TSV header
head -1 autoresearch/meeting-prep/results.tsv
# 期望：timestamp\tcomposite\t...

# 4. 確認 snapshots.md 列出 4 個 fixture
grep "✓" autoresearch/meeting-prep/snapshots.md | wc -l
# 期望：4

# 5. 確認 reports 目錄存在
ls -d autoresearch/meeting-prep/reports/
```

啟動 autoresearch loop：
```bash
# 建立實驗分支
git checkout -b autoresearch/meeting-prep-mar22

# 讀取 program.md 開始 loop
# Claude Code 自主循環
```
