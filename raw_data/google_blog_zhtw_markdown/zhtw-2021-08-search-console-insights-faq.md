# Google Search Console 深入分析功能幕後揭密
- **發佈日期**: 2021-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/08/search-console-insights-faq?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 8 月 9 日，星期一

[Search Console 深入分析](https://search.google.com/search-console/insights/about?hl=zh-tw)這項服務可為內容創作者和網站擁有者提供量身打造的 Google Search Console (GSC) 和 Google Analytics (GA) 資料。上個月[公告](https://developers.google.com/search/blog/2021/06/search-console-insights?hl=zh-tw)相關訊息後，我們收到許多社群成員的寶貴意見，以及有關資料的問題。

本文將回答其中幾個問題，並詳細說明幾項要點。舉例來說，如果嘗試比較 GSC 深入分析與 Google Analytics 中顯示的資料，可能會發現些許差異，這是為什麼？

## Google Search Console 深入分析常見問題

### 為什麼我無法在 Search Console 深入分析中查看 Google Analytics 資料？

只要將 Google Analytics 與 Search Console 正確建立關聯，您就能取得更多深入分析資料，這有助於瞭解內容成效；但如果您沒有建立關聯，則只能存取 **Google 搜尋資訊卡**。

如果 Google Analytics 資料無法顯示在 GSC 深入分析中，可能是以下幾個原因導致：

1. **您的 GSC 資源並未與 Google Analytics 資源建立關聯**：請造訪說明中心，瞭解[如何建立關聯](https://support.google.com/webmasters/answer/9419894?hl=zh-tw#analytics)。特別是如果您在 GSC 上對 HTTP 和 HTTPS 流量分別都設有資源，請務必為流量最高的資源建立關聯，或考慮[驗證網域資源](https://support.google.com/webmasters/answer/9008080?hl=zh-tw#domain_name_verification)，將所有流量集中在同一處。請注意，您目前還無法連結 [Google Analytics 4](https://support.google.com/analytics/answer/10089681?hl=zh-tw) 資源，但我們正在設法解決這個問題。
2. **您的 Google Analytics 權限不足**：如果 GSC 資源已與 Google Analytics 資源建立關聯，但您仍然無法查看 Google Analytics 資料，請檢查您是否具備[讀取及分析權限](https://support.google.com/analytics/answer/2884495?hl=zh-tw)，可以存取相關聯的 Google Analytics 資源。
3. **您在 GSC 中選取的 Google Analytics 資料檢視有誤**：GSC 深入分析會在相關聯的資源下，列出特定 Google Analytics 資料檢視的 Google Analytics 資料。如果該資源下沒有任何資料檢視，我們就無法填入資料。您可以在 Search Console 的[關聯頁面](https://search.google.com/search-console/settings/associations?hl=zh-tw)中查看或變更所選的資料檢視。

### 為什麼 Google Analytics 與 Search Console 深入分析顯示的資料各不相同？

首先，請務必要瞭解 Google Analytics 和 GSC 資料在許多方面都不相同，詳情請參閱這篇[說明中心文章](https://support.google.com/analytics/answer/1308626?hl=zh-tw#diff)。
在這兩者中，其中一項代表 Google 搜尋中的活動，另一項則代表使用者在網站上的行為，因此資料的定義並不一樣。此外，請特別注意下列幾點：

* **網頁標題和網址：**GSC 中的其他報告是以網址為根據，而 GSC 深入分析使用的是 Google Analytics 的網頁標題維度。每個網頁標題可能都有多個網址；GSC 深入分析會擷取最重要的標準網址，藉此擷取 Google 搜尋資料。
* **日期範圍：**GSC 深入分析會顯示過去 28 天的 Google Analytics 資料 (最後一天可能使用部分的資料)，這些資料有時會和前一個 28 天比較。Google Analytics 和 GSC 的預設時間範圍不同，因此比較時請務必檢查日期是否相同。另請注意，雖然您可以在 Google Analytics 上設定時區，但 GSC 深入分析一律會使用太平洋夏令時間，因此在比較時，某個特定日期可能還是會有所不同。
* **指標：**GSC 深入分析結合了 Google Analytics 指標 (網頁瀏覽次數、平均網頁停留時間) 和 Google 搜尋指標 (點擊次數、平均排序)。這些指標代表您網站的不同面向，因此計算方式也不一樣。

### Search Console 深入分析如何選擇「新內容」？

![Search Console 深入分析的新內容資訊卡](https://developers.google.com/static/search/blog/images/search-console-insights-new-content.png?hl=zh-tw "Search Console 深入分析的新內容資訊卡")

**新內容資訊卡**會顯示過去 28 天內，網站中有哪些網頁第一次有人瀏覽。此外，我們也可能根據各個標題，顯示主要標準網址的熱門搜尋查詢。清單中的內容會依回訪率排序，而且都必須至少獲得幾次瀏覽才能顯示在清單中。以下是我們用於填入這張資訊卡的 3 種主要資訊：

* 首先，我們會檢查過去 28 天內曾獲得流量，但前一年並未獲得任何流量的網頁標題。
* 我們會採用多項規則來清理資料，並過濾較不可能是新內容的網頁；例如標題異動、評論網頁、內部搜尋結果網頁等等。
* 我們會將同一個內容的翻譯版本濾除，保留成效最佳的標題。此外，為避免與 Google Analytics 介面的指標混淆，我們不會匯總翻譯網頁的指標。

如果我們沒有為您的新內容產生報告，並不代表該內容沒有 Google Analytics 流量，也不代表內容未編入索引；GSC 深入分析可以顯示從 Google Analytics 提取資料時未編入索引的內容。另請注意，新內容並不取決於第一個檢索時間，您的內容無須經過檢索或編入索引，就能顯示在資訊卡中。

### Search Console 深入分析如何選擇「最熱門的內容」？

![Search Console 深入分析的最熱門的內容資訊卡](https://developers.google.com/static/search/blog/images/search-console-insights-most-popular-content.png?hl=zh-tw "Search Console 深入分析的最熱門的內容資訊卡")

**最熱門的內容資訊卡**會根據過去 28 天內的網頁瀏覽次數，顯示成效最佳的網頁標題。此外，我們也可能根據各個標題，顯示主要標準網址的熱門搜尋查詢。如要查看這項內容的其他 Google 搜尋資料，請按一下標題並細查網頁總覽。

如果網址不在相關聯的 GSC 資源之下，我們將無法提供 Google 搜尋資料。

### Search Console 深入分析如何選擇來自其他網站的推薦連結？

![Search Console 深入分析的推薦連結資訊卡](https://developers.google.com/static/search/blog/images/search-console-insights-referring-links.png?hl=zh-tw "Search Console 深入分析的推薦連結資訊卡")

**來自其他網站的推薦連結資訊卡**會顯示使用者是如何利用從其他網站連至您的內容的網址，來瀏覽您網站的內容。

這份報告的目的是要為您提供 Proxy，說明特定推薦網頁產生的入站次數。在 Google Analytics 中，當您查看來自特定參照連結網址的流量時，範圍會包含目前工作階段的所有網頁瀏覽次數。而在 GSC 深入分析中，對於特定參照連結網址的各個連入工作階段，我們只會計算為一次網頁瀏覽；也就是說這張資訊卡顯示的流量，只是您習慣在 Google Analytics 中看到的參照連結網址流量的一部分。

請注意，這個邏輯不適用於**主要流量管道資訊卡**；與參照連結網址管道相比，**推薦連結資訊卡**中的網頁瀏覽次數通常會比較低。

### Google 搜尋資訊卡中的點擊次數怎麼會低於網頁瀏覽次數？

點擊次數之所以比網頁瀏覽次數低，主要有以下三個原因：

* 每次點擊都可以觸發多次網頁瀏覽，工作階段期間的其他網頁瀏覽次數也會歸到「google/隨機」中。進一步瞭解[工作階段的定義和分類方式](https://support.google.com/analytics/answer/2731565?hl=zh-tw)。
* 「google/隨機」的 Google Analytics 網頁瀏覽量，所含的途徑比網頁搜尋結果 (例如 Google 探索、Google 圖片搜尋和影片搜尋) 還多。
* Google Analytics 和 GSC 不一定會顯示同一組網頁的報告。舉例來說，您的 GSC 帳戶可能只包含您的 HTTP 網頁，而您選擇的 Google Analytics 資料檢視則提供了 HTTP 和 HTTPS 的相關報告。

### GSC 深入分析資訊卡中的各種標記代表什麼意義？

我們在 GSC 深入分析上推出的標記功能，有助於您將注意力放到資料中有趣的模式上。目前共有三種標記：

1. **高平均停留時間**：與網站上其他內容相比，這類內容擁有高平均停留時間。這可能是您的目標對象認為吸引人的內容。
2. **前 5 大熱門搜尋結果**：在最近 28 天內，您的內容在 Google 搜尋 (「隨機」) 上針對特定查詢的平均排名不超過第 5 名。
3. **熱門 x%**：代表過去 28 天與先前成效的比較結果。
   這個標記只會在趨勢大幅高於一般網站趨勢時顯示。

## 進一步瞭解資料、尋找提示及查看其他資源

如要進一步瞭解 GSC 深入分析提供的各種資訊卡，請點選下方螢幕截圖中所示的「帽子」圖示。您隨後即可查看資料的其他背景資訊，並取得如何解讀這些資料的提示。舉例來說，我們會簡述圖表中的變化代表什麼涵義，並定義圖表和資料表中使用的指標。

![Search Console 深入分析的「帽子」圖示](https://developers.google.com/static/search/blog/images/search-console-insights-education.png?hl=zh-tw "Search Console 深入分析的「帽子」圖示")

如有任何問題或意見，請按一下 GSC 深入分析中的 [提供意見] 按鈕、透過 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡，或是前往 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)提問。

發文者：Search Console 團隊成員 Maya Mamo 和 [Daniel Waisberg](https://www.danielwaisberg.com)
