# 告別網站連結搜尋框
- **發佈日期**: 2024-10-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/10/sitelinks-search-box?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 10 月 21 日，星期一

我們在 [Google 搜尋中首次推出網站連結搜尋框](https://developers.google.com/search/blog/2014/09/improved-sitelinks-search-box?hl=zh-tw)，至今已過了十多年，我們發現這項功能的使用率已經下降。有鑑於此，同時為了簡化搜尋結果，我們將自 2024 年 11 月 21 日起移除這項視覺元素。

![搜尋結果顯示網站連結搜尋框](https://developers.google.com/static/search/blog/images/slsb-example-2024.png?hl=zh-tw)

(搜尋結果顯示網站連結搜尋框)

這項異動將套用到全球所有國家/地區與語言的搜尋結果。這項更新不會影響排名或[其他網站連結視覺元素](https://developers.google.com/search/docs/appearance/sitelinks?hl=zh-tw)，也不會列入搜尋狀態資訊主頁中。一旦我們停止在搜尋中顯示網站連結搜尋框元素，就會移除相關的 [Search Console 複合式搜尋結果報表](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)，並停止在[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)中醒目顯示標記。

雖然您可以從網站中移除[網站連結搜尋框結構化資料](https://developers.google.com/search/docs/appearance/structured-data/sitelinks-searchbox?hl=zh-tw)，但不必這麼做。這類不支援的結構化資料不會在 Google 搜尋中造成問題，也不會在 Search Console 報表中觸發錯誤。如果您決定移除網站連結搜尋框結構化資料，請注意，[網站名稱](https://developers.google.com/search/docs/appearance/site-names?hl=zh-tw#add-structured-data)也使用 `WebSite` 結構化資料的變化版本，我們仍會繼續支援這類資料。

如有任何問題，歡迎前往[搜尋中心產品討論社群](https://goo.gle/sc-forum)提問，或在[社群媒體](https://www.linkedin.com/showcase/googlesearchcentral/)上與我們聯絡。

發文者：Google 瑞士團隊搜尋服務代表 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw)
