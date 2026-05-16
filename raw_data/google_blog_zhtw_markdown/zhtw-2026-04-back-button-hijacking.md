# 針對「返回按鈕劫持」推出新版垃圾內容政策
- **發佈日期**: 2026-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2026/04/back-button-hijacking?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2026 年 4 月 13 日

今天，我們將擴大[垃圾內容政策](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw)的適用範圍，以因應「返回按鈕劫持」這類欺騙行為。這類行為明確違反垃圾內容政策的「[惡意行為](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#malicious-practices)」，導致我們可能必須處理垃圾內容。

## 什麼是返回按鈕劫持？

使用者點選瀏覽器的「返回」按鈕時，會明確預期要返回上一個網頁。返回按鈕劫持行為會破壞這項基本期望。如果網站干擾使用者瀏覽器的導覽方式，導致使用者無法使用「返回」按鈕立即返回來源網頁，就屬於返回按鈕劫持行為。使用者可能會被帶往以前從未造訪過的網頁、看到來路不明的推薦內容或廣告，或無法正常瀏覽網頁。

## 我們採取行動的原因為何？

我們認為使用者體驗至關重要。返回按鈕劫持行為會干擾瀏覽器的功能，破壞使用者預期的歷程，導致使用者感到沮喪。使用者表示感覺遭到操弄，最終不太願意造訪不熟悉的網站。如[先前所述](https://developers.google.com/search/blog/2013/07/reminder-about-deceptive-behavior?hl=zh-tw)，在使用者瀏覽器記錄中插入欺騙或操弄性網頁，一律違反 [Google 搜尋基礎入門](https://developers.google.com/search/docs/essentials?hl=zh-tw)中的規定。

由於這類行為日益增加，因此我們將其明確列為違反[惡意行為](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#malicious-practices)政策，該政策規定：

> 惡意行為會導致使用者期望與實際結果不符，進而造成負面和欺騙性的使用者體驗，或損害使用者安全或隱私權。

如果網頁涉及返回按鈕劫持行為，可能會遭到[人工垃圾內容處置](https://support.google.com/webmasters/answer/9044175?hl=zh-tw#back-button-hijacking&zippy=,back-button-hijacking)或自動降級，進而影響網站在 Google 搜尋結果中的成效。為確保網站擁有者有時間進行必要變更，我們會在 2026 年 6 月 15 日開始執法前兩個月發布這項政策。

## 網站擁有者應採取什麼行動？

請確保您未採取任何行動，進而干擾使用者瀏覽自己的瀏覽器記錄。

如果您目前使用任何指令碼或技術，將欺騙或操縱性網頁插入或取代使用者的瀏覽器記錄，導致使用者無法使用「返回」按鈕立即返回來源網頁，請務必移除或停用這類指令碼或技術。

值得注意的是，某些返回按鈕劫持事件可能源自網站內含的程式庫或廣告平台。建議網站擁有者全面檢查技術實作項目，並移除或停用任何會劫持返回按鈕的程式碼、匯入項目或設定，確保使用者獲得實用且不受欺騙的體驗。

如果網站受到人工判決處罰影響，且您已修正問題，則可以隨時透過 Search Console 提交[重審要求](https://support.google.com/webmasters/answer/35843?hl=zh-tw)，如有任何問題或意見，歡迎前往[社群媒體](https://www.linkedin.com/showcase/googlesearchcentral/)與我們聯絡，或在[產品討論社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)中交流討論。

發文者：Google 搜尋品質團隊代表 [Chris Nelson](https://developers.google.com/search/blog/authors/chris-nelson?hl=zh-tw)
