# 透過 Search Console 找出 AMP 的 Signed Exchange 錯誤，並加以修正
- **發佈日期**: 2020-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/08/identify-and-fix-amp-signed-exchange?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 8 月 18 日，星期二

Signed Exchanges (SXG) 屬於名為 [Web Packaging](https://github.com/WICG/webpackage) 的全新規格系列，發布者可以利用這項機制安全地將自身內容變成可供搬運的狀態，同時維護自身的完整性和內容歸屬關係。[Google 搜尋從 2019 年開始連結至經過簽署的 AMP 網頁](https://developers.google.com/search/blog/2019/04/instant-loading-amp-pages-from-your-own?hl=zh-tw)，而這些 AMP 網頁均來自 Google 的快取版本。這項功能可以在維護使用者隱私的前提下讓瀏覽器預先擷取內容，同時正確標註內容的來源。

現在我們很高興地宣布，那些為 AMP 網頁導入 SXG 的網站將能瞭解自身是否存在問題，導致 Google 無法利用 Google AMP 快取提供其網頁的 SXG 版本。

您可以運用 [AMP 報告](https://support.google.com/webmasters/answer/7450883?hl=zh-tw#sgx_warning_list)檢查自己的網站是否有 SXG 相關問題，這類問題的名稱會包含「Signed Exchange」字樣。此外，系統也會在偵測到新問題時透過電子郵件通知您。

![Search Console 中的 Signed Exchange 報告](https://developers.google.com/static/search/blog/images/import/5e3a2136782093be8ecd2a1985f1573a.png?hl=zh-tw)

為了方便您進行偵錯，以及驗證特定網頁是否以 SXG 提供，我們特別提供了[網址檢查工具](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)。您只要在這項工具中輸入網址，就能查看分析的 AMP 部分是否列出 SXG 相關問題。

您可以診斷哪些問題會影響已編入索引的網頁版本，也可以使用 [測試線上網址] 選項，檢查網站目前提供的線上版本是否有效。

![Search Console 中的 Signed Exchange 問題詳細資料](https://developers.google.com/static/search/blog/images/import/ca5e60bd413d590b1d548b4353fd9152.png?hl=zh-tw)

如要進一步瞭解我們可以回報的 SXG 問題類型，請參閱這篇有關 SXG 問題的[說明中心文章](https://support.google.com/webmasters/answer/7450883?hl=zh-tw#sgx_warning_list)。如有任何問題，請前往[產品討論社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 Google 網站管理員的 [Twitter 專頁](https://twitter.com/googlesearchc)提問。

發文者：Search Console 軟體工程師 [Amir Rachum](https://amir.rachum.com/) 和 Google 搜尋產品經理 Jeffrey Jose
