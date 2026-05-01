from __future__ import annotations

from scripts.sync_curated_qa_from_raw import sync_curated_payload


def test_sync_curated_payload_updates_answer_from_raw() -> None:
    current = {
        'qa_database': [
            {
                'id': 1,
                'stable_id': None,
                'question': '何時需要擔心 crawl budget，並應優先檢查哪些訊號？',
                'answer': '舊答案',
                'keywords': ['crawl budget'],
                'source_file': 'raw_data/ahrefs_markdown/crawl-budget.md',
                'category': '技術SEO',
                'difficulty': '進階',
                'evergreen': True,
            }
        ]
    }
    raw = {
        'total_qa_count': 10,
        'meetings_processed': 3,
        'qa_pairs': [
            {
                'question': '何時需要擔心 crawl budget，並應優先檢查哪 些訊號？',
                'answer': '新答案',
                'keywords': ['crawl budget', 'log analysis'],
                'confidence': 0.88,
                'source_file': 'raw_data/ahrefs_markdown/crawl-budget.md',
                'source_title': 'Crawl Budget',
                'source_date': '2026-03-14',
                'source_collection': 'ahrefs-blog',
                'source_type': 'article',
                'maturity_relevance': 'L2',
                'extraction_model': 'claude-code',
                'extraction_provenance': {
                    'source_models': ['claude-code'],
                    'merge_model': None,
                    'merge_strategy': 'none',
                    'provenance_status': 'single-source',
                },
            }
        ],
    }

    updated, summary = sync_curated_payload(current, raw)

    assert summary['matched'] == 1
    assert updated['original_count'] == 10
    assert updated['meetings_processed'] == 3
    synced = updated['qa_database'][0]
    assert synced['answer'] == '新答案'
    assert synced['keywords'] == ['crawl budget', 'log analysis']
    assert synced['raw_sync_status'] == 'matched'
    assert synced['stable_id']
    assert synced['extraction_provenance']['source_models'] == ['claude-code']


def test_sync_curated_payload_preserves_rewritten_entry() -> None:
    current = {
        'qa_database': [
            {
                'id': 1,
                'stable_id': 'existing-1',
                'question': '應如何衡量 FID，並用什麼指標作為實務替代？',
                'answer': '保留答案',
                'source_file': 'raw_data/ahrefs_markdown/core-web-vitals.md',
                'quality_rewritten_from_phrase': 'measure FID',
                'category': '技術SEO',
                'difficulty': '進階',
                'evergreen': True,
            }
        ]
    }
    raw = {'total_qa_count': 1, 'meetings_processed': 1, 'qa_pairs': []}

    updated, summary = sync_curated_payload(current, raw)

    assert summary['preserved_rewritten'] == 1
    synced = updated['qa_database'][0]
    assert synced['answer'] == '保留答案'
    assert synced['raw_sync_status'] == 'preserved-rewritten'
    assert synced['stable_id'] == 'existing-1'