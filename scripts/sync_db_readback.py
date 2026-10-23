"""sync_db_readback.py — 用讀取路由（app-read token）核對遠端內容。

讀取路由不回 content_hash，所以：
  - reports／meeting_prep：取回 content 重算 `sha256:` hash，與寫入端送出的 content_hash 比對；
    另外檢查回傳的 date 等於請求鍵，因為 meeting-prep 詳情在精確鍵找不到時會用 YYYYMMDD 前綴
    回「同日最新一筆」，不檢查會把別的版本誤判成已寫入。
  - sessions（只剩歷史匯入的預檢與對帳用 check_remote）：詳情路由會把 messages 過濾成白名單欄位，
    無法重算 hash，只核對 id、title 與訊息筆數。日常 upload／status 已不處理 sessions（rag-api 為權威）。
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import sync_db_client as client_mod
from sync_db_sources import text_content_hash

SAME, MISSING, KEY_MISMATCH, DIFFERS = "same", "missing", "key_mismatch", "differs"


def check_remote(table: str, item: Mapping[str, Any], data: Mapping[str, Any] | None) -> str:
    if data is None:
        return MISSING
    if table == "sessions":
        if str(data.get("id", "")).lower() != str(item["id"]).lower():
            return KEY_MISMATCH
        messages = data.get("messages")
        same = data.get("title") == item["title"] and isinstance(messages, list) \
            and len(messages) == len(item["messages"])
        return SAME if same else DIFFERS
    if data.get("date") != item["date_key"]:
        return KEY_MISMATCH
    content = data.get("content")
    if not isinstance(content, str):
        return DIFFERS
    return SAME if text_content_hash(content.encode("utf-8")) == item["content_hash"] else DIFFERS


def _key(table: str, item: Mapping[str, Any]) -> str:
    return str(item[client_mod.KEY_FIELD[table]])


READBACK_ERRORS = {
    MISSING: "readback_missing",
    KEY_MISMATCH: "readback_key_mismatch",
    DIFFERS: "readback_hash_mismatch",
}


def readback(client: client_mod.WarehouseClient,
             succeeded: Sequence[tuple[str, Mapping[str, Any], str]], io) -> int:
    """逐筆讀回；succeeded 為 (table, item, POST 回的 result)。回傳錯誤數。"""
    io.say("讀回核對：")
    errors = 0
    for table, item, _result in succeeded:
        key = _key(table, item)
        try:
            state = check_remote(table, item, client.fetch(table, key))
        except client_mod.SyncHttpError as exc:
            errors += 1
            io.warn(f"  [error] readback {table} {key}: {exc}")
            continue
        if state == SAME:
            io.say(f"  [verified] {table} {key}")
        else:
            errors += 1
            io.warn(f"  [error] {table} {key}: {READBACK_ERRORS[state]}")
    return errors


STATUS_LABEL = {SAME: "remote_same", DIFFERS: "remote_differs", MISSING: "remote_missing",
                KEY_MISMATCH: "remote_missing"}


def print_remote_status(client: client_mod.WarehouseClient,
                        tables: Sequence[tuple[str, Sequence[Mapping[str, Any]]]], io,
                        checker: Callable[[str, Mapping[str, Any], Any], str] = check_remote) -> int:
    """status 子命令的遠端比對；只查可上傳的項目。回傳錯誤數。"""
    io.say("遠端比對（讀取路由）：")
    errors = 0
    for table, items in tables:
        for item in items:
            key = _key(table, item)
            try:
                state = checker(table, item, client.fetch(table, key))
            except client_mod.SyncHttpError as exc:
                errors += 1
                io.warn(f"  [error] {table} {key}: {exc}")
                continue
            io.say(f"  [{STATUS_LABEL[state]}] {table} {key}")
    return errors
