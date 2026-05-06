# 第一屆 Virtual Webmaster Unconference 的經驗分享
- **發佈日期**: 2020-09-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/09/sharing-what-we-learned-on-first?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
這篇網誌文章已發布一段時間。部分資訊可能已經過時，例如圖片可能會有缺漏，連結也可能失效。如要瞭解即將舉辦的活動，請前往新版 [Search Central Unconference 頁面](https://developers.google.com/search/events/search-central-live?hl=zh-tw)。

2020 年 9 月 15 日，星期二

第一屆 [Virtual Webmaster Unconference](https://goo.gle/VirtualWebmasterUnconference) 已於 8 月 26 日圓滿落幕。我們先前曾承諾會分享在活動中的主要發現與結論，因此現在就在此提供這些內容。

## 活動進行得如何？

此次活動是一次小規模測試，目的是瞭解 a) 大家是否願意參加非傳統形式的活動；以及 b) 社群是否會積極參與討論。

對於第一個問題，我們發現大家的參與意願超乎預期地高，這讓我們更有動力在日後繼續推出並改善這類活動。儘管很多人都因為沒有收到邀請而感到失望，不過特意將活動控制在較小規模的結果，恰好回答了前述的第二個問題：縮減規模讓大家能更自在地討論。我們認為，有主題演講、分組討論等環節的傳統研討會比較適合參與者眾多的場合；由於 Virtual Webmaster Unconference 的目標是聆聽參與者的聲音，所以不適合讓太多人參加。令人喜悅的是，我們確實在活動中聽見了參與者的聲音。

## 我們在這些環節中有何收穫？

本次活動共有 17 個環節。我們將這些環節分成兩部分，分別在區塊 1 和區塊 2 進行。活動中有很多精彩討論，有些團隊採納了社群的建議來改進產品和功能，也有團隊利用這段時間交流想法和資訊。

### Google 內部團隊的最大領悟為何？

大家在各環節中多次提到「Core Web Vitals」，這讓我們的團隊意識到使用者仍然不熟悉這些指標，需要循序漸進地掌握這些指標。此外，雖然 Google 已提供相關[資源](https://web.dev/articles/vitals?hl=zh-tw)，但很多使用者仍無法順利理解，希望 Google 另外提供適合非專業使用者的說明文件。我們還在「探索」環節分享了最近的[說明文件更新資訊](https://developers.google.com/search/docs/advanced/mobile/google-discover?hl=zh-tw)。

Google 說明文件的尋獲度也是一個值得關注的議題。參與者提到，我們應該將官方的搜尋說明文件集中於一處，好讓使用者更容易找出需要的資訊，而且這對於總是不知道該搜尋什麼的新手特別有幫助。

在「Search Console 腦力激盪」環節中，參與者就實用的功能 (例如每月成效電子郵件) 和對 Search Console 使用者來說不太實用的功能 (例如訊息收發頻率) 提供了寶貴意見。

在「WordPress 專用 Site Kit」環節中，我們發現使用者在看到 Analytics 和 Search Console 的數據不一致時會感到困惑。結構化資料團隊發現，他們仍需要重點釐清[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)和[結構化資料測試工具](https://developers.google.com/search/docs/advanced/structured-data?hl=zh-tw)之間一些易於混淆的地方。

「電子商務」環節得到的結論是，大家對於小型商家在線上零售領域面臨的激烈競爭有諸多顧慮。若要在與大型零售商和市集的競爭中占據優勢，電子商務商店可以試著將重點放在單一小眾市場，進而將所有排名信號與特定主題聯繫起來。此外，小型商店還可以透過提供專業知識來創造更多獨特價值，比如製作傳達產品相關主題資訊的內容，從而提高自身的可信度，強化與目標對象和 Google 之間的關聯性。

### 參加者主要有哪些技術上的收穫？

「Java 指令碼問題」環節得到的結論是，第三方指令碼潛變會對開發人員造成問題。而在「趣味指令碼！」環節中，參與者看到了指令碼是如何取得資料集，並將資料集轉化為可做為行動依據的深入分析資料。活動中分享的資源包括[程式碼研究室](https://codelabs.developers.google.com/?hl=zh-tw)和[數據分析](https://developers.google.com/apps-script/reference/data-studio?hl=zh-tw)，前者是快速獲取知識的最佳平台，後者則適合對應用程式指令碼感興趣或想自行建構連接器的人使用。另外，您也可以先從 [Google Apps Script 影片庫](https://developers.google.com/apps-script/guides/videos?hl=zh-tw)尋找靈感。

### 破除的迷思

我們還在幾個環節中破除了一些常見迷思。例如，行動版內容優先索引系統沒有固有的排名優勢，從技術層面改進網站並不代表網站實際上變得更好，因為內容才是關鍵。

在「破除廣告和搜尋引擎最佳化 (SEO) 迷思」環節中，我們澄清了下列錯誤論述：

1. Google Ads 廣告和放送 Google Ads 廣告的網站有較高排名 (錯誤)
2. 其他公司的廣告會導致停留時間較短/跳出率較高，從而導致排名降低 (錯誤)
3. 網站上是否有廣告會影響搜尋引擎最佳化 (SEO) 作業 (錯誤)

## 為社群服務，與社群同在

此次活動採用互動形式，因此我們非常高興看到大家積極展開討論，分享具有建設性的意見，讓談話更有成效。我們也想藉此機會向在每個環節中協助我們的產品專家致上謝意，他們分別是 (下依姓名字母排序) [Ashley Berman-Hale](https://twitter.com/bermanhale)、[Dave Smart](https://twitter.com/davewsmart)、[Kenichi Suzuki](https://twitter.com/suzukik)、[Mihai Aperghis](https://twitter.com/mihaiaperghis) 以及盡心盡力的眾多 Google 員工。

## 對未來的期許

正如我們之前提到的，此次活動在社群中引起了熱烈反響。我們發現這種形式的活動可以滿足讓 Google 員工和社群進行有意義交流的需求，因此很高興地告訴大家：我們將來還會再次舉辦這樣的活動！

我們正在根據大家的意見探索各種方案，研究將來舉辦活動的時區、語言和頻率。此次試行活動讓我們獲益良多，我們會充分利用這些寶貴經驗，在未來舉辦能讓更多人參加，也更有趣的 Virtual Webmaster Unconference。

除了採取各種措施完善這種活動形式外，我們也會聆聽大家的意見，盡快提供有關線上 Webmaster Conference (常規形式活動) 和其他主題的資訊。如要即時獲得最新消息，請務必在 [Twitter](https://twitter.com/googlesearchc)、[YouTube](https://www.youtube.com/@GoogleSearchCentral?hl=zh-tw) 和這個[網誌](https://developers.google.com/search/blog?hl=zh-tw)上追蹤我們，以免錯過有關日後活動或其他新聞的最新資訊。

再次感謝您的大力支持！

發文者：Virtual Webmaster Unconference 團隊的 [Aurora Morales](https://developers.google.com/search/blog/authors/aurora-morales?hl=zh-tw) 和 [Martin Splitt](https://developers.google.com/search/blog/authors/martin-splitt?hl=zh-tw)
