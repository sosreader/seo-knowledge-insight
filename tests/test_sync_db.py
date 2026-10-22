"""scripts/sync_db.py ＋ sync_db_client.py：/sync-db 經 warehouse-api 推送到 vocus-warehouse。

全部 HTTP 走 httpx.MockTransport，沒有任何測試會碰 live endpoint；
autouse fixture 另外把 build_http_client 換成會爆炸的版本，萬一漏注入也只會失敗不會外連。
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync_db  # noqa: E402
import sync_db_client as client_mod  # noqa: E402
import sync_db_sources as src  # noqa: E402

BASE = "https://warehouse.test"
SYNC_ID, SYNC_SECRET = "sync-id.access", "sync-secret-value-DO-NOT-PRINT"
READ_ID, READ_SECRET = "read-id.access", "read-secret-value-DO-NOT-PRINT"
REPORT = "report_20261012_900a1937.md"
PREP = "meeting_prep_20261009_0fc3dcbc.md"
UUID_A = "0b3c8f4e-1d2a-4b5c-9d8e-7f6a5b4c3d2e"


# ── fixtures ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _no_live_http(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("測試不得建立真的 HTTP client")
    monkeypatch.setattr(client_mod, "build_http_client", _boom)
    for name in ("CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VW_SYNC_ENV_FILE", "VW_APP_READ_ENV_FILE"):
        monkeypatch.delenv(name, raising=False)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "data").mkdir()
        (root / "output" / "sessions").mkdir(parents=True)
        self.entries: list[dict] = []
        self.env = {"VW_SYNC_ENV_FILE": str(root / "sync.env"), "VW_APP_READ_ENV_FILE": str(root / "app-read.env")}
        (root / "sync.env").write_text(f"CF_ACCESS_CLIENT_ID={SYNC_ID}\nCF_ACCESS_CLIENT_SECRET={SYNC_SECRET}\n")
        (root / "app-read.env").write_text(
            f"# comment\nexport CF_ACCESS_CLIENT_ID=\"{READ_ID}\"\nCF_ACCESS_CLIENT_SECRET='{READ_SECRET}'\n")

    def doc(self, filename: str, content: str, status: str | None = "approved", ledger_content: str | None = None):
        (self.root / "output" / filename).write_text(content, encoding="utf-8")
        if status is not None:
            self.entries.append({
                "filename": filename, "sha256": _sha((ledger_content or content).encode("utf-8")),
                "status": status, "reviewed_by": "tester", "reviewed_at": "2026-10-12", "reason": "fixture",
            })
        self.write_manifest()

    def session(self, sid: str, title: str = "t", messages: list | None = None) -> dict:
        data = {"id": sid, "title": title, "messages": messages or [{"role": "user", "content": "q"}],
                "metadata": {}, "created_at": "2026-10-01T00:00:00.000Z", "updated_at": "2026-10-02T00:00:00.000Z"}
        (self.root / "output" / "sessions" / f"{sid}.json").write_text(json.dumps(data), encoding="utf-8")
        return data

    def write_manifest(self) -> None:
        (self.root / "data" / "content-publication-review.json").write_text(
            json.dumps({"version": 1, "entries": self.entries}), encoding="utf-8")


@pytest.fixture()
def repo(tmp_path) -> Repo:
    return Repo(tmp_path)


class FakeWarehouse:
    """記錄每個請求；POST 預設逐筆 created 並回寫入端 hash；GET 回已寫入內容。"""

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

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "POST":
            if self.post_override:
                return self.post_override(request)
            return self._post(request)
        if self.get_override:
            resp = self.get_override(request)
            if resp is not None:
                return resp
        return self._get(request)

    def _post(self, request: httpx.Request) -> httpx.Response:
        table = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content)
        key_field = "id" if table == "sessions" else "date_key"
        results = []
        for item in body:
            key = item[key_field]
            existed = (table, key) in self.store
            self.store[(table, key)] = item
            results.append({"key": key, "result": "updated" if existed else "created",
                            "content_hash": item["content_hash"]})
        return httpx.Response(200, json={"data": {"table": table, "force": False, "results": results,
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


def run(repo: Repo, wh: FakeWarehouse, *args: str, env: dict | None = None):
    out, err = io.StringIO(), io.StringIO()
    http = httpx.Client(transport=httpx.MockTransport(wh.handler))
    code = sync_db.main([*args, "--base-url", BASE], root=repo.root, http=http,
                        environ=repo.env if env is None else env, out=out, err=err)
    text = out.getvalue() + err.getvalue()
    assert SYNC_SECRET not in text and READ_SECRET not in text
    return code, text


# ── 發布閘門 ─────────────────────────────────────────────


class TestGate:
    def test_only_approved_versions_are_posted(self, repo, wh):
        repo.doc(REPORT, "approved report")
        repo.doc("report_20261005_aaaaaaaa.md", "unregistered", status=None)
        repo.doc("report_20260904_9d41f7b2.md", "historical", status="historical")
        repo.doc("report_20260905_bbbbbbbb.md", "pending", status="pending")
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 0
        sent = [json.loads(r.content) for r in wh.posts]
        assert [[i["date_key"] for i in batch] for batch in sent] == [["20261012_900a1937"]]
        assert sent[0][0]["content_hash"] == "sha256:" + _sha(b"approved report")
        assert "missing_review" in text and "historical" in text and "pending" in text

    def test_hash_mismatch_aborts_before_any_http_and_lists_files(self, repo, wh):
        repo.doc(REPORT, "edited after review", ledger_content="reviewed text")
        repo.doc(PREP, "fine")
        code, text = run(repo, wh, "upload")
        assert code == 1
        assert wh.requests == []
        assert REPORT in text and "content_changed" in text
        assert _sha(b"reviewed text")[:12] in text and _sha(b"edited after review")[:12] in text

    @pytest.mark.parametrize("broken", ["missing", "malformed"])
    def test_manifest_unavailable_fails_closed(self, repo, wh, broken):
        repo.doc(REPORT, "x")
        manifest = repo.root / "data" / "content-publication-review.json"
        if broken == "missing":
            manifest.unlink()
        else:
            manifest.write_text("secret-ish garbage", encoding="utf-8")
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and wh.requests == []
        assert "review_manifest_unavailable" in text and "secret-ish" not in text

    def test_sessions_do_not_need_manifest(self, repo, wh):
        repo.session(UUID_A)
        (repo.root / "data" / "content-publication-review.json").unlink(missing_ok=True)
        code, _ = run(repo, wh, "upload", "--type", "sessions")
        assert code == 0
        assert len(wh.posts) == 1 and wh.posts[0].url.path == "/internal/sync/sessions"

    def test_force_still_gated_and_sets_query(self, repo, wh):
        repo.doc(REPORT, "ok")
        repo.doc("report_20260904_9d41f7b2.md", "h", status="historical")
        code, _ = run(repo, wh, "upload", "--type", "reports", "--force")
        assert code == 0
        assert len(wh.posts) == 1
        assert parse_qs(wh.posts[0].url.query.decode()) == {"force": ["true"]}
        assert [i["date_key"] for i in json.loads(wh.posts[0].content)] == ["20261012_900a1937"]

    def test_ledger_approved_without_local_file_is_reported(self, repo, wh):
        repo.entries.append({"filename": PREP, "sha256": "a" * 64, "status": "approved", "reviewed_by": "r",
                             "reviewed_at": "2026-10-12", "reason": "x"})
        repo.write_manifest()
        code, text = run(repo, wh, "upload", "--type", "meeting_prep", "--dry-run")
        assert code == 0 and PREP in text and "本機找不到" in text


# ── dry-run ──────────────────────────────────────────────


class TestDryRun:
    def test_zero_http_and_no_credentials_needed(self, repo, wh):
        repo.doc(REPORT, "r")
        repo.doc(PREP, "p")
        repo.session(UUID_A)
        (repo.root / "sync.env").unlink()
        (repo.root / "app-read.env").unlink()
        code, text = run(repo, wh, "upload", "--dry-run")
        assert code == 0
        assert wh.requests == []
        assert "20261012_900a1937" in text and "20261009_0fc3dcbc" in text and UUID_A in text
        assert "dry-run" in text

    def test_non_utf8_approved_file_blocks(self, repo, wh):
        path = repo.root / "output" / REPORT
        path.write_bytes(b"\xff\xfe")
        repo.entries.append({"filename": REPORT, "sha256": _sha(b"\xff\xfe"), "status": "approved",
                             "reviewed_by": "r", "reviewed_at": "2026-10-12", "reason": "x"})
        repo.write_manifest()
        code, text = run(repo, wh, "upload", "--dry-run")
        assert code == 1 and "invalid_utf8" in text and wh.requests == []

    def test_unserialisable_item_aborts(self, repo, wh, monkeypatch):
        repo.doc(REPORT, "r")
        monkeypatch.setattr(client_mod, "encode_body", lambda items: (_ for _ in ()).throw(ValueError("nan")))
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and "序列化" in text and wh.requests == []

    def test_dry_run_with_drift_still_fails(self, repo, wh):
        repo.doc(REPORT, "new", ledger_content="old")
        code, _ = run(repo, wh, "upload", "--dry-run")
        assert code == 1 and wh.requests == []


# ── 分批與大小上限 ───────────────────────────────────────


class TestBatching:
    def test_sessions_split_into_batches_of_50(self, repo, wh):
        ids = [f"0b3c8f4e-1d2a-4b5c-9d8e-{i:012x}" for i in range(120)]
        for sid in ids:
            repo.session(sid)
        code, _ = run(repo, wh, "upload", "--type", "sessions", "--no-readback")
        assert code == 0
        assert [len(json.loads(r.content)) for r in wh.posts] == [50, 50, 20]
        posted = [i["id"] for r in wh.posts for i in json.loads(r.content)]
        assert sorted(posted) == sorted(ids)

    def test_plan_batches_respects_byte_limit(self):
        items = [{"k": "x" * 600} for _ in range(5)]
        batches = client_mod.plan_batches(items, max_items=50, max_bytes=1300)
        assert [len(b) for b in batches] == [2, 2, 1]
        for batch in batches:
            assert len(client_mod.encode_body(list(batch))) <= 1300

    def test_plan_batches_counts_utf8_bytes(self):
        items = [{"k": "週" * 200} for _ in range(3)]  # 每字 3 bytes
        batches = client_mod.plan_batches(items, max_items=50, max_bytes=1300)
        assert all(len(client_mod.encode_body(list(b))) <= 1300 for b in batches)
        assert len(batches) == 2

    def test_single_item_over_limit_raises(self):
        with pytest.raises(client_mod.ItemTooLarge) as exc:
            client_mod.plan_batches([{"date_key": "k1", "c": "x" * 100}], max_items=50, max_bytes=50)
        assert exc.value.index == 0

    def test_oversize_item_aborts_upload_before_any_http(self, repo, wh, monkeypatch):
        monkeypatch.setattr(client_mod, "MAX_BODY_BYTES", 200)
        repo.doc(REPORT, "x" * 500)
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and wh.requests == []
        assert "20261012_900a1937" in text and "上限" in text

    def test_real_limits_match_contract(self):
        assert client_mod.MAX_BATCH_ITEMS == 50
        assert client_mod.MAX_BODY_BYTES == 2 * 1024 * 1024


# ── 回應解析 ─────────────────────────────────────────────


def _resp(results, status=200):
    return httpx.Response(status, json={"data": {"results": results}, "error": None, "meta": {}})


class TestResponse:
    def test_prints_each_result_and_sends_access_headers(self, repo, wh):
        repo.doc(REPORT, "r")
        repo.doc(PREP, "p")
        code, text = run(repo, wh, "upload", "--type", "all")
        assert code == 0
        assert "created" in text
        for req in wh.posts:
            assert req.headers["CF-Access-Client-Id"] == SYNC_ID
            assert req.headers["CF-Access-Client-Secret"] == SYNC_SECRET
            assert req.headers["Content-Type"] == "application/json"
        for req in wh.gets:
            assert req.headers["CF-Access-Client-Id"] == READ_ID
        assert {r.url.path for r in wh.posts} == {"/internal/sync/reports", "/internal/sync/meeting_prep"}

    def test_skipped_and_updated_are_success(self, repo, wh):
        repo.doc(REPORT, "r")
        item_hash = "sha256:" + _sha(b"r")
        wh.store[("reports", "20261012_900a1937")] = {"date_key": "20261012_900a1937", "content": "r",
                                                       "content_hash": item_hash}
        wh.post_override = lambda req: _resp([{"key": "20261012_900a1937", "result": "skipped",
                                               "content_hash": item_hash}])
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 0 and "skipped" in text

    @pytest.mark.parametrize("results,needle", [
        ([{"key": "20261012_900a1937", "result": "created", "content_hash": "sha256:" + "0" * 64}], "hash_mismatch"),
        ([{"key": "other", "result": "created", "content_hash": "x"}], "key_mismatch"),
        ([{"key": "20261012_900a1937", "result": "weird", "content_hash": "x"}], "unknown_result"),
        ([], "result_count_mismatch"),
    ])
    def test_inconsistent_response_is_error(self, repo, wh, results, needle):
        repo.doc(REPORT, "r")
        wh.post_override = lambda req: _resp(results)
        code, text = run(repo, wh, "upload", "--type", "reports", "--no-readback")
        assert code == 1 and needle in text

    @pytest.mark.parametrize("response,needle", [
        (httpx.Response(413, json={"data": None, "error": "batch_too_large", "meta": {}}), "batch_too_large"),
        (httpx.Response(400, json={"data": None, "error": "invalid_items",
                                   "detail": [{"index": 0, "loc": ["meta"], "type": "dict_type"}]}), "dict_type"),
        (httpx.Response(403, json={"error": "forbidden"}), "forbidden"),
        (httpx.Response(302, headers={"location": "https://login"}), "access_redirect"),
        (httpx.Response(200, headers={"content-type": "text/html"}, text="<html>login</html>"), "access_html"),
        (httpx.Response(502, text="bad gateway"), "http_502"),
        (httpx.Response(200, json={"data": None}), "malformed_response"),
    ])
    def test_http_errors_reported_and_nonzero(self, repo, wh, response, needle):
        repo.doc(REPORT, "r")
        wh.post_override = lambda req: response
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and needle in text
        assert wh.gets == []

    def test_transport_error_is_reported(self, repo, wh):
        repo.doc(REPORT, "r")

        def boom(req):
            raise httpx.ConnectError("refused", request=req)
        wh.post_override = boom
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and "transport_error" in text

    def test_one_failing_batch_does_not_hide_other_types(self, repo, wh):
        repo.doc(REPORT, "r")
        repo.session(UUID_A)

        def override(req):
            if req.url.path.endswith("/reports"):
                return httpx.Response(503, json={"data": None, "error": "db_unavailable"})
            return wh._post(req)
        wh.post_override = override
        code, text = run(repo, wh, "upload")
        assert code == 1
        assert "db_unavailable" in text
        assert any(r.url.path.endswith("/sessions") for r in wh.posts)


# ── 讀回核對 ─────────────────────────────────────────────


class TestReadback:
    def test_readback_hash_mismatch_is_error(self, repo, wh):
        repo.doc(REPORT, "r")

        def tampered(req):
            if "/internal/app/reports/" in req.url.path:
                return httpx.Response(200, json={"data": {"date": "20261012_900a1937", "content": "tampered"}})
            return None
        wh.get_override = tampered
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and "readback_hash_mismatch" in text

    def test_meeting_prep_fuzzy_match_is_not_accepted(self, repo, wh):
        repo.doc(PREP, "p")

        def fuzzy(req):
            if "/internal/app/meeting-prep/" in req.url.path:
                return httpx.Response(200, json={"data": {"date": "20261009_ffffffff", "content": "p"}})
            return None
        wh.get_override = fuzzy
        code, text = run(repo, wh, "upload", "--type", "meeting_prep")
        assert code == 1 and "readback_key_mismatch" in text
        assert wh.gets[0].url.path == "/internal/app/meeting-prep/20261009_0fc3dcbc"

    def test_readback_missing_report_is_error(self, repo, wh):
        repo.doc(REPORT, "r")
        wh.get_override = lambda req: httpx.Response(404, json={"error": "Report not found"})
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and "readback_missing" in text

    def test_session_readback_checks_title_and_message_count(self, repo, wh):
        repo.session(UUID_A, title="t", messages=[{"role": "user", "content": "a"}])

        def wrong(req):
            if "/internal/app/sessions/" in req.url.path:
                return httpx.Response(200, json={"data": {"id": UUID_A, "title": "t", "messages": []}})
            return None
        wh.get_override = wrong
        code, text = run(repo, wh, "upload", "--type", "sessions")
        assert code == 1 and "readback_session_mismatch" in text

    def test_session_soft_deleted_is_warning_only(self, repo, wh):
        repo.session(UUID_A)
        wh.store[("sessions", UUID_A)] = {"id": UUID_A}  # 既有列 → POST 回 updated
        wh.get_override = lambda req: httpx.Response(404, json={"error": "Session not found"})
        code, text = run(repo, wh, "upload", "--type", "sessions")
        assert code == 0 and "軟刪除" in text and "[updated]" in text

    def test_created_session_missing_on_readback_is_error(self, repo, wh):
        repo.session(UUID_A)
        wh.get_override = lambda req: httpx.Response(404, json={"error": "Session not found"})
        code, text = run(repo, wh, "upload", "--type", "sessions")
        assert code == 1 and "readback_session_mismatch" in text

    def test_readback_http_error_is_error(self, repo, wh):
        repo.doc(REPORT, "r")
        wh.get_override = lambda req: httpx.Response(403, json={"error": "forbidden"})
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and "forbidden" in text

    def test_no_readback_skips_gets_and_read_credentials(self, repo, wh):
        repo.doc(REPORT, "r")
        (repo.root / "app-read.env").unlink()
        code, _ = run(repo, wh, "upload", "--type", "reports", "--no-readback")
        assert code == 0 and wh.gets == [] and len(wh.posts) == 1

    def test_failed_batch_items_are_not_read_back(self, repo, wh):
        repo.doc(REPORT, "r")
        wh.post_override = lambda req: httpx.Response(422, json={"data": None, "error": "rejected_by_db"})
        code, _ = run(repo, wh, "upload", "--type", "reports")
        assert code == 1 and wh.gets == []


# ── 憑證 ─────────────────────────────────────────────────


class TestCredentials:
    def test_missing_sync_env_exits_2_without_http(self, repo, wh):
        repo.doc(REPORT, "r")
        (repo.root / "sync.env").unlink()
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 2 and wh.requests == []
        assert str(repo.root / "sync.env") in text and "CF_ACCESS_CLIENT_ID" in text

    def test_missing_key_named_but_value_not_printed(self, repo, wh):
        repo.doc(REPORT, "r")
        (repo.root / "sync.env").write_text(f"CF_ACCESS_CLIENT_ID={SYNC_ID}\n")
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 2 and "CF_ACCESS_CLIENT_SECRET" in text and wh.requests == []

    def test_missing_app_read_env_exits_2_before_writes(self, repo, wh):
        repo.doc(REPORT, "r")
        (repo.root / "app-read.env").unlink()
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 2 and wh.requests == [] and "--no-readback" in text

    def test_default_paths_use_home_config(self, tmp_path):
        env = {"HOME": str(tmp_path)}
        assert client_mod.sync_env_path(env) == tmp_path / ".config/vocus-warehouse/sync.env"
        assert client_mod.app_read_env_path(env) == tmp_path / ".config/vocus-warehouse/app-read.env"
        env2 = {"VW_SYNC_ENV_FILE": "/x/s.env", "VW_APP_READ_ENV_FILE": "/x/r.env"}
        assert client_mod.sync_env_path(env2) == Path("/x/s.env")
        assert client_mod.app_read_env_path(env2) == Path("/x/r.env")

    def test_credentials_repr_hides_secret(self, tmp_path):
        path = tmp_path / "s.env"
        path.write_text(f"CF_ACCESS_CLIENT_ID={SYNC_ID}\nCF_ACCESS_CLIENT_SECRET={SYNC_SECRET}\nOTHER=1\n")
        creds = client_mod.load_credentials(path)
        assert SYNC_SECRET not in repr(creds) and SYNC_SECRET not in str(creds)
        assert creds.headers() == {"CF-Access-Client-Id": SYNC_ID, "CF-Access-Client-Secret": SYNC_SECRET}

    def test_environment_variables_are_ignored(self, repo, wh):
        repo.doc(REPORT, "r")
        (repo.root / "sync.env").unlink()
        env = {**repo.env, "CF_ACCESS_CLIENT_ID": "env-id", "CF_ACCESS_CLIENT_SECRET": "env-secret"}
        code, text = run(repo, wh, "upload", "--type", "reports", env=env)
        assert code == 2 and wh.requests == [] and "env-secret" not in text


# ── status ───────────────────────────────────────────────


class TestStatus:
    def test_lists_local_ledger_and_remote(self, repo, wh):
        repo.doc(REPORT, "r")
        repo.doc(PREP, "p")
        repo.doc("report_20260904_9d41f7b2.md", "h", status="historical")
        repo.session(UUID_A)
        wh.store[("reports", "20261012_900a1937")] = {"date_key": "20261012_900a1937", "content": "r"}
        wh.store[("meeting_prep", "20261009_0fc3dcbc")] = {"date_key": "20261009_0fc3dcbc", "content": "OLD"}
        code, text = run(repo, wh, "status")
        assert code == 0
        assert wh.posts == []
        assert "remote_same" in text and "remote_differs" in text and "remote_missing" in text
        assert "historical" in text
        assert all(r.headers["CF-Access-Client-Id"] == READ_ID for r in wh.gets)
        assert not any("9d41f7b2" in r.url.path for r in wh.gets)

    def test_without_read_credentials_only_local(self, repo, wh):
        repo.doc(REPORT, "r")
        (repo.root / "app-read.env").unlink()
        code, text = run(repo, wh, "status")
        assert code == 0 and wh.requests == [] and "app-read" in text

    def test_drift_makes_status_nonzero(self, repo, wh):
        repo.doc(REPORT, "new", ledger_content="old")
        code, text = run(repo, wh, "status")
        assert code == 1 and "content_changed" in text

    def test_remote_error_makes_status_nonzero(self, repo, wh):
        repo.doc(REPORT, "r")
        wh.get_override = lambda req: httpx.Response(503, json={"data": None, "error": "Store unavailable"})
        code, text = run(repo, wh, "status")
        assert code == 1 and "Store unavailable" in text

    def test_fuzzy_meeting_prep_counts_as_missing(self, repo, wh):
        repo.doc(PREP, "p")
        wh.get_override = lambda req: httpx.Response(200, json={"data": {"date": "20261009_ffffffff", "content": "p"}})
        code, text = run(repo, wh, "status", "--type", "meeting_prep")
        assert code == 0 and "remote_missing" in text


# ── CLI 參數 ─────────────────────────────────────────────


class TestCli:
    def test_type_sessions_only(self, repo, wh):
        repo.doc(REPORT, "r")
        repo.session(UUID_A)
        code, _ = run(repo, wh, "upload", "--type", "sessions")
        assert code == 0 and {r.url.path for r in wh.posts} == {"/internal/sync/sessions"}

    def test_meeting_prep_dash_alias(self, repo, wh):
        repo.doc(PREP, "p")
        repo.doc(REPORT, "r")
        code, text = run(repo, wh, "upload", "--type", "meeting-prep", "--dry-run")
        assert code == 0
        assert "== meeting_prep ==" in text and "== reports ==" not in text and "== sessions ==" not in text

    def test_rejects_non_https_base_url(self, repo, wh):
        out, err = io.StringIO(), io.StringIO()
        http = httpx.Client(transport=httpx.MockTransport(wh.handler))
        code = sync_db.main(["upload", "--base-url", "http://evil.test"], root=repo.root, http=http,
                            environ=repo.env, out=out, err=err)
        assert code == 2 and wh.requests == [] and "https" in err.getvalue()

    def test_nothing_to_upload_is_success_without_http(self, repo, wh):
        repo.doc("report_20260904_9d41f7b2.md", "h", status="historical")
        code, text = run(repo, wh, "upload", "--type", "reports")
        assert code == 0 and wh.requests == [] and "沒有可上傳" in text

    def test_default_base_url(self):
        assert client_mod.DEFAULT_BASE_URL == "https://warehouse-api.vocus.cc"

    def test_invalid_subcommand_exits_2(self, repo, wh):
        with pytest.raises(SystemExit) as exc:
            sync_db.main(["bogus"], root=repo.root, environ=repo.env, out=io.StringIO(), err=io.StringIO())
        assert exc.value.code == 2

    def test_main_builds_client_when_not_injected(self, repo, monkeypatch):
        repo.doc(REPORT, "r")
        wh = FakeWarehouse()
        monkeypatch.setattr(client_mod, "build_http_client",
                            lambda: httpx.Client(transport=httpx.MockTransport(wh.handler)))
        code = sync_db.main(["upload", "--type", "reports", "--base-url", BASE], root=repo.root,
                            environ=repo.env, out=io.StringIO(), err=io.StringIO())
        assert code == 0 and len(wh.posts) == 1
