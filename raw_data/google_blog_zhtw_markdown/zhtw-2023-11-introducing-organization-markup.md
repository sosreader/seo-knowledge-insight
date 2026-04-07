# 擴大機構詳細資料的標記支援範圍，包括標誌結構化資料
- **發佈日期**: 2023-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/11/introducing-organization-markup?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 11 月 29 日，星期三

![插圖：知識面板中的商家資訊](https://developers.google.com/static/search/docs/images/organization.png?hl=zh-tw)

[自 2013 年起](https://developers.google.com/search/blog/2013/05/using-schemaorg-markup-for-organization?hl=zh-tw)，Google 已支援標誌結構化資料，可辨識 `logo` 和 `url` 這兩個 `Organization` 欄位。如今我們要擴大對機構資訊的支援，擷取名稱、地址、聯絡資訊、各種企業 ID 等其他管理資料。你可以繼續提供 `logo` 和 `url` 欄位，指定貴機構要用在 Google 搜尋結果中的標誌圖片。本次更新後，Google 就能在知識面板和其他視覺元素 (例如[出處](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=zh-tw#attribution)) 中使用這個標記，讓使用者更容易在 Google 搜尋中找到貴機構的詳細資料。

隨著機構資料的支援範圍擴大，我們會將標誌說明文件併入新的[機構](https://developers.google.com/search/docs/appearance/structured-data/organization?hl=zh-tw)說明文件。目前在複合式搜尋結果測試中，Search Console 現有的標誌報表和複合式搜尋結果測試的驗證工具，已替換為更詳盡的機構驗證工具。

如果你已透過機構標記新增 `logo` 和 `url` 欄位，則無須採取任何行動，Google 仍然能識別你的標誌標記。建議你根據貴機構的情況新增適用欄位。

你提供額外的機構詳細資料後，標記就有機會顯示在知識面板中，例如[近期宣布的商家知識面板](https://blog.google/products/shopping/google-merchant-new-features-holiday/?hl=zh-tw)。

## 在複合式搜尋結果測試中新增對 `Organization` 的支援

你可以在[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)中提交網頁網址或程式碼片段，測試機構結構化資料。透過這項工具，你就能立即確認標記是否有效。

![複合式搜尋結果測試中的機構標記](https://developers.google.com/static/search/blog/images/organization-rich-results-test.png?hl=zh-tw)

若是當地商家的網站，那麼除了使用新的[機構](https://developers.google.com/search/docs/appearance/structured-data/organization?hl=zh-tw)標記之外，也建議依循現有的[當地商家](https://developers.google.com/search/docs/appearance/structured-data/local-business?hl=zh-tw)標記指南。如果是只經營線上業務的網站，建議使用 `Organization` 的子類型 [`OnlineBusiness`](https://schema.org/OnlineBusiness)。

希望這些新功能推出後，你可以更輕鬆新增機構結構化資料，方便介紹業務內容或貴機構，並顯示在 Google 知識面板上。如有任何問題或疑慮，歡迎透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)與我們聯絡。

發文者：Google 購物軟體工程師 [Irina Tuduce](https://developers.google.com/search/blog/authors/irina-tuduce?hl=zh-tw) 和 Alex Jansen
