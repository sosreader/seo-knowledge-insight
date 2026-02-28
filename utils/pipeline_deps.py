"""
utils/pipeline_deps.py — 統一的 pipeline 依賴檢查

每個 pipeline 步驟啟動時呼叫 preflight_check()，自動：
  1. 檢查前置步驟的產出檔案是否存在
  2. 檢查資料新鮮度（超過閾值 → 警告但不阻斷）
  3. 只驗證本步驟需要的 env vars（不強制不相關的 key）

用法：
    from utils.pipeline_deps import preflight_check, StepDependency

    deps = [
        StepDependency(
            path=Path("output/qa_all_raw.json"),
            required=True,
            max_age_days=7,
            hint="請先執行 python scripts/02_extract_qa.py",
        ),
    ]
    preflight_check(deps, env_keys=["OPENAI_API_KEY"])
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StepDependency:
    """宣告一個 upstream artifact 依賴"""

    path: Path  # 檔案或目錄路徑
    required: bool = True  # True=缺失時 hard exit，False=只警告
    max_age_days: int | None = None  # None=不檢查新鮮度
    min_count: int | None = None  # 目錄下最少要有幾個檔案（glob 搭配）
    glob_pattern: str | None = None  # 搭配 min_count 使用
    hint: str = ""  # 缺失時顯示的修復提示


class PreflightError(Exception):
    """依賴檢查失敗時拋出，方便測試攔截"""

    def __init__(self, errors: list[str], warnings: list[str] | None = None):
        self.errors = list(errors)
        self.warnings = list(warnings or [])
        super().__init__(f"Preflight failed: {'; '.join(errors)}")


def preflight_check(
    deps: list[StepDependency],
    env_keys: list[str] | None = None,
    step_name: str = "",
    *,
    check_only: bool = False,
    _exit: bool = True,
) -> tuple[list[str], list[str]]:
    """
    執行 pre-flight 依賴檢查。

    - required=True 且缺失 → hard exit (sys.exit(1))
    - required=False 且缺失 → 印警告，繼續
    - max_age_days 超過 → 印警告，繼續（不阻斷）
    - env_keys 缺少 → hard exit

    Parameters
    ----------
    deps : 依賴清單
    env_keys : 必需的環境變數名稱
    step_name : 步驟名稱（顯示用）
    check_only : True 時只檢查，不做 exit（搭配 --check flag）
    _exit : False 時不呼叫 sys.exit，改為拋出 PreflightError（方便測試）

    Returns
    -------
    (errors, warnings) 兩個字串清單
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. 環境變數檢查
    for key in env_keys or []:
        val = os.getenv(key)
        if not val or not val.strip():
            errors.append(f"環境變數 {key} 未設定")

    # 2. Artifact 檢查
    for dep in deps:
        if dep.glob_pattern is not None and dep.min_count is not None:
            _check_glob_dep(dep, errors, warnings)
        else:
            _check_file_dep(dep, errors, warnings)

    # 3. 輸出結果
    header = f"[{step_name}] " if step_name else ""
    for w in warnings:
        logger.warning("   %s", w)
    if errors:
        for e in errors:
            logger.error("   %s", e)
        logger.error("\n%s依賴檢查失敗，請先處理上述問題", header)
        if not check_only:
            if _exit:
                sys.exit(1)
            else:
                raise PreflightError(errors, warnings)
    else:
        logger.info("   ✅ %s依賴檢查通過", header)

    return errors, warnings


def _check_glob_dep(
    dep: StepDependency,
    errors: list[str],
    warnings: list[str],
) -> None:
    """檢查目錄 glob 模式的依賴"""
    if dep.glob_pattern is None or dep.min_count is None:
        raise ValueError(
            "_check_glob_dep called with dep.glob_pattern or dep.min_count as None"
        )

    matches = list(dep.path.glob(dep.glob_pattern))
    if len(matches) < dep.min_count:
        icon = "❌" if dep.required else "⚠️ "
        msg = (
            f"{icon} {dep.path}/{dep.glob_pattern} "
            f"找到 {len(matches)} 個檔案（需 ≥ {dep.min_count}）"
        )
        if dep.hint:
            msg += f"\n   💡 {dep.hint}"
        if dep.required:
            errors.append(msg)
        else:
            warnings.append(msg)
    elif dep.max_age_days is not None and matches:
        newest = max(matches, key=lambda p: p.stat().st_mtime)
        _check_freshness(newest, dep.max_age_days, warnings)


def _check_file_dep(
    dep: StepDependency,
    errors: list[str],
    warnings: list[str],
) -> None:
    """檢查單檔模式的依賴"""
    if not dep.path.exists():
        icon = "❌" if dep.required else "⚠️ "
        msg = f"{icon} 找不到 {dep.path}"
        if dep.hint:
            msg += f"\n   💡 {dep.hint}"
        if dep.required:
            errors.append(msg)
        else:
            warnings.append(msg)
    elif dep.max_age_days is not None:
        _check_freshness(dep.path, dep.max_age_days, warnings)


def _check_freshness(
    path: Path,
    max_age_days: int,
    warnings: list[str],
) -> None:
    """檢查檔案新鮮度，超過閾值加入 warnings"""
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age = datetime.now(tz=timezone.utc) - mtime
    if age > timedelta(days=max_age_days):
        warnings.append(
            f"⚠️  {path.name} 已 {age.days} 天未更新"
            f"（上次修改：{mtime:%Y-%m-%d}，建議 ≤ {max_age_days} 天）"
        )
