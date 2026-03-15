#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT_DIR / "raw_data" / "ahrefs_markdown"
OUTPUT_DIR = ROOT_DIR / "output" / "qa_per_meeting"
DEFAULT_SLICE_START = 0
DEFAULT_SLICE_END = 92
DEFAULT_EXPECTED_FIRST = "301-redirects.md"
DEFAULT_EXPECTED_LAST = "enterprise-content-marketing.md"
MODEL_NAME = "sonnet"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MODEL_NAME = MODEL_NAME
MAX_PROMPT_MARKDOWN_CHARS = 12000
DEFAULT_MAX_QA_PAIRS = 4
FAST_RETRY_MAX_QA_PAIRS = 2
FAST_RETRY_ANSWER_MAX_LENGTH = 240
FAST_RETRY_SUMMARY_MAX_LENGTH = 120
KEYWORD_MARKERS: tuple[tuple[str, str], ...] = (
    ("ai overview", "AI Overviews"),
    ("chatgpt", "ChatGPT"),
    ("perplexity", "Perplexity"),
    ("google ai overviews", "Google AI Overviews"),
    ("canonical", "canonical"),
    ("duplicate", "duplicate content"),
    ("ctr", "CTR"),
    ("traffic", "traffic"),
    ("visibility", "visibility"),
    ("brand", "brand visibility"),
    ("citation", "AI citations"),
    ("rank", "ranking"),
    ("search console", "Search Console"),
    ("eeat", "E-E-A-T"),
)


@dataclass(frozen=True)
class ArticleMeta:
    source_file: str
    source_title: str
    source_date: str
    source_type: str
    source_collection: str
    source_url: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="用 Claude CLI 本地萃取 Ahrefs 文章 Q&A")
    parser.add_argument("--start", type=int, default=DEFAULT_SLICE_START)
    parser.add_argument("--end", type=int, default=DEFAULT_SLICE_END)
    parser.add_argument("--expected-first", default=DEFAULT_EXPECTED_FIRST)
    parser.add_argument("--expected-last", default=DEFAULT_EXPECTED_LAST)
    parser.add_argument("--skip-boundary-check", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--max-markdown-chars", type=int, default=MAX_PROMPT_MARKDOWN_CHARS)
    parser.add_argument("--fast-retry", action="store_true")
    parser.add_argument("--heuristic-fallback-on-timeout", action="store_true")
    args = parser.parse_args()
    if args.timeout_seconds < 10:
        parser.error("--timeout-seconds 必須 >= 10")
    if args.start < 0 or args.end <= args.start:
        parser.error("--start / --end 範圍無效")
    if args.max_markdown_chars < 1500:
        parser.error("--max-markdown-chars 必須 >= 1500")
    return args


def _sorted_slice(
    slice_start: int,
    slice_end: int,
    expected_first: str,
    expected_last: str,
    skip_boundary_check: bool,
) -> list[Path]:
    files = sorted(SOURCE_DIR.glob("*.md"), key=lambda item: item.name)
    if not files:
        raise RuntimeError(f"找不到任何 .md 檔案：{SOURCE_DIR}")
    selected = files[slice_start:slice_end]
    if len(selected) != slice_end - slice_start:
        raise RuntimeError(
            f"切片數量錯誤：預期 {slice_end - slice_start}，實際 {len(selected)} "
            f"(總共 {len(files)} 個檔案，請確認 --start/--end 參數)"
        )
    if not skip_boundary_check:
        if selected[0].name != expected_first:
            raise RuntimeError(f"第 1 個檔案錯誤：預期 {expected_first}，實際 {selected[0].name}")
        if selected[-1].name != expected_last:
            raise RuntimeError(f"最後 1 個檔案錯誤：預期 {expected_last}，實際 {selected[-1].name}")
    return selected


def _parse_meta(markdown_text: str, file_name: str) -> ArticleMeta:
    lines = markdown_text.splitlines()
    title = file_name.removesuffix(".md")
    source_date = ""
    source_type = "article"
    source_collection = "ahrefs-blog"
    source_url = ""

    for line in lines[:12]:
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("- **發佈日期**:"):
            source_date = line.split(":", 1)[1].strip()
        elif line.startswith("- **來源 URL**:"):
            source_url = line.split(":", 1)[1].strip()
        elif line.startswith("- **來源類型**:"):
            source_type = line.split(":", 1)[1].strip()
        elif line.startswith("- **來源集合**:"):
            source_collection = line.split(":", 1)[1].strip()

    if not source_date or not source_url:
        raise RuntimeError(f"無法解析 metadata：{file_name}")

    return ArticleMeta(
        source_file=file_name,
        source_title=title,
        source_date=source_date,
        source_type=source_type,
        source_collection=source_collection,
        source_url=source_url,
    )


def _compact_markdown(markdown_text: str, max_chars: int = MAX_PROMPT_MARKDOWN_CHARS) -> str:
    if len(markdown_text) <= max_chars:
        return markdown_text

    lines = markdown_text.splitlines()
    heading_lines = [line.strip() for line in lines if line.startswith("#") or line.startswith("##") or line.startswith("###")]
    headings_block = "\n".join(heading_lines[:40])
    excerpt = markdown_text[:max_chars].rstrip()
    if headings_block:
        return (
            f"{excerpt}\n\n"
            "[以下內容因篇幅過長已節錄；請優先根據上述全文與以下章節標題整理核心 SEO 洞察]\n"
            f"{headings_block}\n"
        )
    return excerpt


def _extract_intro_paragraphs(markdown_text: str, *, limit: int = 3) -> list[str]:
    content = markdown_text.split("---\n", 1)[1] if "---\n" in markdown_text else markdown_text
    paragraphs: list[str] = []
    for raw in content.split("\n\n"):
        block = raw.strip()
        if not block or block.startswith("#") or block.startswith("##"):
            continue
        if block == "Contents":
            break
        if block.startswith("!") or block.startswith("```"):
            continue
        paragraphs.append(re.sub(r"\s+", " ", block))
        if len(paragraphs) >= limit:
            break
    return paragraphs


def _extract_key_takeaways(markdown_text: str, *, limit: int = 4) -> list[str]:
    lines = markdown_text.splitlines()
    bullets: list[str] = []
    in_takeaways = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower() == "## key takeaways":
            in_takeaways = True
            continue
        if in_takeaways and stripped.startswith("##"):
            break
        if in_takeaways and stripped.startswith("*"):
            bullets.append(re.sub(r"\s+", " ", stripped.lstrip("* ")))
            if len(bullets) >= limit:
                break
    return bullets


def _derive_keywords(meta: ArticleMeta, markdown_text: str) -> list[str]:
    source = f"{meta.source_title}\n{markdown_text[:2500]}".lower()
    keywords: list[str] = []
    for marker, keyword in KEYWORD_MARKERS:
        if marker in source and keyword not in keywords:
            keywords.append(keyword)
    title_tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", meta.source_title)
    for token in title_tokens:
        if token.lower() in {"here", "what", "from", "your", "they", "with", "that"}:
            continue
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= 6:
            break
    return keywords[:6] or ["SEO research", "Ahrefs"]


def _derive_maturity_level(question: str, answer: str, keywords: list[str]) -> str:
    try:
        from utils.maturity_classifier import classify_maturity_level

        level = classify_maturity_level(keywords, question, answer)
        return level or "L2"
    except Exception:
        return "L2"


def _build_heuristic_result(meta: ArticleMeta, markdown_text: str) -> dict[str, Any]:
    takeaways = _extract_key_takeaways(markdown_text)
    intros = _extract_intro_paragraphs(markdown_text)
    keywords = _derive_keywords(meta, markdown_text)
    lead_topic = keywords[0] if keywords else "SEO 可見度"
    question = f"Ahrefs 文章「{meta.source_title}」揭示了哪些與 {lead_topic} 相關的重點，對 SEO 有何意涵？"

    evidence_points = takeaways[:3] if takeaways else intros[:2]
    evidence_text = " ".join(f"{index + 1}) {point}" for index, point in enumerate(evidence_points))
    if not evidence_text:
        evidence_text = "文章前段指出這個主題會改變網站在搜尋與 AI 回答中的可見度判斷方式。"

    lower_source = f"{meta.source_title} {markdown_text[:3000]}".lower()
    if "ai" in lower_source or "chatgpt" in lower_source or "perplexity" in lower_source:
        why_text = "這代表 AI 搜尋與傳統排名採用的來源選擇邏輯不完全相同，品牌與內容團隊需要額外監測 AI 引用偏差。"
    elif "canonical" in lower_source or "duplicate" in lower_source:
        why_text = "這代表 canonical 與重複內容處理會直接影響索引整併、crawl budget 與排名訊號集中。"
    else:
        why_text = "這代表該主題不只是單一技巧問題，而會連動影響搜尋可見度、點擊與內容配置策略。"

    answer = (
        f"[What] 文章前段重點指出：{evidence_text} "
        f"[Why] {why_text} "
        "[How] 建議先把文中提到的頁型、來源偏差、排名位置或索引訊號列入固定監測，並用 Search Console、SERP 觀察或站內稽核工具驗證是否出現相同趨勢。"
    )
    maturity_relevance = _derive_maturity_level(question, answer, keywords)
    summary_source = takeaways[0] if takeaways else (intros[0] if intros else meta.source_title)
    meeting_summary = f"這篇文章聚焦 {lead_topic}，前段摘要指出 {summary_source}"

    return {
        "qa_pairs": [
            {
                "question": question,
                "answer": answer,
                "keywords": keywords,
                "confidence": 0.55,
                "source_file": meta.source_file,
                "source_title": meta.source_title,
                "source_date": meta.source_date,
                "source_type": meta.source_type,
                "source_collection": meta.source_collection,
                "source_url": meta.source_url,
                "extraction_model": "claude-code-heuristic",
                "maturity_relevance": maturity_relevance,
            }
        ],
        "meeting_summary": meeting_summary[:FAST_RETRY_SUMMARY_MAX_LENGTH],
    }


def _is_valid_existing_output(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(_read_text(path))
    except json.JSONDecodeError:
        return False
    qa_pairs = data.get("qa_pairs")
    meeting_summary = data.get("meeting_summary", "")
    return isinstance(qa_pairs, list) and "處理失敗" not in str(meeting_summary)


def _json_schema(meta: ArticleMeta, *, fast_retry: bool) -> dict[str, Any]:
    max_pairs = FAST_RETRY_MAX_QA_PAIRS if fast_retry else DEFAULT_MAX_QA_PAIRS
    answer_schema: dict[str, Any] = {"type": "string", "minLength": 1}
    summary_schema: dict[str, Any] = {"type": "string", "minLength": 1}
    if fast_retry:
        answer_schema["maxLength"] = FAST_RETRY_ANSWER_MAX_LENGTH
        summary_schema["maxLength"] = FAST_RETRY_SUMMARY_MAX_LENGTH

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "qa_pairs": {
                "type": "array",
                "maxItems": max_pairs,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "question": {"type": "string", "minLength": 1},
                        "answer": answer_schema,
                        "keywords": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 7,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "confidence": {"type": "number", "minimum": 0.3, "maximum": 1.0},
                        "source_file": {"type": "string", "const": meta.source_file},
                        "source_title": {"type": "string", "const": meta.source_title},
                        "source_date": {"type": "string", "const": meta.source_date},
                        "source_type": {"type": "string", "const": meta.source_type},
                        "source_collection": {"type": "string", "const": meta.source_collection},
                        "source_url": {"type": "string", "const": meta.source_url},
                        "extraction_model": {"type": "string", "const": "claude-code"},
                        "maturity_relevance": {"type": "string", "enum": ["L1", "L2", "L3", "L4"]},
                    },
                    "required": [
                        "question",
                        "answer",
                        "keywords",
                        "confidence",
                        "source_file",
                        "source_title",
                        "source_date",
                        "source_type",
                        "source_collection",
                        "source_url",
                        "extraction_model",
                        "maturity_relevance",
                    ],
                },
            },
            "meeting_summary": summary_schema,
        },
        "required": ["qa_pairs", "meeting_summary"],
    }


def _build_prompt(meta: ArticleMeta, markdown_text: str, *, fast_retry: bool) -> str:
    qa_limit_text = "最多 2 組 Q&A" if fast_retry else "0 到 4 組高價值 Q&A"
    answer_limit_text = "每個 answer 請控制在 80 到 220 字內，summary 控制在 120 字內。" if fast_retry else ""
    return f"""你是 SEO Q&A 萃取員。請只根據提供的 markdown 內容，輸出繁體中文的 SEO 問答資料，不可補充外部知識。

任務要求：
- 這是一篇 Ahrefs 文章，不是會議紀錄。
- 萃取 {qa_limit_text}；若文章缺乏可操作 SEO 洞察，可回傳空陣列。
- 問題必須自包含，答案要包含具體發現、原因、建議、行動或可驗證依據。
- {answer_limit_text}
- 優先保留技術 SEO、AI Search、網站治理、品牌可見度、數據研究、實驗結論等內容。
- meeting_summary 請用 1 到 3 句總結文章對 SEO 的主要價值。
- 嚴格使用以下固定來源欄位：
    source_file={meta.source_file}
    source_title={meta.source_title}
    source_date={meta.source_date}
    source_type={meta.source_type}
    source_collection={meta.source_collection}
    source_url={meta.source_url}
    extraction_model=claude-code

文章 markdown：

```markdown
{markdown_text}
```
"""


def _call_claude(prompt: str, schema: dict[str, Any], timeout_seconds: int, model_name: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                "--model",
                model_name,
                "--permission-mode",
                "dontAsk",
                "--tools",
                "",
                "--output-format",
                "json",
                "--json-schema",
                json.dumps(schema, ensure_ascii=False),
            ],
            input=prompt,
            text=True,
            capture_output=True,
            cwd=str(ROOT_DIR),
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"claude 執行逾時（>{timeout_seconds}s）: {exc.cmd[0]}") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(stderr or "claude CLI 執行失敗")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"claude 輸出不是合法 JSON：{exc}") from exc

    structured = payload.get("structured_output")
    if not isinstance(structured, dict):
        raise RuntimeError("claude 未回傳 structured_output")
    return structured


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _process_file(
    md_path: Path,
    timeout_seconds: int,
    model_name: str,
    max_markdown_chars: int,
    fast_retry: bool,
    heuristic_fallback_on_timeout: bool,
) -> tuple[str, str | None]:
    output_path = OUTPUT_DIR / f"{md_path.stem}_qa.json"
    if _is_valid_existing_output(output_path):
        return "skipped", None

    markdown_text = _read_text(md_path)
    meta = _parse_meta(markdown_text, md_path.name)
    prompt = _build_prompt(meta, _compact_markdown(markdown_text, max_markdown_chars), fast_retry=fast_retry)
    schema = _json_schema(meta, fast_retry=fast_retry)

    try:
        data = _call_claude(prompt, schema, timeout_seconds, model_name)
        _write_json(output_path, data)
        return "processed", md_path.name
    except KeyboardInterrupt:
        raise
    except Exception as exc:  # noqa: BLE001
        if heuristic_fallback_on_timeout and "逾時" in str(exc):
            heuristic_data = _build_heuristic_result(meta, markdown_text)
            _write_json(output_path, heuristic_data)
            return "processed", md_path.name
        failure_data = {
            "qa_pairs": [],
            "meeting_summary": f"處理失敗: {exc}",
        }
        _write_json(output_path, failure_data)
        return "failed", md_path.name


def main() -> int:
    args = _parse_args()
    selected_files = _sorted_slice(
        slice_start=args.start,
        slice_end=args.end,
        expected_first=args.expected_first,
        expected_last=args.expected_last,
        skip_boundary_check=args.skip_boundary_check,
    )

    processed = 0
    skipped = 0
    failed = 0
    first_processed: str | None = None
    last_processed: str | None = None

    for index, md_path in enumerate(selected_files, start=1):
        status, processed_name = _process_file(
            md_path,
            args.timeout_seconds,
            args.model,
            args.max_markdown_chars,
            args.fast_retry,
            args.heuristic_fallback_on_timeout,
        )
        if status == "processed":
            processed += 1
            if first_processed is None:
                first_processed = processed_name
            last_processed = processed_name
        elif status == "skipped":
            skipped += 1
        else:
            failed += 1
            if first_processed is None:
                first_processed = processed_name
            last_processed = processed_name

        print(f"[{index:02d}/{len(selected_files)}] {md_path.name} -> {status}", flush=True)

    summary = {
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
        "first_processed": first_processed,
        "last_processed": last_processed,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())