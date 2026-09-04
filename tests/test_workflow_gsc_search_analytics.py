"""Tests for .github/workflows/gsc-search-analytics.yml —— S2.5 (h)。

只鎖 yaml 的靜態結構：workflow_dispatch 有 dry_run input（S1.2 加的診斷開關）、
freshness job 有一個 step 執行 gsc_discover_pages 這條新 pipeline（S2.4）。
不觸發 gh workflow run、不打 GSC API——那是 S1.2／S2.6 live 驗證的範圍。
"""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent / ".github" / "workflows" / "gsc-search-analytics.yml"
)


def _load_workflow() -> dict:
    """PyYAML 的 safe_load 對裸 `on:` key 沿用 YAML 1.1 的布林解析，會變成
    True 而不是字串 "on"——doc.get("on", doc.get(True)) 兩種解析結果都接得住，
    不依賴 PyYAML 版本或未來改用 yaml.safe_load(..., Loader=...) 的細節。"""
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


class TestWorkflowDispatchDryRunInput:
    def test_workflow_dispatch_has_dry_run_input(self) -> None:
        doc = _load_workflow()
        on_block = doc.get("on", doc.get(True))
        assert "dry_run" in on_block["workflow_dispatch"]["inputs"]

    def test_dry_run_input_defaults_to_false_string(self) -> None:
        """字串 "false" 不是布林 False——MODE_FLAG 表達式用 `== 'true'` 比較，
        預設值型別打錯會讓判斷恆假或恆真而不報錯，必須釘住確切值。"""
        doc = _load_workflow()
        on_block = doc.get("on", doc.get(True))
        assert on_block["workflow_dispatch"]["inputs"]["dry_run"]["default"] == "false"

    def test_ingest_step_env_switches_mode_flag_on_dry_run_input(self) -> None:
        """MODE_FLAG 的表達式要看 github.event.inputs.dry_run，而不是寫死 --execute——
        沒有這條斷言，S1.2 加的 dry_run input 可能只是個沒人接線的裝飾品。"""
        doc = _load_workflow()
        steps = doc["jobs"]["ingest"]["steps"]
        ingest_step = next(s for s in steps if s.get("name") == "Ingest GSC search analytics")
        mode_flag_expr = ingest_step["env"]["MODE_FLAG"]
        assert "dry_run" in mode_flag_expr
        assert "--dry-run" in mode_flag_expr
        assert "--execute" in mode_flag_expr

    def test_verify_step_skips_when_dry_run(self) -> None:
        """dry-run 沒有寫庫，驗證上一輪的舊資料沒有意義，Verify step 要有
        if 條件在 dry_run=true 時跳過。"""
        doc = _load_workflow()
        steps = doc["jobs"]["ingest"]["steps"]
        verify_step = next(s for s in steps if s.get("name") == "Verify last write")
        assert verify_step.get("if") is not None
        assert "dry_run" in verify_step["if"]


class TestFreshnessJobHasDiscoverPagesStep:
    def test_freshness_job_has_a_step_running_gsc_discover_pages(self) -> None:
        doc = _load_workflow()
        steps = doc["jobs"]["freshness"]["steps"]
        run_commands = [step.get("run", "") for step in steps]
        assert any("--pipeline gsc_discover_pages" in run for run in run_commands)

    def test_discover_pages_step_runs_regardless_of_prior_step_outcome(self) -> None:
        """if: always()——各條 pipeline 互不依賴，一個 FAIL 不該蓋掉其他幾個的結果，
        同 stale-running 步驟與其他 gsc_* 步驟的既有寫法一致。"""
        doc = _load_workflow()
        steps = doc["jobs"]["freshness"]["steps"]
        step = next(s for s in steps if "--pipeline gsc_discover_pages" in s.get("run", ""))
        assert step.get("if") == "always()"

    def test_discover_pages_step_is_distinct_from_discover_totals_step(self) -> None:
        """回歸：gsc_discover（totals）與 gsc_discover_pages 是兩條獨立的 step，
        不可誤合成一條、也不可讓其中一條的 --pipeline 打錯字撞成同一個 key。"""
        doc = _load_workflow()
        steps = doc["jobs"]["freshness"]["steps"]
        run_commands = [step.get("run", "") for step in steps if step.get("run")]
        discover_totals = [r for r in run_commands if "--pipeline gsc_discover" in r
                           and "gsc_discover_pages" not in r]
        assert len(discover_totals) == 1
