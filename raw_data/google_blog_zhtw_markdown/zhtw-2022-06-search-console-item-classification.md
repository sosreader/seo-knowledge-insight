# 使用更新後的項目分類功能簡化 Search Console 報表
- **發佈日期**: 2022-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/06/search-console-item-classification?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 6 月 15 日，星期三

我們正在簡化 Search Console 報表中的網頁、項目和問題分類方式，希望這有助您找出會影響 Google 搜尋曝光率的重大問題，而這將有助您優先處理相關工作。在接下來幾個月內，我們將逐步對所有資源進行這項變更，因此您目前可能還看不到任何改變。

使用者告訴我們，網址或項目套用了「警告」狀態時，他們感到困惑，警告的意思究竟是表示網頁可以顯示在 Google 上，還是不可以？

為解決這個問題，我們將頂層項目 (複合式搜尋結果報告的複合式搜尋結果、其他報表的網頁或網址) 分為兩組：含有重大問題的網頁或項目會加上類似「無效」的標籤；而不含重大問題的網頁或項目會加上類似「有效」的標籤。我們認為這種新的分組方式，可協助您迅速掌握哪些問題會影響網站在 Google 上的顯示情形，讓您優先處理這類問題。如要進一步瞭解這項變更對各項報告的影響，請造訪[說明中心](https://support.google.com/webmasters/answer/11510493?hl=zh-tw)。

再次重申，這只是 Search Console 中的報表異動，Google 搜尋檢索網頁、建立索引或提供網頁的方式並沒有任何改變。

![Search Console 報表項目分類更新](https://developers.google.com/static/search/blog/images/search-console-item-classification.png?hl=zh-tw "Search Console 報表項目分類更新")

當您在 Search Console 中檢查特定網址時，本文中所提及的變更會反映在[網址檢查工具](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)中。

不過，只有當我們在幾個月內完成對所有資源進行這項變更時，才會在 [URL Check API](https://developers.google.com/search/blog/2022/01/url-inspection-api?hl=zh-tw) 中更新這些資訊。這就表示，如果資源在 Search Console 中顯示經過更新的項目分類，那麼在比較產品介面與 API 的結果時，您可能就會發現有所差異。請注意，完成對所有資源進行這項變更後，API 中將不會提供新的值。我們將會在 API 更新時，更新這篇網誌文章。

如果您有任何問題或疑慮，請透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：Search Console 工程師 Sion Schori 和 Search Console 產品經理 [Moshe Samet](https://www.linkedin.com/in/moshe-samet-5465326/)
