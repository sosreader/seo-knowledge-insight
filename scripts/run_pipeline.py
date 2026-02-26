#!/usr/bin/env python3
"""
主控流程：一鍵執行完整 pipeline

    python scripts/run_pipeline.py              # 完整流程
    python scripts/run_pipeline.py --step 1     # 只執行步驟 1
    python scripts/run_pipeline.py --step 2     # 只執行步驟 2
    python scripts/run_pipeline.py --step 3     # 只執行步驟 3
    python scripts/run_pipeline.py --dry-run    # 檢查設定但不執行
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def check_config() -> list[str]:
    """驗證設定，回傳問題列表"""
    issues = []
    if not config.NOTION_TOKEN:
        issues.append("❌ NOTION_TOKEN 未設定")
    if not config.NOTION_PARENT_PAGE_ID:
        issues.append("❌ NOTION_PARENT_PAGE_ID 未設定")
    if not config.OPENAI_API_KEY:
        issues.append("❌ OPENAI_API_KEY 未設定（步驟 2、3 需要）")
    return issues


def run_step(script_name: str, extra_args: list[str] | None = None) -> bool:
    """執行子腳本"""
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
        type=int,
        choices=[1, 2, 3],
        default=0,
        help="只執行指定步驟（0=全部）",
    )
    parser.add_argument(
        "--filter",
        default=None,
        help="步驟 1 的標題篩選關鍵字",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="步驟 2 只處理前 N 份（測試用）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只檢查設定，不實際執行",
    )
    parser.add_argument(
        "--skip-dedup",
        action="store_true",
        help="步驟 3 跳過去重",
    )
    parser.add_argument(
        "--skip-classify",
        action="store_true",
        help="步驟 3 跳過分類",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 SEO Q&A 資料庫建構 Pipeline")
    print("=" * 60)

    # 檢查設定
    print("\n🔍 檢查設定 ...")
    issues = check_config()

    # 根據要執行的步驟，放寬檢查
    if args.step == 1:
        issues = [i for i in issues if "NOTION" in i]
    elif args.step in (2, 3):
        issues = [i for i in issues if "OPENAI" in i]

    if issues:
        for issue in issues:
            print(f"   {issue}")
        print("\n💡 請複製 .env.example 為 .env 並填入正確的值")
        sys.exit(1)
    else:
        print("   ✅ 設定檢查通過")

    if args.dry_run:
        print("\n🏁 Dry run 完成，設定正確！")
        return

    start = time.time()
    steps_to_run = [args.step] if args.step else [1, 2, 3]

    for step in steps_to_run:
        if step == 1:
            extra = []
            if args.filter:
                extra += ["--filter", args.filter]
            ok = run_step("01_fetch_notion.py", extra)
        elif step == 2:
            extra = []
            if args.limit:
                extra += ["--limit", str(args.limit)]
            ok = run_step("02_extract_qa.py", extra)
        elif step == 3:
            extra = []
            if args.skip_dedup:
                extra.append("--skip-dedup")
            if args.skip_classify:
                extra.append("--skip-classify")
            ok = run_step("03_dedupe_classify.py", extra)
        else:
            continue

        if not ok:
            print(f"\n❌ 步驟 {step} 執行失敗，中止 pipeline")
            sys.exit(1)

    elapsed = time.time() - start
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print("\n" + "=" * 60)
    print(f"🎉 Pipeline 完成！耗時 {minutes}m {seconds}s")
    print(f"   📁 Raw data:  {config.RAW_MD_DIR}")
    print(f"   📁 Q&A 資料庫: {config.OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
