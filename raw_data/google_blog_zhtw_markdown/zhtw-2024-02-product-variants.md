# 為產品子類新增結構化資料支援
- **發佈日期**: 2024-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/02/product-variants?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 2 月 20日，星期二

2022 年，Google [擴大對產品結構化資料的支援](https://developers.google.com/search/blog/2022/09/merchant-listings?hl=zh-tw)，以便在 Google 搜尋中提供更優質的產品體驗。接著，我們在 2023 年[新增對運送及退貨結構化資料的支援](https://developers.google.com/search/blog/2023/04/shipping-and-returns-information?hl=zh-tw)。如今，我們[為產品子類新增結構化資料支援](https://developers.google.com/search/docs/appearance/structured-data/product-variants?hl=zh-tw)，讓商家能輕鬆顯示更多產品子類，向購物者顯示更相關、更實用的結果。提供產品子類結構化資料也能補充及強化 [Merchant Center 動態饋給](https://support.google.com/merchants/answer/7439882?hl=zh-tw) (包括[自動動態饋給](https://support.google.com/merchants/answer/7538732?hl=zh-tw))。

許多產品都是以不同的子類形式販售。舉例來說，服飾、鞋子、家具和行李販會以各種尺寸、顏色、材質或圖案的販售。
同樣地，筆記型電腦或智慧型手機等電子產品也會搭配不同的記憶體大小、螢幕大小和處理器販售。

![插圖：不同子類在電子商務網站上的顯示方式](https://developers.google.com/static/search/blog/images/product-variants-2024-1.png?hl=zh-tw)

*插圖：不同子類在電子商務網站上的顯示方式*

開始透過 Schema.org `ProductGroup` 類型為產品子類使用新的結構化資料後，您的產品子類就可能符合在 Google 進階搜尋結果中顯示的資格。

## 如何向 Google 提供產品子類？

子類產品的網站比單一產品網站更為複雜，因此相關的結構化資料也會較為複雜。一項額外的複雜性，就是子類必須歸入同一個「父項」產品底下。為了允許這種子類分組，我們現在新增對 [Schema.org](https://schema.org) `ProductGroup` 類型和 3 種新屬性的支援：

* `hasVariant` (在其父項 `ProductGroup` 底下建立 `Product` 子類的巢狀結構)
* `variesBy` (用於列出子類識別屬性) 與
* `productGroupID` (ID，也稱為 `ProductGroup)` 的「父項 SKU」)

為了擴大支援更多產品子類，我們新增了同時適用於單頁和多頁子類網站的新全方位[說明文件](https://developers.google.com/search/docs/appearance/structured-data/product-variants?hl=zh-tw)和驗證功能。

## 透過 Search Console 驗證及監控產品子類結構化資料

我們已在 Search Console 和[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)的[產品摘要和商家資訊報表](https://support.google.com/webmasters/answer/12660034?hl=zh-tw)中新增子類驗證功能：

![複合式搜尋結果測試中的產品子類結構化資料](https://developers.google.com/static/search/blog/images/product-variants-2024-2.png?hl=zh-tw)

我們希望這些新增功能可以讓您更容易新增子類結構化資料，以及在 Google 搜尋中顯示產品子類。如有任何問題或疑慮，請透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)或[社群媒體](https://twitter.com/googlesearchc)與我們聯絡。

發文者：Google 搜尋與購物軟體工程師 [Irina Tuduce](https://developers.google.com/search/blog/authors/irina-tuduce?hl=zh-tw)、[Ryan Levering](https://developers.google.com/search/blog/authors/ryan-levering?hl=zh-tw) 和 Stanislav Dragiev
