"""run_pipeline 的 step 解析與對照表形狀

CI run 28662635378：workflow 呼叫 `--step fetch-articles` 但 STEP_SCRIPTS
沒有這個 step（workflow 與 script 的合約漂移，該 step 自 2026-03-06 寫入
workflow 起從未成功執行）。
"""
import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from run_pipeline import _NO_PREFLIGHT_SCRIPTS, STEP_SCRIPTS, _parse_step


def test_every_workflow_step_exists():
    for step in ("fetch-notion", "fetch-articles", "extract-qa", "dedupe-classify", "generate-report"):
        assert _parse_step(step) == step


def test_fetch_articles_maps_to_httpx_scripts_only():
    scripts = STEP_SCRIPTS["fetch-articles"]
    assert scripts == ("01c_fetch_ithelp.py", "01d_fetch_google_cases.py")
    assert "01b_fetch_medium.py" not in scripts


def test_all_step_scripts_exist_on_disk():
    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    for scripts in STEP_SCRIPTS.values():
        for script in scripts:
            assert (scripts_dir / script).is_file(), f"{script} 不存在"


def test_no_preflight_scripts_are_subset_of_step_scripts():
    all_scripts = {s for group in STEP_SCRIPTS.values() for s in group}
    assert _NO_PREFLIGHT_SCRIPTS <= all_scripts


def test_unknown_step_raises_with_valid_values():
    with pytest.raises(argparse.ArgumentTypeError, match="fetch-articles"):
        _parse_step("fetch-everything")


def test_numeric_aliases_unchanged():
    assert _parse_step("1") == "fetch-notion"
    assert _parse_step("4") == "generate-report"
