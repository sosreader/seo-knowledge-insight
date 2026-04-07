# 以全新做法讓網站在 Google 搜尋中醒目顯示 COVID-19 公告
- **發佈日期**: 2020-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/04/highlight-covid-19-announcements-search?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 4 月 3 日，星期五

由於 COVID-19 疫情爆發，許多機構和團體都在發布有關 COVID-19 的重要公告，這些公告涉及的事宜與我們的日常生活息息相關。

有鑑於此，我們將推出可以讓 Google 搜尋醒目顯示這類特殊公告的新方式。每個網站都可以透過在網頁中[新增 `SpecialAnnouncement` 結構化資料](https://developers.google.com/search/docs/appearance/structured-data/special-announcements?hl=zh-tw)，或是[在 Search Console 中提交 COVID-19 公告](https://developers.google.com/search/docs/appearance/structured-data/special-announcements?hl=zh-tw#using-search-console)來達成這類效果。

我們會先利用這些資訊在 Google 搜尋中醒目顯示來自醫療衛生網站和政府機關網站的公告，讓民眾能夠看到重要的最新資訊，例如學校停課通知或居家避疫指令。

我們正在積極開發這項功能，希望將更多網站納入適用範圍。儘管我們可能無法立即顯示來自其他類型網站的公告，但是仍然可以從查看相關標記更清楚地掌握該如何擴充這項功能。

**請注意**：除了特殊公告外，網站還可以採用一系列其他方法來醒目顯示各類資訊，例如有關活動取消或營業時間異動的資訊。您可以在本文結尾處進一步瞭解這些方法。

## COVID-19 公告在 Google 搜尋中的顯示方式

在網頁中加入 `SpecialAnnouncement` 結構化資料後，相關內容不但會出現在網頁的常規摘要說明中，也可能出現在 COVID-19 公告複合式搜尋結果中。COVID-19 公告的複合式搜尋結果可以包含一段簡短的摘要文字，使用者展開這段文字就能查看詳細資訊。請注意，顯示格式可能會隨著時間的推移而發生變化，而您可能無法立即在 Google 搜尋中看到相關結果。

![Google 搜尋中的 COVID-19 公告](https://developers.google.com/static/search/blog/images/import/9ed0241f779f44f6ab6085e3edb93ab3.png?hl=zh-tw)

## 如何實作 COVID-19 公告

以下提供 COVID-19 公告的兩種實作方式。

### 建議做法：在網頁中加入結構化資料

結構化資料是一種標準化格式，能夠提供網頁相關資訊並分類網頁內容。我們之所以建議使用這種方式，是因為這能讓我們以最簡單的方式收集相關資訊。不僅 [Search Console](https://search.google.com/search-console/about?hl=zh-tw) 可以在之後據此提供報告，您要更新資訊也很容易。歡迎參閱[這篇文章](https://developers.google.com/search/docs/appearance/structured-data/special-announcements?hl=zh-tw)，瞭解如何在 COVID-19 公告中加入結構化資料。

### 替代做法：在 Search Console 中提交公告

如果您沒有實作結構化資料的技術能力，或者無法取得相關協助，則可以在 [Search Console 中提交 COVID-19 公告](https://developers.google.com/search/docs/appearance/structured-data/special-announcements?hl=zh-tw#using-search-console)。這項工具仍處於 Beta 版測試階段，日後可能會有所變動。

這只適合當成暫時的解決方案，一般不建議使用。使用結構化資料時，醒目顯示的公告會隨著網頁內容改變而自動更新；但若使用這項工具，您便需要手動更新公告。此外，日後 Search Console 推出相關特殊報表時，您也無法利用這些報表監控在 Search Console 提交的公告。

如果您需要採用這種做法，則必須先在 [Search Console 通過驗證](https://support.google.com/webmasters/answer/9008080?hl=zh-tw)，接著才能[提交 COVID-19 公告](https://search.google.com/search-console/special-announcement?hl=zh-tw)：

![在 Search Console 中提交 COVID-19 公告](https://developers.google.com/static/search/blog/images/import/7d6d6467e9e2b00768e80032303df1ae.png?hl=zh-tw)

## Google 搜尋可提供網站的其他 COVID-19 相關資源

除了特殊公告標記外，您也可以採用其他方式來突顯可能受到 COVID-19 影響的其他類型活動：

* **醫療衛生網站和政府網站的最佳做法**：如果您是醫療衛生網站或政府網站的代表，而且有關於 COVID-19 的重要資訊要提供給一般大眾參考，請參閱[這篇文章的建議做法](https://developers.google.com/search/docs/advanced/guidelines/health-government-websites?hl=zh-tw)，瞭解如何讓這類資訊在 Google 搜尋中更引人注目。
* **顯示常見問題**：如果您的網站包含常見問題，[加入常見問題標記](https://developers.google.com/search/docs/appearance/structured-data/faqpage?hl=zh-tw)有助於在 Google 搜尋中顯示您的答案。
* **暫停線上業務**：請參閱我們的[網誌文章](https://developers.google.com/search/blog/2020/03/how-to-pause-your-business-online-in?hl=zh-tw)，瞭解如何暫停線上業務，同時盡量降低在 Google 搜尋方面受到的影響。
* **營業時間和暫時停業公告**：詳閱相關指南，瞭解[如何變更營業時間或宣布暫時停業](https://support.google.com/business/answer/9773423?hl=zh-tw)，或者如何建立 [COVID-19 相關貼文](https://support.google.com/business/answer/7342169?p=covid_posts&hl=zh-tw#covidpost)。
* **活動**：如果您是活動舉辦方，請參閱[這篇文章](https://developers.google.com/search/blog/2020/03/new-properties-virtual-or-canceled-events?hl=zh-tw)，瞭解如何使用新的屬性來標示活動已延期、取消或改成線上舉行。
* **知識面板**：瞭解如何[對 Google 知識面板提出修改建議](https://support.google.com/knowledgepanel/answer/7534842?hl=zh-tw)，或是[聲明知識面板的擁有權](https://support.google.com/knowledgepanel/answer/7534902?hl=zh-tw) (如果您尚未這麼做)。
* **修正伺服器超載問題**：瞭解如何[判定伺服器瓶頸、迅速修正瓶頸、改善伺服器效能，以及避免日後再次發生效能問題](https://web.dev/articles/overloaded-server?hl=zh-tw)。

如有任何問題或意見，歡迎透過 [Twitter](https://twitter.com/googlesearchc) 告訴我們。

發布者：搜尋關係團隊的技術內容撰稿人 [Lizzi Sassman](https://www.okaylizzi.com/+) 和搜尋公關 [Danny Sullivan](https://mastodon.social/@searchliaison)
