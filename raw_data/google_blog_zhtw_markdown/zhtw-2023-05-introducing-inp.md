# Core Web Vitals 推出 INP
- **發佈日期**: 2023-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/05/introducing-inp?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 5 月 10 日，星期三

這篇網誌文章已發布一段時間。部分資訊可能已經過時，例如圖片可能會有缺漏，連結也可能失效。請參閱有關[網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)的最新說明文件。

Google 的 Chrome 團隊在 2020 年初推出了 [Core Web Vitals](https://web.dev/articles/vitals?hl=zh-tw)，這是一套網頁品質信號。Google Chrome 團隊今天[宣布](https://web.dev/blog/inp-cwv?hl=zh-tw)，為了更加準確地評估網頁的使用者體驗品質，Core Web Vitals 指標更新即將推出。本文將探索這次變更的內容，以及這對於 Google 搜尋和網站擁有者的影響。

## 更精準的回應情形指標

![INP 指標已由 2022 年 5 月的實驗指標轉換為今日公告的異動內容，2024 年 5 月將成為 Core Web Vitals 中的穩定指標之一。](https://developers.google.com/static/search/blog/images/introducing-inp/inp-timeline.png?hl=zh-tw)

[First Input Delay (FID)](https://web.dev/articles/fid?hl=zh-tw) 是 Core Web Vitals 的其中一項指標，用於評估回應情形，但 [FID 有一些已知的限制](https://web.dev/blog/better-responsiveness-metric?hl=zh-tw)。因此，Chrome 團隊嘗試開發了一項[實驗指標](https://web.dev/blog/responsiveness?hl=zh-tw)，並尋求相關意見，試圖有效解決前述限制。他們在 2022 年宣布了「[Interaction to Next Paint (INP)](https://web.dev/articles/inp?hl=zh-tw)」這個新指標，並開始與社群合作來測試效力。

在經過一年的測試和收集社群的意見回饋後，Chrome 團隊決定將 INP 發展為新的 Core Web Vitals 回應情形指標，2024 年 3 月生效，取代 FID。這篇 [Chrome 團隊的網誌文章](https://web.dev/blog/inp-cwv?hl=zh-tw)詳細說明了這項異動，也闡述了採用這項新指標的背後緣由。

## 對 Google Search Console 有何影響

新指標「INP」將於 2024 年 3 月取代 FID，成為 Core Web Vitals 指標之一。為協助網站擁有者和開發人員針對新指標採取必要步驟，並評估自家網頁，Search Console 會在今年稍晚時將 INP 納入 Core Web Vitals 報表中。2024 年 3 月，INP 取代 FID 後，Search Console 報表將停止顯示 FID 指標，並使用 INP 做為評估回應情形的新指標。

## 對網站擁有者有何影響

如果您持續按照指引改善 Core Web Vitals，表示屆時的您已經評估了網頁的回應情形。針對 FID 所做的改善措施，也會是改善 INP 和網頁回應情形的良好基礎。

我們強烈建議網站擁有者提升 Core Web Vitals 指標數值，以便在 Google 搜尋上獲得良好成效，確保網站能穩定提供優質的使用者體驗。不過，良好的網頁體驗不只與 Core Web Vitals 相關聯。即便在 Search Console 中的 [Core Web Vitals 報告](https://support.google.com/webmasters/answer/9205520?hl=zh-tw)或第三方網站的 Core Web Vitals 報告中呈現的統計資料良好，也不保證能獲得優秀排名。

如要進一步瞭解 Core Web Vitals 如何融入網頁體驗的整體做法中，請參閱「[瞭解並思索 Google 搜尋結果中的網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)」一文的指引。

如要進一步瞭解新指標，請參閱 [Chrome 團隊的網誌文章](https://web.dev/blog/inp-cwv?hl=zh-tw)；關於如何針對 INP 相關項目進行網頁最佳化，請參閱[這份 INP 最佳化指南](https://web.dev/articles/optimize-inp?hl=zh-tw)。

發文者：Google 搜尋關係團隊開發人員關係工程師 [Martin Splitt](https://developers.google.com/search/blog/authors/martin-splitt?hl=zh-tw)

---

## 更新

* **2024 年 1 月 31 日更新**：
  [Interaction to Next Paint (INP)](https://web.dev/blog/inp-cwv-march-12?hl=zh-tw) 將於 2024 年 3 月 12 日取代 FID 成為 Core Web Vitals。
* **2024 年 3 月 12 日更新**：[Interaction to Next Paint (INP)](https://web.dev/blog/inp-cwv-launch?hl=zh-tw) 已取代 FID 成為 Core Web Vitals 的一部分。
