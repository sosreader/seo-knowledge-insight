# 網站名稱更新內容
- **發佈日期**: 2023-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/07/sitenames?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 7 月 28 日星期五

5 月時，我們[加入了](https://twitter.com/googlesearchc/status/1660731696247984136)在子網域上使用[網站名稱](https://developers.google.com/search/docs/appearance/site-names?hl=zh-tw)的支援功能 (僅限行動裝置)，支援的語言為英文、法文、德文與日文。現在，我們支援在所有使用這些語言的裝置上使用子網域。此外，我們最近也更新了網站名稱系統的運作方式，讓選擇的選項更能代表搜尋結果中列出的網站。

![Google 搜尋結果的螢幕截圖，顯示網址上方醒目顯示的網站名稱](https://developers.google.com/static/search/blog/images/sitenames-2023/sitename-developers-google-com.png?hl=zh-tw)

## 更新取得偏好網站名稱的相關指南

提醒您，如要向 Google 指定偏好的網站名稱，最好的方法就是使用 `WebSite` 結構化資料，如[網站名稱說明文件](https://developers.google.com/search/docs/appearance/site-names?hl=zh-tw)中所述。

我們也更新了說明文件，鼓勵使用者多多使用 `alternateName` 資源。有時無法使用偏好的網站名稱。舉例來說，我們的系統通常不會針對兩個不同的全域網站使用相同的網站名稱。如未選取偏好選項，使用 `alternateName` 資源提供替代名稱可讓我們的系統考慮其他選項。

## 未選取偏好名稱或替代名稱時的解決方法

在極少數情況下，我們的系統可能不會選取偏好網站名稱或替代網站名稱。如果某個網站的名稱不是獨特名稱、簡要或廣為人知的狀態，就會發生這種情況。

我們的說明文件現在已針對這種情況[提供解決方法](https://developers.google.com/search/docs/appearance/site-names?hl=zh-tw#workaround)。如果您提供網域或子網域名稱做為網站名稱，通常就會使用您所提供的名稱。
在嘗試這個解決方法之前，建議您先查看透過 `WebSite` 結構化資料提供的偏好名稱與次要名稱，以及首頁中的[其他來源](https://developers.google.com/search/docs/appearance/site-names?hl=zh-tw#sources)，以支援該結構化資料。

## 內部網頁的已知問題

我們注意到在某些情況下，系統針對首頁所顯示的網站名稱可能不會套用並顯示在該網站的其他網頁上。舉例來說，`https://example.com/` 顯示的網站名稱可能與 `https://example.com/internal-page.html` 不同。

我們正積極處理這個問題。我們會在解決這個問題後更新說明文件。
在這段期間，如果您的首頁顯示的是您偏好的網站名稱，請注意，內部網頁最終應該也會顯示該網站名稱。

我們也正設法在日後全面針對所有語言提供網站名稱支援功能。如有任何疑問，歡迎前往[搜尋中心產品討論社群](https://support.google.com/webmasters/thread/227739087?hl=zh-tw)發文提問。

發文者：Google 搜尋團隊 [Kenji Inoue](https://developers.google.com/search/blog/authors/kenji-inoue?hl=zh-tw)
