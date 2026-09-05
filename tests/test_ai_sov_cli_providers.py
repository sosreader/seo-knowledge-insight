"""Tests for scripts/ai_sov_cli_providers.py（S6.2 本機 CLI provider）。

Fixture 來源：tests/fixtures/ai_sov_cli/ 下的 JSONL，是根據真實探測
（knowledge-base `.verification/2026-09-04-ai-sov-golive/local-provider-probe/`）
的事件形狀重建、匿名化後的樣本——不是真實輸出的逐字拷貝（探測內容含使用者
本機路徑），但欄位結構與真實輸出一致。

四個重點：
  1. codex：--output-schema 強制的 {answer, sources} JSON 解析，以及
     schema 被繞過（text 不是合法 JSON／缺欄位）時要拋 ProviderError。
  2. claude-code：grounded 判定＝『來源：』段 URL 與 WebSearch tool_result
     實際回傳過的 URL 的交集，不在交集裡的網址要被濾除、不進 citations。
  3. 完全沒觸發 WebSearch 時，即使文字裡剛好有『來源：』段也要判 ungrounded
     ——那些網址是模型自己編的，不是這次呼叫真的查到的。
  4. _run_cli 的三種失敗映射：找不到執行檔→Fatal、逾時／非零 exit→Error。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ai_sov_cli_providers as cli_providers  # noqa: E402
from ai_sov_cli_providers import (  # noqa: E402
    ClaudeCodeProvider,
    CodexProvider,
    parse_claude_code_output,
    parse_codex_output,
)
from ai_sov_providers import ProviderError, ProviderFatalError  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ai_sov_cli"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestParseCodexOutput:
    def test_parses_grounded_answer_and_citations(self) -> None:
        answer = parse_codex_output(_read("codex_grounded.jsonl"))
        assert answer.is_grounded
        assert {c.url for c in answer.citations} == {
            "https://example.com/review/1",
            "https://vocus.cc/article/abc123",
            "https://blog.example.org/post/2",
        }
        assert "測試用的整理回答" in answer.text

    def test_output_tokens_include_reasoning(self) -> None:
        """output_tokens 與 reasoning_output_tokens 是分開欄位，兩者相加才是總輸出量。"""
        answer = parse_codex_output(_read("codex_grounded.jsonl"))
        assert answer.input_tokens == 15000
        assert answer.output_tokens == 800 + 150

    def test_missing_agent_message_raises(self) -> None:
        with pytest.raises(ProviderError, match="agent_message"):
            parse_codex_output(_read("codex_no_agent_message.jsonl"))

    def test_non_json_final_text_raises(self) -> None:
        with pytest.raises(ProviderError, match="合法 JSON"):
            parse_codex_output(_read("codex_schema_violation.jsonl"))

    def test_missing_required_keys_raises(self) -> None:
        stdout = (
            '{"type":"item.completed","item":{"id":"i","type":"agent_message",'
            '"text":"{\\"answer\\":\\"缺 sources 欄位\\"}"}}\n'
            '{"type":"turn.completed","usage":{}}\n'
        )
        with pytest.raises(ProviderError, match="schema"):
            parse_codex_output(stdout)

    def test_zero_citations_is_legal_result(self) -> None:
        """空 sources 陣列是合法的 ungrounded 結果，不應拋例外。"""
        stdout = (
            '{"type":"item.completed","item":{"id":"i","type":"agent_message",'
            '"text":"{\\"answer\\":\\"沒有找到來源\\",\\"sources\\":[]}"}}\n'
            '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":5}}\n'
        )
        answer = parse_codex_output(stdout)
        assert not answer.is_grounded
        assert answer.citations == ()


class TestParseClaudeCodeOutput:
    def test_grounded_citations_are_intersection_with_search_results(self) -> None:
        """『來源：』段列了 3 個網址，只有 2 個真的出現在 WebSearch 結果裡；
        第 3 個（不在搜尋結果裡）要被濾除，不進 citations。"""
        answer = parse_claude_code_output(_read("claude_code_grounded.jsonl"))
        assert answer.is_grounded
        assert {c.url for c in answer.citations} == {
            "https://vocus.cc/article/xyz123",
            "https://example.com/review/1",
        }
        assert not any("not-searched" in c.url for c in answer.citations)

    def test_unverified_url_is_logged_not_raised(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        with caplog.at_level(logging.WARNING, logger="ai_sov_cli_providers"):
            parse_claude_code_output(_read("claude_code_grounded.jsonl"))
        assert any("未出現在 WebSearch 結果裡" in r.message for r in caplog.records)

    def test_usage_tokens_parsed(self) -> None:
        answer = parse_claude_code_output(_read("claude_code_grounded.jsonl"))
        # input_tokens + cache_read_input_tokens（見設計決定：兩者都是這次呼叫實際
        # 消耗的輸入 token，只是快取命中與否的區分）
        assert answer.input_tokens == 60 + 80000
        assert answer.output_tokens == 1200

    def test_no_search_call_means_ungrounded_even_with_sources_section(self) -> None:
        """沒有任何 WebSearch tool_use 事件時，即使文字裡剛好有『來源：』段，
        也一律判 ungrounded——那些網址是模型自己編的（見設計決定 3）。"""
        answer = parse_claude_code_output(_read("claude_code_ungrounded_no_search.jsonl"))
        assert not answer.is_grounded
        assert answer.citations == ()

    def test_is_error_result_raises(self) -> None:
        with pytest.raises(ProviderError, match="claude code 回報錯誤"):
            parse_claude_code_output(_read("claude_code_error_result.jsonl"))

    def test_missing_result_event_raises(self) -> None:
        with pytest.raises(ProviderError, match="result 事件"):
            parse_claude_code_output('{"type":"system","subtype":"hook_started"}\n')


class TestWebsearchResultUrlsMixedTypes:
    def test_ignores_non_dict_entries_in_results_array(self) -> None:
        """實測踩到的真實落差（不是探測樣本）：tool_use_result.results 可能是
        混型陣列，除了帶 content 的 dict，還混一個 CLI 自己生成的純字串摘要。
        逐項要先判斷型別，不能假設整個陣列同型（否則 .get()/.keys() 對字串
        會直接丟 AttributeError，把整條 run 打斷）。"""
        events = [{
            "type": "user",
            "tool_use_result": {
                "query": "q",
                "results": [
                    {"tool_use_id": "t1", "content": [{"title": "x", "url": "https://real.example.com/a"}]},
                    "純文字摘要，不是搜尋結果 dict，不該被當成 dict 處理",
                ],
            },
        }]
        urls = cli_providers._websearch_result_urls(events)
        assert urls == {"https://real.example.com/a"}


class TestWebsearchResultUrlsFallback:
    def test_falls_back_to_text_extraction_without_structured_results(self) -> None:
        """沒有 tool_use_result.results 結構時，退回對 tool_result 文字內容做 URL 抽取。"""
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "WebSearch", "input": {"query": "q"}},
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "content": "看這篇 https://fallback.example.com/a 或這篇"},
            ]}},
        ]
        urls = cli_providers._websearch_result_urls(events)
        assert "https://fallback.example.com/a" in urls


class TestRunCli:
    def test_missing_executable_raises_fatal(self, tmp_path: Path) -> None:
        with pytest.raises(ProviderFatalError, match="找不到本機 CLI 執行檔"):
            cli_providers._run_cli(["definitely-not-a-real-cli-xyz"], timeout=5, cwd=tmp_path)

    def test_timeout_raises_provider_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="x", timeout=1)

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        with pytest.raises(ProviderError, match="逾時"):
            cli_providers._run_cli(["fake"], timeout=1, cwd=tmp_path)

    def test_nonzero_exit_raises_provider_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "boom"

        monkeypatch.setattr(cli_providers.subprocess, "run", lambda *a, **k: FakeResult())
        with pytest.raises(ProviderError, match="exit=1"):
            cli_providers._run_cli(["fake"], timeout=1, cwd=tmp_path)

    def test_stdin_is_devnull(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = {}

        class FakeResult:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(args, **kwargs):
            captured.update(kwargs)
            return FakeResult()

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        cli_providers._run_cli(["fake"], timeout=1, cwd=tmp_path)
        assert captured["stdin"] == subprocess.DEVNULL

    def test_unset_env_removes_keys(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDECODE", "1")
        captured = {}

        class FakeResult:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(args, **kwargs):
            captured.update(kwargs)
            return FakeResult()

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        cli_providers._run_cli(["fake"], timeout=1, cwd=tmp_path, unset_env=("CLAUDECODE",))
        assert "CLAUDECODE" not in captured["env"]


class TestCodexModelResolution:
    """實跑批次撞到的真 bug：帳戶不接受硬塞的 -m gpt-5.4（400
    invalid_request_error）。修法是『沒明確傳 model 就不帶 -m』；
    self.model 這個記錄用欄位改用 config.toml 或佔位字串（設計決定 6）。"""

    def test_explicit_model_is_recorded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(cli_providers, "_read_codex_config_model", lambda: "should-not-be-used")
        provider = CodexProvider(model="gpt-5.4-custom")
        assert provider.model == "gpt-5.4-custom"

    def test_no_explicit_model_reads_config_toml(self, tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "config.toml").write_text('model = "gpt-5.6-sol"\n', encoding="utf-8")
        monkeypatch.setenv("CODEX_HOME", str(tmp_path))
        provider = CodexProvider()
        assert provider.model == "gpt-5.6-sol"

    def test_no_explicit_model_and_missing_config_falls_back_to_placeholder(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODEX_HOME", str(tmp_path))  # 目錄存在但沒有 config.toml
        provider = CodexProvider()
        assert provider.model == cli_providers.CODEX_FALLBACK_MODEL_LABEL

    def test_falls_back_to_home_dot_codex_when_codex_home_unset(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CODEX_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir()
        (codex_dir / "config.toml").write_text('model = "gpt-5.9-x"\n', encoding="utf-8")
        provider = CodexProvider()
        assert provider.model == "gpt-5.9-x"

    def test_malformed_config_toml_does_not_raise(self, tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "config.toml").write_text("not valid = = toml{{{", encoding="utf-8")
        monkeypatch.setenv("CODEX_HOME", str(tmp_path))
        provider = CodexProvider()
        assert provider.model == cli_providers.CODEX_FALLBACK_MODEL_LABEL


class TestCodexProviderAnswer:
    @staticmethod
    def _fake_run(stdout_by_call, monkeypatch: pytest.MonkeyPatch):
        calls = {"n": 0}

        class FakeResult:
            def __init__(self, returncode, stdout, stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        results = list(stdout_by_call)

        def fake_run(args, **kwargs):
            idx = min(calls["n"], len(results) - 1)
            calls["n"] += 1
            returncode, stdout = results[idx]
            return FakeResult(returncode, stdout)

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        return calls

    def test_answer_invokes_expected_args_and_parses(self, tmp_path: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
        captured = {}

        class FakeResult:
            returncode = 0
            stdout = _read("codex_grounded.jsonl")
            stderr = ""

        def fake_run(args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return FakeResult()

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        provider = CodexProvider(model="gpt-5.4", executable="codex")
        answer = provider.answer("範例問題？")

        args = captured["args"]
        assert args[0] == "codex"
        assert "--search" in args and args[args.index("--search") + 1] == "exec"
        assert "--sandbox" in args and args[args.index("--sandbox") + 1] == "read-only"
        # --ignore-user-config：實測證實 ~/.codex/config.toml 的
        # persistent_instructions 是「codex 主動搜尋/讀取本機專案文件」的
        # 根因（見設計決定 5），不帶這個旗標會誘發不必要的 command_execution。
        assert "--ignore-user-config" in args
        assert "-m" in args and args[args.index("-m") + 1] == "gpt-5.4"
        assert "--output-schema" in args
        assert args[-1].endswith("範例問題？")  # prompt 前綴限制說明後接原始 prompt
        assert answer.is_grounded

    def test_does_not_pass_dash_m_when_model_not_overridden(self, tmp_path: Path,
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
        """實測撞到的真 bug：帳戶不支援硬塞的 -m gpt-5.4。修法是沒有明確
        model 時完全不帶 -m，讓帳戶自己決定（見設計決定 6）。"""
        captured = {}

        class FakeResult:
            returncode = 0
            stdout = _read("codex_grounded.jsonl")
            stderr = ""

        def fake_run(args, **kwargs):
            captured["args"] = args
            return FakeResult()

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        monkeypatch.setattr(cli_providers, "_read_codex_config_model", lambda: None)
        provider = CodexProvider(model=None)
        provider.answer("範例問題？")
        assert "-m" not in captured["args"]

    def test_fatal_when_executable_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(args, **kwargs):
            raise FileNotFoundError(args[0])

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        monkeypatch.setattr(cli_providers, "_read_codex_config_model", lambda: None)
        provider = CodexProvider(executable="no-such-codex-binary")
        with pytest.raises(ProviderFatalError):
            provider.answer("q")

    def test_model_not_supported_400_is_fatal_with_api_message(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        """實例：2026-09-04 真跑批次撞到的原始 bug。stderr 只有
        『Reading additional input from stdin...』，真正原因要從 stdout
        的 JSONL 事件裡挖，不能只截 stderr（team-lead 回報的落差）。"""
        self._fake_run([(1, _read("codex_model_not_supported.jsonl"))], monkeypatch)
        monkeypatch.setattr(cli_providers, "_read_codex_config_model", lambda: None)
        provider = CodexProvider(model="gpt-5.4")
        with pytest.raises(ProviderFatalError, match="not supported when using Codex"):
            provider.answer("q")

    def test_rate_limited_429_retries_then_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = self._fake_run(
            [(1, _read("codex_rate_limited.jsonl")), (0, _read("codex_grounded.jsonl"))],
            monkeypatch,
        )
        monkeypatch.setattr(cli_providers.time, "sleep", lambda _seconds: None)
        monkeypatch.setattr(cli_providers, "_read_codex_config_model", lambda: None)
        provider = CodexProvider(model="gpt-5.4")
        answer = provider.answer("q")
        assert answer.is_grounded
        assert calls["n"] == 2

    def test_rate_limited_429_exhausts_attempts_raises_provider_error(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._fake_run(
            [(1, _read("codex_rate_limited.jsonl"))] * cli_providers.CODEX_MAX_ATTEMPTS,
            monkeypatch,
        )
        monkeypatch.setattr(cli_providers.time, "sleep", lambda _seconds: None)
        monkeypatch.setattr(cli_providers, "_read_codex_config_model", lambda: None)
        provider = CodexProvider(model="gpt-5.4")
        with pytest.raises(ProviderError, match="usage limit"):
            provider.answer("q")

    def test_nonzero_exit_without_parseable_payload_uses_stderr(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        class FakeResult:
            returncode = 1
            stdout = "not jsonl at all\n"
            stderr = "boom from stderr"

        monkeypatch.setattr(cli_providers.subprocess, "run", lambda *a, **k: FakeResult())
        monkeypatch.setattr(cli_providers, "_read_codex_config_model", lambda: None)
        provider = CodexProvider(model="gpt-5.4")
        with pytest.raises(ProviderError, match="boom from stderr"):
            provider.answer("q")


class TestCodexFailureParsing:
    def test_extracts_message_from_turn_failed(self) -> None:
        display, payload = cli_providers._codex_failure_detail(_read("codex_model_not_supported.jsonl"))
        assert "not supported when using Codex" in display
        assert payload["status"] == 400

    def test_is_fatal_for_invalid_request_error(self) -> None:
        _, payload = cli_providers._codex_failure_detail(_read("codex_model_not_supported.jsonl"))
        assert cli_providers._is_fatal_codex_error(payload)
        assert not cli_providers._is_retryable_codex_error(payload)

    def test_is_retryable_for_429(self) -> None:
        _, payload = cli_providers._codex_failure_detail(_read("codex_rate_limited.jsonl"))
        assert cli_providers._is_retryable_codex_error(payload)
        assert not cli_providers._is_fatal_codex_error(payload)

    def test_no_failure_event_returns_empty(self) -> None:
        display, payload = cli_providers._codex_failure_detail(_read("codex_grounded.jsonl"))
        assert display == "" and payload is None

    def test_model_from_events_reads_top_level_or_item_field(self) -> None:
        assert cli_providers._model_from_events([{"type": "x", "model": "m1"}]) == "m1"
        assert cli_providers._model_from_events(
            [{"type": "item.completed", "item": {"model": "m2"}}]) == "m2"
        assert cli_providers._model_from_events([{"type": "thread.started"}]) is None


class TestClaudeCodeProviderAnswer:
    def test_answer_invokes_expected_args_and_parses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = {}

        class FakeResult:
            returncode = 0
            stdout = _read("claude_code_grounded.jsonl")
            stderr = ""

        def fake_run(args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return FakeResult()

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        provider = ClaudeCodeProvider(model="claude-sonnet-5", executable="claude")
        answer = provider.answer("範例問題？")

        args = captured["args"]
        assert args[0] == "claude"
        assert "--allowedTools" in args and args[args.index("--allowedTools") + 1] == "WebSearch"
        assert "--output-format" in args and args[args.index("--output-format") + 1] == "stream-json"
        assert "--model" in args and args[args.index("--model") + 1] == "claude-sonnet-5"
        assert cli_providers.CLAUDE_CODE_SEARCH_DIRECTIVE in args[args.index("-p") + 1]
        assert answer.is_grounded
        assert captured["kwargs"]["env"].get("CLAUDECODE") is None

    def test_timeout_raises_provider_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="claude", timeout=240)

        monkeypatch.setattr(cli_providers.subprocess, "run", fake_run)
        provider = ClaudeCodeProvider(timeout=240)
        with pytest.raises(ProviderError, match="逾時"):
            provider.answer("q")
