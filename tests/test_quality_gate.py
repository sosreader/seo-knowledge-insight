"""回歸測試：scripts/quality_gate.py 的缺值／低於門檻／通過，以及 Supabase 來源。

背景（2026-09-15）：原版 `_check_thresholds` 把缺 hit_rate／mrr fallback 成
0.0、缺 avg_confidence 直接略過；`_load_from_supabase` 把最近 10 筆不分 group
merge 在一起。而 hit_rate／mrr 從來沒有程式碼寫進 eval_runs（live 查 eval_runs
為 0 筆），這道門從設計上不可能通過，失敗訊息卻寫成「hit_rate=0.00% < 90%」。

本檔鎖住：
  1. 缺值一律 FAIL，訊息指出缺哪個指標、該由哪個 group／寫入者提供。
  2. 0.0 是合法值（低於門檻 → FAIL 並報數值）；NaN／bool／字串視為缺值。
  3. Supabase 模式每個 group 各取最新一筆、必須在 max-age 內，不跨 group 借值。
  4. main() 的 exit code：通過 → 正常結束；失敗 → exit 1；--dry-run → 不 exit。
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
import requests

from scripts import quality_gate as qg

_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
# 2026-09-15 live 實測值：data-quality 取自 run 34106023623 log，
# keyword-retrieval 為本機對 Supabase qa_items 唯讀重算（40 cases，top-k=5）。
_PASSING = {"qa_count": 32439, "avg_confidence": 0.7941, "hit_rate": 1.0, "mrr": 0.8967}


def _spec(name: str) -> qg.MetricSpec:
    return next(s for s in qg.METRIC_SPECS if s.name == name)


class TestCheckThresholds:
    def test_all_present_and_above_threshold_passes(self) -> None:
        assert qg._check_thresholds(_PASSING) == []

    def test_exactly_at_threshold_passes(self) -> None:
        metrics = {"qa_count": 1000, "avg_confidence": 0.75, "hit_rate": 0.90, "mrr": 0.80}
        assert qg._check_thresholds(metrics) == []

    @pytest.mark.parametrize("missing", ["qa_count", "avg_confidence", "hit_rate", "mrr"])
    def test_missing_metric_fails_and_names_the_writer(self, missing: str) -> None:
        metrics = {k: v for k, v in _PASSING.items() if k != missing}
        failures = qg._check_thresholds(metrics)
        assert len(failures) == 1
        assert failures[0].startswith(f"{missing} 缺值")
        assert qg.GROUP_WRITERS[_spec(missing).group] in failures[0]
        assert "缺值不視為通過" in failures[0]

    def test_empty_metrics_fails_every_threshold(self) -> None:
        failures = qg._check_thresholds({})
        assert len(failures) == len(qg.METRIC_SPECS)
        assert all("缺值" in f for f in failures)

    def test_missing_avg_confidence_is_not_a_pass(self) -> None:
        """原版 `if avg_conf > 0 and ...`：缺值或 0 直接略過，等於通過。"""
        failures = qg._check_thresholds({**_PASSING, "avg_confidence": 0.0})
        assert failures == ["avg_confidence=0.000 < threshold=0.750"]

    @pytest.mark.parametrize(
        "name,value,expected",
        [
            ("qa_count", 999, "qa_count=999 < threshold=1000"),
            ("avg_confidence", 0.7, "avg_confidence=0.700 < threshold=0.750"),
            ("hit_rate", 0.85, "hit_rate=0.850 < threshold=0.900"),
            ("mrr", 0.0, "mrr=0.000 < threshold=0.800"),
        ],
    )
    def test_below_threshold_fails_with_value(self, name: str, value: float, expected: str) -> None:
        assert qg._check_thresholds({**_PASSING, name: value}) == [expected]

    @pytest.mark.parametrize("bad", [float("nan"), True, "0.95", None, {"v": 1}])
    def test_nan_bool_and_non_numeric_count_as_missing(self, bad: Any) -> None:
        """NaN 最危險：`nan < 0.9` 為 False，不擋就是靜默通過。"""
        failures = qg._check_thresholds({**_PASSING, "hit_rate": bad})
        assert len(failures) == 1 and failures[0].startswith("hit_rate 缺值")

    def test_zero_does_not_fall_through_to_alias(self) -> None:
        """原版 `a or b`：0.0 會被當成缺值，跳去 alias 取一個好看的數字。"""
        failures = qg._check_thresholds({**_PASSING, "hit_rate": 0.0, "hit_rate@5": 0.99})
        assert failures == ["hit_rate=0.000 < threshold=0.900"]

    def test_legacy_aliases_still_accepted(self) -> None:
        metrics = {"total_qa_count": 2000, "average_confidence": 0.8, "hit_rate@5": 0.95, "MRR": 0.85}
        assert qg._check_thresholds(metrics) == []


# ── Supabase 來源 ────────────────────────────────────────────────────────────


def _resp(status: int, payload: Any = None, text: str = "") -> Mock:
    resp = Mock()
    resp.status_code = status
    resp.json.return_value = [] if payload is None else payload
    resp.text = text
    return resp


def _row(group: str, metrics: dict, *, qa_count: int | None = None, age_hours: float = 0.1) -> dict:
    return {
        "group_name": group,
        "metrics": metrics,
        "qa_count": qa_count,
        "run_at": (_NOW - timedelta(hours=age_hours)).isoformat(),
    }


_DQ_ROW = _row(
    "data-quality",
    {"total": 32439, "avg_confidence": 0.7941, "qa_count_in_range": 1.0},
    qa_count=32439,
)
_KR_ROW = _row("keyword-retrieval", {"hit_rate": 1.0, "mrr": 0.8967, "total": 32439}, qa_count=32439)


def _fake_get(rows_by_group: dict[str, dict]):
    def fake(url: str, params: dict, headers: dict, timeout: int) -> Mock:
        row = rows_by_group.get(params["group_name"].removeprefix("eq."))
        return _resp(200, [row] if row else [])

    return fake


@pytest.fixture
def supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co/")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")


@pytest.mark.usefixtures("supabase_env")
class TestLoadFromSupabase:
    def test_latest_row_per_group_merged_into_owned_metrics(self) -> None:
        rows = {"data-quality": _DQ_ROW, "keyword-retrieval": _KR_ROW}
        with patch.object(qg.requests, "get", side_effect=_fake_get(rows)) as get:
            metrics, problems = qg._load_from_supabase(6, now=_NOW)

        assert problems == []
        assert metrics == {"qa_count": 32439.0, "avg_confidence": 0.7941, "hit_rate": 1.0, "mrr": 0.8967}
        assert qg._check_thresholds(metrics) == []

        calls = get.call_args_list
        assert [c.kwargs["params"]["group_name"] for c in calls] == ["eq.data-quality", "eq.keyword-retrieval"]
        for call in calls:
            assert call.args[0] == "https://example.supabase.co/rest/v1/eval_runs"
            assert call.kwargs["params"]["order"] == "run_at.desc"
            assert call.kwargs["params"]["limit"] == "1"
            assert call.kwargs["headers"]["apikey"] == "anon-test-key"

    def test_missing_retrieval_group_is_reported_and_gate_fails(self) -> None:
        """修正前的實況：eval_runs 裡沒有任何 keyword-retrieval 紀錄。"""
        with patch.object(qg.requests, "get", side_effect=_fake_get({"data-quality": _DQ_ROW})):
            metrics, problems = qg._load_from_supabase(6, now=_NOW)

        assert set(metrics) == {"qa_count", "avg_confidence"}
        assert len(problems) == 1
        assert "keyword-retrieval" in problems[0]
        assert qg.GROUP_WRITERS["keyword-retrieval"] in problems[0]
        failed = {f.split(" ")[0] for f in qg._check_thresholds(metrics)}
        assert failed == {"hit_rate", "mrr"}

    def test_empty_table_reports_both_groups(self) -> None:
        with patch.object(qg.requests, "get", side_effect=_fake_get({})):
            metrics, problems = qg._load_from_supabase(6, now=_NOW)
        assert metrics == {}
        assert len(problems) == 2

    def test_does_not_borrow_metrics_across_groups(self) -> None:
        """data-quality 那筆就算帶了 hit_rate，也不能拿來頂 keyword-retrieval 的缺。"""
        dq = _row("data-quality", {**_DQ_ROW["metrics"], "hit_rate": 1.0, "mrr": 1.0}, qa_count=32439)
        with patch.object(qg.requests, "get", side_effect=_fake_get({"data-quality": dq})):
            metrics, _ = qg._load_from_supabase(6, now=_NOW)
        assert "hit_rate" not in metrics and "mrr" not in metrics

    def test_stale_row_is_rejected(self) -> None:
        stale = _row("keyword-retrieval", _KR_ROW["metrics"], age_hours=7 * 24)
        rows = {"data-quality": _DQ_ROW, "keyword-retrieval": stale}
        with patch.object(qg.requests, "get", side_effect=_fake_get(rows)):
            metrics, problems = qg._load_from_supabase(6, now=_NOW)
        assert "hit_rate" not in metrics
        assert len(problems) == 1
        assert "168.0h 前" in problems[0] and "超過 6h" in problems[0]

    def test_max_age_is_configurable(self) -> None:
        stale = _row("keyword-retrieval", _KR_ROW["metrics"], age_hours=7 * 24)
        rows = {"data-quality": _DQ_ROW, "keyword-retrieval": stale}
        with patch.object(qg.requests, "get", side_effect=_fake_get(rows)):
            metrics, problems = qg._load_from_supabase(8 * 24, now=_NOW)
        assert problems == [] and metrics["hit_rate"] == 1.0

    @pytest.mark.parametrize(
        "run_at",
        [
            (_NOW - timedelta(hours=1)).replace(tzinfo=None).isoformat(),
            (_NOW - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ],
    )
    def test_naive_and_z_suffixed_run_at_parse_as_utc(self, run_at: str) -> None:
        rows = {"data-quality": _DQ_ROW, "keyword-retrieval": {**_KR_ROW, "run_at": run_at}}
        with patch.object(qg.requests, "get", side_effect=_fake_get(rows)):
            _, problems = qg._load_from_supabase(6, now=_NOW)
        assert problems == []

    def test_unparseable_run_at_is_reported(self) -> None:
        rows = {"data-quality": _DQ_ROW, "keyword-retrieval": {**_KR_ROW, "run_at": "not-a-date"}}
        with patch.object(qg.requests, "get", side_effect=_fake_get(rows)):
            metrics, problems = qg._load_from_supabase(6, now=_NOW)
        assert "hit_rate" not in metrics
        assert len(problems) == 1 and "無法解析" in problems[0]

    def test_null_qa_count_column_is_missing_not_zero(self) -> None:
        dq = _row("data-quality", {"avg_confidence": 0.8}, qa_count=None)
        rows = {"data-quality": dq, "keyword-retrieval": _KR_ROW}
        with patch.object(qg.requests, "get", side_effect=_fake_get(rows)):
            metrics, _ = qg._load_from_supabase(6, now=_NOW)
        assert "qa_count" not in metrics
        assert any(f.startswith("qa_count 缺值") for f in qg._check_thresholds(metrics))

    def test_http_error_is_reported(self) -> None:
        with patch.object(qg.requests, "get", return_value=_resp(401, text="JWT expired")):
            metrics, problems = qg._load_from_supabase(6, now=_NOW)
        assert metrics == {}
        assert len(problems) == 2 and all("HTTP 401" in p and "JWT expired" in p for p in problems)

    def test_connection_error_is_reported(self) -> None:
        with patch.object(qg.requests, "get", side_effect=requests.ConnectionError("boom")):
            metrics, problems = qg._load_from_supabase(6, now=_NOW)
        assert metrics == {}
        assert len(problems) == 2 and all("連線失敗" in p for p in problems)


def test_missing_credentials_reported_without_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    with patch.object(qg.requests, "get") as get:
        metrics, problems = qg._load_from_supabase(6, now=_NOW)
    get.assert_not_called()
    assert metrics == {}
    assert problems == ["缺 SUPABASE_URL 或 SUPABASE_ANON_KEY，無法讀取 eval_runs"]


# ── 本機來源 ────────────────────────────────────────────────────────────────


class TestLoadFromLocal:
    def test_no_result_files_is_reported(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(qg, "LOCAL_EVALS_DIR", tmp_path / "missing")
        metrics, problems = qg._load_from_local()
        assert metrics == {}
        assert len(problems) == 1 and "找不到本機 eval 結果" in problems[0]

    def test_reads_newest_file_by_mtime(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        older = tmp_path / "eval_results_a.json"
        newer = tmp_path / "eval_results_b.json"
        older.write_text(json.dumps({"hit_rate": 0.1}), encoding="utf-8")
        newer.write_text(json.dumps(_PASSING), encoding="utf-8")
        os.utime(older, (1_000_000, 1_000_000))
        os.utime(newer, (2_000_000, 2_000_000))
        monkeypatch.setattr(qg, "LOCAL_EVALS_DIR", tmp_path)
        assert qg._load_from_local() == (_PASSING, [])


# ── main() exit code ────────────────────────────────────────────────────────


class TestMain:
    @staticmethod
    def _run(argv: list[str], metrics: dict, problems: list[str] | None = None) -> Mock:
        with patch.object(qg, "_load_from_supabase", return_value=(metrics, problems or [])) as load:
            qg.main(argv)
        return load

    def test_pass_returns_normally_with_default_max_age(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.INFO, logger=qg.logger.name)
        load = self._run(["--source", "supabase"], _PASSING)
        load.assert_called_once_with(qg.MAX_EVAL_RUN_AGE_HOURS)
        assert "Quality gate PASSED" in caplog.text

    def test_missing_metric_exits_1(self, caplog: pytest.LogCaptureFixture) -> None:
        with pytest.raises(SystemExit) as exc:
            self._run(["--source", "supabase"], {"qa_count": 32439, "avg_confidence": 0.8})
        assert exc.value.code == 1
        assert "QUALITY GATE FAILED: hit_rate 缺值" in caplog.text
        assert "QUALITY GATE FAILED: mrr 缺值" in caplog.text

    def test_below_threshold_exits_1(self, caplog: pytest.LogCaptureFixture) -> None:
        with pytest.raises(SystemExit) as exc:
            self._run(["--source", "supabase"], {**_PASSING, "mrr": 0.5})
        assert exc.value.code == 1
        assert "mrr=0.500 < threshold=0.800" in caplog.text

    def test_source_problem_fails_even_if_metrics_pass(self) -> None:
        with pytest.raises(SystemExit) as exc:
            self._run(["--source", "supabase"], _PASSING, ["讀取 group='data-quality' 失敗：HTTP 500"])
        assert exc.value.code == 1

    def test_dry_run_reports_but_does_not_exit(self, caplog: pytest.LogCaptureFixture) -> None:
        self._run(["--source", "supabase", "--dry-run"], {})
        assert "QUALITY GATE FAILED" in caplog.text
        assert "Dry-run mode" in caplog.text

    def test_max_age_flag_is_passed_through(self) -> None:
        load = self._run(["--source", "supabase", "--max-age-hours", "48"], _PASSING)
        load.assert_called_once_with(48.0)

    def test_non_positive_max_age_is_rejected(self) -> None:
        with pytest.raises(SystemExit) as exc:
            qg.main(["--source", "supabase", "--max-age-hours", "0"])
        assert exc.value.code == 2

    def test_local_source_without_files_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(qg, "LOCAL_EVALS_DIR", tmp_path)
        with pytest.raises(SystemExit) as exc:
            qg.main(["--source", "local"])
        assert exc.value.code == 1
