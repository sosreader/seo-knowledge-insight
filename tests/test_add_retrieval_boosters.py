from __future__ import annotations

from scripts.add_retrieval_boosters import BOOSTER_TAG, add_retrieval_boosters


def test_add_retrieval_boosters_adds_targeted_qas() -> None:
    payload = {
        'qa_database': [
            {
                'id': 1,
                'question': '既有問題',
                'answer': '既有答案',
                'stable_id': 'existing-1',
            }
        ]
    }

    updated, summary = add_retrieval_boosters(payload)

    assert summary['boosters_added'] == 18
    assert updated['total_count'] == 19
    questions = {qa['question'] for qa in updated['qa_database']}
    assert '當重要頁面的內部連結過少或分配不均時，應如何用 Site Audit 找出並優先補強連結架構？' in questions
    assert '在 Vocus 這類創作者平台上做 SEO 經營時，應如何規劃自訂網域、文章 URL 與方案頁索引策略，才能把平台流量轉成自己的搜尋資產？' in questions
    assert '當 Google News 或新聞型內容流量下降，但 AMP 技術面不一定報錯時，內容團隊應如何調整時效選題、更新頻率與新聞頁供給策略？' in questions
    assert '當圖片搜尋流量下降時，應如何用 Search Console 拆解曝光、點擊與 CTR，判斷問題出在圖片技術設定還是搜尋需求改變？' in questions
    assert '當週文章數減少、整體曝光池跟著縮小時，是否也會拖累 Discover 類型流量？應如何維持新鮮內容供給？' in questions
    assert '當週文章數減少、內容供給下滑、SEO 流量與曝光池縮小時，這是否也代表 Discover 會一起走弱？' in questions
    assert '當平台的 /user 或作者頁流量大幅下降時，應如何重新定義作者頁在平台 IA 中的 SEO 角色，並強化作者資產累積？' in questions
    assert '當 Search Console 顯示 FAQ 搜尋外觀異常時，應如何用曝光、點擊與 rich result 狀態判斷影響範圍，並安排修復優先序？' in questions
    assert '當結構化資料覆蓋率下降時，應優先補哪些 Schema 類型，並用哪些工具持續檢查 rich result 與 AMP 問題？' in questions
    assert '當 GA4 出現大量 unassigned 或 direct 流量、看不清來源歸因時，應如何補強追蹤、事件與 channel group 設定？' in questions
    assert '當圖片搜尋或 Discover 圖片曝光下降時，應優先檢查哪些圖片設定，才能提高圖片 CTR 與 metadata 呈現？' in questions
    assert '當週文章數明顯下滑、整體曝光跟著走弱時，應如何判讀內容供給對曝光池的影響，並恢復穩定產出？' in questions
    assert '當 Google News 或新聞型內容流量下降時，應先檢查哪些時效、AMP 與結構化資料訊號？' in questions
    assert '若要提升多語言影片在 Google 搜尋中的曝光，應如何結合 VideoObject、Key Moments 與語言版本策略？' in questions
    assert '要評估品牌關鍵字與非品牌流量是否同步成長，應優先看哪些指標與結構化資料訊號？' in questions
    assert '建立 Search Console KPI 指標體系時，應優先追蹤哪些流量、曝光與點擊訊號，才能判斷 SEO 改善是否有效？' in questions
    assert '實作影片 SEO 時，應如何導入 VideoObject 結構化資料並檢查影片索引，讓影片頁更容易被 Google 收錄？' in questions
    assert '若想用 Event 結構化資料提升活動頁搜尋流量，應如何擴大 schema 標記並用 Rich Results / Search Console 持續驗證？' in questions


def test_add_retrieval_boosters_is_idempotent() -> None:
    payload = {'qa_database': []}
    first, _ = add_retrieval_boosters(payload)
    second, _ = add_retrieval_boosters(first)

    assert second['total_count'] == first['total_count']
    booster_entries = [qa for qa in second['qa_database'] if qa.get('manual_curation_tag') == BOOSTER_TAG]
    assert len(booster_entries) == 18