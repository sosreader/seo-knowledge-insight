# 請勿使用 403 或 404 限制檢索頻率
- **發佈日期**: 2023-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/02/dont-404-my-yum?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 2 月 17 日，星期五

過去幾個月來，我們發現網站擁有者和部分內容傳遞聯播網 (CDN) 嘗試使用 `404` 和其他 `4xx` 用戶端錯誤 (但並非 `429`) 試圖降低 Googlebot 檢索頻率的情況有所增加。

這篇網誌文章的簡短版就是：請不要這麼做。歡迎參閱我們的[如何降低 Googlebot 檢索頻率](https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate?hl=zh-tw)說明文件。請閱讀該說明文件並瞭解如何有效管理 Googlebot 的檢索頻率。

## 回歸基本概念：`4xx` 錯誤是用戶端錯誤

伺服器傳回至用戶端的 `4xx` 錯誤是一種伺服器信號，表示用戶端要求在某種程度上發生錯誤。這個類別中的錯誤大都無害，包括「找不到」錯誤、「已禁止」、「我的茶壺」(是的，這是事實)。這些錯誤並不意味伺服器本身有任何錯誤。

唯一的例外是 `429`，這個錯誤代表「太多要求」。這個錯誤是對任何正常運作的漫遊器 (包括備受喜愛的 Googlebot) 發出的明確信號，指出錯誤正導致伺服器超載，因此需要降低執行速度。

## 為什麼 `4xx` 錯誤不利於限制 Googlebot 的檢索頻率 (`429` 除外)

用戶端錯誤就是用戶端發生錯誤。這些錯誤通常不是表示伺服器發生錯誤：不是超載，不是發生重大錯誤且無法回應要求，只是表示用戶端的要求在某些方面有誤。例如，`404` 錯誤不會合理等同於伺服器超載。想像一下這種情況，您的朋友不小心連結到您網站上的錯誤頁面，導致您收到大量的 `404` 錯誤，進而造成 Googlebot 的檢索速度變慢。那真是很糟糕的情況。`403`、`410` 和 `418` 也會相同。

`429` 狀態碼則是明顯的例外，這個錯誤表示「太多要求」。

## `4xx` 錯誤對 Googlebot 的檢索頻率有何限制

所有的 `4xx` HTTP 狀態碼 (`429` 例外) 都會導致您的內容從 Google 搜尋中遭到移除。更糟的是，如果您還使用 `4xx` HTTP 狀態碼提供 robots.txt 檔案，系統會將該檔案視為不存在。如果您有一項禁止檢索的規則，現在 Googlebot 也會知道，這對雙方都不是一件好事。

## 如何以正確的方式降低 Googlebot 的檢索頻率

我們有詳盡的說明文件，說明[如何降低 Googlebot 的檢索頻率](https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate?hl=zh-tw)，以及 [Googlebot (和搜尋索引) 如何處理不同的 HTTP 狀態碼](https://developers.google.com/search/docs/crawling-indexing/http-network-errors?hl=zh-tw)，請務必查看這些說明文件。簡而言之，您可以採取下列任一做法：

* [使用 Search Console 暫時降低檢索頻率](https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate?hl=zh-tw#reduce-with-search-console)。
* 在檢索速度過快時，向 Googlebot 傳回 `500`、`503` 或 `429` HTTP 狀態碼。

如需更多提示或說明，歡迎透過 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡，或前往[說明論壇](https://support.google.com/webmasters/community?hl=zh-tw)發文提問。

發文者：[Gary Illyes](https://garyillyes.com/+)
