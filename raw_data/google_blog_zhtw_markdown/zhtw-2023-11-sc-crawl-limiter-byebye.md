# Search Console 中的檢索頻率限制工具即將淘汰
- **發佈日期**: 2023-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/11/sc-crawl-limiter-byebye?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 11 月 24 日，星期五

Search Console 中的檢索頻率限制工具將於 2024 年 1 月 8 日淘汰。這項工具[已推出超過十年](https://developers.google.com/search/blog/2008/12/more-control-of-googlebots-crawl-rate?hl=zh-tw)，但隨著檢索邏輯和發布商可使用的其他工具與日俱進，檢索限制工具的實用性已日益消散。

Googlebot 是根據網站的處理方式，或更具體地說，根據伺服器處理網站的方式，回應 Googlebot 的 HTTP 要求。舉例來說，如果伺服器持續傳回一系列網址的 HTTP `500` 狀態碼，Googlebot 會自動執行，且幾乎立即降低檢索速度。同樣地，如果要求的回應時間大幅變長，Googlebot 就會自動降低速度。如果您遇到檢索作業異常繁重，導致網站無法自行管理，請參閱這篇[說明文章](https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate?hl=zh-tw)。

相較之下，頻率限制工具的影響速度較慢；實際上，可能需要超過一天的時間才會針對檢索作業套用新的限制。不過，幸好網站擁有者很少必須採用這項工具；如有必要使用，在許多情況下，使用者也都會將檢索速度設為最低。淘汰檢索頻率限制工具後，我們也會將最低檢索速度設為較低的頻率，與先前的檢索頻率限制相近。也就是說，當 Google 搜尋熱度低時，如果某些網站擁有者過去設定的搜尋熱度偏低，檢索器就不會浪費網站頻寬，而照樣能繼續採用這些設定。

自動化檢索頻率處理作業日趨進步，而且我們一向秉持著為使用者提供簡便的工具，因此才會在 Search Console 中淘汰這項工具。我們會保留 Googlebot [回報表單](https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate?hl=zh-tw)，以便回報異常的 Googlebot 活動和緊急情況。但請注意，降低檢索頻率的最快方法就是透過伺服器回應指示 Googlebot，詳情請參閱[說明文件](https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate?hl=zh-tw)。

如有任何問題或意見，歡迎透過 [Google 搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)告訴我們。

發文者：[Gary Illyes](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw) 和 [Nir Kalush](https://developers.google.com/search/blog/authors/nir-kalush?hl=zh-tw)
