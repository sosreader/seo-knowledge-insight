# 所有網站將採用行動版內容優先索引系統
- **發佈日期**: 2020-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/03/announcing-mobile-first-indexing-for?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 3 月 5 日，星期四

**已提供更新內容**：這篇文章已過時。請參閱新版的[行動版內容優先索引系統最佳做法](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=zh-tw)。

Google 在[行動版內容優先索引系統](https://developers.google.com/search/blog/2016/11/mobile-first-indexing?hl=zh-tw)耕耘多年，這個系統是建立在利用智慧型手機版的 Googlebot 檢索網頁。根據我們的分析，搜尋結果所顯示的網站大多已能轉移至行動版內容優先索引系統，而事實上 70% 出現在 Google 搜尋結果的網站也都已完成轉移。簡單來說，全面移轉的時機已經成熟。我們在此宣布，自 2020 年 9 月起，所有網站都會改採行動版內容優先索引系統；在那之前，我們仍會持續將 Google 系統判定符合條件的網站，先行搬移至行動版內容優先索引系統。

當某個網域轉移至行動版內容優先索引系統後，Googlebot 對該網域的檢索次數就會增加，這是因為 Google 正在將網站的索引更新至行動版。這項作業可能需要一段時間才能完成，具體時間因網域而異。在此之後，我們偶爾還是會使用傳統的電腦版 Googlebot 進行檢索，但 Google 搜尋的大多數檢索作業都會交由[智慧型手機使用者代理程式](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=zh-tw)執行。這個使用者代理程式的確切名稱會[與用於轉譯網頁的 Chromium 版本相符](https://developers.google.com/search/blog/2019/10/updating-user-agent-of-googlebot?hl=zh-tw)。

在 [Search Console](https://search.google.com/search-console/about?hl=zh-tw) 中，您可以透過多種方式查看行動版內容優先索引系統的狀態。如要檢視特定網址最近一次的檢索狀態，可前往[設定頁面](https://search.google.com/search-console/settings?hl=zh-tw)或使用[網址檢查工具](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)。

此外，無論是對新網站還是現有網站來說，我們為了讓所有網站順利採用行動版內容優先索引系統所編撰的[指南](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=zh-tw)依然具有參考價值。具體來說，我們的建議是確保同一個網站的行動版和電腦版提供完全相同的內容 (包含文字、[圖片](https://developers.google.com/search/docs/appearance/google-images?hl=zh-tw)、[影片](https://developers.google.com/search/docs/appearance/video?hl=zh-tw)及連結)、中繼資料 (包含[標題](https://developers.google.com/search/docs/appearance/title-link?hl=zh-tw)、[說明](https://developers.google.com/search/docs/appearance/snippet?hl=zh-tw)和 [robots `meta` 標記](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=zh-tw)) 和[結構化資料](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=zh-tw)。因此，當您發布網站或對網站進行重大改版後，最好能仔細檢查上述項目。只要使用[網址測試工具](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)，就能輕鬆地直接檢查電腦版和行動版內容。如果您是透過監控工具或檢索器等其他工具來分析網站，請使用行動版使用者代理程式，這樣才能看見 Google 搜尋所檢視到的內容。

雖然我們會繼續支援[各種行動網站實作方法](https://developers.google.com/search/mobile-sites/mobile-seo?hl=zh-tw)，但仍建議新網站採用[回應式網頁設計](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=zh-tw#responsive-design)。我們不建議使用獨立的行動版網址 (通常稱為「m. 網址」)，因為過去幾年來這類網址對搜尋引擎和使用者都造成一些問題，而且容易引起混淆。

行動版內容優先索引系統已逐漸完備。我們很高興能見證網路瀏覽裝置從電腦演進至行動裝置的過程，也很感謝網站管理員協助我們配合使用者與網路互動的方式，建立適合的檢索及索引系統。同時，我們也要對大家在過去幾年付出的心力致上謝意，本次轉移作業正是有賴各位的努力才能順利推動。我們會持續小心監控及評估各種變化。如有任何問題，歡迎造訪[網站管理員論壇](https://support.google.com/webmasters/go/community?hl=zh-tw)，或參加我們舉辦的[公開活動](https://developers.google.com/search/events?hl=zh-tw)。

發文者：Google Zurich 開發人員服務代表 [John Mueller](https://johnmu.com/)
