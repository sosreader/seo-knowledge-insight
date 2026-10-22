"""sync_db_client.py — warehouse-api 同步／讀取路由的薄 client（契約見 vocus-warehouse docs/sync-api.md）。

設計決定：
  1. 憑證只從檔案讀（預設 ~/.config/vocus-warehouse/{sync,app-read}.env，可由 VW_SYNC_ENV_FILE／
     VW_APP_READ_ENV_FILE 覆寫），刻意不吃 CF_ACCESS_* 環境變數：開發機 shell 裡常有別的 Access
     token，env fallback 會讓手動測試誤打 live（KB python-cli-over-cf-access-urllib-pitfalls）。
  2. 寫入用 sync token（SYNC_AUDS）、讀回用 app-read token（APP_READ_AUDS）；server 端兩組 AUD
     不可交集，同一把 token 打不了兩邊。
  3. 不跟 redirect：Access 對失效 token 回 302 到登入頁；200 但 text/html 也視為被 Access 擋下。
  4. 錯誤只回固定代碼（server 的 `error` 字串、HTTP 狀態），不回 body 原文，也絕不輸出憑證值。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import quote

import httpx

DEFAULT_BASE_URL = "https://warehouse-api.vocus.cc"
MAX_BATCH_ITEMS = 50
MAX_BODY_BYTES = 2 * 1024 * 1024
HTTP_TIMEOUT_SECONDS = 30.0
USER_AGENT = "ski-sync-db/1.0"
CREDENTIAL_KEYS = ("CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET")
VALID_RESULTS = frozenset({"created", "updated", "skipped"})
KEY_FIELD = {"reports": "date_key", "meeting_prep": "date_key", "sessions": "id"}
READ_ROUTE = {"reports": "reports", "meeting_prep": "meeting-prep", "sessions": "sessions"}


class CredentialsError(Exception):
    """憑證檔缺失或缺鍵；訊息只含路徑與鍵名。"""


class ItemTooLarge(Exception):
    def __init__(self, index: int, size: int, limit: int) -> None:
        super().__init__(f"item {index} 序列化後 {size} bytes，超過單批上限 {limit} bytes")
        self.index = index
        self.size = size
        self.limit = limit


class SyncHttpError(Exception):
    """HTTP 層失敗；code 為固定代碼（server error 字串、http_<status>、access_redirect 等）。"""

    def __init__(self, code: str, status: int | None = None, detail: str = "") -> None:
        super().__init__(code if not detail else f"{code} {detail}")
        self.code = code
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class Credentials:
    client_id: str
    client_secret: str = field(repr=False)

    def __str__(self) -> str:
        return f"Credentials(client_id={self.client_id!r}, client_secret=***)"

    def headers(self) -> dict[str, str]:
        return {"CF-Access-Client-Id": self.client_id, "CF-Access-Client-Secret": self.client_secret}


@dataclass(frozen=True)
class ItemOutcome:
    key: str
    result: str | None
    error: str | None = None


def _config_dir(environ: Mapping[str, str]) -> Path:
    home = environ.get("HOME") or str(Path.home())
    return Path(home) / ".config" / "vocus-warehouse"


def sync_env_path(environ: Mapping[str, str]) -> Path:
    override = environ.get("VW_SYNC_ENV_FILE")
    return Path(override) if override else _config_dir(environ) / "sync.env"


def app_read_env_path(environ: Mapping[str, str]) -> Path:
    override = environ.get("VW_APP_READ_ENV_FILE")
    return Path(override) if override else _config_dir(environ) / "app-read.env"


def _parse_env_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.removeprefix("export ").partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_credentials(path: Path) -> Credentials:
    try:
        values = _parse_env_lines(path.read_text(encoding="utf-8"))
    except OSError:
        raise CredentialsError(
            f"讀不到憑證檔 {path}（需含 {'、'.join(CREDENTIAL_KEYS)}）") from None
    missing = [key for key in CREDENTIAL_KEYS if not values.get(key)]
    if missing:
        raise CredentialsError(f"憑證檔 {path} 缺少 {'、'.join(missing)}")
    return Credentials(client_id=values["CF_ACCESS_CLIENT_ID"], client_secret=values["CF_ACCESS_CLIENT_SECRET"])


def encode_body(items: Sequence[Mapping[str, Any]]) -> bytes:
    return json.dumps(list(items), ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def plan_batches(items: Sequence[Mapping[str, Any]], *, max_items: int | None = None,
                 max_bytes: int | None = None) -> tuple[tuple[Mapping[str, Any], ...], ...]:
    """依序切批：每批 ≤ max_items 筆且序列化後 ≤ max_bytes；單筆就超過上限時丟 ItemTooLarge。"""
    limit_items = MAX_BATCH_ITEMS if max_items is None else max_items
    limit_bytes = MAX_BODY_BYTES if max_bytes is None else max_bytes
    batches: list[tuple[Mapping[str, Any], ...]] = []
    current: list[Mapping[str, Any]] = []
    for index, item in enumerate(items):
        single = len(encode_body([item]))
        if single > limit_bytes:
            raise ItemTooLarge(index, single, limit_bytes)
        candidate = [*current, item]
        if current and (len(candidate) > limit_items or len(encode_body(candidate)) > limit_bytes):
            batches.append(tuple(current))
            candidate = [item]
        current = candidate
    if current:
        batches.append(tuple(current))
    return tuple(batches)


def build_http_client() -> httpx.Client:
    return httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=False,
                        headers={"User-Agent": USER_AGENT, "Accept": "application/json"})


def _error_code(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"http_{response.status_code}"
    if isinstance(payload, dict) and isinstance(payload.get("error"), str):
        return payload["error"]
    return f"http_{response.status_code}"


def _error_detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        return ""
    if not isinstance(detail, list):
        return ""
    return json.dumps(detail[:10], ensure_ascii=False)


def _json_data(response: httpx.Response) -> Any:
    if 300 <= response.status_code < 400:
        raise SyncHttpError("access_redirect", response.status_code, "（Access 憑證被拒或過期）")
    if "text/html" in response.headers.get("content-type", ""):
        raise SyncHttpError("access_html", response.status_code, "（回應是 HTML，多半是 Access 登入頁）")
    if response.status_code >= 400:
        raise SyncHttpError(_error_code(response), response.status_code, _error_detail(response))
    try:
        payload = response.json()
    except ValueError:
        raise SyncHttpError("malformed_response", response.status_code) from None
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise SyncHttpError("malformed_response", response.status_code)
    return payload["data"]


def parse_write_results(table: str, items: Sequence[Mapping[str, Any]], data: Mapping[str, Any]) -> tuple[ItemOutcome, ...]:
    """逐筆核對回應：同順序、同鍵、result 合法、content_hash 與寫入端相同。"""
    key_field = KEY_FIELD[table]
    results = data.get("results")
    keys = [str(item[key_field]) for item in items]
    if not isinstance(results, list) or len(results) != len(items):
        return tuple(ItemOutcome(key, None, "result_count_mismatch") for key in keys)
    outcomes = []
    for item, key, result in zip(items, keys, results):
        if not isinstance(result, dict) or str(result.get("key", "")).lower() != key.lower():
            outcomes.append(ItemOutcome(key, None, "key_mismatch"))
        elif result.get("result") not in VALID_RESULTS:
            outcomes.append(ItemOutcome(key, None, "unknown_result"))
        elif result.get("content_hash") != item["content_hash"]:
            outcomes.append(ItemOutcome(key, result["result"], "hash_mismatch"))
        else:
            outcomes.append(ItemOutcome(key, result["result"]))
    return tuple(outcomes)


class WarehouseClient:
    def __init__(self, http: httpx.Client, base_url: str, *, sync_creds: Credentials | None = None,
                 read_creds: Credentials | None = None) -> None:
        self._http = http
        self._base = base_url.rstrip("/")
        self._sync = sync_creds
        self._read = read_creds

    def _send(self, request: httpx.Request) -> httpx.Response:
        try:
            return self._http.send(request, follow_redirects=False)
        except httpx.HTTPError as exc:
            raise SyncHttpError("transport_error", None, type(exc).__name__) from None

    def post_batch(self, table: str, items: Sequence[Mapping[str, Any]], *, force: bool) -> tuple[ItemOutcome, ...]:
        if self._sync is None:
            raise CredentialsError("未載入 sync 憑證")
        headers = {**self._sync.headers(), "Content-Type": "application/json",
                   "User-Agent": USER_AGENT, "Accept": "application/json"}
        params = {"force": "true"} if force else {}
        request = self._http.build_request("POST", f"{self._base}/internal/sync/{table}", params=params,
                                           content=encode_body(items), headers=headers)
        data = _json_data(self._send(request))
        return parse_write_results(table, items, data)

    def fetch(self, table: str, key: str) -> dict[str, Any] | None:
        """讀取路由的單筆詳情；404 → None。"""
        if self._read is None:
            raise CredentialsError("未載入 app-read 憑證")
        headers = {**self._read.headers(), "User-Agent": USER_AGENT, "Accept": "application/json"}
        url = f"{self._base}/internal/app/{READ_ROUTE[table]}/{quote(key, safe='')}"
        response = self._send(self._http.build_request("GET", url, headers=headers))
        if response.status_code == 404:
            return None
        return _json_data(response)


def is_https(url: str) -> bool:
    try:
        return httpx.URL(url).scheme == "https"
    except (httpx.InvalidURL, TypeError):
        return False


def default_environ() -> Mapping[str, str]:
    return os.environ
