# 分析 Google 搜尋流量下滑的原因
- **發佈日期**: 2021-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/07/search-traffic-drops?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 7 月 20 日，星期二

這篇網誌文章已發布一段時間。部分資訊可能已經過時，例如圖片可能會有缺漏，連結也可能失效。請參閱[這份新說明文件](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops?hl=zh-tw)，瞭解如何對搜尋流量下滑進行偵錯。

假設開啟 Search Console 後，您發現自己的 Google 搜尋流量下滑了，這時該怎麼做呢？自然搜尋流量下滑的原因有很多，其中大部分是可以恢復的，但要瞭解網站實際發生的問題可能並不容易。

本文將探討會導致流量下滑的一些可能原因，並說明該如何使用 Search Console 的[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)和 [Google 搜尋趨勢](https://trends.google.com?hl=zh-tw)進行偵錯，找出造成搜尋流量下滑的關鍵。

## 搜尋流量下滑的主要原因

為了幫助您瞭解會影響流量的因素，我們列舉了一些流量下滑的情境示例，以及導致這些情境的可能原因。如要進一步瞭解個別示例，請閱讀下文。

![Google 搜尋流量下滑的原因](https://developers.google.com/static/search/blog/images/google-search-traffic-drops.png?hl=zh-tw "Google 搜尋流量下滑的原因")

造成搜尋流量下滑的五個主要原因：

* **技術問題**：Google 因為錯誤而無法檢索您的網頁、為您的網頁建立索引，或對使用者顯示您的網頁。比如：伺服器可用性、robots.txt 擷取、找不到網頁等錯誤。請注意，問題可能是發生在網站層級 (比如網站停止運作) 或網頁層級 (比如 `noindex` 標記放錯位置；視 Google 檢索網頁的情況，流量下滑速度可能較慢)。
* **安全性問題**：如果您的網站受到[安全性威脅](https://developers.google.com/search/docs/monitor-debug/security?hl=zh-tw)影響，Google 可能會在使用者到達您的網站前顯示警告或插頁，導致搜尋流量減少。
* **人工判決處罰**：如果您的網站未遵循 [Google 的指南](https://developers.google.com/search/docs/advanced/guidelines/overview?hl=zh-tw)，Google 可能會透過人工判決處罰，不讓您的部分網頁或整個網站顯示在搜尋結果中。
* **演算法變更**：Google 一直在改進評估內容的方式，並據此更新演算法；[核心更新](https://developers.google.com/search/updates/core-updates?hl=zh-tw)和其他小型更新可能會影響一些網頁在 Google 搜尋結果中的成效。如要即時掌握未來更新情報，請訂閱 [Google Search News](https://www.youtube.com/playlist?list=PLKoqnv2vTMUNDpWUa0TaFPSi7VYLBKV03&hl=zh-tw) YouTube 系列影片，或是在 [Twitter](https://twitter.com/googlesearchc) 追蹤我們。
* **搜尋熱度下降**：有時候，使用者行為的變化會影響對特定查詢的需求，這可能是新趨勢或全年的季節性變化所致。也就是說，您的流量可能單純因為外部影響而下滑。

## 分析搜尋流量下滑模式

由於圖表比文字說明更加直觀，因此如果您想充分瞭解自己的流量變化，最佳做法是查看 Search Console 成效報表的主要圖表，其中匯總了大量資訊。您可以透過分析線條形狀獲得很多資訊。

歡迎前往[搜尋成效報表](https://search.google.com/search-console/performance/search-analytics?hl=zh-tw)並嘗試下列操作：

* **將日期範圍改成包含 16 個月**。這可以幫助您結合環境背景來分析流量下滑情況，確認這不是每年都會由於特定節日或趨勢而發生的情形。如果想進一步擴大日期範圍，可以利用 [Search Analytics API](https://developers.google.com/webmaster-tools/search-console-api-original/v3/searchanalytics?hl=zh-tw) 擷取資料，並將資料儲存在自己的系統中。
* **將流量下滑時期與類似時期進行比較**。您可以藉此瞭解實際發生了哪些變化。請務必點選所有分頁，瞭解是否只有特定查詢、網址、國家/地區、裝置或搜尋外觀的流量發生變化 (瞭解如何建立[比較篩選器](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#comparingdata))。另外，請確保兩段比較時期的天數相同，最好是一週中的同樣幾天。
* **對各種搜尋類型進行獨立分析**。您可以藉此瞭解流量下滑情形是發生在網頁搜尋、Google 圖片，還是影片或新聞分頁的搜尋結果中。

以下這部 Search Console 訓練影片示範了該[如何使用成效報表](https://www.youtube.com/watch?v=wTwnFcWUM3k&hl=zh-tw)。

如果您發現自己的網站存在技術問題、安全問題或受到專人介入處理，請參閱 [Search Console 進階指南](https://developers.google.com/search/docs/advanced/guidelines/search-console?hl=zh-tw)，進一步瞭解該如何解決這些問題。

## 調查產業的整體趨勢

如果您想進一步分析，可以透過 [Google 搜尋趨勢](https://trends.google.com?hl=zh-tw)瞭解流量下滑是整體趨勢，還是只發生在您的網站上。這些變化可能是由兩個主要原因造成：

1. **搜尋熱度下降或新產品**。如果使用者搜尋的內容和方式出現重大變化 (比如因為疫情而改變)，他們就可能開始搜尋不同的查詢關鍵字，或使用裝置處理不同事務。此外，如果您在網路上銷售特定品牌的產品，一旦有新的競爭產品出現，就可能分占您從某些搜尋查詢獲得的流量。
2. **[季節性](https://en.wikipedia.org/wiki/Seasonality)**。舉例來說，[The Rhythm of Food 網站](https://rhythm-of-food.net/)顯示與食物相關的查詢具有很明顯的季節性規律：使用者經常在 1 月搜尋節食，在 11 月搜尋火雞，在 12 月搜尋香檳。
   不同產業存在不同的季節性變化規律。

如要分析不同產業的趨勢，您可以使用 Google 搜尋趨勢取得大量未經過濾的真實 Google 搜尋要求樣本。這些資料為匿名資料，而且經過分類及匯總。透過這種呈現方式，Google 得以顯示從全球到各城市對不同主題的關注度。

您可以觀察會為您的網站帶來流量的查詢，看看這些查詢在每年不同時期是否有明顯減少的現象。下方的例子呈現了三種趨勢 ([查看資料](https://trends.google.com/trends/explore?date=today+5-y&geo=US&q=turkey%2Cchicken%2Ccoffee&hl=zh-tw))：

1. 「turkey」(火雞) 一詞的搜尋量呈現明顯的季節性波動，每年 11 月會達到峰值。
2. 「chicken」(雞肉) 一詞的搜尋量具有一定的季節性波動，但幅度不大。
3. 「coffee」(咖啡) 一詞的搜尋量明顯較為穩定，看來咖啡在全年都有需求。

![搜尋熱度季節性](https://developers.google.com/static/search/blog/images/search-interest-seasonality.png?hl=zh-tw "搜尋熱度季節性")

看過 Google 搜尋趨勢後，我們建議您也參考其他有趣的深入分析，這或許有助您提升搜尋流量：

* **查看您所在地區的熱門查詢，並將這些查詢與您獲得流量的查詢 (參閱 Search Console 的成效報表) 進行比較**。如果您的流量中缺少某些查詢，請檢查您的網站是否提供相應主題的內容，並確認 Google 能檢索這些內容及建立索引。
* **查看與重要主題相關的查詢**。您可以藉此發現有上升趨勢的相關查詢，並為您的網站做好準備，比如添加相關內容。

如有任何問題，歡迎透過[搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 提問。

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com)
