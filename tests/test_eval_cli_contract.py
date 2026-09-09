"""回歸測試：workflow 傳給 scripts/*.py 的 CLI flag，腳本必須真的認得。

背景（2026-09-10）：2026-03-10 的 commit e169788（訊息「Refactor code structure
for improved readability and maintainability」）把 scripts/_eval_laminar.py 的
`--source` argparse 與 `_load_qas_supabase()` 整段刪掉，但
.github/workflows/etl-and-deploy.yml 仍在傳 `--source supabase`。結果
`Eval + Quality Gate` job 每次都以 `unrecognized arguments: --source supabase`
退出碼 2 中止，下游 `Build & Deploy to Lambda`（needs: eval）從未執行過——
保留的 31 筆 run 沒有一次 success，這條路徑沉睡了六個月都沒人發現，因為
沒有任何測試把「workflow 怎麼呼叫」與「腳本認得什麼」綁在一起。

本檔就是那條綁定：從 workflow 的 run: 區塊抽出每一個 `python scripts/X.py`
呼叫與它帶的長參數，實際跑一次 `X.py --help`，斷言每個參數都出現在 help 裡。
用 --help 而不是解析原始碼，是因為它驗的是 argparse 實際接受什麼，而不是
某個字串有沒有出現在檔案裡。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = ROOT_DIR / ".github" / "workflows"

# 只掃這幾支：它們的 run: 是靜態的 `python scripts/X.py --flag` 形式。其他
# workflow 把參數包在 shell 變數裡（BACKFILL_HOURS、DRY_RUN…），靜態抽不出來，
# 那些 workflow 各自有專屬的 test_workflow_*.py 鎖語意。
WORKFLOWS_WITH_STATIC_CLI = ["etl-and-deploy.yml"]

_INVOCATION = re.compile(r"python\s+(scripts/[\w.]+\.py)((?:\s+--?[\w-]+(?:\s+[\w./=-]+)?)*)")
_LONG_FLAG = re.compile(r"(?<!\S)(--[\w-]+)")


def _static_invocations(workflow_name: str) -> list[tuple[str, tuple[str, ...]]]:
    text = (WORKFLOWS_DIR / workflow_name).read_text(encoding="utf-8")
    found: dict[str, set[str]] = {}
    for script, tail in _INVOCATION.findall(text):
        found.setdefault(script, set()).update(_LONG_FLAG.findall(tail))
    return sorted((script, tuple(sorted(flags))) for script, flags in found.items())


def _all_invocations() -> list[tuple[str, tuple[str, ...]]]:
    return [inv for name in WORKFLOWS_WITH_STATIC_CLI for inv in _static_invocations(name)]


def test_etl_workflow_still_passes_source_supabase() -> None:
    """先鎖住前提：本測試的價值建立在 workflow 真的有傳 --source。

    哪天有人改成不傳了，這條會先紅，提醒去更新下面那組參數化的預期，
    而不是讓參數化測試安靜地變成零斷言。
    """
    invocations = dict(_static_invocations("etl-and-deploy.yml"))
    assert "--source" in invocations["scripts/_eval_laminar.py"]
    assert "--source" in invocations["scripts/_eval_data_quality.py"]
    assert "--source" in invocations["scripts/quality_gate.py"]


@pytest.mark.parametrize("script,flags", _all_invocations(), ids=lambda v: str(v))
def test_workflow_flags_are_accepted_by_script(script: str, flags: tuple[str, ...]) -> None:
    if not flags:
        pytest.skip(f"{script} 在 workflow 裡沒帶任何長參數")
    result = subprocess.run(
        [sys.executable, str(ROOT_DIR / script), "--help"],
        capture_output=True, text=True, cwd=ROOT_DIR, timeout=120,
    )
    assert result.returncode == 0, f"{script} --help 失敗：{result.stderr[-500:]}"
    for flag in flags:
        assert flag in result.stdout, (
            f"{script} 的 argparse 不認得 workflow 傳的 {flag}——"
            f"這正是 commit e169788 造成 ETL Pipeline 六個月 0 成功的失敗模式。"
        )


class TestQaCountRange:
    """qa_count_in_range 的門檻必須涵蓋正式庫的實際規模。

    2026-09-10 之前是 100–2000，而 Supabase qa_items 實測 32,439 筆
    （ETL run 34106023623 的 log），這條指標恆為 0.0——即使 --source 修好，
    Quality Gate 這項也一定 FAIL。
    """

    OBSERVED_PRODUCTION_COUNT = 32_439

    def _metrics(self, count: int) -> dict:
        from scripts import _eval_data_quality  # noqa: PLC0415

        qas = [
            {"question": f"q{i}", "answer": f"a{i}", "keywords": ["a", "b", "c"], "confidence": 0.9}
            for i in range(count)
        ]
        return _eval_data_quality.compute_data_quality_metrics(qas)

    def test_observed_production_scale_is_in_range(self) -> None:
        from scripts import _eval_data_quality  # noqa: PLC0415

        assert (
            _eval_data_quality.QA_COUNT_MIN
            <= self.OBSERVED_PRODUCTION_COUNT
            <= _eval_data_quality.QA_COUNT_MAX
        ), "實測正式庫規模落在門檻外——這條 gate 會恆為 FAIL"
        assert self._metrics(_eval_data_quality.QA_COUNT_MIN)["qa_count_in_range"] == 1.0

    def test_catastrophic_data_loss_still_fails(self) -> None:
        """門檻放寬不能放寬到失去告警能力：掉到三位數仍要 FAIL。"""
        assert self._metrics(100)["qa_count_in_range"] == 0.0

    def test_range_keeps_an_order_of_magnitude_of_headroom(self) -> None:
        """上下界各留約一個數量級，資料自然成長不會馬上把 gate 逼紅。"""
        from scripts import _eval_data_quality  # noqa: PLC0415

        assert _eval_data_quality.QA_COUNT_MIN <= self.OBSERVED_PRODUCTION_COUNT / 5
        assert _eval_data_quality.QA_COUNT_MAX >= self.OBSERVED_PRODUCTION_COUNT * 5


class TestGoldenDatasetIsAvailableInCI:
    """_eval_laminar.py 讀的 golden dataset 必須是版控中的檔案。

    2026-09-10 發現的第二個斷點：原本指向 output/evals/golden_retrieval.json，
    而 output/ 整個在 .gitignore 裡，etl-and-deploy.yml 的 eval job 也只
    download-artifact 了 qa-output（qa_final / qa_enriched / qa_embeddings*）。
    這條路徑在 CI runner 上永遠不存在——修好 --source 之後會立刻撞上它。
    """

    def test_golden_retrieval_path_is_git_tracked(self) -> None:
        from scripts import _eval_laminar  # noqa: PLC0415

        path = _eval_laminar.GOLDEN_RETRIEVAL_PATH
        assert path.exists(), f"{path} 不存在"
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT_DIR))],
            capture_output=True, text=True, cwd=ROOT_DIR,
        )
        assert tracked.returncode == 0, (
            f"{path} 不在版控裡——CI checkout 之後不會有這個檔案，"
            "eval step 會以「golden_retrieval.json 不存在」退出。"
        )

    def test_golden_dataset_shared_with_other_eval_consumers(self) -> None:
        """與 evals/eval_retrieval.py 用的是同一份，避免兩套 golden 各自漂移。"""
        from evals import eval_retrieval  # noqa: PLC0415
        from scripts import _eval_laminar  # noqa: PLC0415

        assert _eval_laminar.GOLDEN_RETRIEVAL_PATH == eval_retrieval._golden_path
