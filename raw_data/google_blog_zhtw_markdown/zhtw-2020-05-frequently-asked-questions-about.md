# JavaScript 和連結的相關常見問題與解答
- **發佈日期**: 2020-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/05/frequently-asked-questions-about?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 5 月 26 日，星期二

每天我們都會從[網站管理員諮詢時間](https://youtube.com/channel/UCWf2ZlNsCGDS89VBF_awNvA/community?hl=zh-tw)、各種會議、[網站管理員論壇](https://support.google.com/webmasters/community?hl=zh-tw)以及 [Twiiter](https://twitter.com/googlesearchc) 上收到不計其數的問題。「連結」是這些問題中最常提到的主題之一，尤其是透過 JavaScript 產生的連結。

在近期的《[Webmaster Conference Lightning Talks](https://www.youtube.com/playlist?list=PLKoqnv2vTMUNf6w9wUu7RgxHkaTrq2Zpf&hl=zh-tw)》系列影片中，我們解答了有關連結和 JavaScript 最常見的問題：

**注意**：這部影片也提供多種語言字幕。

由於在影片首播時，我們也在問與答時段收到了社群提出的一些問題，因此我們決定在下方發布這些問題和我們的回答，同時也解答有關連結和 JavaScript 的其他常見問題。

## Googlebot 能夠找到哪些類型的連結？

Googlebot 會剖析網頁的 HTML 來找出連結，以便發掘出可以檢索的相關網頁網址。為了讓 Googlebot 找到這些網頁，您必須遵循[網站管理員指南的連結規範](https://developers.google.com/search/docs/advanced/guidelines/links-crawlable?hl=zh-tw)，將您的連結設為實際的 HTML 連結。

## Googlebot 能夠辨識哪些類型的網址？

Googlebot 會從連結的 href 屬性中擷取網址，然後將網址排入待檢索的佇列。這表示您的網址必須可供解析。簡單而言，輸入瀏覽器的網址列後可以正常開啟，這樣 Googlebot 就能辨識。如需更多資訊，請參閱[網站管理員指南的連結規範](https://developers.google.com/search/docs/advanced/guidelines/links-crawlable?hl=zh-tw)。

## 我可以使用 JavaScript 建立和插入連結嗎？

可以，只要這些連結符合[網站管理員指南](https://developers.google.com/search/docs/advanced/guidelines/links-crawlable?hl=zh-tw)和上文列出的條件就沒問題。

Googlebot 會在轉譯網頁時執行 JavaScript，也會探索透過 JavaScript 產生的連結。值得一提的是，Googlebot 可能會在執行 JavaScript 之前「和」之後分別進行一次連結探索作業。因此，如果將連結加入初始伺服器回應中，Googlebot 就能快一點發現連結。

## Googlebot 能解讀片段網址嗎？

我們在技術上支援片段網址 (又稱「雜湊網址」)，不過 Googlebot 檢索此類網址的方式可能與您的預期不同。

片段網址應該是用來定位到網頁中的特定內容，而如果是這種常規用途，Googlebot 在解讀上完全沒有問題。

但有時候，開發人員會決定**使用片段網址搭配 JavaScript 載入內容，而這種方式顯示的內容與沒有片段網址的網頁並不相同**。由於這並非片段網址原先設定的用途，Googlebot 便無法解讀。請參閱 [JavaScript 搜尋引擎最佳化 (SEO) 指南](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=zh-tw#use-history-api)，瞭解如何改用 History API。

## Googlebot 是否仍採用 AJAX 檢索配置？

[我們在很久以前就淘汰了 AJAX 檢索配置](https://developers.google.com/search/blog/2015/10/deprecating-our-ajax-crawling-scheme?hl=zh-tw)，請勿在您的網頁使用這種配置。

建議運用 [History API](https://developer.mozilla.org/en/docs/Web/API/History)，並將您的網頁應用程式遷移到非以片段網址載入相異內容的網址。

## 敬請密切注意《Webmaster Conference Lightning Talks》的後續更新

儘管本文靈感是來自《[Webmaster Conference Lightning Talks](https://www.youtube.com/playlist?list=PLKoqnv2vTMUNf6w9wUu7RgxHkaTrq2Zpf&hl=zh-tw)》系列第一集，但請務必[訂閱我們的 YouTube 頻道](https://www.youtube.com/channel/UCWf2ZlNsCGDS89VBF_awNvA?sub_confirmation=1&hl=zh-tw)，後續會有更多精彩影片上線！強烈建議您加入我們的 YouTube 首播活動，每一集都會有聊天室和問答時段，歡迎參加！

如果想要觀看更多《Webmaster Conference Lightning Talks》精彩內容，不妨看看 [Google 營利服務政策](https://www.youtube.com/watch?v=bB2FrOyKKuA&%3Blist=PLKoqnv2vTMUNf6w9wUu7RgxHkaTrq2Zpf&hl=zh-tw)影片，並訂閱我們的頻道，密切注意最新一集的推出時間！

您可以加入網站管理員社群，和其他人一起觀看即將推出的影片首播，並參與 YouTube 上的留言討論！

發文者：Google 搜尋關係團隊的 Googlebot 專家 [Martin Splitt](https://50linesofco.de)
