# 改善索引涵蓋範圍資料
- **發佈日期**: 2021-01-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/01/index-coverage-data-improvements?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 1 月 11 日，星期一

協助使用者瞭解 Google 檢索網站並建立網站索引的方式，[一直以來](https://developers.google.com/search/blog/2005/11/more-stats?hl=zh-tw)都是 Search Console 的主要目標之一。我們在推出[新版 Search Console](https://developers.google.com/search/blog/2018/01/introducing-new-search-console?hl=zh-tw) 時，也同時提供[索引涵蓋範圍報表](https://support.google.com/webmasters/answer/7440203?hl=zh-tw)，讓您清楚掌握自己的資源，瞭解 Google 已造訪或嘗試造訪的網址目前處於何種索引狀態。

今天，我們將為這份報表推出多項重大改善措施。這些改善項目採納了社群使用者的意見回饋，針對 Google 無法檢索網頁並建立索引的問題，提供更全面的資訊。此次變更的重點是為現有問題提供更準確的狀態，應該有助您更快解決問題。變更項目如下：

* 移除通泛的「檢索異常」問題類型：從現在起，所有檢索錯誤都會對應至更精細的分類
* 現在，如果已提交的網頁遭到 robots.txt 封鎖後仍成功建立索引，系統會將其記錄為「已建立索引但遭到封鎖」(警告)，而不是「已提交但遭到封鎖」(錯誤)
* 新增問題類別：[已建立索引但沒有內容](https://support.google.com/webmasters/answer/7440203?hl=zh-tw#indexed_no_content) (警告)
* `Soft 404` 報表的內容更為準確

索引涵蓋範圍報表目前已反映上述變更內容，因此您可能會在報表中看到新的問題類型，或發現問題數量出現異動。希望這次變更能讓您更加瞭解 Google 如何[檢索您的網站並建立索引](https://www.google.com/search/howsearchworks/crawling-indexing/?hl=zh-tw)。

如對這份報表有任何意見回饋，歡迎透過[搜尋中心產品討論社群](https://support.google.com/webmasters/community?hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 分享給我們。

發文者：Search Console 軟體工程師 Tal Yadid
