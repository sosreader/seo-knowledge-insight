from __future__ import annotations

from scripts.clean_qa_quality import clean_qa_payload, detect_quality_issues


def test_detect_quality_issues_flags_generic_question_and_answer() -> None:
    qa = {
        'question': '關於「Internal links」，文章提出哪些值得執行的 SEO 重點？',
        'answer': '[What] 文中指出，You should avoid passive parameters。 [Why] 原因在於，tracking 會污染資料。 [How] 實作上可優先採取這些做法：可先依文中提到的設定、資料比對方式或監測條件執行，並在站內逐步驗證影響。 [Evidence] 文中的佐證包括：Most analytics systems have event tracking。',
    }

    reasons = detect_quality_issues(qa)

    assert 'generic-question-template' in reasons
    assert 'generic-answer-template' in reasons


def test_detect_quality_issues_flags_placeholder_heavy_answer() -> None:
    qa = {
        'question': '如何修正 hreflang reciprocal tag 問題？',
        'answer': '[What] 文中指出，hreflang tags work in pairs。 [Why] 原因在於，This is especially important 當 you have multiple versions of a page。 [How] 請搭配 reciprocal tag 一起檢查，並確認這也沒有被其他規則覆蓋。 [Evidence] 文中的佐證包括：作者提醒要搭配回查驗證。',
    }

    reasons = detect_quality_issues(qa)

    assert 'mixed-language-placeholder-heavy' in reasons


def test_clean_qa_payload_keeps_only_high_quality_entries() -> None:
    payload = {
        'version': '1.0',
        'original_count': 2,
        'qa_database': [
            {
                'id': 1,
                'question': '關於「Final thoughts」，文章提出哪些值得執行的 SEO 重點？',
                'answer': '[What] 文中指出，結論是持續更新。 [Why] 原因在於，因為很重要。 [How] 實作上可優先採取這些做法：可先依文中提到的設定、資料比對方式或監測條件執行，並在站內逐步驗證影響。 [Evidence] 文中的佐證包括：作者這樣說。',
                'category': '其他',
                'evergreen': True,
                'difficulty': '基礎',
            },
            {
                'id': 2,
                'question': '當 AI Overview 擠壓自然點擊時，應如何同時監控傳統排名與 AI 引用表現？',
                'answer': '[What] 應把自然排名、AI Overview 出現率與被引用 URL 一起追蹤。 [Why] 單看排名會低估 AI 摘要對點擊與品牌曝光的影響。 [How] 針對核心查詢建立固定監測清單，定期記錄 SERP 排名、是否出現 AI Overview、被引用頁面與點擊變化。 [Evidence] 研究指出 AI Overview 引用與傳統排名高度重疊，但仍有一部分引用來自前十名之外的頁面。',
                'category': '搜尋表現分析',
                'evergreen': True,
                'difficulty': '進階',
            },
        ],
    }

    cleaned, removed = clean_qa_payload(payload)

    assert cleaned['total_count'] == 1
    assert cleaned['quality_filtered_count'] == 1
    assert cleaned['qa_database'][0]['question'] == '當 AI Overview 擠壓自然點擊時，應如何同時監控傳統排名與 AI 引用表現？'
    assert removed[0]['reasons']