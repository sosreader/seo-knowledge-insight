"""eval.yml 的呼叫方式要和腳本的進入點一致。

背景（2026-10-24）：retrieval、grounding、report_quality 把 run_eval() 放在
`if __name__ == "__main__"` 底下，workflow 卻用 `lmnr eval <file>` 執行。lmnr 只匯入模組，
CI log 是 `Loaded 0 evaluations`，門檻閘門從沒跑過。本測試把「怎麼呼叫」與「進入點在哪」綁在一起。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT_DIR / ".github" / "workflows" / "eval.yml"
_MAIN_GUARD = re.compile(r'^if __name__ == ["\']__main__["\']:', re.MULTILINE)
_LMNR_EVAL = re.compile(r"lmnr eval (evals/[\w]+\.py)")
_PYTHON_RUN = re.compile(r"(?<![\w-])python (evals/[\w]+\.py)")


def _run_commands() -> list[str]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = data["jobs"]["eval"]["steps"]
    return [step["run"] for step in steps if "run" in step]


def _targets(pattern: re.Pattern[str]) -> list[str]:
    return sorted({m for cmd in _run_commands() for m in pattern.findall(cmd)})


@pytest.mark.parametrize("script", _targets(_LMNR_EVAL))
def test_lmnr_eval_only_for_module_level_evaluate(script: str) -> None:
    source = (ROOT_DIR / script).read_text(encoding="utf-8")
    assert not _MAIN_GUARD.search(source), (
        f"{script} 的進入點在 __main__ 底下，`lmnr eval` 不會執行它；請改用 `python {script}`"
    )


@pytest.mark.parametrize("script", _targets(_PYTHON_RUN))
def test_python_invocation_matches_main_guard(script: str) -> None:
    source = (ROOT_DIR / script).read_text(encoding="utf-8")
    assert _MAIN_GUARD.search(source), f"{script} 沒有 __main__ 進入點，`python {script}` 不會做任何事"


def test_gate_scripts_are_invoked_with_python() -> None:
    expected = {
        "evals/eval_retrieval.py",
        "evals/eval_meeting_prep_structure.py",
        "evals/eval_meeting_prep_grounding.py",
        "evals/eval_report_quality.py",
    }
    assert expected <= set(_targets(_PYTHON_RUN))


def test_workflow_no_longer_references_supabase_secrets() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets.SUPABASE" not in text
