"""Tests for scripts/ai_sov_warehouse.py（S6.2）。

存取層的三個踩過的坑，各鎖一組測試：
  1. 讀回一律 Range 分頁——PostgREST 的 db-max-rows 會**靜默**蓋掉 querystring
     的 limit，HTTP 仍回 200（KB postgrest-querystring-limit-silently-capped-by-db-max-rows）。
  2. ingested_at 必須進 payload，否則 sweep_stale 分不出哪些列是這次寫的
     （PostgREST 的 merge-duplicates 只 SET payload 裡出現的欄位）。
  3. 同批次重複 key 會殺掉**整批**（015 冪等契約第 3 點）。
"""
from __future__ import annotations

import json
import sys
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ai_sov_warehouse as warehouse  # noqa: E402

UTC = timezone.utc
RUN_AT = datetime(2026, 8, 31, 6, 20, tzinfo=UTC)
WEEK = date(2026, 8, 31)


class _FakeResponse:
    def __init__(self, status: int, body: str, headers: dict | None = None) -> None:
        self.status = status
        self._body = body
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body.encode()

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc) -> None:
        return None


@pytest.fixture(autouse=True)
def _supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://db.test/")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")


def _install_transport(monkeypatch: pytest.MonkeyPatch, responses: list) -> list[dict]:
    """把 urlopen 換成腳本化的回應序列，並記錄每一次送出的請求。"""
    sent: list[dict] = []
    queue = list(responses)

    def fake_urlopen(request, timeout=None):
        sent.append({
            "method": request.method,
            "url": request.full_url,
            "headers": dict(request.headers),
            "body": json.loads(request.data.decode()) if request.data else None,
        })
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return _FakeResponse(*item)

    monkeypatch.setattr(warehouse.urllib.request, "urlopen", fake_urlopen)
    return sent


class TestSupabaseConfig:
    def test_reads_env(self) -> None:
        assert warehouse.supabase_config() == ("https://db.test", "service-key")

    @pytest.mark.parametrize("missing", ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"])
    def test_missing_env_raises(self, monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
        monkeypatch.delenv(missing)
        with pytest.raises(RuntimeError, match="缺少"):
            warehouse.supabase_config()


class TestRequest:
    def test_sends_auth_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _install_transport(monkeypatch, [(200, "[]")])
        warehouse._request("GET", "/rest/v1/x")
        headers = sent[0]["headers"]
        assert headers["Apikey"] == "service-key"
        assert headers["Authorization"] == "Bearer service-key"
        assert headers["User-agent"] == warehouse.USER_AGENT

    def test_http_error_is_returned_not_raised(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PostgREST 的 4xx body 帶著失敗原因，吞掉它就查不出為什麼寫入失敗。"""
        error = urllib.error.HTTPError("u", 409, "conflict", {}, None)
        error.read = lambda: b"duplicate key"  # type: ignore[method-assign]
        _install_transport(monkeypatch, [error])
        status, body, _ = warehouse._request("POST", "/rest/v1/x", body=[{}])
        assert status == 409 and "duplicate key" in body


class TestSelectAllPaging:
    def test_stops_on_short_page(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _install_transport(monkeypatch, [(200, json.dumps([{"i": 1}, {"i": 2}]))])
        assert len(warehouse.select_all("/rest/v1/x")) == 2
        assert sent[0]["headers"]["Range"] == "0-999"

    def test_follows_range_header_until_short_page(self, monkeypatch: pytest.MonkeyPatch) -> None:
        full = json.dumps([{"i": i} for i in range(warehouse.READ_PAGE_SIZE)])
        sent = _install_transport(monkeypatch, [(206, full), (206, json.dumps([{"i": 9999}]))])
        rows = warehouse.select_all("/rest/v1/x")
        assert len(rows) == warehouse.READ_PAGE_SIZE + 1
        assert [s["headers"]["Range"] for s in sent] == ["0-999", "1000-1999"]

    def test_non_2xx_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_transport(monkeypatch, [(500, "boom")])
        with pytest.raises(RuntimeError, match="讀取"):
            warehouse.select_all("/rest/v1/x")


class TestIngestionRun:
    def test_start_run_returns_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _install_transport(monkeypatch, [(201, json.dumps([{"id": "run-1"}]))])
        run_id = warehouse.start_run(RUN_AT, RUN_AT)
        assert run_id == "run-1"
        payload = sent[0]["body"][0]
        assert payload["table_name"] == "ai_sov_response"
        assert payload["status"] == "running" and payload["row_count"] == 0

    def test_start_run_returns_none_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """登記失敗不該讓整個 ingest 掛掉——資料本身還是要寫進去，
        新鮮度檢查查的是目的表不是 run 紀錄。"""
        _install_transport(monkeypatch, [(400, "bad")])
        assert warehouse.start_run(RUN_AT, RUN_AT) is None

    def test_finish_run_patches_status(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _install_transport(monkeypatch, [(204, "")])
        warehouse.finish_run("run-1", "success", 108)
        assert sent[0]["method"] == "PATCH" and "run-1" in sent[0]["url"]
        assert sent[0]["body"]["status"] == "success"
        assert sent[0]["body"]["row_count"] == 108
        assert sent[0]["body"]["finished_at"].endswith("Z")

    def test_finish_run_noop_without_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _install_transport(monkeypatch, [])
        warehouse.finish_run(None, "success", 1)
        assert sent == []

    def test_finish_run_logs_but_does_not_raise_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_transport(monkeypatch, [(500, "boom")])
        warehouse.finish_run("run-1", "success", 1)  # 不拋


class TestUpsertRows:
    @staticmethod
    def _row(repeat_idx: int) -> dict:
        return {"week_start": "2026-08-31", "provider": "fake", "model": "m",
                "prompt_id": "p1", "repeat_idx": repeat_idx}

    def test_stamps_ingested_at_into_payload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """merge-duplicates 只 SET payload 裡出現的欄位；不帶 ingested_at 的話
        衝突時會沿用第一次寫入的值，sweep_stale 就分不出哪些列是這次寫的。"""
        sent = _install_transport(monkeypatch, [(201, "")])
        warehouse.upsert_rows([self._row(0)], RUN_AT)
        assert sent[0]["body"][0]["ingested_at"] == "2026-08-31T06:20:00Z"

    def test_uses_merge_duplicates_on_conflict_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _install_transport(monkeypatch, [(201, "")])
        warehouse.upsert_rows([self._row(0)], RUN_AT)
        assert "on_conflict=week_start%2Cprovider%2Cmodel%2Cprompt_id%2Crepeat_idx" in sent[0]["url"]
        assert "resolution=merge-duplicates" in sent[0]["headers"]["Prefer"]

    def test_counts_success_and_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_transport(monkeypatch, [(201, "")])
        assert warehouse.upsert_rows([self._row(i) for i in range(3)], RUN_AT) == (3, 0)

    def test_non_2xx_counts_as_failed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_transport(monkeypatch, [(400, "bad payload")])
        assert warehouse.upsert_rows([self._row(0)], RUN_AT) == (0, 1)

    def test_batches_at_configured_size(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rows = [self._row(i) for i in range(warehouse.UPSERT_BATCH_SIZE + 1)]
        sent = _install_transport(monkeypatch, [(201, ""), (201, "")])
        assert warehouse.upsert_rows(rows, RUN_AT) == (len(rows), 0)
        assert len(sent) == 2

    def test_deduplicates_before_sending(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """同批次重複 key 會讓 PostgreSQL 殺掉整批，不是那一列。"""
        sent = _install_transport(monkeypatch, [(201, "")])
        warehouse.upsert_rows([self._row(0), self._row(0)], RUN_AT)
        assert len(sent[0]["body"]) == 1


class TestSweepStale:
    def test_deletes_rows_older_than_this_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent = _install_transport(monkeypatch, [(200, json.dumps([{"id": 1}, {"id": 2}]))])
        assert warehouse.sweep_stale(WEEK, RUN_AT) == 2
        assert sent[0]["method"] == "DELETE"
        assert "week_start=eq.2026-08-31" in sent[0]["url"]
        assert "ingested_at=lt." in sent[0]["url"]

    def test_returns_zero_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_transport(monkeypatch, [(500, "boom")])
        assert warehouse.sweep_stale(WEEK, RUN_AT) == 0

    def test_empty_body_means_nothing_removed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_transport(monkeypatch, [(204, "")])
        assert warehouse.sweep_stale(WEEK, RUN_AT) == 0


class TestLatestWeekStart:
    def test_returns_date(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_transport(monkeypatch, [(200, json.dumps([{"week_start": "2026-08-31"}]))])
        assert warehouse.latest_week_start() == WEEK

    def test_empty_table_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """空表回 None 而不是拋——呼叫端要能區分「從未寫入」與「查詢失敗」。"""
        _install_transport(monkeypatch, [(200, "[]")])
        assert warehouse.latest_week_start() is None

    def test_query_failure_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_transport(monkeypatch, [(503, "down")])
        with pytest.raises(RuntimeError, match="查詢"):
            warehouse.latest_week_start()
