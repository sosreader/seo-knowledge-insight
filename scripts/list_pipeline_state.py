#!/usr/bin/env python3
"""
Pipeline 狀態查詢工具 — 供 AI 工具（Claude Code / GitHub Copilot）呼叫

用途：
  不需要 OpenAI API，讓 AI 工具了解 pipeline 目前的狀態，
  並找出需要 AI 工具自行處理的檔案。

用法：
    python scripts/list_pipeline_state.py --step 2    # 列出待萃取的 Markdown 檔案
    python scripts/list_pipeline_state.py --step 3    # 確認 qa_all_raw.json 狀態
    python scripts/list_pipeline_state.py --merge     # 合併 per-meeting JSON → qa_all_raw.json
    python scripts/list_pipeline_state.py --status    # 顯示完整 pipeline 狀態
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config


def list_unprocessed_step2() -> list[Path]:
    """
    回傳尚未萃取 Q&A 的 Markdown 檔案清單。
    （沒有對應的 _qa.json，或 _qa.json 為空的檔案）
    """
    if not config.RAW_MD_DIR.exists():
        print("❌ raw_data/markdown/ 目錄不存在，請先執行 Step 1（make step1）")
        return []

    md_files = sorted(config.RAW_MD_DIR.glob("*.md"))
    if not md_files:
        print("❌ raw_data/markdown/ 目錄下沒有 .md 檔案，請先執行 Step 1（make step1）")
        return []

    unprocessed: list[Path] = []
    already_done: list[Path] = []

    for md_path in md_files:
        qa_path = config.QA_PER_MEETING_DIR / f"{md_path.stem}_qa.json"
        if qa_path.exists():
            try:
                data = json.loads(qa_path.read_text(encoding="utf-8"))
                if data.get("qa_pairs") and "處理失敗" not in data.get("meeting_summary", ""):
                    already_done.append(md_path)
                    continue
            except (json.JSONDecodeError, KeyError):
                pass
        unprocessed.append(md_path)

    print(f"Step 2 狀態")
    print(f"  已完成: {len(already_done)} 份")
    print(f"  待處理: {len(unprocessed)} 份")
    print()

    if not unprocessed:
        print("✅ 全部完成！所有 Markdown 檔案都已萃取 Q&A。")
        print("   可執行：python scripts/list_pipeline_state.py --merge")
        return []

    print("待處理檔案（請 AI 工具依序萃取 Q&A）：")
    for i, path in enumerate(unprocessed, 1):
        print(f"  [{i:3d}] {path}")

    return unprocessed


def check_step3_state() -> bool:
    """
    確認 Step 3（去重+分類）的前置條件。
    回傳 True 表示可以執行。
    """
    raw_path = config.OUTPUT_DIR / "qa_all_raw.json"
    final_path = config.OUTPUT_DIR / "qa_final.json"

    print("Step 3 狀態")

    if not raw_path.exists():
        print(f"  ❌ {raw_path} 不存在")
        print("     請先執行 Step 2（/extract-qa 或 make step2）")
        return False

    try:
        data = json.loads(raw_path.read_text(encoding="utf-8"))
        qa_count = data.get("total_qa_count", 0)
        meetings = data.get("meetings_processed", 0)
        print(f"  ✅ qa_all_raw.json：{qa_count} 個 Q&A（{meetings} 份會議）")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ❌ qa_all_raw.json 格式錯誤: {e}")
        return False

    if final_path.exists():
        try:
            final = json.loads(final_path.read_text(encoding="utf-8"))
            final_count = final.get("total_count", 0)
            print(f"  ℹ️  已有 qa_final.json：{final_count} 個 Q&A（可重新執行覆蓋）")
        except (json.JSONDecodeError, KeyError):
            pass

    print()
    print(f"  可執行去重+分類（{qa_count} 個 Q&A）")
    print("  ➜ 請 AI 工具執行 /dedupe-classify")
    return True


def merge_per_meeting_jsons() -> None:
    """
    合併所有 output/qa_per_meeting/*_qa.json → output/qa_all_raw.json
    （不需要 OpenAI，純 Python I/O）
    """
    qa_dir = config.QA_PER_MEETING_DIR
    if not qa_dir.exists():
        print(f"❌ {qa_dir} 不存在")
        sys.exit(1)

    all_qa: list[dict] = []
    summary: list[dict] = []
    error_count = 0

    for f in sorted(qa_dir.glob("*_qa.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            pairs = data.get("qa_pairs", [])
            if not pairs and "處理失敗" in data.get("meeting_summary", ""):
                error_count += 1
                continue
            all_qa.extend(pairs)
            summary.append({
                "file": f.stem.replace("_qa", "") + ".md",
                "qa_count": len(pairs),
                "summary": data.get("meeting_summary", ""),
            })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  ⚠️  跳過 {f.name}：{e}")
            error_count += 1
            continue

    merged = {
        "total_qa_count": len(all_qa),
        "meetings_processed": len(summary),
        "qa_pairs": all_qa,
        "processing_summary": summary,
    }

    output_path = config.OUTPUT_DIR / "qa_all_raw.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print("合併完成")
    print(f"  ✅ 合併了 {len(summary)} 份會議")
    print(f"  📊 共 {len(all_qa)} 個 Q&A")
    if error_count:
        print(f"  ⚠️  跳過 {error_count} 份（處理失敗或格式錯誤）")
    print(f"  📄 輸出：{output_path}")


def show_full_status() -> None:
    """顯示完整 pipeline 狀態"""
    print("=" * 60)
    print("SEO Q&A Pipeline 狀態")
    print("=" * 60)

    # Step 1：Markdown 檔案
    md_count = len(list(config.RAW_MD_DIR.glob("*.md"))) if config.RAW_MD_DIR.exists() else 0
    print(f"\nStep 1 (Notion 擷取)")
    print(f"  Markdown 檔案: {md_count} 份 ({config.RAW_MD_DIR})")

    # Step 2：Q&A 萃取
    qa_per_meeting = len(list(config.QA_PER_MEETING_DIR.glob("*_qa.json"))) if config.QA_PER_MEETING_DIR.exists() else 0
    unprocessed = max(0, md_count - qa_per_meeting)
    print(f"\nStep 2 (Q&A 萃取)")
    print(f"  已萃取: {qa_per_meeting} 份")
    print(f"  待處理: {unprocessed} 份")

    # Step 3：去重+分類
    raw_path = config.OUTPUT_DIR / "qa_all_raw.json"
    final_path = config.OUTPUT_DIR / "qa_final.json"
    emb_path = config.OUTPUT_DIR / "qa_embeddings.npy"

    print(f"\nStep 3 (去重+分類)")
    if raw_path.exists():
        try:
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            print(f"  qa_all_raw.json: {raw.get('total_qa_count', 0)} 個 Q&A")
        except Exception:
            print(f"  qa_all_raw.json: 格式錯誤")
    else:
        print(f"  qa_all_raw.json: 不存在")

    if final_path.exists():
        try:
            final = json.loads(final_path.read_text(encoding="utf-8"))
            print(f"  qa_final.json: {final.get('total_count', 0)} 個 Q&A")
        except Exception:
            print(f"  qa_final.json: 格式錯誤")
    else:
        print(f"  qa_final.json: 不存在")

    emb_status = "✅" if emb_path.exists() else "❌ 不存在（Step 4 需要）"
    print(f"  qa_embeddings.npy: {emb_status}")

    print("\n" + "=" * 60)
    print("快速執行指令：")
    print("  make dry-run           # 驗證設定")
    print("  make step1             # Notion 擷取（需要 NOTION_TOKEN）")
    print("  /extract-qa            # Q&A 萃取（Claude Code，不需要 OpenAI）")
    print("  /dedupe-classify       # 去重+分類（Claude Code，不需要 OpenAI）")
    print("  /pipeline-local        # 完整流程（Claude Code）")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline 狀態查詢工具（供 AI 工具使用，不需要 OpenAI API）"
    )
    parser.add_argument("--step", type=int, choices=[2, 3], help="查詢指定步驟狀態")
    parser.add_argument("--merge", action="store_true", help="合併 per-meeting JSON → qa_all_raw.json")
    parser.add_argument("--status", action="store_true", help="顯示完整 pipeline 狀態")
    args = parser.parse_args()

    if args.merge:
        merge_per_meeting_jsons()
    elif args.step == 2:
        list_unprocessed_step2()
    elif args.step == 3:
        check_step3_state()
    elif args.status:
        show_full_status()
    else:
        show_full_status()


if __name__ == "__main__":
    main()
