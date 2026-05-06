# 隆重推出 Google 搜尋趨勢 API (Alpha 版)：存取搜尋趨勢資料的新方式
- **發佈日期**: 2025-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/07/trends-api?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 7 月 24 日，星期四

很高興通知您，[Google Trends API 推出囉](https://developers.google.com/search/apis/trends?hl=zh-tw)！Google 搜尋趨勢推出已久，網站一直是存取資料的主要管道。過去幾年來，我們發現使用量不斷增加，而且收到許多希望提供 API 的要求，而這項 API 今天終於推出！

這項 API 僅供極少數測試人員使用。如有意願參與測試，請[申請成為 Alpha 版測試人員](https://developers.google.com/search/apis/trends?hl=zh-tw#apply)。
![Google Trends API 的運作方式](https://developers.google.com/static/search/apis/trends/images/trends-api-marquee.png?hl=zh-tw)

雖然可以透過 [Google 搜尋趨勢網站](https://trends.google.com/trends/?hl=zh-tw)取得趨勢資料，但 API 提供新的方式，讓貴機構以可擴充的方式使用資料。根據初步的使用者體驗研究，我們聽到了以下一些使用案例：

* **研究**：開發人員可影響公共資源分配和科學研究優先事項。
* **發布商**：運用資料追蹤主題和掌握新興趨勢，並根據這些資料，針對重要議題撰寫引人入勝的故事。
* **業務**：行銷人員和 SEO 專家可以安排資源投資的優先次序，制定更完善的業務內容策略。

## 可用的資料

這項 API 會提供經過一致性縮放處理的搜尋熱度資料，最多可回溯 1800 天 (5 年)，包括每日、每週、每月和每年的匯總資料；此外，這項 API 也提供地理限制 (區域和子區域)。還真多！下列各節將詳細說明各項 API 屬性。

### 經過一致性縮放處理的資料

在 Google 搜尋趨勢網站中，每次要求資料時，結果都會縮放至 0 到 100。這個 API 會使用不同的縮放方法，讓各要求之間保持一致，方便您連接、比較及融合多個要求的資料。不過，雖然 API 會傳回經過一致性縮放處理的資料，但這些數字並非絕對值，而是反映[搜尋熱度](https://support.google.com/trends/answer/4365533?hl=zh-tw)。

這種做法的優點是開發人員可以比較不同要求的搜尋熱度。
舉例來說，如果您監控特定字詞一段時間，使用 API 時可以只擷取上個週期的資料；在 Google 搜尋趨勢網站中，您必須擷取每個要求中的整個週期，因為每個 Google 搜尋趨勢網站要求都會將資料縮放至 0 到 100 之間。使用經過一致性縮放處理的資料，還能輕鬆比較數十個字詞，而 Google 搜尋趨勢網站只能比較 5 個字詞。

### 日期範圍和匯總

根據我們的分析，大多數人會保留 5 年內的分析結果。因此，我們決定將資料限制在 1800 天 (約 5 年) 的滾動時間範圍內。雖然使用量最高的 Google 搜尋趨勢資料，多半集中在過去 12 個月，但我們認為研究人員和記者回顧重要時刻時，5 年的資料非常重要，例如上次選舉 (通常每 4 年一次) 和體育賽事 (例如奧運、世界盃)。資料最新只涵蓋到 2 天前。

在日期匯總方面，我們會提供每日、每週、每月和每年的匯總資料。由於用途多元，開發人員可能想將資料與其他報表合併，因此我們提供四種選項，讓開發人員能更彈性地擷取、操控及合併 Google 搜尋趨勢資料與自己的系統。

### 地理資料

API 會提供區域和子區域的細目資料，如 [ISO 3166-2 標準](https://en.wikipedia.org/wiki/ISO_3166-2)所定義。

## Alpha 版測試

我們會開始測試產品，瞭解使用情況並改善最終產品，因此需要喜歡測試的開發人員提供意見回饋，並使用可能還無法部署於正式環境的工具進行疊代。如果符合上述條件，請申請搶先體驗 Google Trends API Alpha 版。

我們將在未來幾週內，逐步開放部分開發人員使用這項功能。如果不在第一批開發人員名單中，請別擔心，我們會在未來幾個月內擴大開放存取權。

[申請成為 Alpha 版測試人員](https://developers.google.com/search/apis/trends?hl=zh-tw#apply)

發文者：Google 搜尋趨勢團隊的 [Daniel Waisberg](https://developers.google.com/search/blog/authors/daniel-waisberg?hl=zh-tw) 和 [Hadas Jacobi](https://developers.google.com/search/blog/authors/hadas-jacobi?hl=zh-tw)
