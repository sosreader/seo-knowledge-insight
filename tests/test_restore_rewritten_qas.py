from __future__ import annotations

from scripts.restore_rewritten_qas import restore_rewritten_qas, rewrite_question


def test_rewrite_question_maps_template_to_natural_question() -> None:
    question = '應如何處理「measure FID」，才能兼顧 SEO 與執行效率？'

    rewritten = rewrite_question(question)

    assert rewritten == '應如何衡量 FID，並用什麼指標作為實務替代？'


def test_restore_rewritten_qas_restores_removed_template_entry() -> None:
    current = {
        'qa_database': [
            {
                'id': 1,
                'stable_id': 'existing-1',
                'question': '既有問題',
                'answer': '既有答案',
                'source_file': 'raw_data/ahrefs_markdown/seo-kpis.md',
            }
        ]
    }
    backup = {
        'qa_database': [
            {
                'id': 9,
                'stable_id': 'old-1',
                'question': '應如何處理「track it」，才能兼顧 SEO 與執行效率？',
                'answer': '追蹤 KPI 的答案',
                'source_file': 'raw_data/ahrefs_markdown/seo-kpis.md',
                'source_title': 'SEO KPIs',
            }
        ]
    }
    report = {
        'removed': [
            {
                'stable_id': 'old-1',
                'question': '應如何處理「track it」，才能兼顧 SEO 與執行效率？',
                'reasons': ['generic-question-template'],
            }
        ]
    }

    updated, restored = restore_rewritten_qas(current, backup, report)

    assert updated['total_count'] == 2
    assert len(restored) == 1
    assert restored[0]['question'] == 'SEO KPI 應如何追蹤，才能兼顧決策與執行？'
    assert restored[0]['quality_rewritten_from_phrase'] == 'track it'