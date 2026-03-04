#!/usr/bin/env python3
"""
稽核軌跡查詢工具 — 分析 fetch_logs / access_logs

用法：
    # Fetch 操作記錄
    python scripts/audit_trail.py fetch                     # 今天所有 fetch 事件
    python scripts/audit_trail.py fetch --date 2026-02-28   # 特定日期
    python scripts/audit_trail.py fetch --sessions          # 顯示 session 摘要

    # 資料存取記錄（哪些 QA 被讀取）
    python scripts/audit_trail.py access                    # 今天所有 access 事件
    python scripts/audit_trail.py access --top 20           # 最常被存取的 QA（Top 20）
    python scripts/audit_trail.py access --event chat       # 只看 chat 事件
    python scripts/audit_trail.py access --ip               # 依 IP 分組

    # 全量報告
    python scripts/audit_trail.py report                    # 今天完整報告
    python scripts/audit_trail.py report --date 2026-02-28
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# 支援直接執行 script
try:
    from utils import audit_logger
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from utils import audit_logger
    import config


# ── 工具函式 ──────────────────────────────────────────

def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_jsonl(path: Path) -> list[dict]:
    """讀取 JSONL 檔案，回傳 list of dict"""
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return records


def _load_qa_index() -> dict[str, dict]:
    """載入 qa_final.json 用於顯示 QA 標題，以 stable_id 為 key"""
    try:
        data = json.loads((config.OUTPUT_DIR / "qa_final.json").read_text(encoding="utf-8"))
        return {q.get("stable_id", str(q["id"])): q for q in data.get("qa_database", [])}
    except Exception:
        return {}


# ── Fetch 相關命令 ──────────────────────────────────────

def cmd_fetch(args: argparse.Namespace) -> None:
    date = args.date or _today_str()
    log_path = audit_logger.FETCH_LOGS_DIR / f"fetch_{date}.jsonl"
    records = _load_jsonl(log_path)

    if not records:
        print(f"無 fetch 日誌（{log_path}）")
        return

    if args.sessions:
        _print_fetch_sessions(records, date)
    else:
        _print_fetch_events(records, date)


def _print_fetch_sessions(records: list[dict], date: str) -> None:
    """顯示 session 級摘要"""
    sessions: dict[str, dict] = {}
    page_counts: dict[str, int] = defaultdict(int)
    skip_counts: dict[str, int] = defaultdict(int)

    for r in records:
        sid = r.get("session_id", "unknown")
        event = r.get("event", "")

        if event == "fetch_start":
            sessions[sid] = r
        elif event == "fetch_page":
            page_counts[sid] += 1
        elif event == "fetch_skip":
            skip_counts[sid] += 1

    print(f"\n{'=' * 65}")
    print(f"Fetch Sessions — {date}")
    print(f"{'=' * 65}")

    if not sessions and not page_counts:
        # session_start 可能沒有，直接從 page 事件重建
        all_sids = set(r.get("session_id", "unknown") for r in records if r.get("session_id"))
        for sid in sorted(all_sids):
            _print_session_summary(records, sid, page_counts, skip_counts)
        return

    for sid, start in sorted(sessions.items(), key=lambda x: x[1].get("ts", "")):
        print(f"\n  Session: {sid}")
        print(f"    時間:   {start.get('ts', 'unknown')}")
        print(f"    模式:   {start.get('mode', 'unknown')}")
        if start.get("since_time"):
            print(f"    起點:   {start['since_time']}")
        print(f"    深度:   {start.get('block_max_depth', '?')}")
        print(f"    擷取:   {page_counts.get(sid, 0)} 頁")
        print(f"    跳過:   {skip_counts.get(sid, 0)} 頁")

        # 找 complete 事件
        for r in records:
            if r.get("session_id") == sid and r.get("event") == "fetch_complete":
                print(f"    耗時:   {r.get('duration_sec', '?')} 秒")
                break

    print(f"\n{'─' * 65}")
    total_sessions = len(sessions)
    total_pages = sum(page_counts.values())
    total_skips = sum(skip_counts.values())
    print(f"合計：{total_sessions} 個 session，{total_pages} 頁擷取，{total_skips} 頁跳過")


def _print_session_summary(records, sid, page_counts, skip_counts):
    pages = [r for r in records if r.get("session_id") == sid and r.get("event") == "fetch_page"]
    skips = [r for r in records if r.get("session_id") == sid and r.get("event") == "fetch_skip"]
    print(f"\n  Session: {sid}")
    print(f"    擷取: {len(pages)} 頁，跳過: {len(skips)} 頁")
    for p in pages[:5]:
        print(f"      [{p.get('event', '')}] {p.get('page_title', '')[:50]}")
    if len(pages) > 5:
        print(f"      ... 還有 {len(pages) - 5} 頁")


def _print_fetch_events(records: list[dict], date: str) -> None:
    """顯示所有 fetch 事件"""
    print(f"\n{'=' * 65}")
    print(f"Fetch 事件 — {date}（共 {len(records)} 筆）")
    print(f"{'=' * 65}")

    for r in records:
        event = r.get("event", "?")
        ts = r.get("ts", "")[:19]
        sid = r.get("session_id", "?")

        if event == "fetch_start":
            print(f"\n  {ts} [{sid}] ▶ fetch_start  mode={r.get('mode')} depth={r.get('block_max_depth')}")
        elif event == "fetch_page":
            title = r.get("page_title", "")[:45]
            print(f"  {ts} [{sid}] ✅ {title:<45} blocks={r.get('block_count')}")
        elif event == "fetch_skip":
            title = r.get("page_title", "")[:45]
            print(f"  {ts} [{sid}] ⏭  {title:<45} reason={r.get('skipped_reason')}")
        elif event == "fetch_complete":
            print(f"  {ts} [{sid}] ✔ fetch_complete  fetched={r.get('fetched_count')} skip={r.get('skipped_count')} {r.get('duration_sec')}s")


# ── Access 相關命令 ─────────────────────────────────────

def cmd_access(args: argparse.Namespace) -> None:
    date = args.date or _today_str()
    log_path = audit_logger.ACCESS_LOGS_DIR / f"access_{date}.jsonl"
    records = _load_jsonl(log_path)

    if not records:
        print(f"無 access 日誌（{log_path}）")
        return

    # 過濾事件類型
    if args.event:
        records = [r for r in records if r.get("event") == args.event]

    if args.top:
        _print_top_accessed(records, args.top, date)
    elif args.ip:
        _print_by_ip(records, date)
    else:
        _print_access_events(records, date)


def _print_access_events(records: list[dict], date: str) -> None:
    """顯示所有 access 事件"""
    print(f"\n{'=' * 65}")
    print(f"Access 事件 — {date}（共 {len(records)} 筆）")
    print(f"{'=' * 65}")

    for r in records:
        event = r.get("event", "?")
        ts = r.get("ts", "")[:19]
        ip = r.get("client_ip", "?")
        ids = r.get("returned_ids", [])

        if event == "search":
            query = r.get("query", "")[:50]
            print(f"\n  {ts} [{ip}] 🔍 search  query='{query}'")
            print(f"          top_k={r.get('top_k')} returned={len(ids)} ids={ids[:5]}")
        elif event == "chat":
            msg = r.get("message", "")[:50]
            print(f"\n  {ts} [{ip}] 💬 chat    '{msg}'")
            print(f"          sources={ids}")
        elif event == "list_qa":
            filters = r.get("filters", {})
            active = {k: v for k, v in filters.items() if v is not None}
            print(f"\n  {ts} [{ip}] 📋 list_qa filters={active} returned={len(ids)}")


def _print_top_accessed(records: list[dict], top_n: int, date: str) -> None:
    """顯示最常被存取的 QA"""
    qa_index = _load_qa_index()
    counter: Counter = Counter()

    for r in records:
        for qa_id in r.get("returned_ids", []):
            counter[qa_id] += 1

    print(f"\n{'=' * 75}")
    print(f"Top {top_n} 最常被存取的 QA — {date}")
    print(f"{'=' * 75}")
    print(f"{'ID':<18}  {'次數':>4}  {'分類':<12}  問題（前 60 字）")
    print(f"{'─' * 75}")

    for qa_id, count in counter.most_common(top_n):
        key = str(qa_id)
        qa = qa_index.get(key, {})
        category = qa.get("category", "?")
        question = qa.get("question", "?")[:60]
        print(f"{key:<18}  {count:>4}x  {category:<12}  {question}")

    print(f"\n合計：{len(counter)} 個不同 QA 被存取，{sum(counter.values())} 次")


def _print_by_ip(records: list[dict], date: str) -> None:
    """依 IP 分組統計"""
    by_ip: dict[str, list] = defaultdict(list)
    for r in records:
        ip = r.get("client_ip") or "unknown"
        by_ip[ip].append(r)

    print(f"\n{'=' * 65}")
    print(f"Access 依 IP 分組 — {date}")
    print(f"{'=' * 65}")

    for ip, recs in sorted(by_ip.items(), key=lambda x: -len(x[1])):
        event_counts = Counter(r.get("event") for r in recs)
        ids_all: list[str] = []
        for r in recs:
            ids_all.extend(str(x) for x in r.get("returned_ids", []))
        print(f"\n  {ip:<20} {len(recs)} 次請求")
        for ev, cnt in event_counts.items():
            print(f"    {ev:<12} {cnt}x")
        print(f"    存取 QA IDs: {sorted(set(ids_all))[:10]}")


# ── 完整報告 ────────────────────────────────────────────

def cmd_report(args: argparse.Namespace) -> None:
    date = args.date or _today_str()
    print(f"\n{'=' * 65}")
    print(f"  稽核報告 — {date}")
    print(f"{'=' * 65}")

    # Fetch 摘要
    fetch_records = _load_jsonl(audit_logger.FETCH_LOGS_DIR / f"fetch_{date}.jsonl")
    fetched = [r for r in fetch_records if r.get("event") == "fetch_page"]
    skipped = [r for r in fetch_records if r.get("event") == "fetch_skip"]
    complete = [r for r in fetch_records if r.get("event") == "fetch_complete"]

    print(f"\n【Fetch 操作】")
    if fetch_records:
        total_dur = sum(r.get("duration_sec", 0) for r in complete)
        print(f"  擷取頁面數: {len(fetched)}")
        print(f"  跳過頁面數: {len(skipped)}")
        print(f"  total 耗時: {round(total_dur, 1)} 秒")
        if fetched:
            print(f"  最新擷取:")
            for r in fetched[-3:]:
                print(f"    ‣ {r.get('page_title', '')[:55]}")
    else:
        print("  （今天無 fetch 操作）")

    # Access 摘要
    access_records = _load_jsonl(audit_logger.ACCESS_LOGS_DIR / f"access_{date}.jsonl")
    searches = [r for r in access_records if r.get("event") == "search"]
    chats = [r for r in access_records if r.get("event") == "chat"]
    lists = [r for r in access_records if r.get("event") == "list_qa"]

    print(f"\n【資料存取】")
    print(f"  search 查詢: {len(searches)} 次")
    print(f"  chat 問答:   {len(chats)} 次")
    print(f"  list_qa:     {len(lists)} 次")

    # Top 10 最常被存取
    if access_records:
        counter: Counter = Counter()
        for r in access_records:
            for qa_id in r.get("returned_ids", []):
                counter[qa_id] += 1
        print(f"\n  Top 10 最常被存取 QA:")
        qa_index = _load_qa_index()
        for qa_id, cnt in counter.most_common(10):
            key = str(qa_id)
            qa = qa_index.get(key, {})
            q = qa.get("question", "?")[:55]
            print(f"    [{key}] {cnt}x  {q}")

    # IP 活動
    ips = Counter(r.get("client_ip") or "unknown" for r in access_records)
    if len(ips) > 0:
        print(f"\n  存取 IP（{len(ips)} 個不同 IP）:")
        for ip, cnt in ips.most_common(5):
            print(f"    {ip:<20} {cnt} 次")

    print(f"\n  日誌目錄:")
    print(f"    {audit_logger.FETCH_LOGS_DIR}")
    print(f"    {audit_logger.ACCESS_LOGS_DIR}")
    print()


# ── Main ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="稽核軌跡查詢工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python scripts/audit_trail.py fetch --sessions
  python scripts/audit_trail.py access --top 20
  python scripts/audit_trail.py report
  python scripts/audit_trail.py access --event chat --date 2026-02-27
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # fetch 子命令
    fetch_p = sub.add_parser("fetch", help="Notion fetch 操作記錄")
    fetch_p.add_argument("--date", default=None, help="日期 YYYY-MM-DD（預設今天）")
    fetch_p.add_argument("--sessions", action="store_true", help="顯示 session 級摘要")

    # access 子命令
    access_p = sub.add_parser("access", help="資料存取記錄")
    access_p.add_argument("--date", default=None, help="日期 YYYY-MM-DD（預設今天）")
    access_p.add_argument("--top", type=int, default=None, metavar="N", help="最常被存取的 Top N QA")
    access_p.add_argument("--event", choices=["search", "chat", "list_qa"], help="篩選事件類型")
    access_p.add_argument("--ip", action="store_true", help="依 IP 分組")

    # report 子命令
    report_p = sub.add_parser("report", help="完整稽核報告")
    report_p.add_argument("--date", default=None, help="日期 YYYY-MM-DD（預設今天）")

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "access":
        cmd_access(args)
    elif args.command == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()
