# Google 搜尋中心一年回顧透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2021-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/11/one-year-of-search-central?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 11 月 17 日，星期三

我們在一年前[推出了新網站](https://developers.google.com/search/blog/2020/11/goodbye-google-webmasters?hl=zh-tw)，同時宣布將放棄「Google 網站管理員」這個令人喜愛的名稱，改以「Google 搜尋中心」之名再次啟航。回首 2020 年初，我們曾滿懷希望地想把所有內容重新彙整到一個好找的地方，但這個夢想很快就被現實要處理的[大量工作](https://search-off-the-record.libsyn.com/launching-google-search-central-step-by-step)澆了冷水 (我必須說，工作量真的很驚人)。

![Googlebot 和 Crawley 歡慶 Google 搜尋中心邁入一週年](https://developers.google.com/static/search/blog/images/one-year-of-google-search-central.png?hl=zh-tw)

## 自 Google 搜尋中心推出以來，我們都在做些什麼？

我們在今年與內部搜尋引擎最佳化 (SEO) 團隊合作改進了內容，還撰寫了大量全新說明文件、遷移了 13 個語言版本的網誌，並在首頁製作了新的檢查清單。

### 與搜尋引擎最佳化 (SEO) 專員合力改善內容

為改善 Google 搜尋中心的內容，我們求助了自家的 SEO 專員。他們提供的協助包括監控涵蓋上千個網址的網站遷移作業、找出損壞的重新導向，以及確保舊網站的流量妥善轉移至新網站。另外，我們也與他們聯手改進了 200 多個頁面的[標題元素](https://developers.google.com/search/docs/appearance/title-link?hl=zh-tw)和[說明](https://developers.google.com/search/docs/appearance/snippet?hl=zh-tw)。

我們先從讀者最常瀏覽的高優先度文件著手，這些也是我們認為應該會獲得更多流量的文件。不過，我們也想針對某些情況「去除」流量最佳化行為 (比如，有搜尋者反映想移除網頁，我們的頁面提供的卻是[讓網站擁有者移除網頁](https://developers.google.com/search/docs/crawling-indexing/remove-information?hl=zh-tw)的說明)。

> 我們難得有機會請 John、Lizzi 偕同搜尋關係團隊協助處理 SEO 事宜。平心而論，要協助權威性的 SEO 內容依照 Google 的搜尋引擎最佳化 (SEO) 指南進行 SEO 作業已經是很不可思議的任務。但更不可思議的是，我們甚至還透過 Google Meet 向 John、Lizzi 及搜尋關係團隊的其他人諮詢了 SEO 事宜。儘管如此，我們當時仍非常期待接受這樣的挑戰與機會。
>
> 在 Google，處理 SEO 就是要紮紮實實地下功夫，即使對象是所有網站的搜尋中心也不例外。我們對這項專案採取的做法，就和處理 Google 其他的行銷網站、內容網站和產品網站一樣。通常其他業界人士也是奉行相同的做法，畢竟大家都是依照各種指南、最佳做法和經驗行事。不過，為了嚴格區分 Google 搜尋和 Google 的 SEO 作業人員，我們特別限制了自身能夠使用的工具、資料和資訊，以確保不會取得不公平的優勢。
>
> 協助搜尋中心遷移就和我們先前協助的其他遷移作業大同小異。我們已針對重要頁面完成關鍵字研究和中繼資料最佳化、協助處理重新導向對應與品保事宜，還設定了 Google 數據分析資訊主頁，以便監控進度及執行遷移後分析。如您所知，就是 SEO 遷移工作檢查清單上通常會有的項目。
>
> 觀察 SEO 社群在遷移後的反應也很有趣。我們不僅活躍於 Twitter，也訂閱了所有 SEO 出版品 (畢竟我們也是普通的 SEO 專員)，因此當我們看到大家的意見回饋和各類文章、聽到[《Search Off The Record》Podcast 節目](https://pod.link/1512522198)的大力宣傳，感覺真的十分美妙！
>
> 感謝有幸與 Lizzi、John 以及搜尋關係團隊的其他成員合作。我們期盼往後能繼續共事，幫助 [Google 搜尋中心](https://developers.google.com/search?hl=zh-tw)成長茁壯 (讓我厚著臉皮放個內部連結)。
>
> - Growth Lab SEO 團隊 (Google 內部的 SEO 團隊) 的 Jason Stevens

### 新增更多說明文件

我們重新調整了索引和檢索說明文件的架構，包括將內容按主題分門別類、發布全新說明文件及改寫下列主題的指南：

* 簡化 [robots.txt 頁面說明](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=zh-tw)，更清楚地介紹 robots.txt 和這個檔案的預定用途，並擴充有關[建立](https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt?hl=zh-tw)及[更新](https://developers.google.com/search/docs/crawling-indexing/robots/submit-updated-robots-txt?hl=zh-tw) robots.txt 檔案的操作說明。
* 新增有關 [HTTP 狀態碼、網路錯誤和 DNS 錯誤對 Google 搜尋有何影響](https://developers.google.com/search/docs/crawling-indexing/http-network-errors?hl=zh-tw)的引導說明。
* 大幅擴充[重新導向指南](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=zh-tw)的內容，介紹各種類型的重新導向及其對 Google 搜尋的影響。
* 撰寫有關 [Google 搜尋運算子](https://developers.google.com/search/docs/monitor-debug/search-operators?hl=zh-tw)的全新說明文章。
* 發布一系列關於[在 Google 搜尋中經營電子商務](https://developers.google.com/search/docs/specialty/ecommerce?hl=zh-tw)的全新指南。

### 遷移 13 種語言版本的網誌

我們在幾週前將 13 個語言版本的網誌全數遷移並重新導向完成，範圍可追溯至 2005 年發布的內容。我們已將數千篇文章對應至英文版，方便讀者在瀏覽內容時切換不同語言。這種同步處理方式讓我們得以使用更多語言提供經典雋永的文章，保存並持續提供前人翻譯的內容，也讓使用者更容易發掘我們早已發布的內容。

**您知道我們的內容已經翻譯成 18 種語言了嗎？**歡迎使用語言下拉式選單切換語言。

### 首頁的全新小工具

我們最近也在首頁發布了新的小工具，這項小工具會根據使用者選取的角色推薦不同文章，以更具互動性的方式幫助使用者探索如何提升在 Google 搜尋中的曝光度。

![Google 搜尋中心到達網頁上的互動式檢查清單](https://developers.google.com/static/search/blog/images/interactive-learning-path.gif?hl=zh-tw)

為了建立學習路徑，我們分析了自身的目標對象，結果發現造訪首頁的使用者不是為了搶先掌握情報，就是為了全面瞭解更多資訊，他們不像那些有具體的問題的使用者會直接前往深層網址。因此，我們希望藉由這個互動式學習路徑，幫助新使用者以更有效率的系統化方式在 Google 搜尋中心瀏覽內容，無論是 SEO 專員、數位行銷人士還是業主，人人都能輕鬆獲得自己需要的資訊。

很多 SEO 專員也反映希望有適合非 SEO 專業人士的資源。您可以分享特定學習路徑或網站擁有者的檢查清單，只要[在網址中使用預先定義的 `?card=owner` 參數](https://developers.google.com/search/?card=owner&hl=zh-tw)即可。簡易的圖像可讓人以更直觀的方式輕鬆瞭解搜尋功能。目前我們仍在持續改進這項小工具，所以您可能在接下來幾個月看到更多變化和改善項目。

## 新網站有哪些更優異的表現？

將 2021 年 1 月至 2021 年 10 月期間的資料與去年同期相比，我們發現遷移至 Google 搜尋中心的網址增加了 240% 的點擊次數。下方的圖表顯示了我們的內容在遷移前後三個月內的點擊次數 (遷移前內容分散在各處，遷移後則集中於一處)：

![圖表中顯示了 Google 搜尋中心內容在遷移前後三個月內的點擊次數](https://developers.google.com/static/search/blog/images/pre-post-migration-chart.png?hl=zh-tw)

經過遷移和重新設計，搜尋中心網誌的成效也優於網站管理員中心網誌：遷移三個月過後，搜尋中心網誌的點擊次數提高了 159%，曝光次數提高了 23%。由於我們目前只完成 13 個語言版本的遷移作業，所以這份資料只涵蓋英文版的網站管理員中心網誌。我們會持續監控搜尋中心網誌的流量，觀察遷移不同語言版本的網誌對於網站流量的影響。

另外，從 Search Console 說明中心遷移過來的文章也有點擊次數增加的情形。舉例來說，下列主題的成效都有所提高：Sitemap (點擊次數增加 99%)、robots.txt (點擊次數增加 27%)、HTTPS (點擊次數增加 66%)。

## 順利達成與未能實現的目標

我們注意到使用者在一個月內就開始使用「Google 搜尋中心」這個新名稱。我們的 SEO 專員運用了[關鍵字規劃工具](https://ads.google.com/home/tools/keyword-planner/?hl=zh-tw)來監控改名對搜尋熱度的影響，結果發現在我們推出並宣傳 Google 搜尋中心之後，「Google 搜尋中心」的搜尋熱度隨即超過了「Google 網站管理員中心」(增加 250%)。

另一件好事是，在新網站發布內容已變得容易許多。隨著我們團隊的貢獻者日漸增加，往後將有更多內容以我們支援的所有語言無縫接軌地陸續發布。不像過去網誌文章的翻譯可能要費時數月，現在新網站在幾天內就能提供翻譯內容。

不過，和實施其他重大計畫一樣，不是所有事情都如預期順利：

* 遷移各種語言版本的網誌。網址對應工作所耗費的時間超乎預期，我們甚至在過程中遇到了其他問題，比如失效的 Python 指令碼。
* 我們未能完成一年前推出網站時所規劃的全部事項 (比如首頁上的檢查清單、遷移網誌，以及願望清單上的其他項目)。

## 我們的經驗教訓

對於團隊來說，執行全站遷移與品牌重塑專案是一次大開眼界的體驗，以下是我們最深刻的心得感想：

* 語言好難。遷移單一語言的網站已足夠困難，更何況還有 13 個語言版本的本地化網站，每個版本都有專屬的網址模式，需要分別透過 JavaScript 重新導向，這一切都令人頭痛。
* 我們的 Dogfood 測試完全失準：事實證明 [JavaScript 重新導向](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=zh-tw#jslocation)不比 [meta 重新導向](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=zh-tw#metarefresh)來得差。
* RSS 仍然很受歡迎，所以我們必須將 RSS [加入新網誌](https://feeds.feedburner.com/blogspot/amDG)。
* 「去搜尋引擎最佳化」就如字面般奇怪，但若想「確實」獲得良好流量，這件事便勢在必行。
* 與 SEO 專員合作處理介紹 SEO 的網站是一件令人傷透腦筋的事，畢竟我們要改進的項目就是提供這方面資訊的平台。

## 我們以後還會這麼做嗎？

Lizzi 對 Gary 問了這個問題，您知道他的回答是什麼嗎？「絕對不會。」

## 我們的下一步

隨著今年邁入尾聲，我們開始思考 Google 搜尋中心網站將在 2022 年帶來哪些新東西。您認為我們明年應該撰寫哪些方面的文章，或是我們的網站應該新增哪些功能嗎？只要在 [Twitter](https://twitter.com/search?q=%23SearchCentral2022&src=typed_query) 發表訊息並加上 #SearchCentral2022 主題標記，即可將您的意見告訴我們。

發文者：搜尋關係團隊的 [Lizzi Sassman](https://www.okaylizzi.com/+) 和 [Gary Illyes](https://garyillyes.com/+)
