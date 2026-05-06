# 結構化資料測試工具的最新資訊
- **發佈日期**: 2020-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/12/structured-data-testing-tool-update?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 12 月 15 日，星期二

[透過複合式搜尋結果測試和結構定義標記驗證工具測試您的結構化資料](https://developers.google.com/search/docs/advanced/structured-data?hl=zh-tw)。

我們曾在 7 月時宣布[複合式搜尋結果測試已通過 Beta 版測試](https://developers.google.com/search/blog/2020/07/rich-results-test-out-of-beta?hl=zh-tw)，並在同一篇網誌文章中提到即將淘汰[結構化資料測試工具](https://developers.google.com/search/docs/advanced/structured-data?hl=zh-tw)。在那之後，我們聽到了來自眾多使用者的意見，因此特地與您分享結構化資料測試工具的未來走向。

為了更妥善支援開放標準和開發體驗，我們正在重新調整結構化資料測試工具的用途，並會在 2021 年 4 月前將這項工具遷移至新的網域，為 schema.org 社群提供服務。屆時，這項工具主要會用來確認標記語法正確且符合 schema.org 的標準，不再檢查 Google 搜尋複合式搜尋結果類型。如果您要測試 Google 搜尋複合式搜尋結果類型的標記，可以繼續使用[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)。

舉例來說，如果您嘗試根據[我們的說明文件](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw)來實作 <https://schema.org/Event> 標記，以在 Google 搜尋上提供複合式活動體驗，那麼[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)和 [Search Console](https://search.google.com/search-console/about?hl=zh-tw) 就是確保您的標記符合 Google 搜尋要求的最佳工具。不過，如果您只想確保系統使用有效的 schema.org 資源，或者驗證我們目前未明確支援的類型 (例如 <https://schema.org/ExercisePlan>)，可以使用重新調整後的 schema.org 驗證工具。

如有任何問題或意見，歡迎造訪 [Google 搜尋中心產品討論社群](https://support.google.com/webmasters/community?hl=zh-tw)，或透過 [Twitter](https://twitter.com/googlesearchc) 告訴我們。

發布者：Google 搜尋工程團隊成員 [Ryan Levering](https://twitter.com/rrlevering)

---

## 更新

* **2021 年 5 月 11 日更新**：原名為「結構化資料測試工具」(SDTT) 的 Schema.org 結構化資料驗證工具現已[推出全新首頁](https://blog.schema.org/2021/05/announcing-schema-markup-validator.html)。全新的[結構定義標記驗證工具](https://validator.schema.org/)目前仍在開發階段，一旦能穩定運作，Google 便計劃將結構化資料測試工具重新導向至複合式搜尋結果測試。
* **2021 年 8 月 9 日更新**：[結構定義標記驗證工具](https://validator.schema.org/)已能穩定運作，Google 現在會將結構化資料測試工具重新導向至[到達網頁](https://developers.google.com/search/docs/advanced/structured-data?hl=zh-tw)，協助您選取合適的工具。
