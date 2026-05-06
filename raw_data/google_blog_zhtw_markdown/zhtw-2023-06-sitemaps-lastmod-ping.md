# Sitemap 連線偵測 (ping) 端點即將淘汰
- **發佈日期**: 2023-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
Sitemap 連線偵測 (ping) 端點淘汰作業已完成。

2023 年 6 月 26 日，星期一

[我們在 2005 年推出了 Sitemap 通訊協定](https://googleblog.blogspot.com/2005/06/webmaster-friendly.html)，協助搜尋引擎發現新網址，並針對已找到的網址安排新檢索作業。它是廣受歡迎的通訊協定，已超過 15 年未變更。雖然這個做法依然有用，但有些層面在現今的網際網路環境中已變得較不實用。

為此，我們宣布將全面淘汰 Sitemap 的「連線偵測」端點機制，並針對 `lastmod` 元素提供其他建議用法。

## Sitemap 連線偵測 (ping)

Sitemap 通訊協定定義了[未經驗證的 REST 方法](https://sitemaps.org/protocol.html#submit_ping)，用來將 Sitemap 提交至搜尋引擎。我們的內部研究以及[其他搜尋引擎 (例如 Bing)](https://blogs.bing.com/webmaster/may-2022/Spring-cleaning-Removed-Bing-anonymous-sitemap-submission) 也指出，這類未通過驗證的 Sitemap 所提交的內容目前不太實用。事實上，對 Google 搜尋而言，大部分的提交內容都會成為垃圾內容。因此，我們即將停止支援 Sitemap 連線偵測 (ping)，且端點會在 6 個月後停止運作。您還是可以[透過 robots.txt 和 Search Console 提交 Sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=zh-tw)，但針對已淘汰 REST 端點的 HTTP 要求 (「連線偵測 (ping)」) 會導致 `404` 錯誤。任何使用此端點的現有程式碼或外掛程式都不會導致 Google 搜尋發生問題，您不必進行任何變更 (但使用此端點也沒有任何實用性)。

## `lastmod` 元素

多年來，我們針對所有提供 `lastmod` 元素的網站，觀察此元素實用程度的變化。這可能是已發布的內容類型或內容管理系統的搜尋結果，不過如今 `lastmod` 在許多情況下都很實用，而且我們會將其做為安排檢索網址的信號，檢索我們先前已找到的網址。

`lastmod` 元素必須採用支援的日期格式 (如 [sitemaps.org](https://sitemaps.org/protocol.html#lastmoddef) 所述) 才能發揮作用。Search Console 會在您提交 Sitemap 後立即告知是否採用支援格式。其次，請確保實際情況一致：如果您的網頁在 7 年前有所變更，但您透過 `lastmod` 元素告知我們變更時間是昨天，我們最後就不會再相信您的網頁上次更新時間。

您可以為 Sitemap 中的所有網頁使用 `lastmod` 元素，或者只針對您信任的網頁使用。例如，某些網站軟體可能只會匯總網站的其他頁面，無法輕易判斷首頁或某個類別頁面的上次修改日期。在這種情況下，您可以省略這些網頁的 `lastmod`。

這裡所謂的「上次修改」，事實上指的是上次的**重大**修改。如果 CMS 變更了側欄或頁尾中一段不重要的文字，則您無須更新該網頁的 `lastmod` 值。不過，如果您變更了主要文字、新增或變更結構化資料，或是更新部分連結，請更新 `lastmod` 值。

```
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
      <lastmod>2005-01-01</lastmod>
      <loc>http://www.example.com/</loc>
      <changefreq>monthly</changefreq>
      <priority>0.8</priority>
  </url>
</urlset>
```

包含所有可能元素的簡易 Sitemap 範例；來源：
[sitemaps.org](https://sitemaps.org/protocol.html)

如果仔細查看 Sitemap 程式碼片段中的 `xmlns` 屬性，就會看到 URI 採用的是 HTTP，而非 HTTPS。這種情況很正常：它是針對用來解析 XML 中元素的剖析器的參照。請勿對此提供更多說明文件意見回饋。

## `changefreq` 和 `priority`

Google 依然一律不使用 `changefreq` 或 `priority` 元素。此外，`changefreq` 也與 `lastmod` 有概念重疊。`priority` 元素是很主觀的欄位，依據我們的內部研究，這通常無法準確反映某個網頁相對於網站上其他網頁的實際優先順序。

如要進一步瞭解 Sitemap，請參閱我們的[說明文件](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=zh-tw)和 [sitemaps.org](https://sitemaps.org)；如果您只想與我們討論 Sitemap，可以造訪 [Google 搜尋中心論壇](https://goo.gle/sc-forum)和 [Twitter](https://twitter.com/GoOgLeSeArChC) 與我們交流。

發文者：[Gary Illyes](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw)
