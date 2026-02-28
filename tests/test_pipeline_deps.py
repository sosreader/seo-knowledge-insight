"""
tests/test_pipeline_deps.py — utils/pipeline_deps.py 單元測試

覆蓋：
- env var 檢查（缺失 → error）
- 單檔依賴（存在/不存在、required/optional）
- glob 依賴（足夠/不足數量）
- 新鮮度檢查（超過閾值 → warning）
- preflight_check 整合（errors → PreflightError, warnings → 繼續）
- check_only 模式（有 error 也不 exit）
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from utils.pipeline_deps import (
    PreflightError,
    StepDependency,
    _check_file_dep,
    _check_freshness,
    _check_glob_dep,
    preflight_check,
)


# ──────────────────────────────────────────────────────
# _check_freshness
# ──────────────────────────────────────────────────────


class TestCheckFreshness:
    def test_fresh_file_no_warning(self, tmp_path: Path) -> None:
        """剛建立的檔案不應產生 warning"""
        f = tmp_path / "fresh.json"
        f.write_text("{}")
        warnings: list[str] = []
        _check_freshness(f, max_age_days=7, warnings=warnings)
        assert warnings == []

    def test_stale_file_adds_warning(self, tmp_path: Path) -> None:
        """超過 max_age_days 的檔案應產生 warning"""
        f = tmp_path / "stale.json"
        f.write_text("{}")
        # 把 mtime 改到 30 天前
        old_time = time.time() - 30 * 86400
        os.utime(f, (old_time, old_time))

        warnings: list[str] = []
        _check_freshness(f, max_age_days=7, warnings=warnings)
        assert len(warnings) == 1
        assert "stale.json" in warnings[0]
        assert "天未更新" in warnings[0]


# ──────────────────────────────────────────────────────
# _check_file_dep
# ──────────────────────────────────────────────────────


class TestCheckFileDep:
    def test_existing_file_no_error(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text("{}")
        dep = StepDependency(path=f, required=True)
        errors: list[str] = []
        warnings: list[str] = []
        _check_file_dep(dep, errors, warnings)
        assert errors == []
        assert warnings == []

    def test_missing_required_file_adds_error(self, tmp_path: Path) -> None:
        dep = StepDependency(
            path=tmp_path / "missing.json",
            required=True,
            hint="請先執行 step X",
        )
        errors: list[str] = []
        warnings: list[str] = []
        _check_file_dep(dep, errors, warnings)
        assert len(errors) == 1
        assert "missing.json" in errors[0]
        assert "請先執行 step X" in errors[0]

    def test_missing_optional_file_adds_warning(self, tmp_path: Path) -> None:
        dep = StepDependency(path=tmp_path / "optional.json", required=False)
        errors: list[str] = []
        warnings: list[str] = []
        _check_file_dep(dep, errors, warnings)
        assert errors == []
        assert len(warnings) == 1

    def test_existing_file_checks_freshness(self, tmp_path: Path) -> None:
        f = tmp_path / "old.json"
        f.write_text("{}")
        old_time = time.time() - 20 * 86400
        os.utime(f, (old_time, old_time))

        dep = StepDependency(path=f, required=True, max_age_days=7)
        errors: list[str] = []
        warnings: list[str] = []
        _check_file_dep(dep, errors, warnings)
        assert errors == []  # 存在就不是 error
        assert len(warnings) == 1  # 但新鮮度有 warning


# ──────────────────────────────────────────────────────
# _check_glob_dep
# ──────────────────────────────────────────────────────


class TestCheckGlobDep:
    def test_enough_files_no_error(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "b.md").write_text("# B")
        dep = StepDependency(
            path=tmp_path,
            glob_pattern="*.md",
            min_count=1,
            required=True,
        )
        errors: list[str] = []
        warnings: list[str] = []
        _check_glob_dep(dep, errors, warnings)
        assert errors == []

    def test_not_enough_files_required_adds_error(self, tmp_path: Path) -> None:
        dep = StepDependency(
            path=tmp_path,
            glob_pattern="*.md",
            min_count=1,
            required=True,
            hint="請先執行 step 1",
        )
        errors: list[str] = []
        warnings: list[str] = []
        _check_glob_dep(dep, errors, warnings)
        assert len(errors) == 1
        assert "0 個檔案" in errors[0]

    def test_not_enough_files_optional_adds_warning(self, tmp_path: Path) -> None:
        dep = StepDependency(
            path=tmp_path,
            glob_pattern="*.md",
            min_count=1,
            required=False,
        )
        errors: list[str] = []
        warnings: list[str] = []
        _check_glob_dep(dep, errors, warnings)
        assert errors == []
        assert len(warnings) == 1

    def test_glob_checks_freshness_of_newest(self, tmp_path: Path) -> None:
        f1 = tmp_path / "old.md"
        f1.write_text("old")
        old_time = time.time() - 20 * 86400
        os.utime(f1, (old_time, old_time))

        dep = StepDependency(
            path=tmp_path,
            glob_pattern="*.md",
            min_count=1,
            required=True,
            max_age_days=7,
        )
        errors: list[str] = []
        warnings: list[str] = []
        _check_glob_dep(dep, errors, warnings)
        assert errors == []
        assert len(warnings) == 1  # newest file is stale


# ──────────────────────────────────────────────────────
# preflight_check（整合）
# ──────────────────────────────────────────────────────


class TestPreflightCheck:
    def test_all_ok(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text("{}")
        deps = [StepDependency(path=f, required=True)]
        # 不需要 env keys
        errors, warnings = preflight_check(deps, step_name="test", _exit=False)
        assert errors == []
        assert warnings == []

    def test_missing_env_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FAKE_MISSING_KEY_12345", raising=False)
        with pytest.raises(PreflightError) as exc_info:
            preflight_check(
                deps=[],
                env_keys=["FAKE_MISSING_KEY_12345"],
                step_name="test",
                _exit=False,
            )
        assert "FAKE_MISSING_KEY_12345" in exc_info.value.errors[0]

    def test_existing_env_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_KEY_PIPELINE", "value123")
        errors, warnings = preflight_check(
            deps=[],
            env_keys=["TEST_KEY_PIPELINE"],
            step_name="test",
            _exit=False,
        )
        assert errors == []

    def test_missing_required_dep_raises(self, tmp_path: Path) -> None:
        deps = [
            StepDependency(
                path=tmp_path / "nope.json",
                required=True,
                hint="run step X",
            )
        ]
        with pytest.raises(PreflightError):
            preflight_check(deps, step_name="test", _exit=False)

    def test_check_only_does_not_exit(self, tmp_path: Path) -> None:
        """check_only=True 時有 error 也不 raise"""
        deps = [StepDependency(path=tmp_path / "missing.json", required=True)]
        errors, warnings = preflight_check(
            deps, step_name="test", check_only=True, _exit=False
        )
        assert len(errors) == 1

    def test_warning_does_not_block(self, tmp_path: Path) -> None:
        """optional dep 缺失只產生 warning，不阻斷"""
        deps = [StepDependency(path=tmp_path / "opt.json", required=False)]
        errors, warnings = preflight_check(deps, step_name="test", _exit=False)
        assert errors == []
        assert len(warnings) == 1
