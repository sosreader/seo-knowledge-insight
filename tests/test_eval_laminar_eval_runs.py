"""回歸測試：_eval_laminar.py 的 keyword-retrieval 把 IR 指標寫進 eval_runs。

背景（2026-09-15）：quality_gate.py 的 hit_rate_min／mrr_min 讀 eval_runs，但
_eval_laminar.py 只把指標推到 Laminar Dashboard，從未寫回 eval_runs（live 查
eval_runs 為 0 筆）——ETL workflow 的 Quality Gate 從設計上不可能通過。

本檔鎖住：
  1. compute_retrieval_metrics 用與 Laminar 相同的 evaluator 組合算平均，
     檢索例外不吞。
  2. keyword-retrieval 以 group=keyword-retrieval、service key 寫入 eval_runs，
     passed 依 quality_gate 的門檻；寫入失敗時 Laminar 照推、process 最後 exit 1。
  3. retrieval-enhancement 不寫 eval_runs（gate 不讀它）。
  4. 寫入端寫的東西，gate 讀得到（writer → gate round-trip）。
  5. workflow 的 Run retrieval eval step 帶 SUPABASE_SERVICE_KEY，且排在 gate 之前。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from scripts import _eval_data_quality as edq
from scripts import _eval_laminar as el
from scripts import quality_gate as qg

_WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "etl-and-deploy.yml"

_QAS = [
    {"id": "1", "question": "canonical 設定", "answer": "說明", "keywords": ["canonical"], "category": "技術SEO"},
    {"id": "2", "question": "外部連結", "answer": "與 canonical 無關", "keywords": ["backlink"], "category": "連結"},
]
# case 1：top1 命中 → hit 1、mrr 1；case 2：唯一結果是「連結」→ hit 0、mrr 0
_CASES = [
    {"query": "canonical", "expected_categories": ["技術SEO"]},
    {"query": "backlink", "expected_categories": ["技術SEO"]},
]


class TestComputeRetrievalMetrics:
    def test_averages_every_laminar_evaluator(self) -> None:
        metrics = el.compute_retrieval_metrics(_CASES, _QAS, top_k=5)
        assert set(metrics) == set(el.KEYWORD_RETRIEVAL_EVALUATORS) | {"cases", "top_k", "total"}
        assert metrics["hit_rate"] == 0.5
        assert metrics["mrr"] == 0.5
        assert metrics["precision"] == 0.25  # (1/2 + 0/1) / 2
        assert (metrics["cases"], metrics["top_k"], metrics["total"]) == (2, 5, 2)

    def test_empty_golden_set_raises(self) -> None:
        with pytest.raises(ValueError, match="golden_cases 不可為空"):
            el.compute_retrieval_metrics([], _QAS, top_k=5)

    def test_search_errors_are_not_swallowed(self) -> None:
        """safe_executor 回 [] 只給 Laminar 用；寫進 eval_runs 的數字不能靠吞例外得來。"""
        with pytest.raises(AttributeError):
            el.compute_retrieval_metrics(_CASES, [{"question": None, "category": "x"}], top_k=5)


class TestPersistKeywordRetrieval:
    def test_writes_keyword_retrieval_group(self) -> None:
        metrics = {"hit_rate": 0.95, "mrr": 0.85, "total": 10}
        with patch.object(el, "_upsert_eval_run") as upsert:
            assert el._persist_keyword_retrieval(metrics) is True
        upsert.assert_called_once_with(metrics, "keyword-retrieval", True)

    @pytest.mark.parametrize("hit_rate,mrr", [(0.89, 0.9), (0.95, 0.79)])
    def test_passed_uses_gate_thresholds(self, hit_rate: float, mrr: float) -> None:
        with patch.object(el, "_upsert_eval_run") as upsert:
            el._persist_keyword_retrieval({"hit_rate": hit_rate, "mrr": mrr})
        assert upsert.call_args.args[2] is False

    def test_write_failure_returns_false_and_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch.object(el, "_upsert_eval_run", side_effect=edq.EvalRunPersistError("HTTP 401")):
            assert el._persist_keyword_retrieval({"hit_rate": 1.0, "mrr": 1.0}) is False
        assert "eval_runs 寫入失敗" in caplog.text and "HTTP 401" in caplog.text

    def test_posts_to_eval_runs_with_service_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-role-test-key")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")
        metrics = el.compute_retrieval_metrics(_CASES, _QAS, top_k=5)

        with patch.object(edq.requests, "post", return_value=Mock(status_code=201)) as post:
            assert el._persist_keyword_retrieval(metrics) is True

        assert post.call_args.args[0] == "https://example.supabase.co/rest/v1/eval_runs"
        assert post.call_args.kwargs["headers"]["apikey"] == "service-role-test-key"
        payload = post.call_args.kwargs["json"]
        assert payload["group_name"] == "keyword-retrieval"
        assert payload["qa_count"] == 2
        assert payload["passed"] is False
        assert payload["metrics"]["hit_rate"] == 0.5 and payload["metrics"]["mrr"] == 0.5

    def test_written_row_is_what_the_gate_reads(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """writer → gate round-trip：把實際 POST 出去的 payload 當成 eval_runs 那一筆餵給 gate。"""
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-role-test-key")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")
        now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
        with patch.object(edq.requests, "post", return_value=Mock(status_code=201)) as post:
            el._persist_keyword_retrieval(el.compute_retrieval_metrics(_CASES, _QAS, top_k=5))
            edq._upsert_eval_run({"total": 32439, "avg_confidence": 0.8}, edq.DEFAULT_GROUP, True)
        rows = {
            call.kwargs["json"]["group_name"]: {**call.kwargs["json"], "run_at": now.isoformat()}
            for call in post.call_args_list
        }

        def fake_get(url: str, params: dict, headers: dict, timeout: int) -> Mock:
            row = rows.get(params["group_name"].removeprefix("eq."))
            return Mock(status_code=200, json=Mock(return_value=[row] if row else []))

        with patch.object(qg.requests, "get", side_effect=fake_get):
            metrics, problems = qg._load_from_supabase(6, now=now)

        assert problems == []
        assert metrics == {"qa_count": 32439.0, "avg_confidence": 0.8, "hit_rate": 0.5, "mrr": 0.5}
        assert qg._check_thresholds(metrics) == [
            "hit_rate=0.500 < threshold=0.900",
            "mrr=0.500 < threshold=0.800",
        ]


# ── main() ──────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_laminar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    golden = tmp_path / "golden_retrieval.json"
    golden.write_text(json.dumps(_CASES, ensure_ascii=False), encoding="utf-8")
    evaluate = MagicMock()
    monkeypatch.setitem(sys.modules, "lmnr", MagicMock(evaluate=evaluate))
    monkeypatch.setattr(el, "init_laminar", lambda: None)
    monkeypatch.setattr(el, "_load_qas", lambda source: _QAS)
    monkeypatch.setattr(el, "GOLDEN_RETRIEVAL_PATH", golden)
    return evaluate


def _argv(monkeypatch: pytest.MonkeyPatch, group: str) -> None:
    monkeypatch.setattr(sys, "argv", ["_eval_laminar.py", "--source", "supabase", "--group", group])


class TestMain:
    def test_keyword_retrieval_persists_then_pushes_laminar(
        self, fake_laminar: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        persist = MagicMock(return_value=True)
        monkeypatch.setattr(el, "_persist_keyword_retrieval", persist)
        _argv(monkeypatch, "keyword-retrieval")

        el.main()

        assert persist.call_args.args[0]["hit_rate"] == 0.5
        kwargs = fake_laminar.call_args.kwargs
        assert kwargs["group_name"] == "keyword-retrieval"
        assert set(kwargs["evaluators"]) == set(el.KEYWORD_RETRIEVAL_EVALUATORS)
        assert len(kwargs["data"]) == len(_CASES)
        assert kwargs["executor"]({"query": "canonical", "top_k": 5})[0]["category"] == "技術SEO"
        assert kwargs["executor"]({"top_k": 5}) == []  # safe_executor 只對 Laminar 吞例外

    def test_persist_failure_still_pushes_laminar_then_exits_1(
        self, fake_laminar: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(el, "_persist_keyword_retrieval", MagicMock(return_value=False))
        _argv(monkeypatch, "keyword-retrieval")

        with pytest.raises(SystemExit) as exc:
            el.main()

        assert exc.value.code == 1
        fake_laminar.assert_called_once()

    def test_retrieval_enhancement_does_not_write_eval_runs(
        self, fake_laminar: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        persist = MagicMock()
        monkeypatch.setattr(el, "_persist_keyword_retrieval", persist)
        _argv(monkeypatch, "retrieval-enhancement")

        el.main()

        persist.assert_not_called()
        assert fake_laminar.call_args.kwargs["group_name"] == "retrieval-enhancement"


# ── 寫入端與 gate 的契約 ────────────────────────────────────────────────────


def test_gate_groups_and_metric_names_match_writers() -> None:
    assert edq.DEFAULT_GROUP == qg.DATA_QUALITY_GROUP
    retrieval_specs = {s.name for s in qg.METRIC_SPECS if s.group == qg.KEYWORD_RETRIEVAL_GROUP}
    assert retrieval_specs <= set(el.KEYWORD_RETRIEVAL_EVALUATORS)
    dq_metrics = edq.compute_data_quality_metrics(
        [{"question": "q", "answer": "a", "keywords": ["a", "b", "c"], "confidence": 0.9}]
    )
    dq_specs = {s.name for s in qg.METRIC_SPECS if s.group == qg.DATA_QUALITY_GROUP}
    # qa_count 由 _upsert_eval_run 從 metrics["total"] 寫到 eval_runs.qa_count 欄位
    assert dq_specs - {"qa_count"} <= set(dq_metrics) and "total" in dq_metrics


class TestWorkflow:
    @staticmethod
    def _step(name: str) -> str:
        workflow = _WORKFLOW.read_text(encoding="utf-8")
        match = re.search(rf"- name: {re.escape(name)}\n(.*?)(?=\n      - name:|\Z)", workflow, re.DOTALL)
        assert match, f"找不到「{name}」這個 step"
        return match.group(1)

    def test_run_retrieval_eval_step_has_service_key(self) -> None:
        step = self._step("Run retrieval eval")
        assert "SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}" in step
        assert "SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}" in step, "讀 qa_items 仍走 anon key"
        assert "--group keyword-retrieval" in step

    def test_both_writers_run_before_the_gate(self) -> None:
        workflow = _WORKFLOW.read_text(encoding="utf-8")
        order = [workflow.index(f"- name: {n}\n") for n in ("Run data quality eval", "Run retrieval eval", "Quality Gate")]
        assert order == sorted(order)

    def test_gate_step_does_not_need_service_key(self) -> None:
        """gate 只讀 eval_runs（anon SELECT 已開放），不該拿到寫入權限。"""
        assert "SUPABASE_SERVICE_KEY" not in self._step("Quality Gate")
