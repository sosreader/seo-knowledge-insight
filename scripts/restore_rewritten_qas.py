#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    import config
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from scripts.clean_qa_quality import export_markdown


TEMPLATE_QUESTION_PATTERN = re.compile(
    r'^應如何處理「(?P<phrase>.+?)」，才能兼顧 SEO 與執行效率？$'
)

REWRITE_MAP: dict[str, str] = {
    'construct a hreflang tag': '建立 hreflang 標記時，應如何兼顧正確性與維護效率？',
    'How does faceted navigation work': 'faceted navigation 的運作方式是什麼？實作時該注意哪些 SEO 風險？',
    'use human intuition': '判斷內容是否為 AI 生成時，為什麼仍需要人類判讀與直覺？',
    'optimize for LLM visibility': '若想提升品牌在 LLM 中的可見度，應優先從哪些方向著手？',
    'analyze any company’s backlink strategy in 60-seconds': '如何在短時間內快速拆解一家公司的 backlink strategy？',
    'measure FID': '應如何衡量 FID，並用什麼指標作為實務替代？',
    'create an SEO-friendly URL slug': '建立 SEO-friendly URL slug 時，應遵循哪些原則？',
    'How does Ahrefs’ search volume data stack up': 'Ahrefs 的 search volume data 與 GSC、GKP 相比有何差異？',
    'track it': 'SEO KPI 應如何追蹤，才能兼顧決策與執行？',
    'find trending products in your niche': '如何找出你所在 niche 的 trending products？',
    'find trending products on ecommerce platforms like Amazon': '如何從 Amazon 這類電商平台找出 trending products？',
    'check your site for PPC and SEO cannibalization': '如何檢查網站是否出現 PPC 與 SEO cannibalization？',
    'find relevant people-oriented keywords in your niche': '如何找出 niche 中與人物相關的高潛力關鍵字？',
    'see CLS': '應如何查看 CLS，並判斷版面位移是否過高？',
    'see the LCP element': '如何找出頁面的 LCP element，並定位拖慢速度的主因？',
    'measure CLS': 'CLS 應如何衡量，lab data 與 field data 要怎麼一起看？',
    'measure LCP': 'LCP 應如何衡量，並優先排查哪些效能瓶頸？',
    'check if you’re indexed in Google': '如何確認頁面是否已被 Google 收錄，而不被 site: 指令誤導？',
    'add canonical tags to your site': '網站應如何加入 canonical tags，避免重複內容與索引混亂？',
    'find and fix common title tag mistakes': '如何找出並修正常見的 title tag 錯誤？',
    'check if a URL is indexed': '如何檢查單一 URL 是否已被收錄，並判讀結果？',
    'fix “indexed, though blocked by robots.txt” in WordPress': 'WordPress 出現「indexed, though blocked by robots.txt」時該如何修正？',
    'add a title tag to your page': '頁面應如何加入 title tag，才能兼顧搜尋理解與點擊率？',
    'How do you monitor your YouTube mentions': '如何持續監測品牌在 YouTube 上的 mentions？',
}


def compute_stable_id(source_file: str, question: str) -> str:
    content = f'{source_file}::{question[:120]}'
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def rewrite_question(question: str) -> str:
    match = TEMPLATE_QUESTION_PATTERN.match(question)
    if not match:
        return question

    phrase = match.group('phrase')
    return REWRITE_MAP.get(phrase, f'在 SEO 實務中，{phrase} 的正確做法是什麼？')


def extract_template_phrase(question: str) -> str | None:
    match = TEMPLATE_QUESTION_PATTERN.match(question)
    if not match:
        return None
    return match.group('phrase')


def restore_rewritten_qas(
    current_data: dict[str, Any],
    backup_data: dict[str, Any],
    removed_report: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    current_qas = list(current_data.get('qa_database', []))
    backup_qas = list(backup_data.get('qa_database', []))
    backup_by_old_id = {str(qa.get('stable_id', '')): qa for qa in backup_qas}
    existing_ids = {str(qa.get('stable_id', '')) for qa in current_qas}

    restored: list[dict[str, Any]] = []

    for removed in removed_report.get('removed', []):
        reasons = set(removed.get('reasons', []))
        if 'generic-question-template' not in reasons:
            continue

        original_id = str(removed.get('stable_id', ''))
        source_qa = backup_by_old_id.get(original_id)
        if not source_qa:
            continue

        new_question = rewrite_question(str(source_qa.get('question', '')))
        if new_question == source_qa.get('question'):
            continue

        phrase = extract_template_phrase(str(source_qa.get('question', '')))
        new_stable_id = compute_stable_id(str(source_qa.get('source_file', '')), new_question)
        if new_stable_id in existing_ids:
            continue

        restored_qa = {
            **source_qa,
            'question': new_question,
            'stable_id': new_stable_id,
            'quality_rewritten_from_phrase': phrase,
            'quality_rewrite_reason': 'generic-question-template',
        }
        restored.append(restored_qa)
        existing_ids.add(new_stable_id)

    next_id = max((int(qa.get('id', 0)) for qa in current_qas), default=0)
    merged_qas = current_qas + [
        {
            **qa,
            'id': next_id + index,
        }
        for index, qa in enumerate(restored, start=1)
    ]

    updated = {
        **current_data,
        'total_count': len(merged_qas),
        'quality_restored_count': len(restored),
        'qa_database': merged_qas,
    }
    return updated, restored


def main() -> None:
    parser = argparse.ArgumentParser(description='把可挽救的模板題改寫後回補到 qa_final.json')
    parser.add_argument('--current', type=Path, default=config.OUTPUT_DIR / 'qa_final.json')
    parser.add_argument('--backup', type=Path, default=config.OUTPUT_DIR / 'qa_final.before_quality_filter.json')
    parser.add_argument('--report', type=Path, default=config.OUTPUT_DIR / 'qa_quality_filter_report.json')
    parser.add_argument('--markdown', type=Path, default=config.OUTPUT_DIR / 'qa_final.md')
    parser.add_argument('--restore-report', type=Path, default=config.OUTPUT_DIR / 'qa_quality_restore_report.json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    current_data = json.loads(args.current.read_text(encoding='utf-8'))
    backup_data = json.loads(args.backup.read_text(encoding='utf-8'))
    removed_report = json.loads(args.report.read_text(encoding='utf-8'))

    updated, restored = restore_rewritten_qas(current_data, backup_data, removed_report)

    summary = {
        'current_total': len(current_data.get('qa_database', [])),
        'restored_count': len(restored),
        'updated_total': updated.get('total_count', 0),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.check:
        return

    args.current.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    args.restore_report.write_text(
        json.dumps({'restored': restored, 'restored_count': len(restored)}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    export_markdown(updated, args.markdown)


if __name__ == '__main__':
    main()