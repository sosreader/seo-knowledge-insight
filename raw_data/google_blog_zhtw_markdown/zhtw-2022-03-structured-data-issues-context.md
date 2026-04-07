# 為 Search Console 中的結構化資料問題新增脈絡資訊透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2022-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/03/structured-data-issues-context?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 3 月 28 日，星期一

為協助您有效找出結構化資料問題，從明天起 Search Console 會在錯誤報表中新增更多脈絡資訊。

舉例來說，如果網站沒有在 `Review snippet` 標記中提供作者名稱，Search Console 目前是回報為**缺少欄位「名稱」**錯誤。從今天起，該項錯誤會命名為**缺少欄位「名稱」(「作者」部分)**。括號中提供的詳細脈絡資訊有助於您找出結構化資料中的問題所在。

![Search Console 中的結構化資料問題脈絡資訊](https://developers.google.com/static/search/blog/images/structured-data-issues-context.png?hl=zh-tw)

這項變更會影響所有 [Search Console 複合式搜尋結果狀態報表](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)、[Search Console 網址檢查工具](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)和[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)，即使您沒有變更結構化資料標記也一樣：

* 所有參照巢狀資源的待解決問題都會自動關閉 (例如上述範例中的 `Missing field "name"` 問題)。
* 系統會顯示新的待解決問題，並附上更多脈絡資訊，說明缺少的是什麼 (例如問題會顯示 `Missing field "name" (in "author")`)。為避免 Search Console 使用者收到過多電子郵件，系統建立這些新問題時不會傳送通知。

請注意，如果您在變更前曾要求 Search Console 驗證某項修正，則必須重新驗證新問題。

總之，這次變更的只是問題名稱，不會影響 Search Console 偵測錯誤的方式，而且所有遭系統關閉的問題，都會替換成新的問題，並在問題名稱上附上更多脈絡資訊。

如果您有任何問題或疑慮，歡迎前往 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 尋求協助。

發文者：Search Console 產品經理 [Moshe Samet](https://www.linkedin.com/in/moshe-samet-5465326/) 與 Google 搜尋工程團隊成員 [Ryan Levering](https://developers.google.com/search/blog/authors/ryan-levering?hl=zh-tw)
