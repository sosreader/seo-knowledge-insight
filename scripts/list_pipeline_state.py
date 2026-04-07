#!/usr/bin/env python3
"""
Pipeline 狀態查詢工具 — 供 AI 工具（Claude Code / GitHub Copilot）呼叫

用途：
  不需要 OpenAI API，讓 AI 工具了解 pipeline 目前的狀態，
  並找出需要 AI 工具自行處理的檔案。

用法：
    python scripts/list_pipeline_state.py --step extract-qa       # 列出待萃取的 Markdown 檔案
    python scripts/list_pipeline_state.py --step dedupe-classify  # 確認 qa_all_raw.json 狀態
    python scripts/list_pipeline_state.py --merge                 # 合併 per-meeting JSON → qa_all_raw.json
    python scripts/list_pipeline_state.py --status                # 顯示完整 pipeline 狀態
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config


def _find_source_markdown(source_file: str) -> Path | None:
    """根據 per-meeting QA 的 source_file 找到對應的 Markdown 原文。"""
    # source_file 可能是完整相對路徑或純檔名
    full_path = config.ROOT_DIR / source_file
    if full_path.exists():
        return full_path

    basename = Path(source_file).name
    for d in [
        config.RAW_MD_DIR,
        config.RAW_MEDIUM_MD_DIR,
        config.RAW_ITHELP_MD_DIR,
        config.RAW_GOOGLE_CASES_MD_DIR,
        config.RAW_AHREFS_MD_DIR,
        config.RAW_SEJ_MD_DIR,
        config.RAW_GROWTHMEMO_MD_DIR,
        config.RAW_GOOGLE_BLOG_MD_DIR,
        config.RAW_GOOGLE_BLOG_ZHTW_MD_DIR,
        config.RAW_WEBDEV_MD_DIR,
        config.RAW_SCREAMINGFROG_MD_DIR,
    ]:
        candidate = d / basename
        if candidate.exists():
            return candidate
    return None


def _read_source_metadata(md_path: Path) -> dict:
    """從 Markdown 原文讀取 source_title、source_url、source_type、source_collection。"""
    content = md_path.read_text(encoding="utf-8")
    dir_name = md_path.parent.name
    source_type, source_collection = config.DIR_COLLECTION_MAP.get(
        dir_name, ("article", dir_name)
    )

    title = md_path.stem
    title_match = re.match(r'^# (.+)', content)
    if title_match:
        title = title_match.group(1).strip()

    source_url = ""
    url_match = re.search(r'\*\*來源 URL\*\*:\s*(.+)', content)
    if url_match:
        source_url = url_match.group(1).strip()

    # Notion meetings: notion_url from metadata
    notion_url = ""
    notion_match = re.search(r'\*\*Notion URL\*\*:\s*(.+)', content)
    if notion_match:
        notion_url = notion_match.group(1).strip()

    return {
        "source_title": title,
        "source_url": source_url or notion_url,
        "source_type": source_type,
        "source_collection": source_collection,
    }


def _enrich_qa_metadata(qa: dict) -> dict:
    """為缺少 metadata 的 QA 從原始 Markdown 補充欄位（回傳新 dict）。"""
    source_file = qa.get("source_file", "")
    if not source_file:
        return qa

    # 只補充缺失的欄位
    needs_enrichment = (
        not qa.get("source_url")
        or not qa.get("source_type")
        or not qa.get("source_title")
    )
    if not needs_enrichment:
        return qa

    md_path = _find_source_markdown(source_file)
    if not md_path:
        return qa

    meta = _read_source_metadata(md_path)
    return {
        **qa,
        "source_title": qa.get("source_title") or meta["source_title"],
        "source_url": qa.get("source_url") or meta["source_url"],
        "source_type": qa.get("source_type") or meta["source_type"],
        "source_collection": qa.get("source_collection") or meta["source_collection"],
    }


def _classify_extract_qa() -> tuple[list[Path], list[Path]]:
    """
    回傳 (already_done, unprocessed) 兩份清單（精確定義：_qa.json 存在且非空非失敗才算完成）。
    掃描所有來源目錄（DIR_COLLECTION_MAP + Notion）。
    不輸出任何內容，供 show_full_status 與 list_unprocessed_extract_qa 共用。
    """
    source_dirs = [
        config.RAW_MD_DIR,
        config.RAW_MEDIUM_MD_DIR,
        config.RAW_ITHELP_MD_DIR,
        config.RAW_GOOGLE_CASES_MD_DIR,
        config.RAW_AHREFS_MD_DIR,
        config.RAW_SEJ_MD_DIR,
        config.RAW_GROWTHMEMO_MD_DIR,
        config.RAW_GOOGLE_BLOG_MD_DIR,
        config.RAW_GOOGLE_BLOG_ZHTW_MD_DIR,
        config.RAW_WEBDEV_MD_DIR,
        config.RAW_SCREAMINGFROG_MD_DIR,
    ]
    md_files: list[Path] = []
    for d in source_dirs:
        if d.exists():
            md_files.extend(sorted(d.glob("*.md")))

    if not md_files:
        return [], []

    already_done: list[Path] = []
    unprocessed: list[Path] = []
    for md_path in md_files:
        done = False
        qa_candidates = [
            config.QA_PER_MEETING_DIR / f"{md_path.stem}_qa.json",
            config.QA_PER_ARTICLE_DIR / f"{md_path.stem}_qa.json",
        ]
        for qa_path in qa_candidates:
            if not qa_path.exists():
                continue
            try:
                data = json.loads(qa_path.read_text(encoding="utf-8"))
                # qa_pairs 是 list 即算完成（空列表 = 非 SEO 文章，也算處理完畢）
                # 只有明確標記「處理失敗」才視為未完成
                if isinstance(data.get("qa_pairs"), list) and "處理失敗" not in data.get("meeting_summary", ""):
                    done = True
                    break
            except (json.JSONDecodeError, KeyError):
                continue
        (already_done if done else unprocessed).append(md_path)
    return already_done, unprocessed


def list_unprocessed_extract_qa() -> list[Path]:
    """
    回傳尚未萃取 Q&A 的 Markdown 檔案清單（涵蓋所有來源）。
    （沒有對應的 _qa.json，或 _qa.json 為空的檔案）
    """
    already_done, unprocessed = _classify_extract_qa()
    if not already_done and not unprocessed:
        print("所有來源目錄下沒有 .md 檔案，請先執行 fetch 步驟")
        return []

    print("extract-qa 狀態（所有來源）")
    print(f"  已完成: {len(already_done)} 份")
    print(f"  待處理: {len(unprocessed)} 份")
    print()

    if not unprocessed:
        print("全部完成！所有 Markdown 檔案都已萃取 Q&A。")
        print("   可執行：python scripts/list_pipeline_state.py --merge")
        return []

    print("待處理檔案（請 AI 工具依序萃取 Q&A）：")
    for i, path in enumerate(unprocessed, 1):
        print(f"  [{i:3d}] {path}")

    return unprocessed


def check_dedupe_classify_state() -> bool:
    """
    確認 dedupe-classify（去重+分類）的前置條件。
    回傳 True 表示可以執行。
    """
    raw_path = config.OUTPUT_DIR / "qa_all_raw.json"
    final_path = config.OUTPUT_DIR / "qa_final.json"

    print("dedupe-classify 狀態")

    if not raw_path.exists():
        print(f"  [MISS] {raw_path} 不存在")
        print("     請先執行 extract-qa（/extract-qa 或 make extract-qa）")
        return False

    try:
        data = json.loads(raw_path.read_text(encoding="utf-8"))
        qa_count = data.get("total_qa_count", 0)
        meetings = data.get("meetings_processed", 0)
        print(f"  [OK]   qa_all_raw.json：{qa_count} 個 Q&A（{meetings} 份會議）")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  [ERR]  qa_all_raw.json 格式錯誤: {e}")
        return False

    if final_path.exists():
        try:
            final = json.loads(final_path.read_text(encoding="utf-8"))
            final_count = final.get("total_count", 0)
            print(f"  [INFO] 已有 qa_final.json：{final_count} 個 Q&A（可重新執行覆蓋）")
        except (json.JSONDecodeError, KeyError):
            pass

    print()
    print(f"  可執行去重+分類（{qa_count} 個 Q&A）")
    print("  -> 請 AI 工具執行 /dedupe-classify")
    return True


def merge_per_meeting_jsons() -> None:
    """
    合併所有 output/qa_per_meeting/*_qa.json → output/qa_all_raw.json
    （不需要 OpenAI，純 Python I/O）
    """
    qa_dirs = [config.QA_PER_MEETING_DIR, config.QA_PER_ARTICLE_DIR]
    if not any(qa_dir.exists() for qa_dir in qa_dirs):
        print(f"[MISS] {config.QA_PER_MEETING_DIR} 與 {config.QA_PER_ARTICLE_DIR} 都不存在")
        sys.exit(1)

    all_qa: list[dict] = []
    summary: list[dict] = []
    error_count = 0

    for qa_dir in qa_dirs:
        if not qa_dir.exists():
            continue
        for f in sorted(qa_dir.glob("*_qa.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                pairs = data.get("qa_pairs", [])
                if not pairs and "處理失敗" in data.get("meeting_summary", ""):
                    error_count += 1
                    continue
                # 從 per-meeting JSON 檔名推導 source_file
                inferred_source = data.get("source_file") or (f.stem.replace("_qa", "") + ".md")
                for qa in pairs:
                    enriched = {**qa} if qa.get("source_file") else {**qa, "source_file": inferred_source}
                    all_qa.append(_enrich_qa_metadata(enriched))
                summary.append({
                    "file": f.stem.replace("_qa", "") + ".md",
                    "qa_count": len(pairs),
                    "summary": data.get("meeting_summary", ""),
                })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  [SKIP] {f.name}：{e}")
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
    print(f"  合併了 {len(summary)} 份會議")
    print(f"  共 {len(all_qa)} 個 Q&A")
    if error_count:
        print(f"  跳過 {error_count} 份（處理失敗或格式錯誤）")
    print(f"  輸出：{output_path}")


def show_full_status() -> None:
    """顯示完整 pipeline 狀態"""
    print("=" * 60)
    print("SEO Q&A Pipeline 狀態")
    print("=" * 60)

    # fetch-notion：Markdown 檔案
    md_count = len(list(config.RAW_MD_DIR.glob("*.md"))) if config.RAW_MD_DIR.exists() else 0
    print(f"\nfetch-notion (Notion 擷取)")
    print(f"  Markdown 檔案: {md_count} 份 ({config.RAW_MD_DIR})")

    # extract-qa：Q&A 萃取（用精確定義：qa_pairs 非空且非失敗才算完成）
    already_done, unprocessed_files = _classify_extract_qa()
    print(f"\nextract-qa (Q&A 萃取)")
    print(f"  已萃取: {len(already_done)} 份")
    print(f"  待處理: {len(unprocessed_files)} 份")

    # dedupe-classify：去重+分類
    raw_path = config.OUTPUT_DIR / "qa_all_raw.json"
    final_path = config.OUTPUT_DIR / "qa_final.json"
    emb_path = config.OUTPUT_DIR / "qa_embeddings.npy"

    print(f"\ndedupe-classify (去重+分類)")
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

    emb_status = "[OK]" if emb_path.exists() else "[MISS] 不存在（generate-report 需要）"
    print(f"  qa_embeddings.npy: {emb_status}")

    print("\n" + "=" * 60)
    print("快速執行指令：")
    print("  make dry-run           # 驗證設定")
    print("  make fetch-notion      # Notion 擷取（需要 NOTION_TOKEN）")
    print("  /extract-qa            # Q&A 萃取（Claude Code，不需要 OpenAI）")
    print("  /dedupe-classify       # 去重+分類（Claude Code，不需要 OpenAI）")
    print("  /pipeline-local        # 完整流程（Claude Code）")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline 狀態查詢工具（供 AI 工具使用，不需要 OpenAI API）"
    )
    _STEP_MAP = {"2": "extract-qa", "3": "dedupe-classify"}

    def _parse_step_state(value: str) -> str:
        if value in _STEP_MAP:
            return _STEP_MAP[value]
        if value in ("extract-qa", "dedupe-classify"):
            return value
        raise argparse.ArgumentTypeError(
            f"有效值：extract-qa, dedupe-classify（也接受數字 2 或 3），收到：{value!r}"
        )

    parser.add_argument(
        "--step",
        type=_parse_step_state,
        metavar="{extract-qa,dedupe-classify}",
        help="查詢指定步驟狀態（extract-qa 或 dedupe-classify，也接受數字 2 或 3）",
    )
    parser.add_argument("--merge", action="store_true", help="合併 per-meeting JSON → qa_all_raw.json")
    parser.add_argument("--status", action="store_true", help="顯示完整 pipeline 狀態")
    args = parser.parse_args()

    if args.merge:
        merge_per_meeting_jsons()
    elif args.step == "extract-qa":
        list_unprocessed_extract_qa()
    elif args.step == "dedupe-classify":
        check_dedupe_classify_state()
    elif args.status:
        show_full_status()
    else:
        show_full_status()


if __name__ == "__main__":
    main()
