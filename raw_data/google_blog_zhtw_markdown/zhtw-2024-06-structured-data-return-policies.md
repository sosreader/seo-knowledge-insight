# 為機構層級退貨政策新增標記支援
- **發佈日期**: 2024-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/06/structured-data-return-policies?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 6 月 11 日，星期二

退貨政策是購物者在線上購買產品時考慮的主要因素，因此[去年](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=zh-tw#product-with-returns-example)我們啟用了針對單一產品提取結構化資料退貨政策的功能。如今我們還在[機構](https://developers.google.com/search/docs/appearance/structured-data/organization?hl=zh-tw)層級新增對退貨政策的支援，這表示您將能為貴商家指定通用退貨政策，而不必為您銷售的每件產品定義一項退貨政策。

![顯示 30 天免費退貨政策的知識面板插圖](https://developers.google.com/static/search/blog/images/merchant-organization-information.png?hl=zh-tw)

新增機構層級退貨政策有助於縮小[產品](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)結構化資料標記的大小，並讓您輕鬆的集中管理退貨政策標記。除了產品搜尋結果之外，這麼做還可以使您的退貨政策與其他搜尋結果一起顯示，例如[知識面板](https://support.google.com/knowledgepanel/answer/9163198?hl=zh-tw)和[品牌資料](https://support.google.com/merchants/answer/14998338?hl=zh-tw)。

如果您沒有 Merchant Center 帳戶，並希望能夠為貴商家提供退貨政策，則為機構結構化資料新增退貨政策尤其重要。Merchant Center 已可讓您為貴商家提供[退貨政策](https://support.google.com/merchants/answer/10220642?hl=zh-tw)，因此，如果您有 Merchant Center 帳戶，建議您改為在其中定義退貨政策。

## 在複合式搜尋結果測試中加入對退貨政策的支援

您可以透過提交網頁網址或程式碼片段，使用[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來測試在機構結構化資料下定義的[退貨政策](https://developers.google.com/search/docs/appearance/structured-data/organization?hl=zh-tw#example-online-store)。透過這項工具，您就能確認標記是否有效。

![顯示機構層級退貨政策的複合式搜尋結果測試](https://developers.google.com/static/search/blog/images/rich-results-test-return-policy.png?hl=zh-tw)

如果您的網站是線上或當地商家，我們建議使用 [`OnlineStore`](https://schema.org/OnlineStore) 之一，或 `Organization` 的 [`LocalBusiness`](https://schema.org/LocalBusiness) 子類型。

我們希望這項新增功能可讓您更輕鬆地為貴商家新增退貨政策，並使其能夠在 Google 購物體驗中顯示。如有任何問題或疑慮，請透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)、[Twitter](https://twitter.com/googlesearchc) 或 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 與我們聯絡。

發文者：Google 購物軟體工程師 [Irina Tuduce](https://developers.google.com/search/blog/authors/irina-tuduce?hl=zh-tw)、Pascal Fleury 和 Johan Linder
