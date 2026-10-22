"""sync_db.py — /sync-db：把本機 reports／meeting_prep／sessions 經 warehouse-api 推到 vocus-warehouse。

取代 api/scripts/sync-db.ts（寫 Supabase）。資料流：
  output/report_*.md、output/meeting_prep_*.md ─(發布閘門)─┐
  output/sessions/*.json ──────────────────────────────────┴─> POST https://warehouse-api.vocus.cc/internal/sync/{table}
  寫入後以 GET /internal/app/{route}/{key}（app-read token）讀回核對。

用法：
  python scripts/sync_db.py status [--type T]
  python scripts/sync_db.py upload [--type reports|meeting_prep|sessions|all] [--dry-run] [--force] [--no-readback]
  共同選項：--base-url（預設 https://warehouse-api.vocus.cc，只收 https）

exit code：0 成功；1 閘門中止／HTTP 失敗／逐筆核對失敗；2 參數或憑證設定錯誤。
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, TextIO

import httpx

import sync_db_client as client_mod
import sync_db_gate as gate
import sync_db_sources as sources
from sync_db_readback import check_remote, print_remote_status, readback

EXIT_OK, EXIT_FAIL, EXIT_CONFIG = 0, 1, 2
TABLES = ("reports", "meeting_prep", "sessions")
DOCUMENT_TABLES = frozenset({"reports", "meeting_prep"})
TYPE_ALIASES = {"meeting-prep": "meeting_prep"}
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class TablePlan:
    table: str
    items: tuple[dict[str, Any], ...]
    excluded: tuple[tuple[str, str], ...]
    blocked: tuple[gate.GateDecision, ...]
    missing_local: tuple[str, ...]


@dataclass(frozen=True)
class Io:
    out: TextIO
    err: TextIO

    def say(self, message: str) -> None:
        print(message, file=self.out)

    def warn(self, message: str) -> None:
        print(message, file=self.err)


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--type", default="all", choices=[*TABLES, "all", *TYPE_ALIASES])
    common.add_argument("--base-url", default=client_mod.DEFAULT_BASE_URL)
    parser = argparse.ArgumentParser(prog="sync_db.py", description="本機報告與 sessions 推送到 vocus-warehouse")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", parents=[common], help="列本機候選、帳冊狀態、遠端是否已有")
    upload = sub.add_parser("upload", parents=[common], help="上傳（只送帳冊核准的版本）")
    upload.add_argument("--dry-run", action="store_true", help="只列出計畫，不送任何 HTTP 請求")
    upload.add_argument("--force", action="store_true", help="遠端 hash 相同也覆寫（仍受閘門限制）")
    upload.add_argument("--no-readback", action="store_true", help="寫入後不讀回核對（不需 app-read 憑證）")
    return parser


def _selected_tables(type_arg: str) -> tuple[str, ...]:
    resolved = TYPE_ALIASES.get(type_arg, type_arg)
    return TABLES if resolved == "all" else (resolved,)


def _document_plan(root: Path, table: str, entries: tuple[gate.ReviewEntry, ...]) -> TablePlan:
    docs = sources.list_documents(root / "output", table)
    items, excluded, blocked = [], [], []
    for doc in docs:
        decision = gate.evaluate(entries, doc.filename, doc.content)
        if decision.reason is None:
            items.append(sources.build_item(doc, decision.entry))
        elif decision.reason in ("content_changed", "invalid_filename"):
            blocked.append(decision)
        else:
            excluded.append((doc.filename, decision.reason))
    local_names = {doc.filename for doc in docs}
    prefix = "report_" if table == "reports" else "meeting_prep_"
    missing = tuple(e.filename for e in entries
                    if e.status == "approved" and e.filename.startswith(prefix) and e.filename not in local_names)
    return TablePlan(table, tuple(items), tuple(excluded), tuple(blocked), missing)


def _session_plan(root: Path) -> TablePlan:
    sessions, skipped = sources.list_sessions(root / "output" / "sessions")
    items = tuple(sources.build_session_item(s) for s in sessions)
    return TablePlan("sessions", items, skipped, (), ())


def _build_plans(root: Path, tables: tuple[str, ...], io: Io) -> tuple[TablePlan, ...] | None:
    entries: tuple[gate.ReviewEntry, ...] = ()
    if DOCUMENT_TABLES.intersection(tables):
        try:
            entries = gate.load_manifest(root / gate.MANIFEST_RELPATH)
        except gate.PublicationBlocked as exc:
            io.warn(f"[閘門] 發布帳冊無法使用：{exc.reason}（{gate.MANIFEST_RELPATH}），不上傳任何報告")
            return None
    return tuple(_session_plan(root) if t == "sessions" else _document_plan(root, t, entries) for t in tables)


def _key(table: str, item: Mapping[str, Any]) -> str:
    return str(item[client_mod.KEY_FIELD[table]])


def _print_plan(plan: TablePlan, io: Io) -> None:
    io.say(f"== {plan.table} ==  可上傳 {len(plan.items)} 筆｜排除 {len(plan.excluded)}｜閘門中止 {len(plan.blocked)}")
    for item in plan.items:
        io.say(f"  [eligible] {_key(plan.table, item)}  {item['content_hash'][:19]}")
    unregistered = [name for name, reason in plan.excluded if reason == "missing_review"]
    if unregistered:
        io.say(f"  [excluded:missing_review] {len(unregistered)} 份未登記帳冊（不上傳，未列出檔名）")
    for name, reason in plan.excluded:
        if reason != "missing_review":
            io.say(f"  [excluded:{reason}] {name}")
    for name in plan.missing_local:
        io.say(f"  [warn] 帳冊核准但本機找不到：{name}")
    for decision in plan.blocked:
        expected = decision.entry.sha256[:12] if decision.entry else "-"
        io.warn(f"  [blocked:{decision.reason}] {decision.filename}  帳冊 {expected}… ≠ 本機 {decision.sha256[:12]}…")


def _plan_or_exit(root: Path, tables: tuple[str, ...], io: Io) -> tuple[tuple[TablePlan, ...] | None, int]:
    plans = _build_plans(root, tables, io)
    if plans is None:
        return None, EXIT_FAIL
    for plan in plans:
        _print_plan(plan, io)
    if any(plan.blocked for plan in plans):
        io.warn("[閘門] 有檔案與帳冊核准的版本不符，整批中止；請重新審核並更新帳冊 sha256 後再跑")
        return plans, EXIT_FAIL
    return plans, EXIT_OK


def _batch_plans(plans: tuple[TablePlan, ...], io: Io) -> dict[str, tuple] | None:
    batches: dict[str, tuple] = {}
    for plan in plans:
        try:
            batches[plan.table] = client_mod.plan_batches(plan.items, max_bytes=client_mod.MAX_BODY_BYTES)
        except client_mod.ItemTooLarge as exc:
            key = _key(plan.table, plan.items[exc.index])
            io.warn(f"[上限] {plan.table} {key} 單筆 {exc.size} bytes 超過單批上限 {exc.limit} bytes，整批中止")
            return None
    return batches


def _load_creds(path: Path, label: str, io: Io, hint: str = "") -> client_mod.Credentials | None:
    try:
        return client_mod.load_credentials(path)
    except client_mod.CredentialsError as exc:
        io.warn(f"[憑證] {label}：{exc}{hint}")
        return None


def _post_all(client: client_mod.WarehouseClient, plans, batches, force: bool, io: Io):
    succeeded: list[tuple[str, dict[str, Any]]] = []
    errors = 0
    for plan in plans:
        for batch in batches[plan.table]:
            try:
                outcomes = client.post_batch(plan.table, batch, force=force)
            except client_mod.SyncHttpError as exc:
                outcomes = tuple(client_mod.ItemOutcome(_key(plan.table, i), None, str(exc)) for i in batch)
            for item, outcome in zip(batch, outcomes):
                if outcome.error:
                    errors += 1
                    io.warn(f"  [error] {plan.table} {outcome.key}: {outcome.error}")
                else:
                    io.say(f"  [{outcome.result}] {plan.table} {outcome.key}")
                    succeeded.append((plan.table, item))
    return tuple(succeeded), errors


def _upload(args, root: Path, http_factory, environ: Mapping[str, str], io: Io) -> int:
    tables = _selected_tables(args.type)
    plans, code = _plan_or_exit(root, tables, io)
    if plans is None or code != EXIT_OK:
        return code
    batches = _batch_plans(plans, io)
    if batches is None:
        return EXIT_FAIL
    if args.dry_run:
        sizes = {t: [len(b) for b in bs] for t, bs in batches.items()}
        io.say(f"dry-run：不送出任何 HTTP 請求；預計批次 {sizes}")
        return EXIT_OK
    if not any(plan.items for plan in plans):
        io.say("沒有可上傳的項目")
        return EXIT_OK
    sync_creds = _load_creds(client_mod.sync_env_path(environ), "sync", io)
    if sync_creds is None:
        return EXIT_CONFIG
    read_creds = None
    if not args.no_readback:
        read_creds = _load_creds(client_mod.app_read_env_path(environ), "app-read", io,
                                 "；讀回核對需要它，或加 --no-readback 略過")
        if read_creds is None:
            return EXIT_CONFIG
    client = client_mod.WarehouseClient(http_factory(), args.base_url, sync_creds=sync_creds, read_creds=read_creds)
    mode = "force 覆寫" if args.force else "hash 相同略過"
    io.say(f"上傳到 {args.base_url}（{mode}）")
    succeeded, errors = _post_all(client, plans, batches, args.force, io)
    if read_creds is not None and succeeded:
        errors += readback(client, succeeded, io)
    io.say(f"完成：成功 {len(succeeded)} 筆｜錯誤 {errors} 筆")
    return EXIT_FAIL if errors else EXIT_OK


def _status(args, root: Path, http_factory, environ: Mapping[str, str], io: Io) -> int:
    tables = _selected_tables(args.type)
    plans, code = _plan_or_exit(root, tables, io)
    if plans is None:
        return code
    path = client_mod.app_read_env_path(environ)
    read_creds = _load_creds(path, "app-read", io, "；只列本機與帳冊，不比對遠端")
    if read_creds is None:
        return code
    client = client_mod.WarehouseClient(http_factory(), args.base_url, read_creds=read_creds)
    remote_errors = print_remote_status(client, [(p.table, p.items) for p in plans], io, check_remote)
    return EXIT_FAIL if remote_errors or code != EXIT_OK else EXIT_OK


def main(argv: list[str] | None = None, *, root: Path | None = None, http: httpx.Client | None = None,
         environ: Mapping[str, str] | None = None, out: TextIO | None = None, err: TextIO | None = None) -> int:
    args = _parser().parse_args(argv)
    io = Io(out or sys.stdout, err or sys.stderr)
    if not client_mod.is_https(args.base_url):
        io.warn(f"--base-url 必須是 https：{args.base_url}")
        return EXIT_CONFIG
    env = client_mod.default_environ() if environ is None else environ
    http_factory = (lambda: http) if http is not None else client_mod.build_http_client
    command = _upload if args.command == "upload" else _status
    return command(args, root or REPO_ROOT, http_factory, env, io)


if __name__ == "__main__":
    sys.exit(main())
