"""回歸測試：scripts/_eval_data_quality.py 寫入 Supabase eval_runs 表。

背景（2026-09-10）：`_upsert_eval_run()` 一直用 `SUPABASE_ANON_KEY` 寫入
`eval_runs`，但該表的 RLS（`supabase/migrations/002_eval_runs.sql`）只開了
`eval_runs_read_all`（SELECT）policy，沒有任何 INSERT policy——anon 寫入
一律被擋下：

    eval_runs upsert returned 401: new row violates row-level security
    policy for table "eval_runs"

而失敗只印一行 warning、exit code 不受影響，代表 eval 歷史紀錄實際上從未
寫入成功，卻沒有任何 CI 訊號能讓人發現（ETL run 34106023623 的 log 才第一次
被人翻出來）。

本檔鎖住三件事：
  1. 寫入改用 SUPABASE_SERVICE_KEY，不能退回 ANON_KEY（本 repo 其他所有
     Supabase 寫入路徑——migrate_to_supabase.py／push_qa_metadata_to_supabase.py
     ／update_freshness.py／backfill_*.py——都已經是這個模式，_eval_data_quality.py
     是唯一的例外）。
  2. 寫入失敗不再靜默吞掉：4xx（權限／schema）立刻失敗不重試；5xx／連線層
     錯誤視為暫時性，重試 _WRITE_MAX_ATTEMPTS 次後仍失敗才算數；憑證只設定
     一半（CI secret 漏掛的典型徵狀）視為設定不完整，直接失敗；憑證完全
     沒設定則視為刻意不接 Supabase（本機 --source local 情境），略過不算失敗。
  3. etl-and-deploy.yml 的「Run data quality eval」step 真的把
     SUPABASE_SERVICE_KEY 傳進去——否則第 1 點修對了程式碼，CI 還是會在
     「環境設定不完整」那條路徑上失敗（見 TestWorkflowPassesServiceKey）。
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from scripts import _eval_data_quality as edq

_URL = "https://example.supabase.co"
_SERVICE_KEY = "service-role-test-key"
_ANON_KEY = "anon-test-key"
_METRICS = {
    "total": 32439,
    "qa_count_in_range": 1.0,
    "avg_confidence": 0.9,
    "keyword_coverage": 0.9,
    "no_admin_content": 1.0,
}


def _resp(status_code: int, text: str = "") -> Mock:
    resp = Mock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestCredentialSelection:
    """寫入必須用 service key；只設定 anon key 視同沒設定 service key。"""

    def test_uses_service_key_not_anon_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPABASE_URL", _URL)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", _SERVICE_KEY)
        monkeypatch.setenv("SUPABASE_ANON_KEY", _ANON_KEY)

        with patch.object(edq.requests, "post", return_value=_resp(201)) as mock_post:
            edq._upsert_eval_run(_METRICS, "data-quality", True)

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["apikey"] == _SERVICE_KEY
        assert kwargs["headers"]["Authorization"] == f"Bearer {_SERVICE_KEY}"
        assert _ANON_KEY not in kwargs["headers"].values()

    def test_only_anon_key_set_is_treated_as_missing_service_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """只設 SUPABASE_ANON_KEY（沒設 SERVICE_KEY）—— 環境設定不完整，直接失敗，
        不能悄悄退化成用 anon key 寫入（那正是原本被 RLS 擋下的行為）。"""
        monkeypatch.setenv("SUPABASE_URL", _URL)
        monkeypatch.setenv("SUPABASE_ANON_KEY", _ANON_KEY)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

        with patch.object(edq.requests, "post") as mock_post:
            with pytest.raises(edq.EvalRunPersistError):
                edq._upsert_eval_run(_METRICS, "data-quality", True)
        mock_post.assert_not_called()


class TestMissingCredentials:
    def test_both_unset_skips_without_raising(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """完全沒接 Supabase（例如本機只想看 --source local 的指標）是刻意的，
        不是失敗。"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

        with caplog.at_level(logging.INFO):
            with patch.object(edq.requests, "post") as mock_post:
                edq._upsert_eval_run(_METRICS, "data-quality", True)
        mock_post.assert_not_called()
        assert "略過" in caplog.text

    def test_only_url_set_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPABASE_URL", _URL)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

        with pytest.raises(edq.EvalRunPersistError):
            edq._upsert_eval_run(_METRICS, "data-quality", True)


class TestWriteFailureClassification:
    """4xx 不重試立刻失敗；5xx／連線層錯誤視為暫時性，重試後仍失敗才算數。"""

    def setup_method(self) -> None:
        self._sleep_patch = patch.object(edq.time, "sleep")  # 測試不必真的等待 backoff
        self._sleep_patch.start()

    def teardown_method(self) -> None:
        self._sleep_patch.stop()

    def test_success_201_returns(self) -> None:
        with patch.object(edq.requests, "post", return_value=_resp(201)) as mock_post:
            edq._post_eval_run(_URL, _SERVICE_KEY, {"trigger": "manual"})
        assert mock_post.call_count == 1

    def test_permission_error_401_fails_without_retry(self) -> None:
        """對應原始 bug 的確切徵狀：42501 RLS violation。"""
        body = '{"code":"42501","message":"new row violates row-level security policy for table \\"eval_runs\\""}'
        with patch.object(edq.requests, "post", return_value=_resp(401, body)) as mock_post:
            with pytest.raises(edq.EvalRunPersistError, match="401"):
                edq._post_eval_run(_URL, _SERVICE_KEY, {"trigger": "manual"})
        assert mock_post.call_count == 1, "4xx 重試沒有意義，不該重送"

    def test_schema_error_400_fails_without_retry(self) -> None:
        with patch.object(edq.requests, "post", return_value=_resp(400, "bad request")) as mock_post:
            with pytest.raises(edq.EvalRunPersistError, match="400"):
                edq._post_eval_run(_URL, _SERVICE_KEY, {"trigger": "manual"})
        assert mock_post.call_count == 1

    def test_server_error_retries_then_recovers(self) -> None:
        with patch.object(
            edq.requests, "post", side_effect=[_resp(503, "unavailable"), _resp(201)]
        ) as mock_post:
            edq._post_eval_run(_URL, _SERVICE_KEY, {"trigger": "manual"})
        assert mock_post.call_count == 2

    def test_server_error_exhausts_retries_then_fails(self) -> None:
        with patch.object(edq.requests, "post", return_value=_resp(503, "unavailable")) as mock_post:
            with pytest.raises(edq.EvalRunPersistError, match="已重試"):
                edq._post_eval_run(_URL, _SERVICE_KEY, {"trigger": "manual"})
        assert mock_post.call_count == edq._WRITE_MAX_ATTEMPTS

    def test_connection_error_retries_then_fails(self) -> None:
        with patch.object(
            edq.requests, "post", side_effect=requests.ConnectionError("boom")
        ) as mock_post:
            with pytest.raises(edq.EvalRunPersistError, match="連線層"):
                edq._post_eval_run(_URL, _SERVICE_KEY, {"trigger": "manual"})
        assert mock_post.call_count == edq._WRITE_MAX_ATTEMPTS

    def test_connection_error_then_recovers(self) -> None:
        with patch.object(
            edq.requests, "post", side_effect=[requests.Timeout("slow"), _resp(200)]
        ) as mock_post:
            edq._post_eval_run(_URL, _SERVICE_KEY, {"trigger": "manual"})
        assert mock_post.call_count == 2


class TestMainSurfacesPersistFailure:
    """main() 不能因為 eval_runs 寫入失敗而中途放棄 Laminar 推送，但整個 process
    最終要以非 0 結束，讓 CI step 顯示失敗（--dry-run 與正常模式都要涵蓋）。"""

    def test_dry_run_exits_nonzero_when_persist_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sys.argv", ["_eval_data_quality.py", "--dry-run"]
        )
        monkeypatch.setattr(edq, "_load_qas", lambda source: [
            {"question": "q", "answer": "a", "keywords": ["a", "b", "c"], "confidence": 0.9}
        ])
        monkeypatch.setattr(
            edq, "_upsert_eval_run",
            Mock(side_effect=edq.EvalRunPersistError("boom")),
        )
        with pytest.raises(SystemExit) as exc_info:
            edq.main()
        assert exc_info.value.code == 1

    def test_dry_run_exits_zero_when_persist_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sys.argv", ["_eval_data_quality.py", "--dry-run"]
        )
        monkeypatch.setattr(edq, "_load_qas", lambda source: [
            {"question": "q", "answer": "a", "keywords": ["a", "b", "c"], "confidence": 0.9}
        ])
        monkeypatch.setattr(edq, "_upsert_eval_run", Mock(return_value=None))

        edq.main()  # 不應該 raise SystemExit


class TestWorkflowPassesServiceKey:
    """etl-and-deploy.yml 的『Run data quality eval』step 必須帶
    SUPABASE_SERVICE_KEY，否則即使程式碼改對了，CI 還是會在
    「環境設定不完整」那條路徑上失敗——這正是本次要修的 CI secret 漏掛類問題。"""

    def test_run_data_quality_eval_step_has_service_key(self) -> None:
        workflow = (
            Path(__file__).resolve().parent.parent
            / ".github" / "workflows" / "etl-and-deploy.yml"
        ).read_text(encoding="utf-8")

        step_match = re.search(
            r"- name: Run data quality eval\n(.*?)\n      - name:", workflow, re.DOTALL
        )
        assert step_match, "找不到「Run data quality eval」這個 step"
        step_text = step_match.group(1)

        assert "SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}" in step_text
        assert "SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}" in step_text, (
            "讀 qa_items 仍然要用 anon key，不要把整個 step 換成 service key"
        )
