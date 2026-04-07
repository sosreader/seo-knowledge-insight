# Search Console 推出新的特殊公告報告透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/05/special-announcements-search-console?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 5 月 5 日，星期二

上個月，我們推出了一種能讓 Google 搜尋針對網站[醒目顯示 COVID-19 公告](https://developers.google.com/search/blog/2020/04/highlight-covid-19-announcements-search?hl=zh-tw)的新方式。我們會先利用這些資訊在 Google 搜尋中醒目顯示來自醫療衛生網站和政府機關網站的公告，讓民眾能夠看到重要的最新資訊，例如學校停課通知或居家避疫指令。

今天我們宣布 [Google Search Console](https://search.google.com/search-console?hl=zh-tw) 將針對 [`SpecialAnnouncement`](https://developers.google.com/search/docs/appearance/structured-data/special-announcements?hl=zh-tw) 提供支援，包括加入許多新的報告來協助您找出實作方面的問題，以及監控這類型複合式搜尋結果的成效。此外，我們現在也支援在[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)中使用標記，您可以利用這項功能檢查現有的網址，或針對標記程式碼進行偵錯，等確認沒有問題後再發布內容。

## 特殊公告強化報告

Search Console 已針對實作 `SpecialAnnouncement` 結構化資料的網站提供一份全新報告。您可以從這份報告中掌握網站在實作標記方面的錯誤、警告和有效網頁。

此外，您也可以在修正問題後使用這份報告進行驗證，讓 Google 重新檢索原本有問題的網頁。如要進一步瞭解複合式搜尋結果狀態報告，請參閱[這篇文章](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)。

![特殊公告強化報告](https://developers.google.com/static/search/blog/images/import/e262fb4bddc2f6da5b9c6a270fe20a49.png?hl=zh-tw)

## 成效報表中的特殊公告資料

現在您也能使用 Search Console 的成效報表，查看已加入 `SpecialAnnouncement` 標記的網頁在 Google 搜尋中的成效。也就是說，您可以查看特殊公告網頁的曝光次數、點擊次數和點閱率資料，透過這些成效資料掌握在任何維度方面的趨勢。如要進一步瞭解成效報表中的搜尋外觀分頁，請[按這裡](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#by_search_appearance)。

![成效報表中的特殊公告資料](https://developers.google.com/static/search/blog/images/import/9738e5cbb9c924e60839d6e9e6edc162.png?hl=zh-tw)

## 複合式搜尋結果測試中的特殊公告資料

為網頁加入 `SpecialAnnouncement` 結構化資料後，您可以透過[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來檢驗成果。如果您尚未在網站上發布標記，也可以上傳一小段程式碼來檢查標記。測試結果會顯示結構化資料是否有任何錯誤並提供相關建議。

![複合式搜尋結果測試中的特殊公告資料](https://developers.google.com/static/search/blog/images/import/10e186db47a98ba39ae97e50b6e1f262.png?hl=zh-tw)

有了這些新工具，您應該就能更輕鬆地針對包含 `SpecialAnnouncement` 標記的網頁掌握搜尋成效，辨識並修正相關問題。

如有任何問題，請造訪 [Google 網站管理員社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)。

搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com) 和 Search Console 產品經理 [Moshe Samet](https://www.linkedin.com/in/moshe-samet-5465326/)
