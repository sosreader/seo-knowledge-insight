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


from utils.stable_id import compute_stable_id


def normalize_question(text: str) -> str:
    collapsed = re.sub(r'\s+', ' ', text).strip()
    return re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', collapsed)


def _raw_key(qa: dict[str, Any]) -> tuple[str, str]:
    return str(qa.get('source_file', '')), normalize_question(str(qa.get('question', '')))


def build_raw_index(raw_qas: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {_raw_key(qa): qa for qa in raw_qas}


def _sync_from_raw(current_qa: dict[str, Any], raw_qa: dict[str, Any]) -> dict[str, Any]:
    stable_id = current_qa.get('stable_id') or raw_qa.get('stable_id')
    if not stable_id:
        stable_id = compute_stable_id(
            str(raw_qa.get('source_file', current_qa.get('source_file', ''))),
            str(current_qa.get('question', raw_qa.get('question', ''))),
        )

    return {
        **current_qa,
        'question': current_qa.get('question', raw_qa.get('question', '')),
        'answer': raw_qa.get('answer', current_qa.get('answer', '')),
        'keywords': list(raw_qa.get('keywords', current_qa.get('keywords', []))),
        'confidence': raw_qa.get('confidence', current_qa.get('confidence')),
        'source_file': raw_qa.get('source_file', current_qa.get('source_file', '')),
        'source_title': raw_qa.get('source_title', current_qa.get('source_title', '')),
        'source_date': raw_qa.get('source_date', current_qa.get('source_date', '')),
        'source_url': raw_qa.get('source_url', current_qa.get('source_url', '')),
        'source_type': raw_qa.get('source_type', current_qa.get('source_type', '')),
        'source_collection': raw_qa.get('source_collection', current_qa.get('source_collection', '')),
        'maturity_relevance': raw_qa.get('maturity_relevance', current_qa.get('maturity_relevance')),
        'extraction_model': raw_qa.get('extraction_model', current_qa.get('extraction_model')),
        'extraction_provenance': raw_qa.get('extraction_provenance', current_qa.get('extraction_provenance')),
        'stable_id': stable_id,
        'raw_sync_status': 'matched',
    }


def sync_curated_payload(
    current_data: dict[str, Any],
    raw_data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    current_qas = list(current_data.get('qa_database', []))
    raw_qas = list(raw_data.get('qa_pairs', []))
    raw_index = build_raw_index(raw_qas)

    matched = 0
    preserved_rewritten = 0
    preserved_missing = 0
    synced_qas: list[dict[str, Any]] = []

    for index, current_qa in enumerate(current_qas, start=1):
        raw_qa = raw_index.get(_raw_key(current_qa))
        if raw_qa is not None:
            next_qa = _sync_from_raw(current_qa, raw_qa)
            matched += 1
        else:
            stable_id = current_qa.get('stable_id') or compute_stable_id(
                str(current_qa.get('source_file', '')),
                str(current_qa.get('question', '')),
            )
            status = 'preserved-rewritten' if current_qa.get('quality_rewritten_from_phrase') else 'preserved-missing'
            next_qa = {
                **current_qa,
                'stable_id': stable_id,
                'raw_sync_status': status,
            }
            if status == 'preserved-rewritten':
                preserved_rewritten += 1
            else:
                preserved_missing += 1

        synced_qas.append({**next_qa, 'id': index})

    updated = {
        **current_data,
        'total_count': len(synced_qas),
        'original_count': raw_data.get('total_qa_count', len(raw_qas)),
        'meetings_processed': raw_data.get('meetings_processed', current_data.get('meetings_processed', 0)),
        'qa_database': synced_qas,
    }
    summary = {
        'current_total': len(current_qas),
        'raw_total': len(raw_qas),
        'matched': matched,
        'preserved_rewritten': preserved_rewritten,
        'preserved_missing': preserved_missing,
        'updated_total': len(synced_qas),
    }
    return updated, summary


def main() -> None:
    parser = argparse.ArgumentParser(description='以最新 qa_all_raw.json 同步目前的 curated qa_final.json')
    parser.add_argument('--current', type=Path, default=config.OUTPUT_DIR / 'qa_final.json')
    parser.add_argument('--raw', type=Path, default=config.OUTPUT_DIR / 'qa_all_raw.json')
    parser.add_argument('--backup', type=Path, default=config.OUTPUT_DIR / 'qa_final.before_sync_from_raw.json')
    parser.add_argument('--markdown', type=Path, default=config.OUTPUT_DIR / 'qa_final.md')
    parser.add_argument('--report', type=Path, default=config.OUTPUT_DIR / 'qa_sync_from_raw_report.json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    current_data = json.loads(args.current.read_text(encoding='utf-8'))
    raw_data = json.loads(args.raw.read_text(encoding='utf-8'))
    updated, summary = sync_curated_payload(current_data, raw_data)

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.check:
        return

    args.backup.write_text(json.dumps(current_data, ensure_ascii=False, indent=2), encoding='utf-8')
    args.current.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    export_markdown(updated, args.markdown)


if __name__ == '__main__':
    main()