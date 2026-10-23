"""scripts/sync_db_import.py：`upload --from-ndjson <dir>` 歷史匯入模式（Supabase 三表 NDJSON → vocus-warehouse）。

全部 HTTP 走 httpx.MockTransport，沒有任何測試會碰 live endpoint；
autouse fixture 另外把 build_http_client 換成會爆炸的版本，萬一漏注入也只會失敗不會外連。
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import subprocess
import sys
import uuid
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync_db  # noqa: E402
import sync_db_client as client_mod  # noqa: E402
import sync_db_import as imp  # noqa: E402
import sync_db_sources as src  # noqa: E402

BASE = "https://warehouse.test"
SYNC_ID, SYNC_SECRET = "sync-id.access", "sync-secret-value-DO-NOT-PRINT"
READ_ID, READ_SECRET = "read-id.access", "read-secret-value-DO-NOT-PRINT"
SOURCE = "supabase-2026-10-22"
SESSIONS_WARNING = "會與 rag-api 寫入衝突，僅限初次匯入"
REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_META_COMMENT = ('<!-- report_meta {"weeks": 2, "generated_at": "2026-09-29", '
                       '"generation_mode": "claude-code-semantic", "generation_label": "週報"} -->')


@pytest.fixture(autouse=True)
def _no_live_http(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("測試不得建立真的 HTTP client")
    monkeypatch.setattr(client_mod, "build_http_client", _boom)
    for name in ("CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VW_SYNC_ENV_FILE", "VW_APP_READ_ENV_FILE"):
        monkeypatch.delenv(name, raising=False)


# ── fixtures ─────────────────────────────────────────────


def report_row(date_key: str = "20260220", content: str | None = None, *, meta=None, filename: str | None = None,
               **extra) -> dict:
    text = content if content is not None else f"## 週報 {date_key}\n\n內文\n"
    return {"id": 7, "date_key": date_key, "filename": filename or f"report_{date_key}.md", "content": text,
            "size_bytes": len(text) + 50, "meta": meta, "deleted_at": None,
            "created_at": "2026-03-06 01:45:41.243011+00", **extra}


def prep_row(date_key: str = "20260220", content: str | None = None, *, meta="default", filename: str | None = None,
             **extra) -> dict:
    text = content if content is not None else f"# 會議準備 {date_key}\n"
    return {"date_key": date_key, "filename": filename or f"meeting_prep_{date_key}.md", "content": text,
            "size_bytes": len(text.encode("utf-8")), "meta": {"alert_down_count": 6} if meta == "default" else meta,
            "created_at": "2026-04-13 02:31:39.916207+00", "updated_at": "2026-04-13 02:31:40.202356+00", **extra}


def session_row(sid: str | None = None, title: str = "轉址式 404?", messages: list | None = None, **extra) -> dict:
    msgs = [{"role": "user", "content": "q", "created_at": "2026-05-11T02:19:31Z", "metadata": {}, "sources": []}] \
        if messages is None else messages
    return {"id": sid or str(uuid.uuid4()), "title": title, "messages": msgs, "metadata": {}, "deleted_at": None,
            "created_at": "2026-05-11 02:19:31.481+00", "updated_at": "2026-05-11 02:19:45.3+00", **extra}


def write_export(directory: Path, *, reports=(), meeting_prep=(), sessions=(), manifest: bool = True) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    tables = {}
    for name, rows in (("reports", reports), ("meeting_prep", meeting_prep), ("sessions", sessions)):
        raw = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode("utf-8")
        blob = gzip.compress(raw, mtime=0)
        (directory / f"{name}.ndjson.gz").write_bytes(blob)
        tables[name] = {"file": f"{name}.ndjson.gz", "rows": len(rows), "sha256": hashlib.sha256(blob).hexdigest()}
    if manifest:
        (directory / "manifest.json").write_text(json.dumps({"exported_at": "2026-10-22", "tables": tables}))
    return directory


class FakeWarehouse:
    """記錄請求；POST 依 content_hash 回 created／skipped／updated；GET 回已寫入內容（可預載或覆寫）。"""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.store: dict[tuple[str, str], dict] = {}
        self.post_override = None
        self.get_override = None

    @property
    def posts(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == "POST"]

    @property
    def gets(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == "GET"]

    def post_bodies(self, table: str | None = None) -> list[list[dict]]:
        return [json.loads(r.content) for r in self.posts if table is None or r.url.path.endswith(f"/{table}")]

    def preload(self, table: str, item: dict) -> None:
        key = item["id" if table == "sessions" else "date_key"]
        self.store[(table, key)] = item

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "POST":
            return self.post_override(request) if self.post_override else self._post(request)
        if self.get_override:
            response = self.get_override(request)
            if response is not None:
                return response
        return self._get(request)

    def _post(self, request: httpx.Request) -> httpx.Response:
        table = request.url.path.rsplit("/", 1)[-1]
        force = request.url.params.get("force") == "true"
        key_field = "id" if table == "sessions" else "date_key"
        results = []
        for item in json.loads(request.content):
            key = item[key_field]
            old = self.store.get((table, key))
            if old is None:
                result = "created"
            elif old["content_hash"] == item["content_hash"] and not force:
                result = "skipped"
            else:
                result = "updated"
            if result != "skipped":
                self.store[(table, key)] = item
            results.append({"key": key, "result": result, "content_hash": item["content_hash"]})
        return httpx.Response(200, json={"data": {"table": table, "force": force, "results": results,
                                                  "counts": {}}, "error": None, "meta": {}})

    def _get(self, request: httpx.Request) -> httpx.Response:
        parts = request.url.path.split("/")
        route, key = parts[-2], parts[-1]
        table = {"reports": "reports", "meeting-prep": "meeting_prep", "sessions": "sessions"}[route]
        item = self.store.get((table, key))
        if item is None:
            return httpx.Response(404, json={"data": None, "error": "not found", "meta": {}})
        if table == "sessions":
            data = {"id": item["id"], "title": item["title"], "messages": item["messages"]}
        else:
            data = {"date": item["date_key"], "filename": item.get("filename"), "content": item["content"]}
        return httpx.Response(200, json={"data": data, "error": None, "meta": {}})


@pytest.fixture()
def wh() -> FakeWarehouse:
    return FakeWarehouse()


@pytest.fixture()
def env(tmp_path) -> dict:
    (tmp_path / "sync.env").write_text(f"CF_ACCESS_CLIENT_ID={SYNC_ID}\nCF_ACCESS_CLIENT_SECRET={SYNC_SECRET}\n")
    (tmp_path / "app-read.env").write_text(f"CF_ACCESS_CLIENT_ID={READ_ID}\nCF_ACCESS_CLIENT_SECRET={READ_SECRET}\n")
    return {"VW_SYNC_ENV_FILE": str(tmp_path / "sync.env"), "VW_APP_READ_ENV_FILE": str(tmp_path / "app-read.env")}


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def run(directory: Path, wh: FakeWarehouse, env: dict, *args: str, err=None):
    out, err = io.StringIO(), err or io.StringIO()
    http = httpx.Client(transport=httpx.MockTransport(wh.handler))
    code = sync_db.main(["upload", "--from-ndjson", str(directory), *args, "--base-url", BASE],
                        root=REPO_ROOT, http=http, environ=env, out=out, err=err)
    text = out.getvalue() + err.getvalue()
    assert SYNC_SECRET not in text and READ_SECRET not in text
    return code, text


# ── 逐列轉換 ─────────────────────────────────────────────


class TestRowConversion:
    def test_report_keeps_filename_and_meta_and_adds_source(self):
        item = imp.build_item("reports", report_row("20260322_f6733b08", meta={"weeks": 3},
                                                    filename="report_custom.md"))
        assert item["date_key"] == "20260322_f6733b08"
        assert item["filename"] == "report_custom.md"
        assert item["meta"] == {"weeks": 3, "source": SOURCE}
        assert item["content_hash"] == src.text_content_hash(item["content"].encode("utf-8"))

    def test_report_null_meta_falls_back_to_content_report_meta(self):
        """meta NULL 時讀取路由靠內文 report_meta 解析；若直接塞 {"source"} 會讓 fallback 失效，所以先解析再加 source。"""
        item = imp.build_item("reports", report_row(content=f"{REPORT_META_COMMENT}\n\n內文"))
        assert item["meta"]["weeks"] == 2
        assert item["meta"]["generation_label"] == "週報"
        assert item["meta"]["source"] == SOURCE

    def test_report_null_meta_without_embedded_meta_only_has_source(self):
        assert imp.build_item("reports", report_row(content="無 meta"))["meta"] == {"source": SOURCE}

    def test_row_only_sends_endpoint_fields(self):
        """不送 id、size_bytes、deleted_at、approved_version（server extra=forbid；歷史列 approved_version NULL）。"""
        item = imp.build_item("reports", report_row())
        assert set(item) == {"date_key", "filename", "content", "meta", "content_hash", "created_at"}

    def test_meeting_prep_filename_is_mandatory_and_original(self):
        item = imp.build_item("meeting_prep", prep_row("20260220", filename="meeting_prep_20260220_v33.md"))
        assert item["filename"] == "meeting_prep_20260220_v33.md"
        assert item["meta"] == {"alert_down_count": 6, "source": SOURCE}
        assert set(item) == {"date_key", "filename", "content", "meta", "content_hash", "created_at"}

    def test_meeting_prep_updated_at_is_not_sent(self):
        assert "updated_at" not in imp.build_item("meeting_prep", prep_row())

    def test_meeting_prep_null_meta_is_parsed_or_empty(self):
        item = imp.build_item("meeting_prep", prep_row(meta=None, content="無 meta"))
        assert item["meta"] == {"source": SOURCE}

    def test_session_hash_uses_current_algorithm_and_metadata_gets_source(self):
        row = session_row("0192a6e4-0d00-463f-a3ab-dfa3ef098dc2", metadata={"maturity_level": "L2"})
        item = imp.build_item("sessions", row)
        assert item["content_hash"] == src.session_content_hash(row["title"], row["messages"])
        assert item["metadata"] == {"maturity_level": "L2", "source": SOURCE}
        assert item["updated_at"] == "2026-05-11T02:19:45.300000+00:00"
        assert set(item) == {"id", "title", "messages", "metadata", "content_hash", "created_at", "updated_at"}

    def test_timestamps_are_normalised_to_iso8601_with_offset(self):
        item = imp.build_item("reports", report_row())
        assert item["created_at"] == "2026-03-06T01:45:41.243011+00:00"

    def test_missing_created_at_is_omitted(self):
        row = report_row()
        row["created_at"] = None
        assert "created_at" not in imp.build_item("reports", row)

    @pytest.mark.parametrize("table,row,needle", [
        ("reports", report_row("bad/key"), "date_key"),
        ("reports", report_row(filename="../x.md"), "filename"),
        ("reports", report_row(content="a\x00b"), "content"),
        ("reports", report_row(content="\ud800"), "content"),
        ("reports", report_row(created_at="not-a-date"), "created_at"),
        ("reports", report_row(created_at="2026-03-06 01:45:41"), "created_at"),
        ("meeting_prep", {**prep_row(), "filename": None}, "filename"),
        ("sessions", session_row("not-a-uuid"), "id"),
        ("sessions", session_row(title="x" * 201), "title"),
        ("sessions", session_row(messages=["not-an-object"]), "messages"),
    ])
    def test_invalid_rows_are_rejected_with_field_name(self, table, row, needle):
        with pytest.raises(imp.InvalidRow) as exc:
            imp.build_item(table, row)
        assert needle in exc.value.reason

    def test_session_id_is_lowercased_canonical(self):
        sid = "0192A6E4-0D00-463F-A3AB-DFA3EF098DC2"
        assert imp.build_item("sessions", session_row(sid))["id"] == sid.lower()


# ── dry-run ──────────────────────────────────────────────


class TestDryRun:
    def test_zero_http_no_credentials_and_banner(self, tmp_path, wh):
        directory = write_export(tmp_path / "x", reports=[report_row()], meeting_prep=[prep_row()],
                                 sessions=[session_row()])
        code, text = run(directory, wh, {}, "--dry-run")
        assert code == 0 and wh.requests == []
        assert "歷史匯入模式，未經發布閘門" in text
        assert "dry-run" in text
        for table in ("reports", "meeting_prep"):
            assert table in text
        assert "sessions" not in text and SESSIONS_WARNING not in text

    def test_explicit_sessions_dry_run_warns_about_rag_api_conflict(self, tmp_path, wh):
        directory = write_export(tmp_path / "x", sessions=[session_row()])
        code, text = run(directory, wh, {}, "--dry-run", "--type", "sessions")
        assert code == 0 and wh.requests == []
        assert SESSIONS_WARNING in text and "== sessions ==" in text

    def test_dry_run_lists_batch_sizes(self, tmp_path, wh):
        directory = write_export(tmp_path / "x", sessions=[session_row() for _ in range(120)])
        code, text = run(directory, wh, {}, "--dry-run", "--type", "sessions")
        assert code == 0 and "[50, 50, 20]" in text

    def test_dry_run_still_fails_on_invalid_rows(self, tmp_path, wh):
        directory = write_export(tmp_path / "x", reports=[report_row("bad/key")])
        code, text = run(directory, wh, {}, "--dry-run", "--type", "reports")
        assert code == 1 and "bad/key" in text and wh.requests == []


# ── 上傳、去重、切批 ─────────────────────────────────────


class TestUpload:
    def test_creates_all_rows_and_verifies(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220"), report_row("20260221")],
                                 meeting_prep=[prep_row("20260220", filename="meeting_prep_20260220_v33.md")],
                                 sessions=[session_row("0192a6e4-0d00-463f-a3ab-dfa3ef098dc2")])
        code, text = run(directory, wh, env)
        assert code == 0
        assert "歷史匯入模式，未經發布閘門" in text
        assert "[created] reports 20260220" in text
        assert "verified 3" in text and "mismatch 0" in text
        sent = wh.post_bodies("meeting_prep")[0][0]
        assert sent["filename"] == "meeting_prep_20260220_v33.md" and "approved_version" not in sent
        assert ("sessions", "0192a6e4-0d00-463f-a3ab-dfa3ef098dc2") not in wh.store

    def test_explicit_sessions_import_writes_source_metadata(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", sessions=[session_row("0192a6e4-0d00-463f-a3ab-dfa3ef098dc2")])
        code, _ = run(directory, wh, env, "--type", "sessions")
        assert code == 0
        assert wh.store[("sessions", "0192a6e4-0d00-463f-a3ab-dfa3ef098dc2")]["metadata"] == {"source": SOURCE}

    def test_requests_carry_sync_and_read_tokens_on_right_routes(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        run(directory, wh, env, "--type", "reports")
        for request in wh.posts:
            assert request.headers["CF-Access-Client-Id"] == SYNC_ID
            assert request.url.path == "/internal/sync/reports" and "force" not in request.url.params
        for request in wh.gets:
            assert request.headers["CF-Access-Client-Id"] == READ_ID

    def test_remote_same_hash_is_skipped_without_post(self, tmp_path, wh, env):
        row = report_row("20260911_961c2c5f", content="same content")
        wh.preload("reports", imp.build_item("reports", row))
        directory = write_export(tmp_path / "x", reports=[row, report_row("20260220")])
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 0
        assert "[skipped] reports 20260911_961c2c5f" in text
        posted = [item["date_key"] for body in wh.post_bodies() for item in body]
        assert posted == ["20260220"]
        assert "verified 2" in text

    def test_remote_differs_is_withheld_and_flagged_nonzero(self, tmp_path, wh, env):
        wh.preload("reports", imp.build_item("reports", report_row("20260911_961c2c5f", content="remote version")))
        directory = write_export(tmp_path / "x", reports=[report_row("20260911_961c2c5f", content="supabase version")])
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1
        assert "[conflict] reports 20260911_961c2c5f" in text
        assert wh.posts == []
        assert wh.store[("reports", "20260911_961c2c5f")]["content"] == "remote version"
        assert "--force" in text

    def test_force_overwrites_differing_rows_and_flags_them(self, tmp_path, wh, env):
        wh.preload("reports", imp.build_item("reports", report_row("20260911_961c2c5f", content="remote version")))
        directory = write_export(tmp_path / "x", reports=[report_row("20260911_961c2c5f", content="supabase version")])
        code, text = run(directory, wh, env, "--type", "reports", "--force")
        assert code == 0
        assert "[overwrite] reports 20260911_961c2c5f" in text
        assert wh.store[("reports", "20260911_961c2c5f")]["content"] == "supabase version"
        assert wh.posts[0].url.params["force"] == "true"

    def test_unexpected_updated_without_force_is_flagged(self, tmp_path, wh, env):
        """預檢之後遠端才被改（競態）：POST 回 updated 也要標示，不能靜默通過。"""
        directory = write_export(tmp_path / "x", reports=[report_row("20260220")])
        wh.post_override = lambda request: httpx.Response(200, json={"data": {"results": [
            {"key": "20260220", "result": "updated",
             "content_hash": json.loads(request.content)[0]["content_hash"]}]}})
        _, text = run(directory, wh, env, "--type", "reports")
        assert "[overwrite] reports 20260220" in text

    def test_conflicts_are_red_on_a_tty(self, tmp_path, wh, env):
        wh.preload("reports", imp.build_item("reports", report_row("20260220", content="remote")))
        directory = write_export(tmp_path / "x", reports=[report_row("20260220", content="local")])
        err = _Tty()
        run(directory, wh, env, "--type", "reports", err=err)
        assert "\x1b[31m" in err.getvalue() and "[conflict]" in err.getvalue()

    def test_no_color_when_not_a_tty(self, tmp_path, wh, env):
        wh.preload("reports", imp.build_item("reports", report_row("20260220", content="remote")))
        directory = write_export(tmp_path / "x", reports=[report_row("20260220", content="local")])
        _, text = run(directory, wh, env, "--type", "reports")
        assert "\x1b[" not in text

    def test_meeting_prep_prefix_fallback_is_treated_as_missing(self, tmp_path, wh, env):
        """讀取路由精確鍵找不到時回同日最新一筆（date 不同）；預檢必須視為不存在而不是衝突。"""
        wh.get_override = lambda r: httpx.Response(200, json={"data": {
            "date": "20260220_aaaaaaaa", "filename": "x.md", "content": "other"}}) \
            if r.url.path.endswith("/20260220") and not wh.posts else None
        directory = write_export(tmp_path / "x", meeting_prep=[prep_row("20260220")])
        code, text = run(directory, wh, env, "--type", "meeting-prep")
        assert code == 0 and "[created] meeting_prep 20260220" in text

    def test_session_remote_existing_same_title_and_count_is_skipped(self, tmp_path, wh, env):
        row = session_row("0192a6e4-0d00-463f-a3ab-dfa3ef098dc2")
        wh.preload("sessions", imp.build_item("sessions", row))
        directory = write_export(tmp_path / "x", sessions=[row])
        code, text = run(directory, wh, env, "--type", "sessions")
        assert code == 0 and wh.posts == [] and "[skipped] sessions" in text

    def test_sessions_split_into_batches_of_50(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", sessions=[session_row() for _ in range(120)])
        code, _ = run(directory, wh, env, "--type", "sessions")
        assert code == 0
        assert [len(b) for b in wh.post_bodies("sessions")] == [50, 50, 20]

    def test_type_filter_reads_only_selected_table(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()], sessions=[session_row()])
        (directory / "meeting_prep.ndjson.gz").unlink()
        code, _ = run(directory, wh, env, "--type", "reports")
        assert code == 0
        assert all(r.url.path.endswith("/reports") or "/reports/" in r.url.path for r in wh.requests)

    def test_soft_deleted_rows_are_excluded_not_resurrected(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[
            report_row("20260220"), report_row("20260221", deleted_at="2026-09-01 00:00:00+00")])
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 0
        assert "[excluded:soft_deleted] reports 20260221" in text
        assert [i["date_key"] for b in wh.post_bodies() for i in b] == ["20260220"]


class TestBatchBoundary:
    @staticmethod
    def _rows_for_total(extra: int) -> list[dict]:
        """兩筆 report 序列化後 body 剛好 MAX_BODY_BYTES + extra。"""
        keys = ("20260101", "20260102")
        probe = [imp.build_item("reports", report_row(k, content="")) for k in keys]
        pad = client_mod.MAX_BODY_BYTES + extra - len(client_mod.encode_body(probe))
        first = pad // 2
        return [report_row(keys[0], content="a" * first), report_row(keys[1], content="a" * (pad - first))]

    def test_exactly_at_limit_fits_one_batch(self, tmp_path, wh, env):
        rows = self._rows_for_total(0)
        assert len(client_mod.encode_body([imp.build_item("reports", r) for r in rows])) == client_mod.MAX_BODY_BYTES
        code, _ = run(write_export(tmp_path / "x", reports=rows), wh, env, "--type", "reports")
        assert code == 0 and [len(b) for b in wh.post_bodies()] == [2]

    def test_one_byte_over_splits_into_two_batches(self, tmp_path, wh, env):
        code, _ = run(write_export(tmp_path / "x", reports=self._rows_for_total(1)), wh, env, "--type", "reports")
        assert code == 0 and [len(b) for b in wh.post_bodies()] == [1, 1]

    def test_single_row_over_limit_aborts_listing_every_key(self, tmp_path, wh, env):
        huge = "a" * (client_mod.MAX_BODY_BYTES + 10)
        directory = write_export(tmp_path / "x", reports=[report_row("20260101", content=huge),
                                                          report_row("20260102"),
                                                          report_row("20260103", content=huge)])
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and wh.requests == []
        assert "20260101" in text and "20260103" in text and "[上限]" in text

    def test_multibyte_content_is_measured_in_bytes(self, tmp_path, wh, env):
        """中文一字 3 bytes：字元數遠低於上限，位元組超過就必須切批。"""
        text = "字" * 400_000
        rows = [report_row("20260101", content=text), report_row("20260102", content=text)]
        code, _ = run(write_export(tmp_path / "x", reports=rows), wh, env, "--type", "reports")
        assert code == 0 and [len(b) for b in wh.post_bodies()] == [1, 1]


# ── 讀回對帳 ─────────────────────────────────────────────


class TestReadback:
    def test_mismatch_after_write_exits_nonzero_and_counts(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220"), report_row("20260221")])

        def tampered(request):
            if request.url.path.endswith("/20260221") and wh.posts:
                return httpx.Response(200, json={"data": {"date": "20260221", "content": "tampered"}})
            return None
        wh.get_override = tampered
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1
        assert "[mismatch] reports 20260221" in text and "[verified] reports 20260220" in text
        assert "verified 1" in text and "mismatch 1" in text

    def test_readback_404_is_mismatch(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220")])
        wh.get_override = lambda r: httpx.Response(404, json={"error": "nf"}) if wh.posts else None
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "mismatch 1" in text

    def test_readback_http_error_is_mismatch(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220")])
        wh.get_override = lambda r: httpx.Response(500, json={"error": "boom"}) if wh.posts else None
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "mismatch 1" in text and "boom" in text

    def test_session_mismatch_on_message_count(self, tmp_path, wh, env):
        sid = "0192a6e4-0d00-463f-a3ab-dfa3ef098dc2"
        directory = write_export(tmp_path / "x", sessions=[session_row(sid)])
        wh.get_override = lambda r: httpx.Response(200, json={"data": {"id": sid, "title": "轉址式 404?",
                                                                       "messages": []}}) if wh.posts else None
        code, text = run(directory, wh, env, "--type", "sessions")
        assert code == 1 and "[mismatch] sessions" in text

    def test_post_error_exits_nonzero_and_failed_rows_are_not_read_back(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220")])
        wh.post_override = lambda r: httpx.Response(422, json={"data": None, "error": "rejected_by_db"})
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "rejected_by_db" in text
        assert [r for r in wh.gets if wh.posts and r.url.path.endswith("/20260220")][1:] == []
        assert "mismatch 0" in text

    def test_response_hash_mismatch_is_error(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220")])
        wh.post_override = lambda r: httpx.Response(200, json={"data": {"results": [
            {"key": "20260220", "result": "created", "content_hash": "sha256:" + "0" * 64}]}})
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "hash_mismatch" in text

    def test_precheck_http_error_blocks_that_row_and_fails(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220"), report_row("20260221")])
        wh.get_override = lambda r: httpx.Response(503, json={"error": "Store unavailable"}) \
            if r.url.path.endswith("/20260220") and not wh.posts else None
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "Store unavailable" in text
        assert [i["date_key"] for b in wh.post_bodies() for i in b] == ["20260221"]


# ── 輸入檔、憑證、參數 ────────────────────────────────────


class TestInputsAndConfig:
    def test_missing_directory_exits_2(self, tmp_path, wh, env):
        code, text = run(tmp_path / "nope", wh, env)
        assert code == 2 and wh.requests == []

    def test_missing_table_file_exits_2(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        (directory / "meeting_prep.ndjson.gz").unlink()
        code, text = run(directory, wh, env)
        assert code == 2 and "meeting_prep.ndjson.gz" in text and wh.requests == []

    def test_default_all_does_not_read_or_require_sessions(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()], meeting_prep=[prep_row()],
                                 sessions=[session_row()])
        (directory / "sessions.ndjson.gz").unlink()
        code, text = run(directory, wh, env)
        assert code == 0 and SESSIONS_WARNING not in text
        assert not any("/sessions" in r.url.path for r in wh.requests)

    def test_default_all_with_sessions_present_never_posts_sessions(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()], meeting_prep=[prep_row()],
                                 sessions=[session_row()])
        code, _ = run(directory, wh, env)
        assert code == 0 and wh.post_bodies("sessions") == []
        assert wh.post_bodies("reports") and wh.post_bodies("meeting_prep")

    def test_explicit_sessions_import_warns_and_still_works(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", sessions=[session_row()])
        code, text = run(directory, wh, env, "--type", "sessions")
        assert code == 0 and SESSIONS_WARNING in text
        assert len(wh.post_bodies("sessions")) == 1

    def test_malformed_line_reports_line_number_without_content(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()], manifest=False)
        (directory / "reports.ndjson.gz").write_bytes(
            gzip.compress('{"date_key": "SECRET-BODY-TEXT\n'.encode("utf-8")))
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "reports" in text and "第 1 行" in text
        assert "SECRET-BODY-TEXT" not in text and wh.requests == []

    def test_corrupt_gzip_is_reported(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()], manifest=False)
        (directory / "reports.ndjson.gz").write_bytes(b"not gzip")
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "reports.ndjson.gz" in text and wh.requests == []

    def test_non_object_line_is_reported(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", manifest=False)
        (directory / "reports.ndjson.gz").write_bytes(gzip.compress(b"[1,2]\n"))
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "第 1 行" in text

    def test_blank_lines_are_ignored(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", manifest=False)
        line = json.dumps(report_row("20260220"), ensure_ascii=False)
        (directory / "reports.ndjson.gz").write_bytes(gzip.compress(f"\n{line}\n\n".encode("utf-8")))
        code, _ = run(directory, wh, env, "--type", "reports")
        assert code == 0

    def test_invalid_rows_abort_before_any_http_and_list_keys(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220"), report_row("bad/key"),
                                                          report_row("20260221", content="a\x00b")])
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and wh.requests == []
        assert "bad/key" in text and "20260221" in text

    def test_duplicate_keys_in_export_abort(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row("20260220"), report_row("20260220")])
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 1 and "20260220" in text and wh.requests == []

    def test_session_ids_duplicate_ignoring_case_abort(self, tmp_path, wh, env):
        sid = "0192a6e4-0d00-463f-a3ab-dfa3ef098dc2"
        directory = write_export(tmp_path / "x", sessions=[session_row(sid), session_row(sid.upper())])
        code, text = run(directory, wh, env, "--type", "sessions")
        assert code == 1 and wh.requests == []

    def test_manifest_row_count_mismatch_exits_2(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        manifest = json.loads((directory / "manifest.json").read_text())
        manifest["tables"]["reports"]["rows"] = 99
        (directory / "manifest.json").write_text(json.dumps(manifest))
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 2 and "manifest" in text and wh.requests == []

    def test_manifest_sha_mismatch_exits_2(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        manifest = json.loads((directory / "manifest.json").read_text())
        manifest["tables"]["reports"]["sha256"] = "0" * 64
        (directory / "manifest.json").write_text(json.dumps(manifest))
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 2 and "sha256" in text and wh.requests == []

    def test_missing_manifest_only_warns(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()], manifest=False)
        code, text = run(directory, wh, env, "--type", "reports")
        assert code == 0 and "manifest" in text

    def test_broken_manifest_exits_2(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        (directory / "manifest.json").write_text("{not json")
        code, _ = run(directory, wh, env, "--type", "reports")
        assert code == 2

    def test_missing_sync_credentials_exit_2_without_http(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        code, text = run(directory, wh, {**env, "VW_SYNC_ENV_FILE": str(tmp_path / "absent.env")})
        assert code == 2 and wh.requests == []

    def test_missing_read_credentials_exit_2_without_http(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        code, text = run(directory, wh, {**env, "VW_APP_READ_ENV_FILE": str(tmp_path / "absent.env")})
        assert code == 2 and wh.requests == [] and "app-read" in text

    def test_no_readback_flag_is_rejected_in_import_mode(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        code, text = run(directory, wh, env, "--no-readback")
        assert code == 2 and wh.requests == [] and "--no-readback" in text

    def test_empty_export_is_success_without_http(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x")
        code, text = run(directory, wh, env)
        assert code == 0 and wh.requests == []

    def test_non_https_base_url_rejected(self, tmp_path, wh, env):
        directory = write_export(tmp_path / "x", reports=[report_row()])
        out, err = io.StringIO(), io.StringIO()
        code = sync_db.main(["upload", "--from-ndjson", str(directory), "--base-url", "http://x"],
                            root=REPO_ROOT, http=httpx.Client(transport=httpx.MockTransport(wh.handler)),
                            environ=env, out=out, err=err)
        assert code == 2 and wh.requests == []

    def test_regular_upload_still_works_without_flag(self, tmp_path, wh, env):
        """沒帶 --from-ndjson 時走原本的帳冊閘門流程（本測試用空 repo，只確認沒被匯入模式攔截）。"""
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "content-publication-review.json").write_text(json.dumps({"version": 1, "entries": []}))
        (tmp_path / "output").mkdir()
        out, err = io.StringIO(), io.StringIO()
        code = sync_db.main(["upload", "--dry-run", "--type", "reports", "--base-url", BASE], root=tmp_path,
                            http=httpx.Client(transport=httpx.MockTransport(wh.handler)),
                            environ=env, out=out, err=err)
        assert code == 0 and "歷史匯入模式" not in out.getvalue()


class TestMakefile:
    @pytest.mark.parametrize("target,needles", [
        ("sync-db-import-ndjson", ["--from-ndjson", "/some/dir"]),
        ("sync-db-import-ndjson-dry", ["--from-ndjson", "/some/dir", "--dry-run"]),
    ])
    def test_targets_expand_to_the_cli(self, target, needles):
        result = subprocess.run(["make", "-n", target, "DIR=/some/dir"], cwd=REPO_ROOT,
                                capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert all(n in result.stdout for n in needles)

    def test_target_requires_dir(self):
        result = subprocess.run(["make", "-n", "sync-db-import-ndjson"], cwd=REPO_ROOT,
                                capture_output=True, text=True, check=False)
        assert result.returncode != 0
