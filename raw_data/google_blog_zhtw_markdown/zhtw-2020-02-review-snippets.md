# Search Console 推出新的評論摘錄報告透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/02/review-snippets?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020年 2 月 10 日，星期一

[評論摘錄](https://developers.google.com/search/docs/appearance/structured-data/review-snippet?hl=zh-tw)是來自評論網站上的簡短評論摘錄或評分，通常是許多評論者所給出綜合評分的平均值。這是網路上最常見的結構化資料類型之一，至今已有數百萬個網站將這種結構化資料運用在多種類型的內容上，例如[書籍](https://schema.org/Book)、[電影](https://schema.org/Movie)、[活動](https://schema.org/Event)、[產品](https://schema.org/Product)等等。

當 Google 找到有效的評論或評分標記時，就可能顯示包含星級評等和其他摘要資訊的複合式搜尋結果。這類複合式搜尋結果可以直接顯示在搜尋結果或 Google 知識面板中，如下方螢幕截圖所示。

今天我們宣布 [Google Search Console](https://search.google.com/search-console?hl=zh-tw) 將針對評論摘錄提供支援，包括加入許多新的報告來協助您找出實作方面的問題，以及監控這類型複合式搜尋結果對改進網站成效有何幫助。您也可以使用[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來檢查現有的網址，或針對標記程式碼進行偵錯，等確認沒有問題後再發布內容。

![Google 搜尋結果中的評論摘錄](https://developers.google.com/static/search/blog/images/import/b2a668d1a7ead99e4356d5de8cc4d60f.png?hl=zh-tw)

## 評論摘錄強化報告

為了協助網站擁有者充分利用評論，Search Console 已針對實作評論或評分[結構化資料](https://developers.google.com/search/docs/appearance/structured-data/review-snippet?hl=zh-tw#structured-data-type-definitions)的網站推出新的評論摘錄報告。您可以從這份報告中掌握網站在實作標記方面的錯誤、警告和有效網頁。

此外，您也可以在修正問題後使用這份報告進行驗證，讓 Google 重新檢索原本有問題的網頁。這份報告涵蓋目前支援評論摘錄的所有內容類型，如要進一步瞭解複合式搜尋結果狀態報告，請參閱[這篇文章](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)。

![Search Console 中的評論摘錄強化報告](https://developers.google.com/static/search/blog/images/import/f31479e47cebca8a3379d2835a170b74.png?hl=zh-tw)

## 成效報表中的評論摘錄資料

現在，只要在 Search Console 的[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)中使用新的「評論摘錄」搜尋外觀篩選器，即可針對已加入評論或評分標記的網頁，查看在 Google 搜尋和探索專區中的成效。

![Search Console 成效報表中的評論摘錄資料](https://developers.google.com/static/search/blog/images/import/f577e1261db545f9908aedba43127b08.png?hl=zh-tw)

也就是說，您可以查看評論摘錄網頁的曝光次數、點擊次數和點閱率資料，透過這些成效資料掌握在任何維度方面的趨勢。舉例來說，您可以[篩選資料](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#filteringdata)，查看評論摘錄流量來自哪些搜尋查詢、網頁、國家/地區和裝置。

## 複合式搜尋結果測試中的評論摘錄資料

![複合式搜尋結果測試中的評論摘錄資料](https://developers.google.com/static/search/blog/images/import/43f0a9c498836df46d36dbcb7c699b97.png?hl=zh-tw)

為網頁加入評論摘錄結構化資料後，您可以透過[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來檢驗成果。測試時可以選擇提交程式碼片段或網頁網址，測試結果則會顯示結構化資料是否有任何錯誤並提供相關建議。

有了這些新工具，您應該就能更輕鬆地針對包含評論摘錄標記的網頁掌握搜尋成效，辨識並修正評論問題。

如有任何問題，請造訪 [Google 網站管理員社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)。

發文者：Search Console 工程團隊的 Tomer Hodadi 和 Yuval Kurtser
