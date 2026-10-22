"""sync_db_import.py — `sync_db.py upload --from-ndjson <dir>`：Supabase 三表 NDJSON 歷史匯入 vocus-warehouse。

資料來源是 Supabase 匯出的 `reports／meeting_prep／sessions.ndjson.gz`（附 manifest.json），
每行一列、欄位同 Supabase 表。逐列轉成 `/internal/sync/{table}` 的 body 後走與日常 sync-db 相同的 client。

與日常 upload 的差異（刻意的）：
  1. 跳過發布閘門：歷史列沒有帳冊，approved_version 不送（NULL）。輸出會明確標示「歷史匯入模式，未經發布閘門」。
  2. 去重＝先查後送：每列先用讀取路由（app-read token）查遠端同鍵；內容相同就不送、內容不同預設不送也不蓋。
     不選「直接送出讓 endpoint 回 skipped」，因為 hash 不同時 endpoint 會直接 updated 並覆寫 approved_version，
     等於已經蓋掉 S2.2 登記過的列才事後標紅；先查後送可以把「蓋不蓋」留給人決定（--force 才蓋）。
     代價是每列多一次 GET，約 160 次，量可忽略，而且讀回對帳本來就要同樣的 GET。
  3. 結尾逐鍵讀回對帳（verified／mismatch），任何 mismatch 或錯誤都 exit 非零。

欄位對照（Supabase → endpoint body）：
  - reports：date_key、filename（原值）、content、meta、created_at。id／size_bytes／deleted_at 不送。
    meta 為 NULL 時先用內文 report_meta 解析（同日常 upload），再加 source；若直接塞 {"source"}，
    讀取路由「meta NULL 才從內文解析」的 fallback 會失效。
  - meeting_prep：同上，filename 必帶原值（10 列的檔名不是預設推導）。原始 updated_at 沒有欄位可帶，匯入後為匯入時刻。
  - sessions：id、title、messages、metadata、created_at、updated_at。metadata 加 source 不影響 hash
    （hash 只含 title＋messages）也不影響前端（讀取路由只白名單輸出 maturity_level）。
  - content_hash 與日常 upload 完全相同：documents 為 sha256(content UTF-8)、sessions 為 session_content_hash。
  - meta／metadata 的 source 值是 SOURCE_TAG。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import uuid
import zlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import sync_db_client as client_mod
from sync_db_meta import parse_meeting_prep_meta, parse_report_meta
from sync_db_readback import DIFFERS, SAME, check_remote
from sync_db_sources import MAX_SESSION_TITLE_LENGTH, session_content_hash, text_content_hash

EXIT_OK, EXIT_FAIL, EXIT_CONFIG = 0, 1, 2
SOURCE_TAG = "supabase-2026-10-22"
BANNER = "歷史匯入模式，未經發布閘門（approved_version 為 NULL）"
MANIFEST_NAME = "manifest.json"
ANSI_RED, ANSI_RESET = "\x1b[31m", "\x1b[0m"
# 與 vocus-warehouse sync/models.py 相同的鍵與檔名規則
DATE_KEY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]{0,63}")
FILENAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]{0,254}")
DOCUMENT_TABLES = ("reports", "meeting_prep")

Item = dict[str, Any]


class ExportConfigError(Exception):
    """匯出目錄／檔案／manifest 本身有問題（exit 2）。"""


class ExportDataError(Exception):
    """檔案內容讀不出來（壞 gzip、壞 JSON 行；exit 1）。訊息只含檔名與行號，不帶原文。"""


class InvalidRow(Exception):
    """單列轉換失敗；reason 只含欄位名與原因，不帶內容。"""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class TableImport:
    table: str
    items: tuple[Item, ...]
    excluded: tuple[tuple[str, str], ...]
    invalid: tuple[tuple[str, str], ...]
    duplicates: tuple[str, ...]


@dataclass(frozen=True)
class Export:
    tables: tuple[TableImport, ...]
    warnings: tuple[str, ...]


# ── 逐列轉換 ─────────────────────────────────────────────


def _contains_nul(value: Any) -> bool:
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, list):
        return any(_contains_nul(v) for v in value)
    if isinstance(value, dict):
        return any(_contains_nul(k) or _contains_nul(v) for k, v in value.items())
    return False


def _clean_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidRow(f"{field} 不是字串")
    if "\x00" in value:
        raise InvalidRow(f"{field} 含 NUL")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise InvalidRow(f"{field} 含無法編成 UTF-8 的孤立 surrogate") from None
    return value


def _matching(value: Any, pattern: re.Pattern[str], field: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise InvalidRow(f"{field} 格式不合")
    return value


def _timestamp(row: Mapping[str, Any], field: str) -> str | None:
    value = row.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidRow(f"{field} 不是字串")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise InvalidRow(f"{field} 不是 ISO 8601") from None
    if parsed.tzinfo is None:
        raise InvalidRow(f"{field} 缺時區")
    return parsed.isoformat()


def _with_created_at(item: Item, row: Mapping[str, Any]) -> Item:
    created = _timestamp(row, "created_at")
    return item if created is None else {**item, "created_at": created}


def _json_object(value: Any, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise InvalidRow(f"{field} 不是物件")
    return value


def _build_report(row: Mapping[str, Any]) -> Item:
    key = _matching(row.get("date_key"), DATE_KEY_RE, "date_key")
    content = _clean_text(row.get("content"), "content")
    filename = row.get("filename")
    if filename is not None:
        _matching(filename, FILENAME_RE, "filename")
    meta = _json_object(row.get("meta"), "meta")
    if meta is None:
        meta = parse_report_meta(content) or {}
    item: Item = {"date_key": key, "content": content, "meta": {**meta, "source": SOURCE_TAG},
                  "content_hash": text_content_hash(content.encode("utf-8"))}
    if filename is not None:
        item["filename"] = filename
    return _with_created_at(item, row)


def _build_meeting_prep(row: Mapping[str, Any]) -> Item:
    key = _matching(row.get("date_key"), DATE_KEY_RE, "date_key")
    if row.get("filename") is None:
        raise InvalidRow("filename 必填")
    filename = _matching(row.get("filename"), FILENAME_RE, "filename")
    content = _clean_text(row.get("content"), "content")
    meta = _json_object(row.get("meta"), "meta")
    if meta is None:
        meta = parse_meeting_prep_meta(content) or {}
    item: Item = {"date_key": key, "filename": filename, "content": content,
                  "meta": {**meta, "source": SOURCE_TAG},
                  "content_hash": text_content_hash(content.encode("utf-8"))}
    return _with_created_at(item, row)


def _build_session(row: Mapping[str, Any]) -> Item:
    try:
        sid = str(uuid.UUID(str(row.get("id"))))
    except ValueError:
        raise InvalidRow("id 不是 UUID") from None
    title = _clean_text(row.get("title"), "title")
    if len(title) > MAX_SESSION_TITLE_LENGTH:
        raise InvalidRow(f"title 超過 {MAX_SESSION_TITLE_LENGTH} 字")
    messages = row.get("messages")
    if not (isinstance(messages, list) and all(isinstance(m, dict) for m in messages)):
        raise InvalidRow("messages 不是物件陣列")
    if _contains_nul(messages):
        raise InvalidRow("messages 含 NUL")
    try:
        json.dumps(messages, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (UnicodeEncodeError, ValueError):
        raise InvalidRow("messages 含無法編成 UTF-8 的孤立 surrogate 或 NaN") from None
    metadata = _json_object(row.get("metadata"), "metadata") or {}
    item: Item = {"id": sid, "title": title, "messages": messages, "metadata": {**metadata, "source": SOURCE_TAG},
                  "content_hash": session_content_hash(title, messages)}
    updated = _timestamp(row, "updated_at")
    if updated is not None:
        item["updated_at"] = updated
    return _with_created_at(item, row)


_BUILDERS = {"reports": _build_report, "meeting_prep": _build_meeting_prep, "sessions": _build_session}


def build_item(table: str, row: Mapping[str, Any]) -> Item:
    """單列轉成 endpoint body；格式不合丟 InvalidRow。"""
    return _BUILDERS[table](row)


# ── 讀檔 ─────────────────────────────────────────────────


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-standard JSON constant {name}")


def read_rows(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    try:
        with gzip.open(path, "rb") as handle:
            for number, raw in enumerate(handle, 1):
                if not raw.strip():
                    continue
                try:
                    row = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
                except ValueError:
                    raise ExportDataError(f"{path.name} 第 {number} 行不是合法的 JSON") from None
                if not isinstance(row, dict):
                    raise ExportDataError(f"{path.name} 第 {number} 行不是 JSON 物件")
                rows.append(row)
    except (OSError, EOFError, zlib.error):
        raise ExportDataError(f"{path.name} 無法解壓（不是完整的 gzip）") from None
    return tuple(rows)


def _verify_manifest(directory: Path, table: str, filename: str, row_count: int, manifest: Mapping[str, Any]) -> None:
    entry = (manifest.get("tables") or {}).get(table) if isinstance(manifest.get("tables"), dict) else None
    if not isinstance(entry, dict):
        raise ExportConfigError(f"{MANIFEST_NAME} 缺少 {table} 的紀錄")
    digest = hashlib.sha256((directory / filename).read_bytes()).hexdigest()
    if entry.get("sha256") != digest:
        raise ExportConfigError(f"{MANIFEST_NAME} 的 {table} sha256 與 {filename} 不符，匯出檔可能被改過或不完整")
    if entry.get("rows") != row_count:
        raise ExportConfigError(f"{MANIFEST_NAME} 的 {table} 列數 {entry.get('rows')} ≠ 實際 {row_count}")


def _load_manifest(directory: Path) -> Mapping[str, Any] | None:
    path = directory / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ExportConfigError(f"{MANIFEST_NAME} 無法解析") from None
    if not isinstance(manifest, dict):
        raise ExportConfigError(f"{MANIFEST_NAME} 格式不合")
    return manifest


def _row_key(table: str, row: Mapping[str, Any]) -> str:
    return str(row.get(client_mod.KEY_FIELD[table]))


def _convert_table(table: str, rows: Sequence[Mapping[str, Any]]) -> TableImport:
    items: list[Item] = []
    excluded: list[tuple[str, str]] = []
    invalid: list[tuple[str, str]] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        key = _row_key(table, row)
        if row.get("deleted_at") is not None:
            excluded.append((key, "soft_deleted"))
            continue
        try:
            item = build_item(table, row)
        except InvalidRow as exc:
            invalid.append((key, exc.reason))
            continue
        normalised = str(item[client_mod.KEY_FIELD[table]]).lower()
        if normalised in seen:
            duplicates.append(key)
        seen.add(normalised)
        items.append(item)
    return TableImport(table, tuple(items), tuple(excluded), tuple(invalid), tuple(duplicates))


def load_export(directory: Path, tables: Sequence[str]) -> Export:
    if not directory.is_dir():
        raise ExportConfigError(f"找不到匯出目錄 {directory}")
    manifest = _load_manifest(directory)
    warnings = () if manifest is not None else (f"{directory} 沒有 {MANIFEST_NAME}，略過檔案完整性檢查",)
    loaded: list[TableImport] = []
    for table in tables:
        filename = f"{table}.ndjson.gz"
        if not (directory / filename).is_file():
            raise ExportConfigError(f"找不到 {directory / filename}")
        rows = read_rows(directory / filename)
        if manifest is not None:
            _verify_manifest(directory, table, filename, len(rows), manifest)
        loaded.append(_convert_table(table, rows))
    return Export(tuple(loaded), warnings)


# ── 輸出 ─────────────────────────────────────────────────


def _red(io, text: str) -> str:
    isatty = getattr(io.err, "isatty", None)
    return f"{ANSI_RED}{text}{ANSI_RESET}" if callable(isatty) and isatty() else text


def _key(table: str, item: Mapping[str, Any]) -> str:
    return str(item[client_mod.KEY_FIELD[table]])


def _print_table(entry: TableImport, io) -> None:
    io.say(f"== {entry.table} ==  可匯入 {len(entry.items)} 筆｜排除 {len(entry.excluded)}｜"
           f"無效 {len(entry.invalid)}")
    for key, reason in entry.excluded:
        io.say(f"  [excluded:{reason}] {entry.table} {key}")


def _report_problems(export: Export, io) -> bool:
    """有任何無效列或重複鍵就回 False（整批中止，零 HTTP）。"""
    clean = True
    for entry in export.tables:
        for key, reason in entry.invalid:
            io.warn(f"  [invalid] {entry.table} {key}: {reason}")
            clean = False
        for key in entry.duplicates:
            io.warn(f"  [duplicate] {entry.table} {key}: 匯出檔內重複鍵")
            clean = False
    if not clean:
        io.warn("[匯入] 有無效或重複的列，整批中止，未送出任何請求；請修正匯出檔後再跑")
    return clean


def _oversize_ok(export: Export, io) -> bool:
    ok = True
    for entry in export.tables:
        for item in entry.items:
            try:
                size = len(client_mod.encode_body([item]))
            except ValueError as exc:
                io.warn(f"[序列化] {entry.table} {_key(entry.table, item)} 無法編成 JSON（{type(exc).__name__}）")
                ok = False
                continue
            if size > client_mod.MAX_BODY_BYTES:
                io.warn(f"[上限] {entry.table} {_key(entry.table, item)} 單筆 {size} bytes 超過單批上限 "
                        f"{client_mod.MAX_BODY_BYTES} bytes，整批中止")
                ok = False
    return ok


# ── 去重、寫入、讀回 ─────────────────────────────────────


def _precheck(client: client_mod.WarehouseClient, export: Export, force: bool, io):
    """逐列查遠端。回 (待送 {table: [item]}, 已相同數, 衝突數, 錯誤數)。"""
    to_send: dict[str, list[Item]] = {entry.table: [] for entry in export.tables}
    counts: Counter[str] = Counter()
    for entry in export.tables:
        for item in entry.items:
            key = _key(entry.table, item)
            try:
                state = check_remote(entry.table, item, client.fetch(entry.table, key))
            except client_mod.SyncHttpError as exc:
                counts["error"] += 1
                io.warn(f"  [error] precheck {entry.table} {key}: {exc}")
                continue
            if state == SAME:
                counts["same"] += 1
                io.say(f"  [skipped] {entry.table} {key}（遠端已有且內容相同，不送）")
            elif state == DIFFERS and not force:
                counts["conflict"] += 1
                io.warn(_red(io, f"  [conflict] {entry.table} {key}: 遠端已有但內容不同，未送出（確認後以 --force 覆寫）"))
            else:
                to_send[entry.table].append(item)
    return to_send, counts["same"], counts["conflict"], counts["error"]


def _post_table(client: client_mod.WarehouseClient, table: str, items: Sequence[Item], force: bool, io):
    posted: list[tuple[str, Item, str]] = []
    results: Counter[str] = Counter()
    for batch in client_mod.plan_batches(items):
        try:
            outcomes = client.post_batch(table, batch, force=force)
        except client_mod.SyncHttpError as exc:
            outcomes = tuple(client_mod.ItemOutcome(_key(table, i), None, str(exc)) for i in batch)
        for item, outcome in zip(batch, outcomes):
            if outcome.error:
                results["error"] += 1
                io.warn(f"  [error] {table} {outcome.key}: {outcome.error}")
                continue
            results[outcome.result] += 1
            if outcome.result == "updated":
                io.warn(_red(io, f"  [overwrite] {table} {outcome.key}: 遠端既有列已被覆寫"))
            else:
                io.say(f"  [{outcome.result}] {table} {outcome.key}")
            posted.append((table, item, outcome.result))
    return posted, results


def _verify(client: client_mod.WarehouseClient, posted: Sequence[tuple[str, Item, str]], io) -> tuple[int, int]:
    verified = mismatch = 0
    for table, item, _result in posted:
        key = _key(table, item)
        try:
            state = check_remote(table, item, client.fetch(table, key))
        except client_mod.SyncHttpError as exc:
            mismatch += 1
            io.warn(f"  [mismatch] {table} {key}: {exc}")
            continue
        if state == SAME:
            verified += 1
            io.say(f"  [verified] {table} {key}")
        else:
            mismatch += 1
            io.warn(f"  [mismatch] {table} {key}: 讀回內容與送出的不一致（{state}）")
    return verified, mismatch


def _credentials(environ: Mapping[str, str], io):
    try:
        sync = client_mod.load_credentials(client_mod.sync_env_path(environ))
    except client_mod.CredentialsError as exc:
        io.warn(f"[憑證] sync：{exc}")
        return None
    try:
        read = client_mod.load_credentials(client_mod.app_read_env_path(environ))
    except client_mod.CredentialsError as exc:
        io.warn(f"[憑證] app-read：{exc}（去重預檢與讀回對帳都需要它）")
        return None
    return sync, read


def _execute(args, export: Export, http_factory, environ: Mapping[str, str], io) -> int:
    creds = _credentials(environ, io)
    if creds is None:
        return EXIT_CONFIG
    client = client_mod.WarehouseClient(http_factory(), args.base_url, sync_creds=creds[0], read_creds=creds[1])
    mode = "force（遠端內容不同的列也覆寫）" if args.force else "遠端已有的列不覆寫"
    io.say(f"匯入到 {args.base_url}（{mode}）")
    io.say("去重預檢（讀取路由）：")
    to_send, same, conflicts, errors = _precheck(client, export, args.force, io)
    totals: Counter[str] = Counter()
    posted: list[tuple[str, Item, str]] = []
    io.say("寫入：")
    for table, items in to_send.items():
        table_posted, results = _post_table(client, table, items, args.force, io)
        posted.extend(table_posted)
        totals.update(results)
    io.say("讀回對帳：")
    verified, mismatch = _verify(client, posted, io)
    verified += same
    errors += totals["error"]
    excluded = sum(len(entry.excluded) for entry in export.tables)
    io.say(f"讀回對帳：verified {verified}｜mismatch {mismatch}（含預檢已相同 {same} 筆）")
    io.say(f"完成：created {totals['created']}｜updated {totals['updated']}（覆寫）｜skipped {same + totals['skipped']}"
           f"｜conflict {conflicts}（未送出）｜excluded {excluded}｜錯誤 {errors}")
    if conflicts:
        io.warn(_red(io, f"[匯入] {conflicts} 筆遠端內容與匯出檔不同、未覆寫；確認要以匯出檔為準再加 --force 重跑"))
    return EXIT_FAIL if (errors or mismatch or conflicts) else EXIT_OK


def run_import(args, http_factory, environ: Mapping[str, str], io, tables: Sequence[str]) -> int:
    io.say(f"[匯入] {BANNER}")
    try:
        export = load_export(Path(args.from_ndjson), tables)
    except ExportConfigError as exc:
        io.warn(f"[匯入] {exc}")
        return EXIT_CONFIG
    except ExportDataError as exc:
        io.warn(f"[匯入] {exc}")
        return EXIT_FAIL
    for warning in export.warnings:
        io.warn(f"[manifest] {warning}")
    for entry in export.tables:
        _print_table(entry, io)
    if not _report_problems(export, io) or not _oversize_ok(export, io):
        return EXIT_FAIL
    if args.dry_run:
        sizes = {e.table: [len(b) for b in client_mod.plan_batches(e.items)] for e in export.tables}
        io.say(f"dry-run：不送出任何 HTTP 請求（未查遠端是否已有同鍵）；預計批次 {sizes}")
        return EXIT_OK
    if not any(entry.items for entry in export.tables):
        io.say("沒有可匯入的項目")
        return EXIT_OK
    return _execute(args, export, http_factory, environ, io)
