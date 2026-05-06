#!/usr/bin/env python3
"""
qa_tools.py — Claude Code 友善的 Q&A 知識庫輕量 CLI（無需 OpenAI）

子命令一覽請執行 ``python scripts/qa_tools.py -h``。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 禁止 import config：避免 _require_env("OPENAI_API_KEY") 在啟動時觸發
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_local_capabilities() -> dict:
    """Inline capability detection (no openai_helper import).

    llm is always "claude-code" — this CLI is designed for slash commands
    where Claude Code itself acts as the LLM engine. OPENAI_API_KEY
    availability does not change this tool's LLM context.
    """
    has_supabase = bool(
        os.getenv("SUPABASE_URL", "").strip()
        and os.getenv("SUPABASE_ANON_KEY", "").strip()
    )
    return {
        "runtime": "cli",
        "llm": "claude-code",
        "store": "supabase" if has_supabase else "file",
        "agent": "disabled",
    }


def _print_capabilities() -> None:
    """Print mode line to stderr."""
    caps = _get_local_capabilities()
    parts = [f"{k}:{v}" for k, v in caps.items()]
    print(f"Mode: [{' | '.join(parts)}]", file=sys.stderr)

# 載入 .env（config.py 不被 import，需手動載入以取得 LMNR_PROJECT_API_KEY 等）
from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

# Laminar observability（safe no-op if lmnr not installed）
sys.path.insert(0, str(PROJECT_ROOT))
from utils.observability import init_laminar, flush_laminar, observe  # noqa: E402
from utils.laminar_scoring import score_event  # noqa: E402
from utils.synonym_dict import expand_query_tokens  # noqa: E402
from utils.execution_log import log_execution  # noqa: E402


class CLIError(Exception):
    """Non-zero exit with a message already printed to stderr."""

    def __init__(self, code: int = 1):
        self.code = code


OUTPUT_DIR = PROJECT_ROOT / "output"
RAW_MD_DIR = PROJECT_ROOT / "raw_data" / "markdown"
QA_PER_MEETING_DIR = OUTPUT_DIR / "qa_per_meeting"
QA_FINAL_PATH = OUTPUT_DIR / "qa_final.json"
QA_RAW_PATH = OUTPUT_DIR / "qa_all_raw.json"
QA_ENRICHED_PATH = OUTPUT_DIR / "qa_enriched.json"
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
    except (json.JSONDecodeError, KeyError, OSError) as e:
        print(f"qa_final.json 讀取失敗：{e}", file=sys.stderr)
        return []


def _load_qa_enriched() -> list[dict]:
    """載入 qa_enriched.json，回傳 qa_database 清單（含 synonym / freshness enrichment）。"""
    if not QA_ENRICHED_PATH.exists():
        print(f"qa_enriched.json 不存在：{QA_ENRICHED_PATH}", file=sys.stderr)
        return []
    try:
        data = json.loads(QA_ENRICHED_PATH.read_text(encoding="utf-8"))
        return data.get("qa_database", [])
    except (json.JSONDecodeError, KeyError, OSError) as e:
        print(f"qa_enriched.json 讀取失敗：{e}", file=sys.stderr)
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
    source_dir = getattr(_args, "source_dir", None)
    if source_dir:
        list_unprocessed_extract_qa([PROJECT_ROOT / source_dir])
        return
    list_unprocessed_extract_qa()


def cmd_list_unprocessed_names(_args: argparse.Namespace) -> None:
    """列出待處理檔名，方便喂給 --file。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.list_pipeline_state import _classify_extract_qa

    source_dir = getattr(_args, "source_dir", None)
    if source_dir:
        _, paths = _classify_extract_qa([PROJECT_ROOT / source_dir])
    else:
        _, paths = _classify_extract_qa()
    for path in paths:
        print(path.name)


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

@observe(name="qa_tools.merge_qa")
def cmd_merge_qa(_args: argparse.Namespace) -> None:
    """合併 per-meeting JSON → qa_all_raw.json（委派給 list_pipeline_state.py）。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.list_pipeline_state import merge_per_meeting_jsons
    merge_per_meeting_jsons()

    # 合併完成後補登 qa_all_raw.json 到 version registry
    if QA_RAW_PATH.exists():
        try:
            from utils.pipeline_version import register_existing_file
            entry = register_existing_file(step="extract-qa", file_path=QA_RAW_PATH)
            print(f"已補登 qa_all_raw.json 到 version registry：{entry['version_id']}")
        except Exception as exc:
            print(f"補登 version registry 失敗（非致命）：{exc}", file=sys.stderr)


# ──────────────────────────────────────────────────────
# register-version / version-history / label-version
# ──────────────────────────────────────────────────────

def cmd_register_version(args: argparse.Namespace) -> None:
    """將既有檔案補登入 version registry。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from utils.pipeline_version import register_existing_file

    file_path = Path(args.file) if args.file else None
    if file_path is None:
        print("請指定 --file 或讓系統自動偵測。", file=sys.stderr)
        sys.exit(1)

    try:
        entry = register_existing_file(
            step=args.step,
            file_path=file_path,
            label=args.label or None,
        )
        print(f"已登記：{entry['version_id']}")
        if entry.get("label"):
            print(f"標籤：{entry['label']}")
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


def cmd_version_history(args: argparse.Namespace) -> None:
    """顯示 version registry 歷史記錄。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from utils.pipeline_version import get_version_history, get_latest_version, STEP_NAMES

    step = args.step if args.step else None

    if step:
        try:
            history = get_version_history(step)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
        print(f"步驟 {step!r} 的版本歷史：")
        if not history:
            print("  （尚無記錄）")
        for entry in history:
            label = f" [{entry['label']}]" if entry.get("label") else ""
            ts = entry.get("timestamp", "")[:10]
            print(f"  {entry['version_id']}{label}  ({ts})")
    else:
        # 顯示所有步驟的最新版本
        print("所有步驟的最新版本：")
        for step_num, step_name in STEP_NAMES.items():
            latest = get_latest_version(step_num)
            if latest:
                label = f" [{latest['label']}]" if latest.get("label") else ""
                ts = latest.get("timestamp", "")[:10]
                print(f"  Step {step_num} ({step_name}): {latest['version_id']}{label}  ({ts})")
            else:
                print(f"  Step {step_num} ({step_name}): （尚無記錄）")


def cmd_label_version(args: argparse.Namespace) -> None:
    """為已登記的版本加上語意標籤。"""
    sys.path.insert(0, str(PROJECT_ROOT))
    from utils.pipeline_version import label_version

    result = label_version(args.version_id, args.label)
    if result is None:
        print(f"版本 {args.version_id!r} 不存在。", file=sys.stderr)
        sys.exit(1)
    print(f"已標記：{args.version_id} → {args.label!r}")


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

@observe(name="qa_tools.search")
def cmd_search(args: argparse.Namespace) -> None:
    """關鍵字搜尋知識庫（無 OpenAI）。"""
    _print_capabilities()
    query = args.query
    top_k = args.top_k
    category = getattr(args, "category", None)

    qas = _load_qa_final()
    if not qas:
        raise CLIError(1)

    pool = [qa for qa in qas if qa.get("category") == category] if category else qas
    results = _keyword_search(query, pool, top_k=top_k)

    if not results:
        print(f"沒有找到與 '{query}' 相關的 Q&A。")
        return

    score_event("results_count", float(len(results)))
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

@observe(name="qa_tools.load_metrics")
def cmd_load_metrics(args: argparse.Namespace) -> None:
    """
    從 Google Sheets URL 或本機 TSV 解析 SEO 指標。
    輸出異常指標清單（供 Claude Code 生成週報）。
    """
    _print_capabilities()
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
            raise CLIError(1)
        raw_tsv = src_path.read_text(encoding="utf-8")

    metrics = parse_metrics_tsv(raw_tsv)
    anomalies = detect_anomalies(metrics)

    if getattr(args, "json", False):
        output = {
            "metrics": metrics,
            "anomalies": anomalies,
            "total_metrics": len(metrics),
            "total_anomalies": len(anomalies),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

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
# eval-sample（抽樣 Q&A 供 Claude Code 評估）
# ──────────────────────────────────────────────────────

@observe(name="qa_tools.eval_sample")
def cmd_eval_sample(args: argparse.Namespace) -> None:
    """從 qa_final.json 隨機抽樣 N 筆 Q&A，輸出 JSON（--with-golden 做分類對照）。"""
    size = args.size
    seed = args.seed
    with_golden = getattr(args, "with_golden", False)

    qas = _load_qa_final()
    if not qas:
        raise CLIError(1)

    rng = random.Random(seed)
    sample_size = min(size, len(qas))
    sampled = rng.sample(qas, sample_size)

    # 如果要做分類對照，載入 golden_qa.json 做 question 匹配
    golden_map: dict[str, dict] = {}
    if with_golden and GOLDEN_QA_PATH.exists():
        golden = json.loads(GOLDEN_QA_PATH.read_text(encoding="utf-8"))
        for g in golden:
            golden_map[g["question"].strip()] = g

    output_items: list[dict] = []
    for qa in sampled:
        question = qa.get("question", "")
        answer = qa.get("answer", "")
        item: dict = {
            "stable_id": qa.get("stable_id", qa.get("id", "")),
            "question": question,
            "answer": answer,
            "keywords": qa.get("keywords", []),
            "confidence": qa.get("confidence", "N/A"),
            "category": qa.get("category", ""),
            "difficulty": qa.get("difficulty", ""),
            "evergreen": qa.get("evergreen", ""),
            "source_title": qa.get("source_title", ""),
            "source_date": qa.get("source_date", ""),
        }
        # 匹配 golden 做分類對照
        g = golden_map.get(question.strip())
        if g:
            item = {
                **item,
                "expected_category": g.get("expected_category", ""),
                "expected_difficulty": g.get("expected_difficulty", ""),
                "expected_evergreen": g.get("expected_evergreen", ""),
            }
        output_items.append(item)

    result = {
        "sample_size": len(output_items),
        "seed": seed,
        "with_golden": with_golden,
        "golden_matched": sum(1 for i in output_items if "expected_category" in i),
        "sampled_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": output_items,
    }

    # 寫入檔案 + stdout
    EVAL_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(EVAL_SAMPLE_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ──────────────────────────────────────────────────────
# eval-retrieval-local（規則式 Retrieval 評估，無 OpenAI）
# ──────────────────────────────────────────────────────

def _kw_fuzzy_hit(exp_kw: str, retrieved_kws: set[str]) -> bool:
    """子字串雙向匹配（與 05_evaluate.py 相同邏輯）。"""
    kw = exp_kw.lower()
    return any(
        kw in rkw or (len(rkw) >= 2 and rkw in kw)
        for rkw in retrieved_kws
    )


_QUERY_INTENT_HINTS: dict[str, tuple[str, ...]] = {
    "diagnosis": ("異常", "下滑", "原因", "診斷", "why", "根因"),
    "root-cause": ("root cause", "根因", "canonical", "waf", "衝突"),
    "implementation": ("如何", "修正", "設定", "實作", "schema", "標記"),
    "measurement": ("ga", "ga4", "gsc", "ctr", "曝光", "點擊", "追蹤", "kpi"),
    "reporting": ("報表", "週報", "監測", "趨勢"),
    "platform-decision": ("平台", "策略", "路徑", "作者"),
}

_QUERY_SCENARIO_HINTS: dict[str, tuple[str, ...]] = {
    "discover": ("discover", "探索"),
    "google-news": ("google news", "news", "新聞"),
    "faq-rich-result": ("faq", "rich result", "搜尋外觀"),
    "ga4-attribution": ("ga4", "歸因", "unassigned"),
    "author-page": ("/user", "作者頁", "author"),
    "image-seo": ("image", "圖片", "alt", "縮圖"),
}

_QUERY_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "技術SEO": ("schema", "結構化資料", "core web vitals", "lcp", "cls", "ttfb", "amp"),
    "索引與檢索": ("索引", "coverage", "googlebot", "canonical", "檢索未索引"),
    "搜尋表現分析": ("ctr", "曝光", "點擊", "serp", "search console"),
    "GA與數據追蹤": ("ga", "ga4", "追蹤", "歸因", "direct"),
    "Discover與AMP": ("discover", "amp", "news"),
    "內容策略": ("內容", "文章", "eeat", "供給", "更新"),
    "連結策略": ("連結", "內部連結", "錨點"),
    "平台策略": ("平台", "作者", "/user", "路徑"),
    "演算法與趨勢": ("演算法", "趨勢", "ai", "gemini", "perplexity"),
}


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, (tuple, set)):
        return [str(item) for item in value if item]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _qa_categories(qa: dict) -> list[str]:
    categories = _as_list(qa.get("categories"))
    if categories:
        return categories
    category = str(qa.get("primary_category") or qa.get("category") or "").strip()
    return [category] if category else []


def _qa_intents(qa: dict) -> list[str]:
    return _as_list(qa.get("intent_labels"))


def _qa_scenarios(qa: dict) -> list[str]:
    return _as_list(qa.get("scenario_tags"))


def _question_signature(question: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", question.lower())
    return text[:80]


def _infer_query_labels(query: str, label_hints: dict[str, tuple[str, ...]]) -> set[str]:
    query_lower = query.lower()
    labels: set[str] = set()
    for label, hints in label_hints.items():
        if any(hint in query_lower for hint in hints):
            labels.add(label)
    return labels


def _serving_tier_prior(
    qa: dict,
    query_lower: str,
    canonical_bonus: float,
    supporting_bonus: float,
    booster_penalty: float,
) -> float:
    tier = str(qa.get("serving_tier", "canonical")).lower()
    base = {
        "canonical": canonical_bonus,
        "supporting": supporting_bonus,
        "booster": -abs(booster_penalty),
    }.get(tier, 0.0)

    if tier == "booster":
        target_queries = _as_list(qa.get("booster_target_queries"))
        if any(target.lower() in query_lower for target in target_queries if target):
            return base + 0.9
    return base


def _keyword_search(
    query: str,
    qas: list[dict],
    top_k: int = 5,
    candidate_k: int = 30,
    canonical_bonus: float = 0.8,
    supporting_bonus: float = 0.3,
    booster_penalty: float = 0.6,
) -> list[tuple[dict, float]]:
    """Metadata-aware keyword retrieval with diversity rerank."""
    tokens = expand_query_tokens(query)
    query_lower = query.lower()
    query_intents = _infer_query_labels(query, _QUERY_INTENT_HINTS)
    query_scenarios = _infer_query_labels(query, _QUERY_SCENARIO_HINTS)
    query_categories = _infer_query_labels(query, _QUERY_CATEGORY_HINTS)

    scored: list[tuple[dict, float]] = []
    for qa in qas:
        kw_tokens = {kw.lower() for kw in _as_list(qa.get("keywords"))}
        phrase_tokens = {phrase.lower() for phrase in _as_list(qa.get("retrieval_phrases"))}
        q_tokens = set(qa.get("question", "").lower().split())
        a_tokens = set(qa.get("answer", "").lower().split())
        surface_tokens = set(str(qa.get("retrieval_surface_text", "")).lower().split())

        categories = set(_qa_categories(qa))
        intents = set(_qa_intents(qa))
        scenarios = set(_qa_scenarios(qa))

        lexical_score = (
            len(tokens & kw_tokens) * 3.2
            + len(tokens & phrase_tokens) * 2.3
            + len(tokens & q_tokens) * 2.0
            + len(tokens & a_tokens) * 0.8
            + len(tokens & surface_tokens) * 1.2
        )
        score = (
            lexical_score
            + len(query_categories & categories) * 2.2
            + len(query_intents & intents) * 1.8
            + len(query_scenarios & scenarios) * 1.6
            + _serving_tier_prior(
                qa,
                query_lower,
                canonical_bonus=canonical_bonus,
                supporting_bonus=supporting_bonus,
                booster_penalty=booster_penalty,
            )
        )

        hard_negative_terms = _as_list(qa.get("hard_negative_terms"))
        if any(term and term.lower() in query_lower for term in hard_negative_terms):
            score -= 0.6

        if lexical_score > 0 and score > 0:
            scored.append((qa, float(score)))

    candidates = sorted(scored, key=lambda x: -x[1])[: max(candidate_k, top_k)]
    selected: list[tuple[dict, float]] = []

    while candidates and len(selected) < top_k:
        selected_sigs = {_question_signature(item[0].get("question", "")) for item in selected}
        selected_categories = {cat for item, _ in selected for cat in _qa_categories(item)}
        selected_intents = {intent for item, _ in selected for intent in _qa_intents(item)}

        best_idx = 0
        best_score = float("-inf")

        for idx, (qa, base_score) in enumerate(candidates):
            adjusted = base_score
            sig = _question_signature(qa.get("question", ""))
            if sig in selected_sigs:
                adjusted -= 2.4

            qa_categories = set(_qa_categories(qa))
            if qa_categories and qa_categories.isdisjoint(selected_categories):
                adjusted += 0.5
            elif qa_categories:
                adjusted -= 0.15

            qa_intents = set(_qa_intents(qa))
            if qa_intents and qa_intents.isdisjoint(selected_intents):
                adjusted += 0.35

            if adjusted > best_score:
                best_score = adjusted
                best_idx = idx

        if best_score == float("-inf"):
            break
        selected.append((candidates[best_idx][0], float(best_score)))
        candidates.pop(best_idx)

    return selected


def _derive_expected_case_metadata(case: dict) -> tuple[list[str], list[str], list[str], bool]:
    expected_categories = list(dict.fromkeys(_as_list(case.get("expected_categories"))))
    expected_intents = _as_list(case.get("expected_intents"))
    expected_scenarios = _as_list(case.get("expected_scenarios"))
    booster_sensitive = bool(case.get("booster_sensitive", len(expected_categories) >= 2))
    return expected_categories, expected_intents, expected_scenarios, booster_sensitive


@observe(name="qa_tools.eval_retrieval_local")
def cmd_eval_retrieval_local(args: argparse.Namespace) -> None:
    """規則式 Retrieval 評估（KW Hit Rate / MRR / Cat Hit Rate），輸出 top-1 供 LLM 判斷。"""
    top_k = getattr(args, "top_k", 5)
    candidate_k = getattr(args, "candidate_k", 30)
    use_enriched = getattr(args, "use_enriched", False)
    save_failure_report = getattr(args, "save_failure_report", "")
    canonical_bonus = float(getattr(args, "canonical_bonus", 0.8))
    supporting_bonus = float(getattr(args, "supporting_bonus", 0.3))
    booster_penalty = float(getattr(args, "booster_penalty", 0.6))

    if not GOLDEN_RETRIEVAL_PATH.exists():
        print(f"golden_retrieval.json 不存在：{GOLDEN_RETRIEVAL_PATH}", file=sys.stderr)
        raise CLIError(1)

    try:
        golden_cases = json.loads(GOLDEN_RETRIEVAL_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"golden_retrieval.json 格式錯誤：{e}", file=sys.stderr)
        raise CLIError(1)
    if not isinstance(golden_cases, list):
        print("golden_retrieval.json 應為 JSON array", file=sys.stderr)
        raise CLIError(1)

    if use_enriched:
        qas = _load_qa_enriched()
    else:
        qas = _load_qa_final()
    if not qas:
        raise CLIError(1)

    case_results: list[dict] = []
    failure_buckets: dict[str, int] = {
        "keyword_surface_miss": 0,
        "category_miss": 0,
        "dual_intent_miss": 0,
        "duplicate_noise": 0,
        "booster_leakage": 0,
        "ranking_miss": 0,
        "pass": 0,
    }

    for case in golden_cases:
        query = case.get("query", "")
        if not query:
            continue
        expected_kws = [kw.lower() for kw in case.get("expected_keywords", [])]
        expected_cats, expected_intents, expected_scenarios, booster_sensitive = _derive_expected_case_metadata(case)

        results = _keyword_search(
            query,
            qas,
            top_k=top_k,
            candidate_k=candidate_k,
            canonical_bonus=canonical_bonus,
            supporting_bonus=supporting_bonus,
            booster_penalty=booster_penalty,
        )
        retrieved = [r[0] for r in results]
        retrieved_scores = [r[1] for r in results]

        # KW Hit Rate（fuzzy 匹配）
        all_retrieved_kws: set[str] = set()
        for qa in retrieved:
            all_retrieved_kws.update(kw.lower() for kw in qa.get("keywords", []))

        kw_hits = sum(1 for kw in expected_kws if _kw_fuzzy_hit(kw, all_retrieved_kws))
        kw_hit_rate = kw_hits / len(expected_kws) if expected_kws else 0

        # Category Hit Rate（支援 multi-category）
        retrieved_cats = {cat for qa in retrieved for cat in _qa_categories(qa)}
        cat_hits = len(retrieved_cats & set(expected_cats))
        cat_hit_rate = cat_hits / len(expected_cats) if expected_cats else 0

        # Intent Coverage
        retrieved_intents = {intent for qa in retrieved for intent in _qa_intents(qa)}
        intent_hits = len(retrieved_intents & set(expected_intents))
        intent_coverage = intent_hits / len(expected_intents) if expected_intents else 0

        # MRR: 找第一個 category 命中的位置
        first_relevant_rank = 0
        for rank, qa in enumerate(retrieved, 1):
            if set(_qa_categories(qa)) & set(expected_cats):
                first_relevant_rank = rank
                break
        mrr = 1 / first_relevant_rank if first_relevant_rank > 0 else 0

        # Precision@K: top_k 中有幾個 QA 的 category 在 expected_cats
        relevant_in_topk = sum(
            1 for qa in retrieved if set(_qa_categories(qa)) & set(expected_cats)
        )
        precision_at_k = relevant_in_topk / top_k if top_k > 0 else 0.0

        boosterless = [qa for qa in retrieved if str(qa.get("serving_tier", "canonical")).lower() != "booster"]
        relevant_non_booster = sum(1 for qa in boosterless if set(_qa_categories(qa)) & set(expected_cats))
        boosterless_precision_at_k = relevant_non_booster / len(boosterless) if boosterless else 0.0

        signatures = [_question_signature(qa.get("question", "")) for qa in retrieved]
        unique_signatures = len(set(signatures))
        duplicate_rate_at_k = 1 - (unique_signatures / len(signatures)) if signatures else 0.0

        booster_topk = [qa for qa in retrieved if str(qa.get("serving_tier", "canonical")).lower() == "booster"]
        booster_top1 = bool(retrieved and str(retrieved[0].get("serving_tier", "canonical")).lower() == "booster")
        canonical_top1 = bool(retrieved and str(retrieved[0].get("serving_tier", "canonical")).lower() == "canonical")
        booster_top1_share = 1.0 if booster_top1 else 0.0
        booster_topk_share = len(booster_topk) / len(retrieved) if retrieved else 0.0

        # F1 Score
        p = precision_at_k
        r = cat_hit_rate
        f1_score = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        dual_category_recall_at_k = cat_hit_rate if len(expected_cats) >= 2 else None
        multi_label_f1_at_k = f1_score if len(expected_cats) >= 2 else None

        if duplicate_rate_at_k > 0.30:
            failure_bucket = "duplicate_noise"
        elif booster_sensitive and booster_topk_share >= 0.6 and precision_at_k < 0.6:
            failure_bucket = "booster_leakage"
        elif len(expected_cats) >= 2 and cat_hit_rate < 1.0:
            failure_bucket = "dual_intent_miss"
        elif cat_hit_rate == 0:
            failure_bucket = "category_miss"
        elif kw_hit_rate < 0.6:
            failure_bucket = "keyword_surface_miss"
        elif mrr < 1.0:
            failure_bucket = "ranking_miss"
        else:
            failure_bucket = "pass"
        failure_buckets[failure_bucket] += 1

        top1 = retrieved[0] if retrieved else {}
        case_results.append({
            "scenario": case.get("scenario", ""),
            "query": query,
            "expected_categories": expected_cats,
            "expected_intents": expected_intents,
            "expected_scenarios": expected_scenarios,
            "booster_sensitive": booster_sensitive,
            "keyword_hit_rate": round(kw_hit_rate, 2),
            "category_hit_rate": round(cat_hit_rate, 2),
            "intent_coverage_at_k": round(intent_coverage, 2),
            "mrr": round(mrr, 2),
            "precision_at_k": round(precision_at_k, 2),
            "boosterless_precision_at_k": round(boosterless_precision_at_k, 2),
            "recall_at_k": round(cat_hit_rate, 2),
            "f1_score": round(f1_score, 2),
            "dual_category_recall_at_k": round(dual_category_recall_at_k, 2) if dual_category_recall_at_k is not None else None,
            "multi_label_f1_at_k": round(multi_label_f1_at_k, 2) if multi_label_f1_at_k is not None else None,
            "duplicate_rate_at_k": round(duplicate_rate_at_k, 2),
            "booster_topk_share": round(booster_topk_share, 2),
            "booster_top1_share": round(booster_top1_share, 2),
            "canonical_top1_rate": 1.0 if canonical_top1 else 0.0,
            "failure_bucket": failure_bucket,
            "top1_question": top1.get("question", ""),
            "top1_answer": top1.get("answer", "")[:500],
            "top1_category": top1.get("primary_category") or top1.get("category", ""),
            "top1_serving_tier": top1.get("serving_tier", "canonical"),
            "top1_score": retrieved_scores[0] if retrieved_scores else 0,
            "top_k_questions": [qa.get("question", "")[:60] for qa in retrieved],
        })

    # 彙整統計
    if not case_results:
        print("所有 golden case 均無結果。", file=sys.stderr)
        raise CLIError(1)

    avg_kw_hit = sum(c["keyword_hit_rate"] for c in case_results) / len(case_results)
    avg_cat_hit = sum(c["category_hit_rate"] for c in case_results) / len(case_results)
    avg_mrr = sum(c["mrr"] for c in case_results) / len(case_results)
    avg_precision_at_k = sum(c["precision_at_k"] for c in case_results) / len(case_results)
    avg_recall_at_k = sum(c["recall_at_k"] for c in case_results) / len(case_results)
    avg_f1_score = sum(c["f1_score"] for c in case_results) / len(case_results)
    avg_boosterless_precision = sum(c["boosterless_precision_at_k"] for c in case_results) / len(case_results)
    avg_duplicate_rate = sum(c["duplicate_rate_at_k"] for c in case_results) / len(case_results)
    avg_canonical_top1 = sum(c["canonical_top1_rate"] for c in case_results) / len(case_results)
    avg_booster_top1 = sum(c["booster_top1_share"] for c in case_results) / len(case_results)
    avg_intent_coverage = sum(c["intent_coverage_at_k"] for c in case_results) / len(case_results)
    dual_cases = [c for c in case_results if c["dual_category_recall_at_k"] is not None]
    avg_dual_recall = (
        sum(float(c["dual_category_recall_at_k"]) for c in dual_cases) / len(dual_cases)
        if dual_cases else 0.0
    )
    avg_multi_label_f1 = (
        sum(float(c["multi_label_f1_at_k"]) for c in dual_cases) / len(dual_cases)
        if dual_cases else 0.0
    )

    single_label_cases = [c for c in case_results if len(c.get("expected_categories", [])) <= 1]
    dual_label_cases = [c for c in case_results if len(c.get("expected_categories", [])) >= 2]
    booster_sensitive_cases = [c for c in case_results if c.get("booster_sensitive")]

    def _slice_avg(cases: list[dict], key: str) -> float:
        return round(sum(float(case[key]) for case in cases) / len(cases), 2) if cases else 0.0

    engine_label = "keyword-enriched" if use_enriched else "keyword"
    output = {
        "search_engine": engine_label,
        "total_cases": len(case_results),
        "avg_keyword_hit_rate": round(avg_kw_hit, 2),
        "avg_category_hit_rate": round(avg_cat_hit, 2),
        "avg_mrr": round(avg_mrr, 2),
        "avg_precision_at_k": round(avg_precision_at_k, 2),
        "avg_recall_at_k": round(avg_recall_at_k, 2),
        "avg_f1_score": round(avg_f1_score, 2),
        "avg_dual_category_recall_at_k": round(avg_dual_recall, 2),
        "avg_multi_label_f1_at_k": round(avg_multi_label_f1, 2),
        "avg_boosterless_precision_at_k": round(avg_boosterless_precision, 2),
        "avg_duplicate_rate_at_k": round(avg_duplicate_rate, 2),
        "avg_intent_coverage_at_k": round(avg_intent_coverage, 2),
        "canonical_top1_rate": round(avg_canonical_top1, 2),
        "booster_top1_share": round(avg_booster_top1, 2),
        "slice_metrics": {
            "single_label": {
                "cases": len(single_label_cases),
                "precision_at_k": _slice_avg(single_label_cases, "precision_at_k"),
                "mrr": _slice_avg(single_label_cases, "mrr"),
            },
            "dual_label": {
                "cases": len(dual_label_cases),
                "precision_at_k": _slice_avg(dual_label_cases, "precision_at_k"),
                "dual_category_recall_at_k": _slice_avg(dual_label_cases, "recall_at_k"),
                "multi_label_f1_at_k": _slice_avg(dual_label_cases, "f1_score"),
            },
            "booster_sensitive": {
                "cases": len(booster_sensitive_cases),
                "precision_at_k": _slice_avg(booster_sensitive_cases, "precision_at_k"),
                "boosterless_precision_at_k": _slice_avg(booster_sensitive_cases, "boosterless_precision_at_k"),
            },
        },
        "failure_buckets": failure_buckets,
        "note": "llm_top1_relevant 需由 Claude Code 逐一判斷",
        "case_details": case_results,
    }

    score_event("precision_at_k", avg_precision_at_k)
    score_event("recall_at_k", avg_recall_at_k)
    score_event("f1_score", avg_f1_score)
    score_event("kw_hit_rate", avg_kw_hit)
    score_event("mrr", avg_mrr)

    if save_failure_report:
        report_path = Path(save_failure_report)
        report_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "avg_precision_at_k": round(avg_precision_at_k, 4),
                "avg_dual_category_recall_at_k": round(avg_dual_recall, 4),
                "avg_multi_label_f1_at_k": round(avg_multi_label_f1, 4),
                "avg_boosterless_precision_at_k": round(avg_boosterless_precision, 4),
                "avg_duplicate_rate_at_k": round(avg_duplicate_rate, 4),
            },
            "failure_buckets": failure_buckets,
            "slice_metrics": output["slice_metrics"],
            "top_failures": sorted(
                [case for case in case_results if case["failure_bucket"] != "pass"],
                key=lambda item: item["precision_at_k"],
            )[:12],
        }
        _write_atomic(report_path, report_payload)

    print(json.dumps(output, ensure_ascii=False, indent=2))


# ──────────────────────────────────────────────────────
# eval-save（儲存 Claude Code 評估結果）
# ──────────────────────────────────────────────────────

_REQUIRED_SECTIONS = {"generation", "retrieval", "classification"}
_GENERATION_DIMS = {"relevance", "accuracy", "completeness", "granularity"}
_SAFE_ENGINE_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def _validate_eval_result(data: dict) -> list[str]:
    """驗證 eval 結果 JSON 結構，回傳錯誤清單（空 = 通過）。"""
    errors: list[str] = []
    missing = _REQUIRED_SECTIONS - set(data.keys())
    if missing:
        errors.append(f"缺少必要區塊：{missing}")
        return errors

    gen = data["generation"]
    if not isinstance(gen, dict):
        errors.append("generation 應為 dict")
    else:
        missing_dims = _GENERATION_DIMS - set(gen.keys())
        if missing_dims:
            errors.append(f"generation 缺少維度：{missing_dims}")
        for dim in _GENERATION_DIMS & set(gen.keys()):
            val = gen[dim]
            if not isinstance(val, (int, float)) or val < 1 or val > 5:
                errors.append(f"generation.{dim} 應為 1-5 的數值，實際：{val}")

    ret = data["retrieval"]
    if not isinstance(ret, dict):
        errors.append("retrieval 應為 dict")
    else:
        for key in ["kw_hit_rate", "mrr"]:
            if key not in ret:
                errors.append(f"retrieval 缺少 {key}")

    cls = data["classification"]
    if not isinstance(cls, dict):
        errors.append("classification 應為 dict")
    else:
        if "category_accuracy" not in cls:
            errors.append("classification 缺少 category_accuracy")

    return errors


@observe(name="qa_tools.eval_save")
def cmd_eval_save(args: argparse.Namespace) -> None:
    """儲存 Claude Code 評估結果為版本化 JSON（output/evals/{date}_claude-code_{engine}.json）。"""
    input_path = Path(args.input)
    raw_engine = getattr(args, "extraction_engine", "claude-code")
    engine = _SAFE_ENGINE_RE.sub("_", raw_engine)
    update_baseline = getattr(args, "update_baseline", False)
    extraction_model = getattr(args, "extraction_model", None)
    embedding_model = getattr(args, "embedding_model", None)
    classify_model = getattr(args, "classify_model", None)

    if not input_path.exists():
        print(f"輸入檔案不存在：{input_path}", file=sys.stderr)
        raise CLIError(1)

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"JSON 格式錯誤：{e}", file=sys.stderr)
        raise CLIError(1)

    errors = _validate_eval_result(data)
    if errors:
        print("eval 結果驗證失敗：", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        raise CLIError(1)

    # 補充 metadata（immutable — model provenance）
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    model_meta: dict[str, str] = {}
    if extraction_model:
        model_meta["extraction_model"] = extraction_model
    if embedding_model:
        model_meta["embedding_model"] = embedding_model
    if classify_model:
        model_meta["classify_model"] = classify_model
    data = {
        **data,
        "provider": "claude-code",
        "extraction_engine": engine,
        "date": today,
        **model_meta,
    }

    # 寫入版本化 JSON（路徑驗證防 traversal）
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{today}_claude-code_{engine}.json"
    eval_path = EVALS_DIR / filename
    if not eval_path.resolve().is_relative_to(EVALS_DIR.resolve()):
        print("輸出路徑異常，拒絕寫入。", file=sys.stderr)
        raise CLIError(1)
    _write_atomic(eval_path, data)
    print(f"已儲存：{eval_path}")

    # Baseline 比較
    if EVAL_BASELINE_PATH.exists():
        try:
            baseline = json.loads(EVAL_BASELINE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("基準線檔案格式錯誤，跳過比較。", file=sys.stderr)
            return
        base_gen = baseline.get("generation", {})
        new_gen = data["generation"]

        base_avg = sum(base_gen.get(d, 0) for d in _GENERATION_DIMS) / len(_GENERATION_DIMS)
        new_avg = sum(new_gen.get(d, 0) for d in _GENERATION_DIMS) / len(_GENERATION_DIMS)
        delta = new_avg - base_avg

        print("\n基準線比較：")
        print(f"  基準線平均：{base_avg:.2f}")
        print(f"  本次平均：{new_avg:.2f}")
        print(f"  差異：{delta:+.2f}")

        for dim in sorted(_GENERATION_DIMS):
            bv = base_gen.get(dim, 0)
            nv = new_gen.get(dim, 0)
            d = nv - bv
            print(f"  {dim}: {nv:.2f} (基準: {bv:.2f}, {d:+.2f})")

        if update_baseline:
            if delta >= 0.05:
                new_baseline = {
                    "version": "baseline",
                    "date": today,
                    "sample_size": data.get("sample_size", 20),
                    "note": f"由 /evaluate-qa-local 更新（delta={delta:+.2f}）",
                    "generation": new_gen,
                    "retrieval": data["retrieval"],
                    "classification": data["classification"],
                }
                _write_atomic(EVAL_BASELINE_PATH, new_baseline)
                print(f"\n基準線已更新（delta={delta:+.2f} >= 0.05）")
            else:
                print(f"\n未更新基準線（delta={delta:+.2f} < 0.05）")
    else:
        print("\n基準線比較：")
        print("  （無基準線可比較）")


# ──────────────────────────────────────────────────────
# eval-compare
# ──────────────────────────────────────────────────────

def cmd_eval_compare(_args: argparse.Namespace) -> None:
    """掃描 output/evals/*.json，輸出跨 provider eval 比較表。"""
    if not EVALS_DIR.exists():
        if getattr(_args, "json", False):
            print(json.dumps({"runs": [], "baseline": {}}, ensure_ascii=False))
        else:
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

    if getattr(_args, "json", False):
        output = {"runs": runs, "baseline": baseline}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    dims = ["relevance", "accuracy", "completeness", "granularity"]

    def _avg(scores: dict) -> float:
        vals = [scores.get(d, 0.0) for d in dims]
        return sum(vals) / len(vals) if vals else 0.0

    # 表頭
    header = f"{'版本':<30s} {'provider':<10s} {'ext_model':<18s} {'avg':>5s} {'rel':>5s} {'acc':>5s} {'comp':>5s} {'gran':>5s} {'KW%':>6s}"
    print("Eval 比較報告\n")
    print(header)
    print("─" * len(header))

    # Baseline 行
    if baseline:
        bs = baseline.get("generation", baseline.get("scores", {}))
        br = baseline.get("retrieval", {})
        provider = baseline.get("provider", baseline.get("extraction_engine", "openai"))
        ext_model = baseline.get("extraction_model", baseline.get("model", ""))
        avg = _avg(bs)
        kw = br.get("kw_hit_rate", float("nan"))
        kw_str = f"{kw:.0%}" if isinstance(kw, float) else "N/A"
        print(
            f"{'* BASELINE (' + baseline.get('date', '') + ')':<30s} {provider:<10s} {ext_model:<18s}"
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
        ext_model = run.get("extraction_model", run.get("model", ""))
        label = run.get("_filename", "?")[:30]
        print(
            f"  {label:<28s} {provider:<10s} {ext_model:<18s}"
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
    p_list = sub.add_parser("list-unprocessed", help="列出待萃取的 Markdown 檔")
    p_list.add_argument("--source-dir", help="只列出指定來源目錄（例如 raw_data/google_blog_zhtw_markdown）")
    p_list_names = sub.add_parser("list-unprocessed-names", help="列出待處理檔名")
    p_list_names.add_argument("--source-dir", help="只列出指定來源目錄（例如 raw_data/google_blog_zhtw_markdown）")
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
    p_metrics.add_argument("--json", action="store_true", help="輸出 JSON 格式（供 API 使用）")

    p_reg = sub.add_parser("register-version", help="將既有檔案補登入 version registry")
    p_reg.add_argument("--step", required=True, help="步驟名稱或編號（如 extract-qa 或 2）")
    p_reg.add_argument("--file", required=True, help="已存在的檔案路徑")
    p_reg.add_argument("--label", help="語意標籤（如 全量重跑@2026-03-02）")

    p_hist = sub.add_parser("version-history", help="顯示 version registry 歷史記錄")
    p_hist.add_argument("--step", help="步驟名稱或編號（不指定則顯示所有步驟）")

    p_lbl = sub.add_parser("label-version", help="為已登記的版本加上語意標籤")
    p_lbl.add_argument("--version-id", required=True, help="版本 ID")
    p_lbl.add_argument("--label", required=True, help="語意標籤")

    p_compare = sub.add_parser("eval-compare", help="跨 provider eval 比較表")
    p_compare.add_argument("--json", action="store_true", help="輸出 JSON 格式（供 API 使用）")

    p_sample = sub.add_parser("eval-sample", help="從 qa_final.json 抽樣 N 筆 Q&A")
    p_sample.add_argument("--size", type=int, default=20, help="抽樣筆數（預設 20）")
    p_sample.add_argument("--seed", type=int, default=42, help="隨機種子（預設 42）")
    p_sample.add_argument("--with-golden", action="store_true", help="載入 golden_qa.json 做分類對照")

    p_ret_local = sub.add_parser("eval-retrieval-local", help="規則式 Retrieval 評估（無 OpenAI）")
    p_ret_local.add_argument("--top-k", type=int, default=5, help="每個 case 取 top-K（預設 5）")
    p_ret_local.add_argument("--candidate-k", type=int, default=30, help="候選池大小（預設 30）")
    p_ret_local.add_argument("--canonical-bonus", type=float, default=0.8, help="canonical prior bonus（預設 0.8）")
    p_ret_local.add_argument("--supporting-bonus", type=float, default=0.3, help="supporting prior bonus（預設 0.3）")
    p_ret_local.add_argument("--booster-penalty", type=float, default=0.6, help="booster prior penalty（預設 0.6）")
    p_ret_local.add_argument("--use-enriched", action="store_true", help="使用 qa_enriched.json（含 synonym/freshness）")
    p_ret_local.add_argument("--save-failure-report", default="", help="輸出失敗切片報告 JSON 路徑")

    p_save = sub.add_parser("eval-save", help="儲存 Claude Code 評估結果")
    p_save.add_argument("--input", required=True, help="評估結果 JSON 路徑")
    p_save.add_argument("--extraction-engine", default="claude-code", help="萃取引擎（預設 claude-code）")
    p_save.add_argument("--update-baseline", action="store_true", help="若超過基準線 +0.05 則更新")
    p_save.add_argument("--extraction-model", default=None, help="Model used for QA extraction")
    p_save.add_argument("--embedding-model", default=None, help="Model used for embeddings")
    p_save.add_argument("--classify-model", default=None, help="Model used for classification")

    args = parser.parse_args()

    dispatch = {
        "pipeline-status":  cmd_pipeline_status,
        "list-unprocessed": cmd_list_unprocessed,
        "list-unprocessed-names": cmd_list_unprocessed_names,
        "list-needs-review": cmd_list_needs_review,
        "merge-qa":         cmd_merge_qa,
        "add-meeting":      cmd_add_meeting,
        "fix-meeting":      cmd_fix_meeting,
        "diff-snapshot":    cmd_diff_snapshot,
        "search":           cmd_search,
        "load-metrics":     cmd_load_metrics,
        "register-version": cmd_register_version,
        "version-history":  cmd_version_history,
        "label-version":    cmd_label_version,
        "eval-compare":     cmd_eval_compare,
        "eval-sample":      cmd_eval_sample,
        "eval-retrieval-local": cmd_eval_retrieval_local,
        "eval-save":        cmd_eval_save,
    }

    init_laminar()
    exit_code = 0
    result_stats: dict = {}
    start = time.monotonic()
    try:
        dispatch[args.cmd](args)
        result_stats = {"status": "ok"}
    except CLIError as exc:
        exit_code = exc.code
        result_stats = {"status": "error", "exit_code": exc.code}
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        log_execution(
            command=args.cmd,
            args=vars(args),
            result=result_stats,
            duration_ms=duration_ms,
        )
        flush_laminar()
    if exit_code:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
