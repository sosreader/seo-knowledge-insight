"""回歸測試：02_extract_qa.py 在額度用盡／全部失敗時必須讓 step 失敗。

背景：
  - run 34106023623（2026-09-07）：Extract 步驟 835 次 429 insufficient_quota，
    0 筆萃取成功，step 仍 success；dedupe、migrate（上傳 0 筆）也都 success。
  - run 34827893748（2026-09-14）：同樣 835 次 429，要到 dedupe 才以不相干的
    「Embedding manifest requires nonempty candidates」失敗。

本檔鎖住：
  1. 遇到第一個 insufficient_quota 就中止（exit 1），不再逐份呼叫、逐份失敗。
  2. 本次處理的檔案全部失敗 → exit 1，且不記錄版本。
  3. 部分失敗維持原行為（寫「處理失敗」artifact 供下次重跑，step 照常結束）。
"""
from __future__ import annotations

import importlib
import json
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import MagicMock, patch

import httpx
import openai
import pytest

import config as cfg

mod = importlib.import_module("scripts.02_extract_qa")

_ARGS = SimpleNamespace(limit=0, file="", force=True, check=False)
_OK_RESULT = {"qa_pairs": [{"question": "canonical 怎麼設？", "answer": "指向正規網址"}], "meeting_summary": "ok"}


def _rate_limit_error(code: str) -> openai.RateLimitError:
    body = {"message": "You have no credits remaining.", "type": code, "param": None, "code": code}
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request, json={"error": body})
    return openai.RateLimitError(f"Error code: 429 - {body}", response=response, body=body)


@pytest.fixture
def sandbox(tmp_path: Path) -> Iterator[SimpleNamespace]:
    raw = tmp_path / "markdown"
    raw.mkdir()
    for i in range(3):
        (raw / f"SEO_會議_2026090{i}.md").write_text(f"# SEO 會議 {i}\n\n內容 {i}\n", encoding="utf-8")
    meeting_dir, article_dir, output_dir = (tmp_path / n for n in ("qa_per_meeting", "qa_per_article", "output"))
    for d in (meeting_dir, article_dir, output_dir):
        d.mkdir()

    record = MagicMock(return_value={"version_id": "v-test"})
    with ExitStack() as stack:
        stack.enter_context(patch.object(cfg, "get_all_markdown_source_dirs", return_value=(raw,)))
        stack.enter_context(patch.object(cfg, "QA_PER_MEETING_DIR", meeting_dir))
        stack.enter_context(patch.object(cfg, "QA_PER_ARTICLE_DIR", article_dir))
        stack.enter_context(patch.object(cfg, "OUTPUT_DIR", output_dir))
        stack.enter_context(patch.object(mod, "preflight_check"))
        stack.enter_context(patch.object(mod, "init_laminar"))
        stack.enter_context(patch.object(mod, "flush_laminar"))
        stack.enter_context(patch.object(mod, "record_artifact", record))
        stack.enter_context(patch("time.sleep"))
        yield SimpleNamespace(meeting_dir=meeting_dir, output_dir=output_dir, record=record)


def test_quota_exhausted_aborts_on_first_file(sandbox: SimpleNamespace, caplog: pytest.LogCaptureFixture) -> None:
    process = MagicMock(side_effect=_rate_limit_error("insufficient_quota"))
    with patch.object(mod, "process_single_meeting", process), pytest.raises(SystemExit) as exc:
        mod.main(_ARGS)

    assert exc.value.code == 1
    assert process.call_count == 1
    assert "OpenAI 額度用盡（insufficient_quota）" in caplog.text
    assert "剩餘 3 份未處理" in caplog.text
    assert not (sandbox.output_dir / "qa_all_raw.json").exists()
    sandbox.record.assert_not_called()


def test_all_files_failed_exits_1_without_recording_a_version(
    sandbox: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    process = MagicMock(side_effect=RuntimeError("boom"))
    with patch.object(mod, "process_single_meeting", process), pytest.raises(SystemExit) as exc:
        mod.main(_ARGS)

    assert exc.value.code == 1
    assert process.call_count == 3
    assert "本次 3 份全部萃取失敗" in caplog.text
    sandbox.record.assert_not_called()
    # 失敗 artifact 仍寫出，且標成「處理失敗」——下次增量會重跑，不會被當成已完成
    artifacts = sorted(sandbox.meeting_dir.glob("*_qa.json"))
    assert len(artifacts) == 3
    assert all(not mod._is_completed_qa_artifact(json.loads(p.read_text(encoding="utf-8"))) for p in artifacts)


def test_partial_failure_keeps_existing_behaviour(sandbox: SimpleNamespace) -> None:
    process = MagicMock(side_effect=[RuntimeError("boom"), _OK_RESULT, _OK_RESULT])
    with patch.object(mod, "process_single_meeting", process):
        mod.main(_ARGS)

    merged = json.loads((sandbox.output_dir / "qa_all_raw.json").read_text(encoding="utf-8"))
    assert merged["total_qa_count"] == 2
    sandbox.record.assert_called_once()


@pytest.mark.parametrize(
    "exc,expected",
    [
        (_rate_limit_error("insufficient_quota"), True),
        (_rate_limit_error("rate_limit_exceeded"), False),
        (RuntimeError("insufficient_quota"), False),
    ],
)
def test_is_quota_exhausted_only_matches_the_quota_code(exc: BaseException, expected: bool) -> None:
    """一般 rate limit（rate_limit_exceeded）是暫時性的，不該觸發中止。"""
    assert mod._is_quota_exhausted(exc) is expected
