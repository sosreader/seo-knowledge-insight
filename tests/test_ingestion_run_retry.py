"""Tests for scripts/ingestion_run_retry.py。

背景：finish_run() 收尾 PATCH 撞到 Supabase/PostgREST 暫時性 504 時，舊版
只 log 不重試也不 raise，導致 ingestion_run 永久卡在 status='running'（見 KB
session-2026-09-15-seo-insight-ci-stale-running-and-runner.md）。本檔鎖三件事：
  1. 只對暫時性錯誤（502/503/504、連線層例外）重試，且有上限（3 次、
     退避 1s/2s/4s）——非暫時性錯誤（4xx）第一次失敗就回傳，不浪費重試預算。
  2. 收尾（finish_run_or_raise）重試用盡或遇到非暫時性錯誤時一定 raise，
     不能只 log——這是讓孤兒 run 當場讓 CI 紅燈的唯一機制。
  3. 重試次數與退避秒數精確符合預期，不是「大概有重試就好」。
"""
from __future__ import annotations

import sys
import urllib.error
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ingestion_run_retry as retry_mod  # noqa: E402


class TestRequestWithRetry:
    def test_succeeds_on_first_try_without_sleeping(self) -> None:
        request_fn = Mock(return_value=(200, "ok"))
        sleep = Mock()
        result = retry_mod.request_with_retry(request_fn, description="test", sleep=sleep)
        assert result == (200, "ok")
        assert request_fn.call_count == 1
        sleep.assert_not_called()

    def test_does_not_retry_non_retryable_http_status(self) -> None:
        """400 是客戶端錯誤，重試沒有意義——第一次失敗就該回傳。"""
        request_fn = Mock(return_value=(400, "bad request"))
        sleep = Mock()
        result = retry_mod.request_with_retry(request_fn, description="test", sleep=sleep)
        assert result == (400, "bad request")
        assert request_fn.call_count == 1
        sleep.assert_not_called()

    @pytest.mark.parametrize("status", [502, 503, 504])
    def test_retries_retryable_status_then_succeeds(self, status: int) -> None:
        request_fn = Mock(side_effect=[(status, "gateway"), (status, "gateway"), (200, "ok")])
        sleep = Mock()
        result = retry_mod.request_with_retry(request_fn, description="test", sleep=sleep)
        assert result == (200, "ok")
        assert request_fn.call_count == 3
        assert sleep.call_args_list == [((1.0,),), ((2.0,),)]

    def test_exhausts_retries_and_returns_final_failure(self) -> None:
        request_fn = Mock(return_value=(504, "gateway timeout"))
        sleep = Mock()
        result = retry_mod.request_with_retry(request_fn, description="test", sleep=sleep)
        assert result == (504, "gateway timeout")
        # 1 次原始嘗試 + MAX_RETRY_ATTEMPTS 次重試。
        assert request_fn.call_count == 1 + retry_mod.MAX_RETRY_ATTEMPTS
        assert [call.args[0] for call in sleep.call_args_list] == list(
            retry_mod.RETRY_BACKOFF_SECONDS
        )

    def test_retries_connection_error_then_succeeds(self) -> None:
        request_fn = Mock(side_effect=[urllib.error.URLError("dns failure"), (200, "ok")])
        sleep = Mock()
        result = retry_mod.request_with_retry(request_fn, description="test", sleep=sleep)
        assert result == (200, "ok")
        assert request_fn.call_count == 2
        assert sleep.call_args_list == [((1.0,),)]

    def test_exhausts_on_persistent_connection_error(self) -> None:
        request_fn = Mock(side_effect=urllib.error.URLError("connection refused"))
        sleep = Mock()
        result = retry_mod.request_with_retry(request_fn, description="test", sleep=sleep)
        status, body = result
        assert status == 0
        assert "connection refused" in body
        assert request_fn.call_count == 1 + retry_mod.MAX_RETRY_ATTEMPTS

    def test_timeout_error_is_retried_like_connection_error(self) -> None:
        request_fn = Mock(side_effect=[TimeoutError("timed out"), (200, "ok")])
        sleep = Mock()
        result = retry_mod.request_with_retry(request_fn, description="test", sleep=sleep)
        assert result == (200, "ok")
        assert request_fn.call_count == 2

    def test_forwards_extra_tuple_elements_unchanged(self) -> None:
        """crawl_warehouse._request 回 3-tuple（含 headers），_supabase_request
        回 2-tuple——重試邏輯不該強制轉型，原樣轉發呼叫端的回傳值。"""
        request_fn = Mock(return_value=(200, "ok", {"Content-Range": "0-0/1"}))
        result = retry_mod.request_with_retry(request_fn, description="test", sleep=Mock())
        assert result == (200, "ok", {"Content-Range": "0-0/1"})


class TestFinishRunOrRaise:
    def test_success_returns_none_without_raising(self) -> None:
        request_fn = Mock(return_value=(204, ""))
        retry_mod.finish_run_or_raise(request_fn, run_id="run-1")
        assert request_fn.call_count == 1

    @pytest.mark.parametrize("status", [200, 204])
    def test_success_status_codes(self, status: int) -> None:
        request_fn = Mock(return_value=(status, ""))
        retry_mod.finish_run_or_raise(request_fn, run_id="run-1")

    def test_non_retryable_failure_raises_immediately(self) -> None:
        request_fn = Mock(return_value=(400, "bad"))
        with pytest.raises(retry_mod.IngestionRunFinishError, match="run-1"):
            retry_mod.finish_run_or_raise(request_fn, run_id="run-1")
        assert request_fn.call_count == 1

    def test_retry_exhausted_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(retry_mod.time, "sleep", Mock())
        request_fn = Mock(return_value=(504, "gateway timeout"))
        with pytest.raises(retry_mod.IngestionRunFinishError):
            retry_mod.finish_run_or_raise(request_fn, run_id="run-2")
        assert request_fn.call_count == 1 + retry_mod.MAX_RETRY_ATTEMPTS

    def test_retry_succeeds_within_budget_does_not_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(retry_mod.time, "sleep", Mock())
        request_fn = Mock(side_effect=[(504, "gw"), (200, "")])
        retry_mod.finish_run_or_raise(request_fn, run_id="run-3")
        assert request_fn.call_count == 2

    def test_failure_logs_run_id_and_reap_hint(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setattr(retry_mod.time, "sleep", Mock())
        request_fn = Mock(return_value=(504, "gateway timeout"))
        with pytest.raises(retry_mod.IngestionRunFinishError):
            retry_mod.finish_run_or_raise(request_fn, run_id="orphan-run-9")
        assert "orphan-run-9" in caplog.text
        assert "--reap-stale-running" in caplog.text

    def test_uses_default_description_when_not_given(self) -> None:
        request_fn = Mock(return_value=(400, "bad"))
        with pytest.raises(retry_mod.IngestionRunFinishError, match="收尾 ingestion_run"):
            retry_mod.finish_run_or_raise(request_fn, run_id="run-4")
