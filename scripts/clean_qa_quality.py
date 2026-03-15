#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import config
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config


GENERIC_QUESTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'^關於「.+?」，文章提出哪些\s*(?:值得執行的 SEO 重點|SEO 判斷與行動建議)？?$'),
    re.compile(r'^.+這篇研究／案例揭露了哪些關鍵 SEO 發現？?$'),
    re.compile(r'^關於「段落重點\s*\d+」，文章提出哪些\s*(?:值得執行的 SEO 重點|SEO 判斷與行動建議)？?$'),
    re.compile(r'^應如何處理「.+?」，才能兼顧 SEO 與執行效率？$'),
)

GENERIC_ANSWER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'可先依文中提到的設定、資料比對方式或監測條件執行'),
    re.compile(r'\[How\]\s*實作上可優先採取這些做法：\s*$'),
)

PLACEHOLDER_TOKENS: tuple[str, ...] = (
    '搭配',
    '有助於',
    '這也',
    '當 ',
    '當你',
)

LOW_SIGNAL_TOPICS: tuple[str, ...] = (
    'Final thoughts',
    'Conclusion',
    'Content',
    'Features',
    'Docs',
    'Web Search',
    'AI Mode',
    'AI Overviews',
    'ChatGPT ⚠️',
    'Google Gemini ⚠️',
    'Methodology and findings',
    'The data',
)

CRITICAL_REASONS: frozenset[str] = frozenset(
    {
        'generic-question-template',
        'generic-answer-template',
        'mixed-language-placeholder-heavy',
        'multi-block-fragmented-answer',
    }
)


@dataclass(frozen=True)
class QualityDecision:
    keep: bool
    reasons: tuple[str, ...]


def _question_topic(question: str) -> str | None:
    match = re.match(r'^關於「(.+?)」', question)
    if not match:
        return None
    return match.group(1).strip()


def _placeholder_count(answer: str) -> int:
    return sum(answer.count(token) for token in PLACEHOLDER_TOKENS)


def detect_quality_issues(qa: dict[str, Any]) -> tuple[str, ...]:
    question = str(qa.get('question', '')).strip()
    answer = str(qa.get('answer', '')).strip()
    reasons: list[str] = []

    if not question or not answer:
        reasons.append('empty-field')

    if any(pattern.search(question) for pattern in GENERIC_QUESTION_PATTERNS):
        reasons.append('generic-question-template')

    topic = _question_topic(question)
    if topic and topic in LOW_SIGNAL_TOPICS:
        reasons.append('low-signal-section-heading')

    if any(pattern.search(answer) for pattern in GENERIC_ANSWER_PATTERNS):
        reasons.append('generic-answer-template')

    placeholder_count = _placeholder_count(answer)
    if placeholder_count >= 2:
        reasons.append('mixed-language-placeholder-heavy')

    if answer.count('[Evidence]') > 1 or answer.count('[How]') > 1:
        reasons.append('multi-block-fragmented-answer')

    if len(answer) < 80:
        reasons.append('answer-too-short')

    return tuple(dict.fromkeys(reasons))


def decide_quality(qa: dict[str, Any]) -> QualityDecision:
    reasons = detect_quality_issues(qa)
    keep = not (set(reasons) & CRITICAL_REASONS)
    return QualityDecision(keep=keep, reasons=reasons)


def _group_by_category(qa_pairs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for qa in qa_pairs:
        category = str(qa.get('category', '其他'))
        grouped.setdefault(category, []).append(qa)
    return grouped


def export_markdown(data: dict[str, Any], md_path: Path) -> None:
    qa_pairs = list(data.get('qa_database', []))
    lines = [
        '# SEO 問答資料庫',
        '',
        f"共 {data.get('total_count', len(qa_pairs))} 筆問答",
        '',
        f"- 原始 Q&A：{data.get('original_count', len(qa_pairs))}",
        f"- 品質過濾移除：{data.get('quality_filtered_count', 0)}",
        f"- 最終 Q&A：{data.get('total_count', len(qa_pairs))}",
        '',
        '---',
        '',
    ]

    for category, items in sorted(_group_by_category(qa_pairs).items()):
        lines.append(f'## {category} ({len(items)})')
        lines.append('')
        for index, qa in enumerate(items, start=1):
            difficulty = qa.get('difficulty', '未標記')
            evergreen = '是' if qa.get('evergreen', False) else '否'
            source = qa.get('source_title', qa.get('source_file', ''))
            merged = '是' if qa.get('is_merged') else '否'
            keywords = ', '.join(qa.get('keywords', []))

            lines.append(f"### {index}. Q: {qa.get('question', '')}")
            lines.append('')
            lines.append(
                f'難度：{difficulty} | 常青：{evergreen} | 來源：{source} | 合併：{merged}'
            )
            lines.append('')
            lines.append(str(qa.get('answer', '')))
            lines.append('')
            if keywords:
                lines.append(f'關鍵字：{keywords}')
                lines.append('')
            lines.append('---')
            lines.append('')

    md_path.write_text('\n'.join(lines), encoding='utf-8')


def clean_qa_payload(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    qa_pairs = list(data.get('qa_database', []))
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []

    for qa in qa_pairs:
        decision = decide_quality(qa)
        if decision.keep:
            kept.append(qa)
            continue

        removed.append(
            {
                'question': qa.get('question', ''),
                'source_file': qa.get('source_file', ''),
                'stable_id': qa.get('stable_id', ''),
                'reasons': list(decision.reasons),
            }
        )

    cleaned = {
        **data,
        'total_count': len(kept),
        'quality_filtered_count': len(removed),
        'qa_database': [
            {
                **qa,
                'id': index,
            }
            for index, qa in enumerate(kept, start=1)
        ],
    }
    return cleaned, removed


def main() -> None:
    parser = argparse.ArgumentParser(description='清理 qa_final.json 中的低品質 Q&A')
    parser.add_argument(
        '--input',
        type=Path,
        default=config.OUTPUT_DIR / 'qa_final.json',
        help='輸入 JSON 路徑',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=config.OUTPUT_DIR / 'qa_final.json',
        help='輸出 JSON 路徑',
    )
    parser.add_argument(
        '--markdown',
        type=Path,
        default=config.OUTPUT_DIR / 'qa_final.md',
        help='輸出 Markdown 路徑',
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=config.OUTPUT_DIR / 'qa_quality_filter_report.json',
        help='輸出移除報告路徑',
    )
    parser.add_argument(
        '--backup',
        type=Path,
        default=config.OUTPUT_DIR / 'qa_final.before_quality_filter.json',
        help='備份原始 JSON 路徑',
    )
    parser.add_argument('--check', action='store_true', help='只顯示統計，不寫入檔案')
    args = parser.parse_args()

    raw_data = json.loads(args.input.read_text(encoding='utf-8'))
    cleaned, removed = clean_qa_payload(raw_data)

    print(
        json.dumps(
            {
                'input_total': len(raw_data.get('qa_database', [])),
                'removed_count': len(removed),
                'output_total': cleaned.get('total_count', 0),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    if args.check:
        return

    args.backup.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding='utf-8')
    args.output.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding='utf-8')
    args.report.write_text(
        json.dumps({'removed': removed, 'removed_count': len(removed)}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    export_markdown(cleaned, args.markdown)


if __name__ == '__main__':
    main()