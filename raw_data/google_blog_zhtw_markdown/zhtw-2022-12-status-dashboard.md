# Google 搜尋狀態資訊主頁簡介
- **發佈日期**: 2022-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/12/status-dashboard?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 12 月 14 日，星期三

我們希望在 2023 年推出另一項工具，協助大眾瞭解影響 Google 搜尋的系統最新狀態，包含檢索、建立索引以及提供內容。雖然系統中斷問題極為少見，但我們希望能公開透明呈現中斷發生的情形。過去我們曾與[網站可靠性工程師 (SRE)](https://sre.google/?hl=zh-tw) 合作，在 [Google 搜尋中心 Twitter](https://twitter.com/googlesearchc) 帳戶對外說明這些中斷情形。今天，我們要推出 [Google 搜尋狀態資訊主頁](https://status.search.google.com/?hl=zh-tw)，藉此提供您日後的 Google 搜尋狀態資訊。

過去幾年來，我們一直與 SRE 合作，設法以更有效的方式，讓重大事件的相關資訊可供大眾存取，且具有實用價值。這麼做的目的是要能快速、準確且方便地回報問題。因此，我們推出了全新的[狀態資訊主頁](https://status.search.google.com/?hl=zh-tw)，並簡化了事件發生期間的溝通程序。

這個資訊主頁會顯示過去 7 天內發生的廣泛問題，並提供一些詳細資料和事件目前的狀態。廣泛問題是指 [Google 搜尋系統](https://developers.google.com/search/docs/advanced/guidelines/how-search-works?hl=zh-tw)發生系統性問題，影響到許多網站或搜尋使用者。這類問題通常能在外部可見，且 [SRE 的監控和快訊機制](https://sre.google/sre-book/monitoring-distributed-systems/?hl=zh-tw)會在內部運作，標記問題。

![Google 搜尋狀態資訊主頁顯示目前沒有事件發生](https://developers.google.com/static/search/blog/images/searchstatusdashboard.png?hl=zh-tw)

這個資訊主頁提供多項其他 Google 狀態資訊主頁都具備的功能，比如可供訂閱的 [RSS 動態消息](https://status.search.google.com/en/feed.atom?hl=zh-tw)和[歷來資料檢視畫面](https://status.search.google.com/summary?hl=zh-tw)。

### 我們如何通知事件與更新資訊

我們與 SRE 確認目前 Google 搜尋正發生廣泛問題後，會盡可能在一小時內於資訊主頁張貼事件資訊，並在 12 小時內提供該事件的後續資訊。有別於傳統自動化資訊主頁，這些更新資訊由我們的全球工作人員回報。事件的開始時間大致上是我們設法確認問題的時間。

除了您可能看見的傳統狀態更新之外，我們也會嘗試提供可能有助解決問題的其他資訊。舉例來說，假設情境為數百萬個網站處理網域名稱解決方案的網域名稱伺服器拒絕 Googlebot 的連線要求，我們可能會張貼更新資訊，表示變更網域名稱伺服器或許能減輕網站遭遇的問題。當然，我們會持續針對事件發布最新消息 (可能的話也提供緩解措施)，直到事件解決。

當工程師所做的變更能終結系統受到的影響，我們就會判定事件已解決。這表示系統現在健康狀態良好，但網站可能仍會受到影響一段時間，直到完成重新處理，這要視事件類型而定。

如要進一步瞭解資訊主頁，請參閱 Google 搜尋中心的[搜尋狀態資訊主頁專屬頁面](https://developers.google.com/search/help/status-dashboard?hl=zh-tw)。如果您想針對資訊主頁提出意見，歡迎透過 Twitter 傳送訊息給我們：[@googlesearchc](https://twitter.com/googlesearchc)。

**2023 年 3 月 21 日**：資訊主頁現在包含「排名」區域，顯示近期排名更新。
按一下資訊圖示即可查看更新的詳細資訊，以及任何特定指引。

發文者：Google 搜尋團隊 [Gary Illyes](https://garyillyes.com/+)
