#!/usr/bin/env python3
"""針對指定的 markdown 檔案重新萃取 Q&A（使用新 prompt）"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

import json
import time
from pathlib import Path

import config
from utils.openai_helper import extract_qa_from_text
from scripts.extract_qa_helpers import _extract_date_from_title as extract_date_from_title

TARGET_FILES = [
    "SEO_會議_2024_01_03.md",      # 2024 早
    "SEO_會議_2024_06_13.md",      # 2024 中
    "SEO_會議_2024_09_09.md",      # 2024 下半
    "SEO_會議_2024_12_09.md",      # 2024 末
    "SEO_會議_20260112.md",         # 2026 初
    "SEO_會議_20260209.md",         # 2026 2月
    "SEO_會議_20260223.md",         # 2026 最新
]

for fname in TARGET_FILES:
    md_path = config.RAW_MD_DIR / fname
    if not md_path.exists():
        print(f"❌ 找不到 {fname}")
        continue

    title = md_path.stem
    text = md_path.read_text(encoding="utf-8")
    date = extract_date_from_title(title) or ""

    print(f"\n📄 {fname}（{len(text)} 字）...")
    result = extract_qa_from_text(text, meeting_title=title, meeting_date=date)

    qa_pairs = result.get("qa_pairs", [])
    print(f"   ✅ 萃取 {len(qa_pairs)} 筆 Q&A")

    # 覆寫 qa_per_meeting 的對應檔案
    out_path = config.OUTPUT_DIR / "qa_per_meeting" / f"{title}_qa.json"
    out_path.write_text(
        json.dumps({"source_file": fname, "qa_pairs": qa_pairs}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    time.sleep(1)

print("\n✅ 完成")
