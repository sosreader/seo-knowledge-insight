#!/usr/bin/env python3
"""
步驟 2：用 OpenAI 從每份會議 Markdown 中萃取 Q&A pairs

功能：
- 讀取 raw_data/markdown/ 下所有 .md 檔
- 逐一呼叫 OpenAI API 萃取 Q&A
- 每份會議的 Q&A 存到 output/qa_per_meeting/
- 合併成一份完整的 Q&A 列表

用法：
    python scripts/02_extract_qa.py
    python scripts/02_extract_qa.py --limit 5          # 先試 5 份
    python scripts/02_extract_qa.py --file xxx.md      # 只處理指定檔案
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils.openai_helper import extract_qa_from_text


def _extract_date_from_title(title: str) -> str:
    """嘗試從標題中擷取日期"""
    # 常見格式: 2024-01-15, 2024/01/15, 20240115
    patterns = [
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(\d{4}\d{2}\d{2})',
    ]
    for pattern in patterns:
        m = re.search(pattern, title)
        if m:
            return m.group(1)
    return ""


def process_single_meeting(md_path: Path) -> dict:
    """處理單份會議紀錄"""
    content = md_path.read_text(encoding="utf-8")
    filename = md_path.stem

    # 從 Markdown 內容中擷取標題和日期
    title = filename
    title_match = re.match(r'^# (.+)', content)
    if title_match:
        title = title_match.group(1)

    date = _extract_date_from_title(title) or _extract_date_from_title(filename)

    print(f"  📄 {title}")
    print(f"     字數: {len(content)}")

    # 如果內容太長，分段處理
    max_chars = config.MAX_TOKENS_PER_CHUNK * 3  # 大約 3 chars per token
    if len(content) > max_chars:
        print(f"     ⚠️  內容較長，分段處理 ...")
        chunks = _split_content(content, max_chars)
        all_qa_pairs = []
        for chunk_i, chunk in enumerate(chunks, 1):
            print(f"     段落 {chunk_i}/{len(chunks)} ...")
            result = extract_qa_from_text(chunk, title, date)
            all_qa_pairs.extend(result.get("qa_pairs", []))
            time.sleep(0.5)  # 避免 rate limit

        meeting_result = {
            "qa_pairs": all_qa_pairs,
            "meeting_summary": f"（分 {len(chunks)} 段處理）",
        }
    else:
        meeting_result = extract_qa_from_text(content, title, date)

    # 為每個 Q&A 加上來源資訊
    for qa in meeting_result.get("qa_pairs", []):
        qa["source_file"] = md_path.name
        qa["source_title"] = title
        qa["source_date"] = date

    qa_count = len(meeting_result.get("qa_pairs", []))
    print(f"     ✅ 萃取 {qa_count} 個 Q&A")

    return meeting_result


def _split_content(content: str, max_chars: int) -> list[str]:
    """
    把長內容依標題分段。
    優先以 ## 標題切分，如果沒有就等距切分。
    """
    # 以 ## 或 ### 標題為切分點
    sections = re.split(r'(?=\n##\s)', content)

    if len(sections) <= 1:
        # 沒有標題結構，等距切分
        chunks = []
        for i in range(0, len(content), max_chars):
            chunks.append(content[i:i + max_chars])
        return chunks

    # 合併太小的段落
    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) > max_chars and current:
            chunks.append(current)
            current = section
        else:
            current += section
    if current:
        chunks.append(current)

    return chunks


def main(args: argparse.Namespace) -> None:
    if not config.OPENAI_API_KEY:
        print("❌ 請設定 OPENAI_API_KEY（在 .env）")
        sys.exit(1)

    print("=" * 60)
    print("🤖 步驟 2：用 OpenAI 萃取 Q&A")
    print(f"   模型: {config.OPENAI_MODEL}")
    print("=" * 60)

    # 收集要處理的檔案
    if args.file:
        md_files = [config.RAW_MD_DIR / args.file]
        if not md_files[0].exists():
            print(f"❌ 找不到: {md_files[0]}")
            sys.exit(1)
    else:
        md_files = sorted(config.RAW_MD_DIR.glob("*.md"))

    if not md_files:
        print("❌ raw_data/markdown/ 下沒有 .md 檔案，請先執行步驟 1")
        sys.exit(1)

    if args.limit:
        md_files = md_files[: args.limit]

    print(f"\n📚 共 {len(md_files)} 份待處理\n")

    # 逐一處理
    all_qa_pairs = []
    results_per_meeting = []

    for i, md_path in enumerate(md_files, 1):
        print(f"\n[{i}/{len(md_files)}]")

        try:
            result = process_single_meeting(md_path)
        except Exception as e:
            print(f"     ❌ 錯誤: {e}")
            result = {"qa_pairs": [], "meeting_summary": f"處理失敗: {e}"}

        # 存單份結果
        out_path = config.QA_PER_MEETING_DIR / f"{md_path.stem}_qa.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        all_qa_pairs.extend(result.get("qa_pairs", []))
        results_per_meeting.append({
            "file": md_path.name,
            "qa_count": len(result.get("qa_pairs", [])),
            "summary": result.get("meeting_summary", ""),
        })

        # 簡單的 rate limit 保護
        time.sleep(1)

    # 合併輸出
    merged_output = {
        "total_qa_count": len(all_qa_pairs),
        "meetings_processed": len(md_files),
        "qa_pairs": all_qa_pairs,
        "processing_summary": results_per_meeting,
    }

    merged_path = config.OUTPUT_DIR / "qa_all_raw.json"
    merged_path.write_text(
        json.dumps(merged_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print(f"✅ 步驟 2 完成！")
    print(f"   共萃取 {len(all_qa_pairs)} 個 Q&A pairs")
    print(f"   單份結果: {config.QA_PER_MEETING_DIR}")
    print(f"   合併結果: {merged_path}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="用 OpenAI 萃取 Q&A")
    parser.add_argument("--limit", type=int, default=0, help="只處理前 N 份")
    parser.add_argument("--file", default="", help="只處理指定檔案名稱")
    args = parser.parse_args()
    main(args)
