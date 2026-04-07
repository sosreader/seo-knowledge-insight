# 將網頁體驗納入電腦版網頁排名考量的更新推出時程
- **發佈日期**: 2021-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/11/bringing-page-experience-to-desktop?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 11 月 4 日，星期四

這篇網誌文章已發布一段時間。部分資訊可能已經過時，例如圖片可能會有缺漏，連結也可能失效。請參閱有關[網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)的最新說明文件。

在 2021 年 I/O 大會上，我們[透露](https://youtu.be/h00kn5J-F2Q?t=430)了要將網頁體驗納入電腦版網頁排名考量的計畫。今天，我們將公布更多詳情，包括相關變更的推出時程。這項變更是 2021 年 6 月至 8 月間行動版網頁[網頁體驗更新](https://developers.google.com/search/blog/2021/04/more-details-page-experience?hl=zh-tw)的後續更新。

## 變更將於 2022 年 2 月開始推出

我們將從 2022 年 2 月開始將網頁體驗納入電腦版網頁的排名系統，推出程序將於 2022 年 3 月底前完成。這項變更將與今年初推出的行動版網頁更新採用相同的[網頁體驗信號](https://developers.google.com/search/docs/guides/page-experience?hl=zh-tw)。我們也計劃在網頁體驗成為電腦版網頁排名信號之前推出一份 Search Console 報告，協助網站擁有者瞭解其電腦版網頁在網頁體驗方面的表現。

這項更新意味著，[LCP](https://web.dev/articles/lcp?hl=zh-tw)、[FID](https://web.dev/articles/fid?hl=zh-tw) 和 [CLS](https://web.dev/articles/cls?hl=zh-tw) 這三項 [Core Web Vitals 指標](https://web.dev/articles/vitals?hl=zh-tw)及其相關門檻將適用於電腦版網頁排名系統。其他面向的網頁體驗信號 (例如 HTTPS 安全性和排除插頁式廣告干擾) 也包含在這次更新中；不過，行動裝置相容性信號只會影響行動版網頁排名，對電腦版網頁則沒有影響。如果某個網站採用[獨立的電腦版網址和行動版網址](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=zh-tw)，而且配置有適當設定，電腦版的排名信號就會以電腦使用者所看到網址的表現為依據。

| 考量要素 | 行動版 | 電腦版 |
| --- | --- | --- |
| 最大內容繪製 (LCP) |  |  |
| 累計版面配置位移 (CLS) |  |  |
| 首次輸入延遲時間 (FID) |  |  |
| HTTPS 加密 |  |  |
| 排除插頁式廣告干擾 |  |  |
| 行動裝置相容性 |  | (不適用) |

希望這篇網誌文章提供的詳細資訊能讓您[瞭解網頁體驗並進行最佳化調整](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw#optimize)，為即將推出的變更做好準備，進而協助您打造更出色的網站。

如有任何問題或意見，歡迎造訪[說明論壇](https://support.google.com/webmasters/community/?hl=zh-tw)，或透過 [Twitter](https://twitter.com/googlesearchc) 告訴我們。

發布者：Google 搜尋產品經理 Jeffrey Jose

---

## 更新

* **2022 年 1 月 17 日更新內容**：Search Console 現已在[網頁體驗報表](https://search.google.com/search-console/page-experience?hl=zh-tw)中推出專屬的「電腦版」專區。
* **2022 年 2 月 22 日更新內容**：我們目前已逐步推出電腦版網頁體驗更新，並將於 2022 年 3 月底前完成推出程序。
* **2024 年 1 月 31 日更新**：
  [Interaction to Next Paint (INP)](https://web.dev/blog/inp-cwv-march-12?hl=zh-tw) 將於 2024 年 3 月 12 日取代 FID 成為 Core Web Vitals 的一部分。
* **2024 年 3 月 12 日更新**：[Interaction to Next Paint (INP)](https://web.dev/blog/inp-cwv-launch?hl=zh-tw) 已取代 FID 成為 Core Web Vitals。
