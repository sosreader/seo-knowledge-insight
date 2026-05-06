# 行動版內容優先索引系統隆重登場，感謝您的支持與愛護
- **發佈日期**: 2023-10-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/10/mobile-first-is-here?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 10 月 31 日，星期二

從開始到現在，這是一趟漫長的旅程。
很高興在此宣布，行動版內容優先索引系統現已開發完成。

![Googlebot 和 Crawley 拿著紅色手機，正在慶祝](https://developers.google.com/static/search/blog/images/2023-mfi-googlebot.png?hl=zh-tw)

2015 年起，Google 搜尋開始將重點放在行動裝置，推出[適合行動裝置的更新](https://developers.google.com/search/blog/2015/04/rolling-out-mobile-friendly-update?hl=zh-tw)。
2016 年，我們[開始研發行動版內容優先檢索及建立索引系統](https://developers.google.com/search/blog/2016/11/mobile-first-indexing?hl=zh-tw)。
透過這套系統，Google 搜尋會將特定內容編入索引，讓使用者透過手機存取網站時查看。
對於 Google 的基礎架構來說，針對智慧型手機進行檢索及建立索引是一項重大改變，對於公開網路而言也是如此：行動版網頁現在必須如同對應的電腦版網頁一樣完備。

過去幾年來，行動版網站的流量持續成長。在某些地區，使用者幾乎只用手機上網。
感謝各位網站擁有者、搜尋引擎最佳化 (SEO) 專員、網頁開發人員、設計人員和所有網站相關工作者，感謝各位使行動網路蓬勃發展！

## 後續步驟

我們目前知道，少數網站完全無法在行動裝置上運作。
我們看到的錯誤類型，主要有網頁向所有行動裝置使用者顯示錯誤、電腦版網站可以檢索，但行動版網站遭到 robots.txt 封鎖，或是行動網站上的所有網頁都會重新導向至首頁。
這些是 Google 無法解決的問題。
我們會暫時繼續使用原有的電腦版 Googlebot 檢索器檢索這些網站，並且每年會重新評估這份清單數次。
詳情請參閱我們的[行動版內容索引最佳做法](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=zh-tw)。

此外，我們會盡可能持續減少使用原有電腦版 Googlebot 進行檢索的作業。
這有助於網站擁有者和我們節省資源。

## Search Console 異動

改用行動版內容優先索引系統後，我們也會關閉 [Search Console](https://search.google.com/search-console/?hl=zh-tw) 中[設定頁面](https://search.google.com/search-console/settings?hl=zh-tw)的索引檢索器資訊。
由於現在所有在行動裝置上運作的網站，主要都是由行動檢索器進行檢索，因此您不再需要這項資訊。[檢索統計資料報告](https://support.google.com/webmasters/answer/9679690?hl=zh-tw)會顯示網站目前受到檢索的狀況，您想知道的話可以參考。

![Search Console 檢索統計資料的部分螢幕截圖，其中顯示 Googlebot 類型](https://developers.google.com/static/search/blog/images/2023-mfi-sc.png?hl=zh-tw)

Google 很榮幸能與這麼多的網站擁有者合作進行轉換作業，各位的努力讓所有行動裝置使用者 (包括所有檢索器) 更容易存取網路，十分感謝。
謝謝！

發文者：搜尋服務代表 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw) 和 Search Console 的 [Nir Kalush](https://developers.google.com/search/blog/authors/nir-kalush?hl=zh-tw)
