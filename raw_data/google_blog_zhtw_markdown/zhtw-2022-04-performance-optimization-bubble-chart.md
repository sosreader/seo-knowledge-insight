# 使用 Search Console 泡泡圖最佳化網站成效
- **發佈日期**: 2022-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/04/performance-optimization-bubble-chart?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 4 月 6 日，星期三

這篇網誌文章已發布一段時間。部分資訊可能已經過時，例如圖片可能會有缺漏，連結也可能失效。請參閱[這份新說明文件](https://developers.google.com/search/docs/monitor-debug/bubble-chart-analysis?hl=zh-tw)，瞭解如何使用 Search Console 泡泡圖改善搜尋引擎最佳化 (SEO)。

分析搜尋成效資料一直是個挑戰，尤其當您有大量長尾查詢時，會更難以理解以及視覺化。本文將提供一些訣竅，協助您找出方法提升自家網站在 Google 搜尋中的成效。

如果您尚未讀過「[將 Search Console 連結至數據分析](https://developers.google.com/search/blog/2022/03/connecting-data-studio?hl=zh-tw)」和「[使用數據分析監控搜尋流量](https://developers.google.com/search/blog/2022/03/monitoring-dashboard?hl=zh-tw)」這兩篇近期貼文，建議您前往閱讀，以便進一步瞭解如何在數據分析中使用 Search Console。

今天我們要討論的是[泡泡圖](https://support.google.com/datastudio/answer/7207785?hl=zh-tw)，這種圖表可協助您瞭解哪些查詢對您網站來說成效較佳，哪些有待改善。我們會先解釋圖表中的主要元素，說明詳細設定及其影響資料的方式。接下來，我們會提供一些指引，說明分析資料的重點。

首先有個好消息：您不需要從頭開始建立圖表，可以利用[這個範本](https://datastudio.google.com/reporting/1e5b5f6a-38d7-4547-a54b-69594681a09b/page/xFbeC/preview?hl=zh-tw)連結您的資料，再視需要調整任何設定。

免除多餘雜務…

![數據分析報表顯示含有 Search Console 資料的泡泡圖](https://developers.google.com/static/search/blog/images/search-performance-analysis.png?hl=zh-tw "數據分析報表顯示含有 Search Console 資料的泡泡圖")

## 瞭解圖表內容

如果您擁有多項指標和維度，**泡泡圖**就是絕佳的視覺化圖表，可讓您更有效率地查看資料中的關係和模式。在此處顯示的範例中，您可以同時查看不同維度 (查詢、裝置) 的流量屬性 (點閱率、[平均排序](https://support.google.com/webmasters/answer/7042828?hl=zh-tw#position)) 和數量 ([點擊](https://support.google.com/webmasters/answer/7042828?hl=zh-tw#click)總數)。

我們會說明部分圖表元素，釐清哪些資料會顯示在其中，哪些不會。

### 資料來源

針對這張圖表，我們使用了透過 [Search Console 資料來源](https://support.google.com/datastudio/answer/7314895?hl=zh-tw)取得的「**網站曝光**」表格，其中含有按網站和查詢匯總的[搜尋成效資料](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)。

### 篩選條件和資料控制項

為方便您有效控管資料，我們在圖表中加入了以下五個自訂選項：

1. **[資料控制](https://support.google.com/datastudio/answer/7415591?hl=zh-tw)**：選擇您想要分析的 Search Console 資源。
2. **日期範圍**：選擇您想在報表中查看的日期範圍，系統預設顯示過去 28 天。
3. **查詢**：納入或排除要聚焦的查詢。您可以[使用規則運算式](https://developers.google.com/search/blog/2021/06/regex-negative-match?hl=zh-tw)，做法類似您在 Search Console 中使用規則運算式的方式。
4. **國家/地區**：納入或排除國家/地區。
5. **裝置**：納入或排除裝置類別。

### 軸

圖表中的軸線是**平均排序** (Y 軸) 和**網站點閱率** (X 軸)，但我們實施了三項重大轉型，使圖表能呈現更深入的分析資：

* **倒轉 Y 軸方向**：Y 軸顯示的是平均排序，倒轉代表 1 位於頂端。就大部分商務圖表來說，最佳位置在右上角，因此用圖表顯示平均排序時，倒轉 Y 軸較符合直覺。
* **對數刻度**：[對數刻度](https://en.wikipedia.org/wiki/Logarithmic_scale)是指「以簡明的方式顯示資料值跨距極大的數值型資料 (...) 沿著刻度移動一個單位的距離表示該數值乘以 10」。兩個軸都採用對數刻度，可讓您深入瞭解圖表中極端值的查詢情形 (極低的點閱率、平均排序或兩者兼具)。
* **[參考資料行](https://support.google.com/datastudio/answer/9921462?hl=zh-tw)**：參考資料行的作用是醒目顯示高於或低於特定門檻的值。查看平均值、中位數或特定百分位數，可能會讓人注意到偏離模式的情況。

### 泡泡

圖表中的每個泡泡代表單一查詢；為提高圖表的實用性，我們使用兩種[樣式屬性](https://support.google.com/datastudio/answer/7207785?hl=zh-tw#style-properties)。

* **大小**：以泡泡大小表示點擊次數，可協助您快速瞭解哪些查詢帶來大量流量 — 泡泡越大，表示該查詢產生的流量越多。
* **顏色**：以泡泡顏色表示裝置類別，可協助您瞭解行動裝置和電腦兩者間的搜尋成效差異。您可以採用任何維度當做顏色，不過，值的數量越多，會越難識別出模式。

## 分析資料

這種視覺化呈現方式的目標是要突顯查詢最佳化商機。圖表會顯示查詢效能，其中 Y 軸代表**平均排序**，X 軸代表**點閱率**，泡泡大小代表總**點擊**次數，而泡泡顏色代表**裝置類別**。

紅色參考線代表各個軸的平均值，這兩條線將圖表分割成不同象限，代表四種類型的查詢效能。您的象限可能會與本文中分享的圖表看起來不太一樣，因為畫面是由您的網站查詢分布情形決定的。

![顯示四種查詢效能類型的圖表](https://developers.google.com/static/search/blog/images/query-performance-types.png?hl=zh-tw "顯示四種查詢效能類型的圖表")

一般來說，圖表會顯示四個群組供您分析，協助您判斷在哪些部分投注時間最能提升查詢效能。

1. **高排名，高點閱率**：這部分沒什麼需要做的，效果已經很好。
2. **低排名，高點閱率**：這些查詢似乎很貼近使用者需求，雖然排名低於網站上的平均查詢排名，點閱率卻很高。如果能提升這些查詢的排名，可能會大幅改善成效；因此，請全力最佳化這些項目！
3. **低排名，低點閱率**：查看低點閱率 (本項目與下一項) 的查詢時，最有趣的部分是查看泡泡大小，瞭解哪些查詢雖然點閱率低，但仍帶來大量流量。雖然在此象限的查詢似乎不值得您投資改善，但這些查詢主要可分為兩組：
   * 「相關查詢」：如果此處的查詢對您來說很重要，這是個好的開始，因為這表示這些查詢已經顯示在 Google 搜尋中了。將這些查詢排在完全不會顯示在搜尋結果中的查詢之前，因為這類查詢比較容易最佳化。
   * 「不相關查詢」：如果查詢與您的網站不相關，也許這正是個好機會，可以微調您的內容，鎖定能帶來相關流量的查詢。
4. **高排名，低點閱率**：這些查詢的點閱率偏低可能有各種不同理由。請查看最大的泡泡，找出下列訊號：
   * 您的競爭對手可能使用了結構化資料標記，而且搭配複合式搜尋結果顯示，這有可能吸引使用者點擊他們的結果，而非點擊您的結果。建議[為網站啟用搜尋結果功能](https://developers.google.com/search/docs/appearance/search-result-features?hl=zh-tw)。
   * 您已最佳化的查詢，或「意外」獲得排名的查詢，可能是與您的網站相關但使用者不感興趣的查詢。
   * 使用者可能已經找到所需的資訊，例如公司的營業時間、地址或電話號碼。

## 最佳化網站成效

一旦找到值得您投入時間與心力的查詢，請務必參考[搜尋引擎最佳化 (SEO) 入門指南](https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=zh-tw)的說明，針對這些查詢進行最佳化。以下提供幾個訣竅：

* 確保您的 [`title`](https://developers.google.com/search/docs/appearance/title-link?hl=zh-tw#page-titles) 元素、[說明 `meta` 標記](https://developers.google.com/search/docs/appearance/snippet?hl=zh-tw#meta-descriptions)和 `alt` 屬性具有描述性、具體且準確。
* 使用標題元素強調重要文字，並為內容建立階層式結構，方便使用者和搜尋引擎瀏覽您的文件。
* 新增[結構化資料標記](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=zh-tw)，這樣做不僅能向搜尋引擎說明您的內容，還能讓您的內容以實用 (且引人注目) 的方式顯示在搜尋結果中。
* 考量使用者為找到您的某些內容而可能搜尋的字詞。您可以運用 Google Ads 提供的[關鍵字規劃工具](https://ads.google.com/home/tools/keyword-planner/?hl=zh-tw)，藉此找出新的關鍵字變化版本，並查看每個關鍵字的大致搜尋量。您也可以利用 [Google 搜尋趨勢](https://trends.google.com/trends/?hl=zh-tw)，從與您網站相關的新熱門話題與查詢中尋找靈感。

## 意見回饋

如有任何問題，歡迎隨時透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或[數據分析社群](https://support.google.com/datastudio/threads?thread_filter=%28category%3Aconnect_to_data%29&hl=zh-tw)提問。此外，如果您使用 Twitter，請務必[追蹤我們](https://twitter.com/googlesearchc)，我們會在上面公告最新文章的相關資訊。

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com)
