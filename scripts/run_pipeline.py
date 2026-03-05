#!/usr/bin/env python3
"""
主控流程：一鍵執行完整 pipeline

    python scripts/run_pipeline.py                              # 完整流程 (fetch-notion→extract-qa→dedupe-classify)
    python scripts/run_pipeline.py --step fetch-notion          # 只執行 Notion 擷取
    python scripts/run_pipeline.py --step extract-qa            # 只執行 Q&A 萃取
    python scripts/run_pipeline.py --step dedupe-classify       # 只執行去重 + 分類
    python scripts/run_pipeline.py --step generate-report --input metrics.tsv  # 產生週報
    python scripts/run_pipeline.py --check      # 只檢查所有步驟的依賴
    python scripts/run_pipeline.py --dry-run    # 同 --check（向下相容）
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

# ── 步驟名稱 → 腳本對照表 ────────────────────────────
STEP_SCRIPTS = {
    "fetch-notion":    "01_fetch_notion.py",
    "extract-qa":      "02_extract_qa.py",
    "dedupe-classify": "03_dedupe_classify.py",
    "generate-report": "04_generate_report.py",
}

# 向下相容：數字 1-4 對應步驟名稱
_STEP_NUMBER_MAP = {
    1: "fetch-notion",
    2: "extract-qa",
    3: "dedupe-classify",
    4: "generate-report",
}


def _parse_step(value: str) -> str:
    """接受步驟名稱或數字（1-4），回傳步驟名稱"""
    if value.isdigit():
        n = int(value)
        if n in _STEP_NUMBER_MAP:
            return _STEP_NUMBER_MAP[n]
        raise argparse.ArgumentTypeError(
            f"步驟數字必須是 1-4，收到：{n}"
        )
    if value in STEP_SCRIPTS:
        return value
    valid = ", ".join(STEP_SCRIPTS.keys())
    raise argparse.ArgumentTypeError(
        f"未知步驟 '{value}'，有效值：{valid}"
    )


def run_step(script_name: str, extra_args: list[str] | None = None) -> bool:
    """執行子腳本，回傳是否成功"""
    script_path = Path(__file__).parent / script_name
    cmd = [sys.executable, str(script_path)] + (extra_args or [])

    print(f"\n{'─' * 60}")
    print(f"▶ 執行: {' '.join(cmd)}")
    print(f"{'─' * 60}\n")

    result = subprocess.run(cmd, cwd=str(config.ROOT_DIR))
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="SEO Q&A Pipeline 主控")
    parser.add_argument(
        "--step",
        type=_parse_step,
        default=None,
        metavar="{fetch-notion,extract-qa,dedupe-classify,generate-report}",
        help="只執行指定步驟（也接受數字 1-4，不指定則執行 fetch-notion→extract-qa→dedupe-classify）",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只執行依賴檢查，不實際跑（各子腳本的 preflight_check）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="同 --check（向下相容）",
    )
    # 其餘 args 透過 parse_known_args 轉發給子腳本
    args, remaining = parser.parse_known_args()

    # --dry-run 向下相容：等同 --check
    check_only = args.check or args.dry_run

    print("=" * 60)
    print("SEO Q&A 資料庫建構 Pipeline")
    print("=" * 60)

    if check_only:
        print("\n依賴檢查模式（不實際執行）")

    start = time.time()
    # generate-report / evaluate-qa 是獨立流程，不列入預設 pipeline
    default_steps = ["fetch-notion", "extract-qa", "dedupe-classify"]
    steps_to_run = [args.step] if args.step else default_steps

    for step in steps_to_run:
        script = STEP_SCRIPTS[step]

        # 只在單步模式時轉發 remaining args（避免 step-specific flags 傳給不相關的步驟）
        extra = list(remaining) if args.step else []
        if check_only:
            extra.append("--check")

        ok = run_step(script, extra)
        if not ok:
            print(f"\n步驟 {step} {'檢查' if check_only else '執行'}失敗，中止 pipeline")
            sys.exit(1)

    elapsed = time.time() - start
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    if check_only:
        print(f"\n依賴檢查完成！（{minutes}m {seconds}s）")
    else:
        print("\n" + "=" * 60)
        print(f"Pipeline 完成！耗時 {minutes}m {seconds}s")
        print(f"   Raw data:  {config.RAW_MD_DIR}")
        print(f"   Q&A 資料庫: {config.OUTPUT_DIR}")
        print("=" * 60)


if __name__ == "__main__":
    main()
