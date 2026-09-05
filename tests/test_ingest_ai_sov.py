"""Tests for scripts/ingest_ai_sov.py 與 scripts/ai_sov_warehouse.py（S6.2）。

三個重點：
  1. build_row 產出的形狀必須通得過 migration 024 的 CHECK（rank 與 cited
     成對、陣列長度等於 citation_count、hash 是 64 位 hex、week_start 是週一）。
     這裡用純函式驗，DB 那邊另有實測（.verification/.../migration-024-local-postgres.txt）。
  2. summarize() 與 SQL 視圖 ai_sov_weekly 必須算出同一組數字——本檔用與
     本機 postgres 驗證時**完全相同的測資**，把兩邊的結果釘在一起。
  3. 失敗路徑：provider 失敗不產生列、不計入比例；半套的 run 不得 sweep。
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ai_sov_cli_providers as cli_providers  # noqa: E402
import ai_sov_warehouse as warehouse  # noqa: E402
import ingest_ai_sov as ingest  # noqa: E402
from ai_sov_panel import PanelPrompt  # noqa: E402
from ai_sov_providers import (  # noqa: E402
    Citation,
    FakeProvider,
    ProviderAnswer,
    ProviderError,
    ProviderFatalError,
    dedupe_citations,
)

UTC = timezone.utc
WEEK = date(2026, 8, 31)          # 週一
RUN_AT = datetime(2026, 8, 31, 6, 20, tzinfo=UTC)
PROMPT = PanelPrompt(id="p1", theme="theme-a", prompt="問題？", source_query="q")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _row(answer: ProviderAnswer, *, prompt: PanelPrompt = PROMPT, repeat_idx: int = 0) -> dict:
    return ingest.build_row(prompt, repeat_idx, answer, provider="fake", model="fake-1",
                            week_start=WEEK, run_at=RUN_AT, target_domain="vocus.cc")


def _answer(urls: list[str], text: str = "答案") -> ProviderAnswer:
    return ProviderAnswer(text=text, citations=dedupe_citations(urls))


class TestWeekStartAlignment:
    @pytest.mark.parametrize("moment,expected", [
        ("2026-08-31T00:00:00Z", date(2026, 8, 31)),
        ("2026-08-31T23:59:59Z", date(2026, 8, 31)),
        ("2026-09-04T06:20:00Z", date(2026, 8, 31)),
        ("2026-09-06T23:59:59Z", date(2026, 8, 31)),
        ("2026-09-07T00:00:00Z", date(2026, 9, 7)),
    ])
    def test_aligns_to_monday(self, moment: str, expected: date) -> None:
        got = warehouse.week_start_for(datetime.fromisoformat(moment.replace("Z", "+00:00")))
        assert got == expected and got.isoweekday() == 1

    def test_non_utc_input_is_converted_first(self) -> None:
        """本地時間的週一凌晨在 UTC 可能還是上週日——對齊前必須先轉 UTC，
        否則 week_start 會標成下一週，撞 migration 024 的 run_at_in_week_ck。"""
        from datetime import timedelta
        taipei_monday = datetime(2026, 9, 7, 1, 0, tzinfo=timezone(timedelta(hours=8)))
        assert warehouse.week_start_for(taipei_monday) == date(2026, 8, 31)


class TestBuildRow:
    def test_cited_row_shape(self) -> None:
        row = _row(_answer(["https://a.test/1", "https://vocus.cc/x"]))
        assert row["cited"] is True
        assert row["citation_rank"] == 2
        assert row["citation_count"] == 2
        assert row["grounding"] == "grounded"
        assert row["cited_domains"] == ["a.test", "vocus.cc"]

    def test_grounded_but_not_cited_has_null_rank(self) -> None:
        row = _row(_answer(["https://a.test/1"]))
        assert row["cited"] is False and row["citation_rank"] is None
        assert row["grounding"] == "grounded"

    def test_ungrounded_row(self) -> None:
        row = _row(_answer([]))
        assert row["grounding"] == "ungrounded"
        assert row["citation_count"] == 0
        assert row["cited_urls"] == [] and row["cited_domains"] == []
        assert row["cited"] is False and row["citation_rank"] is None

    def test_subdomain_counts_as_target(self) -> None:
        assert _row(_answer(["https://m.vocus.cc/x"]))["cited"] is True

    def test_lookalike_domain_does_not_count(self) -> None:
        assert _row(_answer(["https://notvocus.cc/x"]))["cited"] is False

    @pytest.mark.parametrize("urls", [[], ["https://a.test/1"], ["https://vocus.cc/x", "https://b.test/1"]])
    def test_satisfies_migration_024_checks(self, urls: list[str]) -> None:
        """逐條對應 024 的 CHECK：陣列長度、rank 成對、hash 形狀、週一標籤。"""
        row = _row(_answer(urls))
        assert len(row["cited_urls"]) == row["citation_count"]
        assert len(row["cited_domains"]) == row["citation_count"]
        assert (row["grounding"] == "grounded") == (row["citation_count"] > 0)
        if row["cited"]:
            assert 1 <= row["citation_rank"] <= row["citation_count"]
        else:
            assert row["citation_rank"] is None
        assert HEX64.match(row["response_hash"])
        assert date.fromisoformat(row["week_start"]).isoweekday() == 1
        assert row["run_at"].endswith("Z")

    def test_response_text_is_not_stored(self) -> None:
        """全文刻意不入庫（可能含個資或第三方內容片段），只留長度與摘要。"""
        row = _row(_answer([], text="這是一段不該進資料庫的回應全文"))
        assert "response_text" not in row
        assert row["response_chars"] == len("這是一段不該進資料庫的回應全文")


class TestSummarizeMatchesSqlView:
    """與 .verification/.../migration-024-local-postgres.txt 同一組測資、同一組期望值。

    postgres 實測輸出（ai_sov_weekly）：
      responses=8 grounded=4 cited=2 prompts_with_grounded_answer=3
      sov_pooled=0.5000 sov_macro=0.3333 ungrounded_ratio=0.5000
    這裡用 Python 重算，兩邊必須一致——不一致代表 SQL 或 summarize 其中一邊
    改了定義而另一邊沒跟上（分母該不該含 ungrounded 是最容易分岔的一條）。
    """

    @staticmethod
    def _fixture_rows() -> list[dict]:
        p1 = PanelPrompt(id="p1", theme="t", prompt="a？", source_query="")
        p2 = PanelPrompt(id="p2", theme="t", prompt="b？", source_query="")
        p3 = PanelPrompt(id="p3", theme="t", prompt="c？", source_query="")
        p4 = PanelPrompt(id="p4", theme="t", prompt="d？", source_query="")
        return [
            _row(_answer(["https://vocus.cc/z"]), prompt=p1, repeat_idx=0),
            _row(_answer(["https://x.test/2", "https://vocus.cc/b"]), prompt=p1, repeat_idx=1),
            _row(_answer([]), prompt=p1, repeat_idx=2),
            _row(_answer([]), prompt=p2, repeat_idx=0),
            _row(_answer([]), prompt=p2, repeat_idx=1),
            _row(_answer([]), prompt=p2, repeat_idx=2),
            _row(_answer(["https://x.test/3", "https://x.test/4"]), prompt=p3, repeat_idx=0),
            _row(_answer(["https://x.test/5", "https://x.test/6"]), prompt=p4, repeat_idx=0),
        ]

    def test_counts_match(self) -> None:
        stats = ingest.summarize(self._fixture_rows())
        assert stats["responses"] == 8
        assert stats["grounded_responses"] == 4
        assert stats["cited_responses"] == 2
        assert stats["prompts_with_grounded_answer"] == 3

    def test_ratios_match_postgres_output(self) -> None:
        stats = ingest.summarize(self._fixture_rows())
        assert stats["sov_pooled"] == pytest.approx(0.5)
        assert stats["sov_macro"] == pytest.approx(1 / 3)
        assert stats["ungrounded_ratio"] == pytest.approx(0.5)

    def test_fully_ungrounded_prompt_excluded_from_macro(self) -> None:
        """p2 三次全 ungrounded，在視圖裡 cite_rate 是 NULL、不參與平均；
        若誤當成 0 併進去，macro 會變成 0.25 而不是 0.3333。"""
        stats = ingest.summarize(self._fixture_rows())
        assert stats["sov_macro"] != pytest.approx(0.25)

    def test_empty_rows_give_none_not_zero(self) -> None:
        """任務書：查不到資料不得以 0 呈現。"""
        stats = ingest.summarize([])
        assert stats["sov_pooled"] is None
        assert stats["sov_macro"] is None
        assert stats["ungrounded_ratio"] is None

    def test_all_ungrounded_gives_none_sov_but_ratio_one(self) -> None:
        rows = [_row(_answer([]), repeat_idx=i) for i in range(3)]
        stats = ingest.summarize(rows)
        assert stats["sov_pooled"] is None and stats["sov_macro"] is None
        assert stats["ungrounded_ratio"] == pytest.approx(1.0)


class TestRunPanel:
    @staticmethod
    def _prompts(n: int) -> tuple[PanelPrompt, ...]:
        return tuple(PanelPrompt(id=f"p{i}", theme="t", prompt=f"問題 {i}？", source_query="")
                     for i in range(n))

    def test_produces_prompts_times_repeats_rows(self) -> None:
        rows, failures = ingest.run_panel(FakeProvider(), self._prompts(4), repeats=3,
                                          target_domain="vocus.cc", week_start=WEEK, run_at=RUN_AT)
        assert len(rows) == 12 and failures == []
        assert sorted({r["repeat_idx"] for r in rows}) == [0, 1, 2]

    def test_provider_failure_produces_no_row_and_is_recorded(self) -> None:
        """失敗不得被記成『這次沒引用』——那會讓 API 故障偽裝成可見度下降。"""

        class FlakyProvider:
            name, model = "flaky", "m"

            def __init__(self) -> None:
                self.calls = 0

            def answer(self, prompt: str) -> ProviderAnswer:
                self.calls += 1
                if self.calls == 2:
                    raise ProviderError("boom")
                return ProviderAnswer(text="ok", citations=(Citation("https://a.test/1", "a.test"),))

        rows, failures = ingest.run_panel(FlakyProvider(), self._prompts(2), repeats=2,
                                          target_domain="vocus.cc", week_start=WEEK, run_at=RUN_AT)
        assert len(rows) == 3
        assert len(failures) == 1 and failures[0].startswith("p0#1")
        assert not any(r["prompt_id"] == "p0" and r["repeat_idx"] == 1 for r in rows)

    def test_failures_do_not_enter_any_ratio(self) -> None:
        class AlwaysFails:
            name, model = "x", "m"

            def answer(self, prompt: str) -> ProviderAnswer:
                raise ProviderError("down")

        rows, failures = ingest.run_panel(AlwaysFails(), self._prompts(3), repeats=2,
                                          target_domain="vocus.cc", week_start=WEEK, run_at=RUN_AT)
        assert rows == [] and len(failures) == 6
        assert ingest.summarize(rows)["ungrounded_ratio"] is None

    def test_fatal_error_aborts_entire_run_immediately(self) -> None:
        """實例：run 33862967625，OpenAI insufficient_quota 對 108 次呼叫各重試，
        白耗 21 分鐘、0 列產出。fatal 錯誤必須在第一次遇到就中止整條 run，
        不得繼續問下一個 prompt（設計決定 4b）。"""

        class QuotaExhausted:
            name, model = "openai", "m"

            def __init__(self) -> None:
                self.calls = 0

            def answer(self, prompt: str) -> ProviderAnswer:
                self.calls += 1
                raise ProviderFatalError("OpenAI 呼叫失敗（不可重試）：HTTP 429：insufficient_quota")

        provider = QuotaExhausted()
        rows, failures = ingest.run_panel(provider, self._prompts(36), repeats=3,
                                          target_domain="vocus.cc", week_start=WEEK, run_at=RUN_AT)
        assert rows == []
        assert len(failures) == 1 and failures[0].startswith("p0#0")
        assert "不可重試" in failures[0]
        assert provider.calls == 1  # 不是 36 * 3 = 108 次

    def test_fatal_error_after_partial_success_keeps_earlier_rows(self) -> None:
        """中止前已成功累積的列要保留，不因為後面遇到 fatal 就整批丟棄
        （既有行為：失敗只影響失敗當下與之後，不回頭抹掉已成功的部分）。"""

        class SucceedsOnceThenFatal:
            name, model = "openai", "m"

            def __init__(self) -> None:
                self.calls = 0

            def answer(self, prompt: str) -> ProviderAnswer:
                self.calls += 1
                if self.calls == 1:
                    return ProviderAnswer(text="ok", citations=(Citation("https://a.test/1", "a.test"),))
                raise ProviderFatalError("quota exhausted")

        provider = SucceedsOnceThenFatal()
        rows, failures = ingest.run_panel(provider, self._prompts(2), repeats=2,
                                          target_domain="vocus.cc", week_start=WEEK, run_at=RUN_AT)
        assert len(rows) == 1 and rows[0]["prompt_id"] == "p0" and rows[0]["repeat_idx"] == 0
        assert len(failures) == 1 and failures[0].startswith("p0#1")
        assert provider.calls == 2


class TestRunPanelConcurrent:
    """concurrency > 1 時走 _run_panel_concurrent，語意與循序模式不完全相同
    （見 run_panel docstring）：fatal 早停在這裡是『偵測到後不再送出新呼叫』，
    不保證恰好只呼叫 1 次。"""

    @staticmethod
    def _prompts(n: int) -> tuple:
        from ai_sov_panel import PanelPrompt

        return tuple(PanelPrompt(id=f"p{i}", theme="t", prompt=f"問題 {i}？", source_query="")
                     for i in range(n))

    def test_produces_same_row_count_as_sequential(self) -> None:
        rows, failures = ingest.run_panel(FakeProvider(), self._prompts(4), repeats=3,
                                          target_domain="vocus.cc", week_start=WEEK, run_at=RUN_AT,
                                          concurrency=3)
        assert len(rows) == 12 and failures == []

    def test_failures_are_recorded_not_dropped(self) -> None:
        import threading

        class FlakyThreadSafe:
            name, model = "flaky", "m"

            def __init__(self) -> None:
                self._lock = threading.Lock()
                self.calls = 0

            def answer(self, prompt: str) -> ProviderAnswer:
                with self._lock:
                    self.calls += 1
                    call_no = self.calls
                if call_no % 3 == 0:
                    raise ProviderError("boom")
                return ProviderAnswer(text="ok", citations=(Citation("https://a.test/1", "a.test"),))

        rows, failures = ingest.run_panel(FlakyThreadSafe(), self._prompts(3), repeats=3,
                                          target_domain="vocus.cc", week_start=WEEK, run_at=RUN_AT,
                                          concurrency=2)
        assert len(rows) + len(failures) == 9
        assert len(failures) == 3

    def test_fatal_error_stops_new_calls_and_keeps_partial_rows(self) -> None:
        import threading

        class FatalAfterFew:
            name, model = "openai", "m"

            def __init__(self) -> None:
                self._lock = threading.Lock()
                self.calls = 0

            def answer(self, prompt: str) -> ProviderAnswer:
                with self._lock:
                    self.calls += 1
                    call_no = self.calls
                if call_no == 1:
                    return ProviderAnswer(text="ok", citations=(Citation("https://a.test/1", "a.test"),))
                raise ProviderFatalError("quota exhausted")

        # 直接呼叫 _run_panel_concurrent（而非經 run_panel）以確保真的走
        # 並行路徑——run_panel(concurrency=1) 會被導去 _run_panel_sequential。
        provider = FatalAfterFew()
        rows, failures = ingest._run_panel_concurrent(
            provider, self._prompts(6), repeats=1, target_domain="vocus.cc",
            week_start=WEEK, run_at=RUN_AT, concurrency=1)
        assert len(rows) == 1
        assert len(failures) == 1 and "quota exhausted" in failures[0]
        assert provider.calls <= 2  # concurrency=1 時最多『飛行中的 1 個』再多 1 個排隊中


class TestRunPanelDispatch:
    def test_concurrency_1_matches_sequential_semantics(self) -> None:
        """run_panel(concurrency=1) 必須精確落在 _run_panel_sequential，
        fatal 時 provider 恰好只被呼叫 1 次——這是 concurrency 這個新參數
        對既有行為做出的唯一承諾（並行模式本身不保證這麼精確，見上面
        TestRunPanelConcurrent 的說明）。"""
        class QuotaExhausted:
            name, model = "openai", "m"

            def __init__(self) -> None:
                self.calls = 0

            def answer(self, prompt: str) -> ProviderAnswer:
                self.calls += 1
                raise ProviderFatalError("不可重試")

        provider = QuotaExhausted()
        prompts = TestRunPanelConcurrent._prompts(5)
        rows, failures = ingest.run_panel(provider, prompts, repeats=2,
                                          target_domain="vocus.cc", week_start=WEEK, run_at=RUN_AT,
                                          concurrency=1)
        assert rows == [] and len(failures) == 1 and provider.calls == 1


class TestResolveProvider:
    def test_fake(self) -> None:
        provider = ingest.resolve_provider("fake", ingest.DEFAULT_MODEL, "vocus.cc")
        assert provider.name == "fake"

    def test_openai_without_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
            ingest.resolve_provider("openai", "m", "vocus.cc")

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ProviderError, match="未知"):
            ingest.resolve_provider("perplexity", "m", "vocus.cc")

    def test_codex_uses_given_model(self) -> None:
        provider = ingest.resolve_provider("codex", "gpt-5.4-custom", "vocus.cc")
        assert provider.name == "codex" and provider.model == "gpt-5.4-custom"

    def test_codex_ignores_sentinel_default_and_does_not_force_dash_m(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        """實例：2026-09-04 真跑批次撞到——沒明確傳 --model 時 CLI 參數落到
        openai 系的 DEFAULT_MODEL（gpt-5.4），ChatGPT 帳戶不接受這個模型，
        回 400 invalid_request_error。resolve_provider 必須把這個 sentinel
        換成 None，讓 CodexProvider 不帶 -m（見該類別 docstring 設計決定 6）。"""
        monkeypatch.setattr(cli_providers, "_read_codex_config_model", lambda: None)
        provider = ingest.resolve_provider("codex", ingest.DEFAULT_MODEL, "vocus.cc")
        assert provider.name == "codex"
        assert provider.model == cli_providers.CODEX_FALLBACK_MODEL_LABEL

    def test_claude_code_falls_back_to_its_own_default_model(self) -> None:
        """--model 未被使用者覆寫時會落到 openai 系的 DEFAULT_MODEL（gpt-5.4），
        對 claude-code 是錯的模型字串，必須換成 claude-code 自己的預設。"""
        provider = ingest.resolve_provider("claude-code", ingest.DEFAULT_MODEL, "vocus.cc")
        assert provider.name == "claude-code" and provider.model == ingest.DEFAULT_CLAUDE_CODE_MODEL

    def test_claude_code_respects_explicit_model_override(self) -> None:
        provider = ingest.resolve_provider("claude-code", "claude-opus-5", "vocus.cc")
        assert provider.model == "claude-opus-5"


class TestArgValidation:
    @staticmethod
    def _args(**kwargs) -> argparse.Namespace:
        base = {"repeats": 3, "concurrency": 1, "max_prompts": 0, "execute": False}
        base.update(kwargs)
        return argparse.Namespace(**base)

    def test_accepts_defaults(self) -> None:
        ingest._validate_args(self._args())

    @pytest.mark.parametrize("repeats", [0, -1, ingest.MAX_REPEATS + 1])
    def test_rejects_out_of_range_repeats(self, repeats: int) -> None:
        with pytest.raises(SystemExit, match="repeats"):
            ingest._validate_args(self._args(repeats=repeats))

    @pytest.mark.parametrize("concurrency", [0, -1, ingest.MAX_CONCURRENCY + 1])
    def test_rejects_out_of_range_concurrency(self, concurrency: int) -> None:
        with pytest.raises(SystemExit, match="concurrency"):
            ingest._validate_args(self._args(concurrency=concurrency))

    def test_rejects_partial_panel_with_execute(self) -> None:
        """半套 panel 寫進去會讓該週的分母與其他週不可比，而且沒有任何訊號。"""
        with pytest.raises(SystemExit, match="max-prompts"):
            ingest._validate_args(self._args(max_prompts=3, execute=True))

    def test_allows_partial_panel_in_dry_run(self) -> None:
        ingest._validate_args(self._args(max_prompts=3, execute=False))


class TestPersistFailureHandling:
    """半套的 run 不得 sweep_stale（會刪掉上一次成功寫入的好資料）。"""

    @pytest.fixture
    def spy(self, monkeypatch: pytest.MonkeyPatch) -> dict:
        state: dict = {"swept": 0, "finished": []}
        monkeypatch.setattr(warehouse, "start_run", lambda *a, **k: "run-1")
        monkeypatch.setattr(warehouse, "finish_run",
                            lambda rid, status, count: state["finished"].append((status, count)))
        monkeypatch.setattr(warehouse, "sweep_stale",
                            lambda *a, **k: state.__setitem__("swept", state["swept"] + 1) or 0)
        return state

    def test_clean_run_sweeps_and_marks_success(self, spy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(warehouse, "upsert_rows", lambda rows, ts: (len(rows), 0))
        code = ingest._persist([_row(_answer([]))], [], WEEK, RUN_AT)
        assert code == 0 and spy["swept"] == 1 and spy["finished"] == [("success", 1)]

    def test_provider_failures_skip_sweep_and_mark_failed(self, spy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(warehouse, "upsert_rows", lambda rows, ts: (len(rows), 0))
        code = ingest._persist([_row(_answer([]))], ["p9#0: boom"], WEEK, RUN_AT)
        assert code == 1 and spy["swept"] == 0 and spy["finished"] == [("failed", 1)]

    def test_write_failures_skip_sweep_and_mark_failed(self, spy: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(warehouse, "upsert_rows", lambda rows, ts: (0, len(rows)))
        code = ingest._persist([_row(_answer([]))], [], WEEK, RUN_AT)
        assert code == 1 and spy["swept"] == 0 and spy["finished"] == [("failed", 0)]


class TestWarehouseHelpers:
    def test_dedupe_rows_keeps_last_on_conflict_key(self) -> None:
        """同批次重複 key 會讓 PostgreSQL 殺掉**整批**（015 冪等契約第 3 點）。"""
        base = dict(week_start="2026-08-31", provider="fake", model="m", prompt_id="p1",
                    repeat_idx=0, marker="old")
        rows = warehouse.dedupe_rows([base, dict(base, marker="new")])
        assert len(rows) == 1 and rows[0]["marker"] == "new"

    def test_dedupe_rows_keeps_distinct_repeats(self) -> None:
        base = dict(week_start="2026-08-31", provider="fake", model="m", prompt_id="p1")
        rows = warehouse.dedupe_rows([dict(base, repeat_idx=i) for i in range(3)])
        assert len(rows) == 3

    def test_iso_z_format(self) -> None:
        assert warehouse.iso_z(RUN_AT) == "2026-08-31T06:20:00Z"

    def test_conflict_key_matches_migration_unique_constraint(self) -> None:
        sql = (Path(__file__).resolve().parent.parent
               / "supabase" / "migrations" / "024_ai_sov.sql").read_text()
        assert "UNIQUE (week_start, provider, model, prompt_id, repeat_idx)" in sql
        assert warehouse.CONFLICT_KEY == "week_start,provider,model,prompt_id,repeat_idx"


class TestVerifyMode:
    """--verify 讀回最新一週的聚合，不呼叫 provider（零成本、可在 workflow 裡當寫入後驗證）。"""

    def test_empty_table_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(warehouse, "latest_week_start", lambda: None)
        assert ingest._verify() == 1

    def test_reads_back_the_aggregate_view_not_the_base_table(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict = {}

        def fake_select_all(path: str) -> list[dict]:
            captured["path"] = path
            return [{"provider": "openai", "model": "m", "responses": 108,
                     "grounded_responses": 90, "sov_macro": 0.31, "ungrounded_ratio": 0.16}]

        monkeypatch.setattr(warehouse, "latest_week_start", lambda: WEEK)
        monkeypatch.setattr(warehouse, "select_all", fake_select_all)
        assert ingest._verify() == 0
        assert "ai_sov_weekly" in captured["path"]
        assert "week_start=eq.2026-08-31" in captured["path"]

    def test_week_present_but_no_aggregate_rows_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(warehouse, "latest_week_start", lambda: WEEK)
        monkeypatch.setattr(warehouse, "select_all", lambda path: [])
        assert ingest._verify() == 1


class TestCliEndToEnd:
    def test_dry_run_with_fake_provider_writes_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        writes: list = []
        monkeypatch.setattr(warehouse, "upsert_rows", lambda *a, **k: writes.append(a) or (0, 0))
        monkeypatch.setattr(sys, "argv",
                            ["ingest_ai_sov.py", "--provider", "fake", "--max-prompts", "2"])
        with pytest.raises(SystemExit) as exc:
            ingest.main()
        assert exc.value.code == 0 and writes == []

    def test_partial_panel_with_execute_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv",
                            ["ingest_ai_sov.py", "--provider", "fake", "--max-prompts", "2", "--execute"])
        with pytest.raises(SystemExit) as exc:
            ingest.main()
        assert "max-prompts" in str(exc.value.code)

    def test_execute_path_persists_and_sweeps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        state: dict = {"swept": 0, "rows": 0, "finished": []}
        monkeypatch.setattr(warehouse, "start_run", lambda *a, **k: "run-1")
        monkeypatch.setattr(warehouse, "upsert_rows",
                            lambda rows, ts: (state.__setitem__("rows", len(rows)), (len(rows), 0))[1])
        monkeypatch.setattr(warehouse, "sweep_stale",
                            lambda *a, **k: state.__setitem__("swept", 1) or 0)
        monkeypatch.setattr(warehouse, "finish_run",
                            lambda rid, status, count: state["finished"].append(status))
        monkeypatch.setattr(sys, "argv",
                            ["ingest_ai_sov.py", "--provider", "fake", "--repeats", "1", "--execute"])
        with pytest.raises(SystemExit) as exc:
            ingest.main()
        assert exc.value.code == 0
        assert state["rows"] == 36 and state["swept"] == 1 and state["finished"] == ["success"]

    def test_verify_flag_short_circuits_before_calling_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(warehouse, "latest_week_start", lambda: None)
        monkeypatch.setattr(sys, "argv", ["ingest_ai_sov.py", "--verify"])
        with pytest.raises(SystemExit) as exc:
            ingest.main()
        assert exc.value.code == 1

    def test_env_supplies_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_SOV_REPEATS", "5")
        monkeypatch.setenv("AI_SOV_MODEL", "some-model")
        monkeypatch.setenv("AI_SOV_PROVIDER", "fake")
        monkeypatch.setattr(sys, "argv", ["ingest_ai_sov.py"])
        args = ingest._parse_args()
        assert (args.repeats, args.model, args.provider) == (5, "some-model", "fake")


class TestLogSummary:
    def test_handles_empty_rows_and_failures(self, caplog: pytest.LogCaptureFixture) -> None:
        """全部失敗時 log 不得印出一個看起來像 0% 的比例（那是任務書禁止的形狀）。"""
        with caplog.at_level("INFO"):
            ingest._log_summary([], ["p1#0: boom"])
        assert "n/a" in caplog.text
        assert "失敗 1 次" in caplog.text


class TestProviderResolutionFailureIsLoud:
    def test_missing_key_exits_with_message_not_fallback_to_fake(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """靜默退回 FakeProvider 會寫進一整週捏造的資料，而且事後分辨不出來。"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr(sys, "argv", ["ingest_ai_sov.py", "--provider", "openai"])
        with pytest.raises(SystemExit) as exc:
            ingest.main()
        assert "OPENAI_API_KEY" in str(exc.value.code)
