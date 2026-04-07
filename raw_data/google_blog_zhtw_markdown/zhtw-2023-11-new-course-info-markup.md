# 使用全新課程資訊結構化資料列出課程
- **發佈日期**: 2023-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/11/new-course-info-markup?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 11 月 15 日，星期三

隨著使用者持續在 Google 上搜尋課程，對於更詳細課程資訊的需求也越來越高。今天我們在此提出新的建議，將課程結構化資料提供給 Google。發布者現在可以透過結構化資料提供定價、教育程度、評分和課程長度等詳細資訊，在 Google 搜尋中顯示補充課程資訊。這些資料可能會顯示在課程資訊複合式搜尋結果中。複合式搜尋結果是 Google 搜尋中的全新輪轉介面功能，可讓學習者發掘及比較符合自己獨特需求的課程。

## 在課程結構化資料功能中顯示課程

![這張插圖顯示課程資訊在 Google 搜尋中可能的顯示方式](https://developers.google.com/static/search/docs/images/course-info-rich-result.png?hl=zh-tw)

過去幾年來，Google 一直支援[課程清單](https://developers.google.com/search/docs/appearance/structured-data/course?hl=zh-tw)標記功能 (原稱「課程」)。透過這項功能，單一發布者就能提供課程結構化資料 (名稱、說明和發布商)。系統會繼續支援課程清單複合式搜尋結果，而且流量不會受到影響，無論您是否加入新的課程資訊標記都一樣。我們會繼續針對這兩項功能採用相同的 [schema.org 結構化資料類型](https://schema.org/Course)。

新的[課程資訊開發人員說明文件](https://developers.google.com/search/docs/appearance/structured-data/course-info?hl=zh-tw)說明如何填寫必填欄位和建議欄位。只要符合[功能指南和資格條件](https://developers.google.com/search/docs/appearance/structured-data/course-info?hl=zh-tw#guidelines)，您的課程就能同時顯示在現有的課程資訊功能和新的課程資訊功能中。

## 使用 Search Console 驗證及監控您的結構化資料

為協助您監控及修正結構化資料，我們將在 Search Console 中加入新的課程資訊[複合式搜尋結果報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)。這份報告會針對含有課程資訊結構化資料的頁面，顯示有效和無效的結構化資料項目，以及導致項目失效的問題。您可以利用這份報告，對結構化資料問題進行偵錯、修正及驗證。

![Search Console 中的課程資訊複合式搜尋結果報告](https://developers.google.com/static/search/blog/images/course-info-report.png?hl=zh-tw)

此外，您還可以使用 Search Console 中的[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)，提交網頁網址或程式碼片段，藉此測試課程資訊標記是否有效。您可以使用這項工具，立即確認標記是否有效，不需等待複合式搜尋結果報告完成更新。

![複合式搜尋結果測試中的課程資訊](https://developers.google.com/static/search/blog/images/course-info-rrt.png?hl=zh-tw)

我們希望這個新的標記可讓您更輕鬆在 Google 上顯示課程資訊。如有任何問題或疑慮，歡迎透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)與我們聯絡。

發文者：Google 學習產品經理 [Candice Denic](https://developers.google.com/search/blog/authors/candice-denic?hl=zh-tw) 和 Google 學習軟體工程師 Ashwin Vaidyanathan
