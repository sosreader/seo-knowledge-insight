#!/usr/bin/env python3
"""
qa_tools.py — Claude Code 友善的 Q&A 知識庫輕量 CLI

不需要 OpenAI API 即可執行所有資料查詢與操作。
作為 Claude Code Slash Commands 的資料介面（Layer 2）。

子命令：
  pipeline-status        顯示 pipeline 各步驟狀態
  list-unprocessed       列出待 Q&A 萃取的 Markdown 檔
  list-needs-review      列出 needs_review=true 的 merged Q&A
  merge-qa               合併 per-meeting JSON → qa_all_raw.json
  add-meeting            增量加入新會議 Q&A（情境 A）
  fix-meeting            目標性刪除/標記異常會議的 Q&A（情境 B）
  diff-snapshot          與快照比對，列出新增/刪除/變更的 Q&A
  search                 關鍵字搜尋知識庫（無 OpenAI）
  load-metrics           從 Google Sheets / TSV 解析 SEO 指標
  eval-compare           跨 provider eval 結果比較表
  eval-sample            從 qa_final.json 抽樣 N 筆 Q&A（供 Claude Code 評估）
  eval-retrieval-local   規則式 Retrieval 評估（KW/MRR/Cat，無 OpenAI）
  eval-save              儲存 Claude Code 評估結果（版本化 JSON）

用法範例：
    python scripts/qa_tools.py pipeline-status
    python scripts/qa_tools.py search --query "canonical"
    python scripts/qa_tools.py load-metrics --source "https://docs.google.com/..."
    python scripts/qa_tools.py eval-compare
    python scripts/qa_tools.py eval-sample --size 20 --seed 42 --with-golden
    python scripts/qa_tools.py eval-retrieval-local
    python scripts/qa_tools.py eval-save --input result.json --extraction-engine claude-code
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

# 禁止 import config：避免 _require_env("OPENAI_API_KEY") 在啟動時觸發
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
RAW_MD_DIR = PROJECT_ROOT / "raw_data" / "markdown"
QA_PER_MEETING_DIR = OUTPUT_DIR / "qa_per_meeting"
QA_FINAL_PATH = OUTPUT_DIR / "qa_final.json"
QA_RAW_PATH = OUTPUT_DIR / "qa_all_raw.json"
EVALS_DIR = OUTPUT_DIR / "evals"
EVAL_BASELINE_PATH = OUTPUT_DIR / "eval_baseline.json"
EVAL_SAMPLE_PATH = OUTPUT_DIR / "eval_sample.json"
SNAPSHOTS_DIR = OUTPUT_DIR / "snapshots"
EVAL_DIR = PROJECT_ROOT / "eval"
GOLDEN_QA_PATH = EVAL_DIR / "golden_qa.json"
GOLDEN_RETRIEVAL_PATH = EVAL_DIR / "golden_retrieval.json"


# ──────────────────────────────────────────────────────
# 共用工具
# ──────────────────────────────────────────────────────

def _load_qa_final() -> list[dict]:
    """載入 qa_final.json，回傳 qa_database 清單。"""
    if not QA_FINAL_PATH.exists():
        print(f"qa_final.json 不存在：{QA_FINAL_PATH}", file=sys.stderr)
        return []
    try:
        data = json.loads(QA_FINAL_PATH.read_text(encoding="utf-8"))
        return data.get("qa_database", [])
    except (json.JSONDecodeError, KeyError) as e:
        print(f"qa_final.json 格式錯誤：{e}", file=sys.stderr)
        return []


def _write_atomic(path: Path, data: dict) -> None:
    """Atomic write：先寫 .tmp，再 rename，避免中途失敗導致資料損毀。"""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# ──────────────────────────────────────────────────────
# pipeline-status / list-unprocessed
# ──────────────────────────────────────────────────────

def cmd_pipeline_status(_args: argparse.Namespace) -> None:
    """顯示完整 pipeline 狀態（委派給 list_pipeline_state.py）。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.list_pipeline_state import show_full_status
    show_full_status()


def cmd_list_unprocessed(_args: argparse.Namespace) -> None:
    """列出待 Q&A 萃取的 Markdown 檔（委派給 list_pipeline_state.py）。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.list_pipeline_state import list_unprocessed_extract_qa
    list_unprocessed_extract_qa()


# ──────────────────────────────────────────────────────
# list-needs-review
# ──────────────────────────────────────────────────────

def cmd_list_needs_review(_args: argparse.Namespace) -> None:
    """列出 needs_review=true 的 merged Q&A（fix-meeting 執行後生成）。"""
    qas = _load_qa_final()
    if not qas:
        return

    candidates = [qa for qa in qas if qa.get("needs_review") is True]
    if not candidates:
        print("沒有需要複審的 Q&A。")
        return

    print(f"需要複審的 merged Q&A（共 {len(candidates)} 筆）：\n")
    for qa in candidates:
        sid = qa.get("stable_id", qa.get("id", "?"))
        print(f"  [{sid}] {qa['question'][:80]}")
        sources = qa.get("merged_from", [])
        for src in sources:
            sf = src.get("source_file", src.get("source_title", ""))
            print(f"         來源：{sf}")
    print()
    print("建議：逐一確認後將 needs_review 設為 false，或重新執行 /dedupe-classify。")


# ──────────────────────────────────────────────────────
# merge-qa
# ──────────────────────────────────────────────────────

def cmd_merge_qa(_args: argparse.Namespace) -> None:
    """合併 per-meeting JSON → qa_all_raw.json（委派給 list_pipeline_state.py）。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.list_pipeline_state import merge_per_meeting_jsons
    merge_per_meeting_jsons()


# ──────────────────────────────────────────────────────
# add-meeting（情境 A：增量加入新會議）
# ──────────────────────────────────────────────────────

def cmd_add_meeting(args: argparse.Namespace) -> None:
    """
    增量加入新會議 Q&A 到 qa_final.json。

    流程：
      1. 載入新 meeting JSON（--file 指定路徑）
      2. 檢查 stable_id 是否已存在（exact match）
      3. 以關鍵字粗篩可能重複的候選（供 Claude Code 判斷）
      4. 新增非重複項，輸出操作摘要

    LLM 合併判斷由 Claude Code 負責（qa_tools.py 只做 I/O）。
    """
    src_path = Path(args.file)
    if not src_path.exists():
        print(f"檔案不存在：{src_path}", file=sys.stderr)
        sys.exit(1)

    try:
        new_data = json.loads(src_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"JSON 格式錯誤：{e}", file=sys.stderr)
        sys.exit(1)

    new_qas: list[dict] = new_data.get("qa_pairs", new_data.get("qa_database", []))
    if not new_qas:
        print("來源檔案沒有 Q&A 資料（qa_pairs 或 qa_database）。")
        return

    existing = _load_qa_final()
    existing_ids = {qa.get("stable_id") for qa in existing if qa.get("stable_id")}

    duplicates: list[dict] = []
    to_add: list[dict] = []

    for qa in new_qas:
        sid = qa.get("stable_id")
        if sid and sid in existing_ids:
            duplicates.append(qa)
        else:
            to_add.append(qa)

    print(f"新會議 Q&A：{len(new_qas)} 筆")
    print(f"  exact 重複（stable_id 相同）：{len(duplicates)} 筆，跳過")
    print(f"  待加入：{len(to_add)} 筆")

    if not to_add:
        print("沒有新 Q&A 需要加入。")
        return

    # 列出可能相似的候選（關鍵字重疊，供 Claude Code 確認）
    _print_similar_candidates(to_add, existing)

    # 更新 qa_final.json
    if not QA_FINAL_PATH.exists():
        print("qa_final.json 不存在，請先執行 dedupe-classify 產生基底。")
        sys.exit(1)

    existing_data = json.loads(QA_FINAL_PATH.read_text(encoding="utf-8"))
    existing_db: list[dict] = existing_data.get("qa_database", [])
    max_id = max((qa.get("id", 0) for qa in existing_db), default=0)
    to_add_with_id = [{**qa, "id": max_id + i} for i, qa in enumerate(to_add, start=1)]
    new_db = existing_db + to_add_with_id
    _write_atomic(QA_FINAL_PATH, {**existing_data, "qa_database": new_db, "total_count": len(new_db), "last_updated": datetime.now().strftime("%Y-%m-%d")})
    print(f"\n已新增 {len(to_add_with_id)} 筆 Q&A 到 qa_final.json（總計 {len(new_db)} 筆）。")
    print("建議執行 /evaluate-qa 驗證品質，或 /dedupe-classify 重新去重。")


def _print_similar_candidates(
    new_qas: list[dict], existing: list[dict], top: int = 5
) -> None:
    """以關鍵字粗篩可能相似的 Q&A（供 Claude Code 確認是否合併）。"""
    candidates: list[tuple[dict, dict, int]] = []  # (new, existing, overlap)
    for new_qa in new_qas:
        new_kws = set(kw.lower() for kw in new_qa.get("keywords", []))
        new_tokens = set(new_qa.get("question", "").lower().split())
        for ex_qa in existing:
            ex_kws = set(kw.lower() for kw in ex_qa.get("keywords", []))
            ex_tokens = set(ex_qa.get("question", "").lower().split())
            overlap = len((new_kws | new_tokens) & (ex_kws | ex_tokens))
            if overlap >= 2:
                candidates.append((new_qa, ex_qa, overlap))

    if not candidates:
        return

    candidates.sort(key=lambda x: -x[2])
    print(f"\n可能相似的 Q&A（關鍵字重疊，Claude Code 請判斷是否合併，最多顯示 {top} 組）：")
    for new_qa, ex_qa, overlap in candidates[:top]:
        print(f"  [新增] {new_qa.get('question', '')[:60]}")
        print(f"  [現有] {ex_qa.get('question', '')[:60]}  (重疊 token: {overlap})")
        print()


# ──────────────────────────────────────────────────────
# fix-meeting（情境 B：目標性替換異常會議）
# ──────────────────────────────────────────────────────

def cmd_fix_meeting(args: argparse.Namespace) -> None:
    """
    目標性刪除/標記異常會議的 Q&A。

    --source-file <filename> 指定來源檔（如 meeting_20240115.md）：
      - is_merged=false 且 source_file 匹配 → 刪除
      - is_merged=true 且 source_file 在 merged_from 中 → 標記 needs_review=true

    --dry-run：只列出將受影響的 Q&A，不寫入
    """
    source_file = args.source_file
    dry_run = getattr(args, "dry_run", False)

    qas = _load_qa_final()
    if not qas:
        sys.exit(1)

    to_delete: list[dict] = []
    to_flag: list[dict] = []
    unchanged: list[dict] = []

    for qa in qas:
        sf = qa.get("source_file", "")
        is_merged = qa.get("is_merged", False)
        merged_from: list[dict] = qa.get("merged_from", [])
        in_merged_from = any(
            src.get("source_file", "") == source_file for src in merged_from
        )

        if not is_merged and sf == source_file:
            to_delete.append(qa)
        elif is_merged and in_merged_from:
            to_flag.append(qa)
        else:
            unchanged.append(qa)

    print(f"來源檔案：{source_file}")
    print(f"  刪除（is_merged=false）：{len(to_delete)} 筆")
    for qa in to_delete:
        print(f"    [{qa.get('stable_id', qa.get('id', '?'))}] {qa['question'][:60]}")
    print(f"  標記複審（is_merged=true）：{len(to_flag)} 筆")
    for qa in to_flag:
        print(f"    [{qa.get('stable_id', qa.get('id', '?'))}] {qa['question'][:60]}")
    print(f"  不受影響：{len(unchanged)} 筆")

    if dry_run:
        print("\n（dry-run 模式，未寫入）")
        return

    if not to_delete and not to_flag:
        print("\n沒有需要處理的 Q&A。")
        return

    flagged = [{**qa, "needs_review": True} for qa in to_flag]
    new_db = unchanged + flagged
    existing_data = json.loads(QA_FINAL_PATH.read_text(encoding="utf-8"))
    _write_atomic(QA_FINAL_PATH, {**existing_data, "qa_database": new_db, "total_count": len(new_db), "last_updated": datetime.now().strftime("%Y-%m-%d")})
    print(f"\n完成：刪除 {len(to_delete)} 筆，標記 {len(to_flag)} 筆為 needs_review。")
    print("執行 list-needs-review 可查看待複審清單。")


# ──────────────────────────────────────────────────────
# diff-snapshot
# ──────────────────────────────────────────────────────

def cmd_diff_snapshot(args: argparse.Namespace) -> None:
    """與快照比對，列出新增/刪除的 stable_id 集合。"""
    before_path = Path(args.before)
    if not before_path.exists():
        print(f"快照不存在：{before_path}", file=sys.stderr)
        sys.exit(1)

    before_data = json.loads(before_path.read_text(encoding="utf-8"))
    before_ids = {
        qa.get("stable_id") for qa in before_data.get("qa_database", [])
        if qa.get("stable_id")
    }

    current = _load_qa_final()
    current_ids = {qa.get("stable_id") for qa in current if qa.get("stable_id")}

    added = current_ids - before_ids
    removed = before_ids - current_ids

    print(f"快照比對：{before_path.name} → qa_final.json")
    print(f"  新增：{len(added)} 筆")
    for sid in sorted(added):
        qa = next((q for q in current if q.get("stable_id") == sid), {})
        print(f"    + {sid}  {qa.get('question', '')[:50]}")
    print(f"  刪除：{len(removed)} 筆")
    for sid in sorted(removed):
        qa = next((q for q in before_data.get("qa_database", []) if q.get("stable_id") == sid), {})
        print(f"    - {sid}  {qa.get('question', '')[:50]}")


# ──────────────────────────────────────────────────────
# search（關鍵字搜尋，無 OpenAI）
# ──────────────────────────────────────────────────────

def cmd_search(args: argparse.Namespace) -> None:
    """
    關鍵字搜尋知識庫（無 OpenAI）。

    評分：query token 與 question/answer/keywords 的重疊數，加權：
      keywords 命中 ×3 / question 命中 ×2 / answer 命中 ×1
    """
    query = args.query
    top_k = args.top_k
    category = getattr(args, "category", None)

    qas = _load_qa_final()
    if not qas:
        sys.exit(1)

    tokens = set(query.lower().split())
    scored: list[tuple[dict, float]] = []

    for qa in qas:
        if category and qa.get("category") != category:
            continue
        kw_tokens = set(kw.lower() for kw in qa.get("keywords", []))
        q_tokens = set(qa.get("question", "").lower().split())
        a_tokens = set(qa.get("answer", "").lower().split())
        score = (
            len(tokens & kw_tokens) * 3
            + len(tokens & q_tokens) * 2
            + len(tokens & a_tokens) * 1
        )
        if score > 0:
            scored.append((qa, float(score)))

    results = sorted(scored, key=lambda x: -x[1])[:top_k]

    if not results:
        print(f"沒有找到與 '{query}' 相關的 Q&A。")
        return

    print(f"搜尋：'{query}'  找到 {len(results)} 筆（top {top_k}）\n")
    for rank, (qa, score) in enumerate(results, 1):
        sid = qa.get("stable_id", qa.get("id", "?"))
        cat = qa.get("category", "")
        diff = qa.get("difficulty", "")
        print(f"[{rank}] score={score:.0f}  [{cat}]{diff}  id={sid}")
        print(f"     Q: {qa['question']}")
        print(f"     A: {qa['answer'][:200]}{'...' if len(qa['answer']) > 200 else ''}")
        print(f"     來源：{qa.get('source_title', '')} ({qa.get('source_date', '')})")
        print()


# ──────────────────────────────────────────────────────
# load-metrics
# ──────────────────────────────────────────────────────

def cmd_load_metrics(args: argparse.Namespace) -> None:
    """
    從 Google Sheets URL 或本機 TSV 解析 SEO 指標。
    輸出異常指標清單（供 Claude Code 生成週報）。
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    from utils.metrics_parser import fetch_from_sheets, parse_metrics_tsv, detect_anomalies

    source = args.source
    tab = getattr(args, "tab", "vocus")

    if source.startswith("http"):
        print(f"從 Google Sheets 下載：{source[:60]}...")
        raw_tsv = fetch_from_sheets(source, tab=tab)
    else:
        src_path = Path(source)
        if not src_path.exists():
            print(f"檔案不存在：{src_path}", file=sys.stderr)
            sys.exit(1)
        raw_tsv = src_path.read_text(encoding="utf-8")

    metrics = parse_metrics_tsv(raw_tsv)
    anomalies = detect_anomalies(metrics)

    print(f"解析完成：{len(metrics)} 個指標，{len(anomalies)} 個關注指標\n")
    for a in anomalies:
        flag = a.get("flag", "")
        name = a.get("name", "")
        monthly = a.get("monthly")
        weekly = a.get("weekly")
        monthly_str = f"{monthly*100:+.1f}%" if isinstance(monthly, float) else "N/A"
        weekly_str = f"{weekly*100:+.1f}%" if isinstance(weekly, float) else "N/A"
        print(f"  [{flag:10s}] {name:<30s}  月: {monthly_str:>8s}  週: {weekly_str:>8s}")


# ──────────────────────────────────────────────────────
# eval-compare
# ──────────────────────────────────────────────────────

def cmd_eval_compare(_args: argparse.Namespace) -> None:
    """掃描 output/evals/*.json，輸出跨 provider eval 比較表。"""
    if not EVALS_DIR.exists():
        print("output/evals/ 目錄不存在，尚未有 eval 結果。")
        return

    runs: list[dict] = []
    for path in sorted(EVALS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_filename"] = path.stem
            runs.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    baseline: dict = {}
    if EVAL_BASELINE_PATH.exists():
        try:
            baseline = json.loads(EVAL_BASELINE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    dims = ["relevance", "accuracy", "completeness", "granularity"]

    def _avg(scores: dict) -> float:
        vals = [scores.get(d, 0.0) for d in dims]
        return sum(vals) / len(vals) if vals else 0.0

    # 表頭
    header = f"{'版本':<30s} {'provider':<10s} {'引擎':<14s} {'avg':>5s} {'rel':>5s} {'acc':>5s} {'comp':>5s} {'gran':>5s} {'KW%':>6s}"
    print("Eval 比較報告\n")
    print(header)
    print("─" * len(header))

    # Baseline 行
    if baseline:
        bs = baseline.get("generation", baseline.get("scores", {}))
        br = baseline.get("retrieval", {})
        provider = baseline.get("provider", baseline.get("extraction_engine", "openai"))
        model = baseline.get("model", "")
        avg = _avg(bs)
        kw = br.get("kw_hit_rate", float("nan"))
        kw_str = f"{kw:.0%}" if isinstance(kw, float) else "N/A"
        print(
            f"{'* BASELINE (' + baseline.get('date', '') + ')':<30s} {provider:<10s} {model:<14s}"
            f" {avg:>5.2f} {bs.get('relevance', 0):>5.2f} {bs.get('accuracy', 0):>5.2f}"
            f" {bs.get('completeness', 0):>5.2f} {bs.get('granularity', 0):>5.2f} {kw_str:>6s}"
        )

    for run in runs:
        scores = run.get("scores", run.get("generation", {}))
        retrieval = run.get("retrieval", {})
        avg = _avg(scores)
        kw = retrieval.get("kw_hit_rate", float("nan"))
        kw_str = f"{kw:.0%}" if isinstance(kw, float) else "N/A"
        provider = run.get("provider", run.get("extraction_engine", "openai"))
        model = run.get("model", "")
        label = run.get("_filename", "?")[:30]
        print(
            f"  {label:<28s} {provider:<10s} {model:<14s}"
            f" {avg:>5.2f} {scores.get('relevance', 0):>5.2f} {scores.get('accuracy', 0):>5.2f}"
            f" {scores.get('completeness', 0):>5.2f} {scores.get('granularity', 0):>5.2f} {kw_str:>6s}"
        )

    print("\n* = 受保護的基準線，需 --update-baseline 且平均分 +0.05 以上才能覆寫。")


# ──────────────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="qa_tools.py — Claude Code Q&A 知識庫輕量 CLI（無需 OpenAI）"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("pipeline-status", help="顯示 pipeline 各步驟狀態")
    sub.add_parser("list-unprocessed", help="列出待萃取的 Markdown 檔")
    sub.add_parser("list-needs-review", help="列出 needs_review=true 的 merged Q&A")
    sub.add_parser("merge-qa", help="合併 per-meeting JSON → qa_all_raw.json")

    p_add = sub.add_parser("add-meeting", help="增量加入新會議 Q&A（情境 A）")
    p_add.add_argument("--file", required=True, help="新會議 Q&A JSON 路徑")

    p_fix = sub.add_parser("fix-meeting", help="目標性替換異常會議 Q&A（情境 B）")
    p_fix.add_argument("--source-file", required=True, help="來源檔名（如 meeting_20240115.md）")
    p_fix.add_argument("--dry-run", action="store_true", help="只列出影響範圍，不寫入")

    p_diff = sub.add_parser("diff-snapshot", help="與快照比對")
    p_diff.add_argument("--before", required=True, help="快照 JSON 路徑（output/snapshots/...）")

    p_search = sub.add_parser("search", help="關鍵字搜尋知識庫（無 OpenAI）")
    p_search.add_argument("--query", required=True, help="搜尋字串")
    p_search.add_argument("--top-k", type=int, default=5, help="回傳筆數（預設 5）")
    p_search.add_argument("--category", help="限定 category")

    p_metrics = sub.add_parser("load-metrics", help="從 Sheets / TSV 解析 SEO 指標")
    p_metrics.add_argument("--source", required=True, help="Google Sheets URL 或 TSV 路徑")
    p_metrics.add_argument("--tab", default="vocus", help="Sheets 分頁名稱（預設 vocus）")

    sub.add_parser("eval-compare", help="跨 provider eval 比較表")

    args = parser.parse_args()

    dispatch = {
        "pipeline-status":  cmd_pipeline_status,
        "list-unprocessed": cmd_list_unprocessed,
        "list-needs-review": cmd_list_needs_review,
        "merge-qa":         cmd_merge_qa,
        "add-meeting":      cmd_add_meeting,
        "fix-meeting":      cmd_fix_meeting,
        "diff-snapshot":    cmd_diff_snapshot,
        "search":           cmd_search,
        "load-metrics":     cmd_load_metrics,
        "eval-compare":     cmd_eval_compare,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
