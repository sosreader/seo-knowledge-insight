# 汽車經銷商的車輛資訊結構化資料
- **發佈日期**: 2023-10-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/10/vehicle-listings-structured-data?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 10 月 16 日，星期一

Google 上的車輛資訊可讓汽車經銷商在 Google 搜尋和其他 Google 平台上顯示待售商品目錄。這項功能目前僅供美國和美國領土使用。今天，我們宣布將推出更簡單的新方法，向 Google 提供待售車輛商品目錄資料。

![圖片：顯示如何在 Google 搜尋中顯示車輛產品資訊複合式搜尋結果](https://developers.google.com/static/search/blog/images/vehicle-listing-rich-resut.png?hl=zh-tw)

現在，任何規模的汽車經銷商都可以使用[車輛資訊標記](https://developers.google.com/search/docs/appearance/structured-data/vehicle-listing?hl=zh-tw)在 Google 上刊登車輛產品資訊。對於想要建立及維護動態饋給檔案的汽車經銷商而言，現有的[動態饋給方法](https://developers.google.com/vehicle-listings/reference/feed-specification?hl=zh-tw)仍然是很好的選擇。對於尚未在 Google 上註冊車輛產品資訊，並偏好透過標記進行簡易設定的汽車經銷商，我們建議使用標記。

您可以在車輛詳細資料頁面上導入車輛資訊標記，提供基本車輛資訊和供應情形。詳情請參閱[說明文件](https://developers.google.com/search/docs/appearance/structured-data/vehicle-listing?hl=zh-tw)。

我們也透過 Search Console 的報表和工具，讓使用者更容易監控與修正使用這項功能時所需的結構化資料。

## Search Console 中的複合式搜尋結果報表

為了協助您監控標記問題，我們也開始支援在 Search Console 全新的[複合式搜尋結果報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)中使用車輛資訊結構化資料。這類報告會針對含有結構化資料的網頁顯示有效和無效項目。

![Search Console 中新版車輛產品資訊複合式搜尋結果報告的螢幕截圖](https://developers.google.com/static/search/blog/images/vehicle-listings-status-report.png?hl=zh-tw)

## 複合式搜尋結果測試

您也可以提交網頁網址或程式碼片段，透過[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來測試結構化資料。您可以使用這項工具，立即確認標記是否有效，不需等待複合式搜尋結果報告完成更新。

![複合式搜尋結果測試中新版車輛產品資訊驗證的螢幕截圖](https://developers.google.com/static/search/blog/images/vehicle-listing-rich-resut-test.png?hl=zh-tw)

希望這些新增功能可讓汽車經銷商更輕鬆地在 Google 搜尋中觸及潛在客戶。如果有任何問題或疑慮，請透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：Google 搜尋軟體工程師 Daniel Yosef 和 Alexander Ikonomidis
