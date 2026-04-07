# Google 於 2022 年處理垃圾搜尋結果的成效
- **發佈日期**: 2023-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/04/webspam-report-2022?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 4 月 11 日，星期二

![Googlebot 和 Crawly 一同說明我們如何因應 2022 年的 Google 搜尋垃圾內容](https://developers.google.com/static/search/blog/images/webspamreport2022/webspam-report-2022-blog.png?hl=zh-tw)

我們每天都會找出數十億個網頁、為它們建立索引並提供給使用者，而我們發現有相當多的網頁都含有垃圾內容。我們在 2022 年推出了多項系統更新，以防堵這類攻擊，確保所有 Google 搜尋的使用者都能不受到垃圾內容干擾。

## 改善 SpamBrain 系統

[SpamBrain](https://developers.google.com/search/blog/2022/04/webspam-report-2021?hl=zh-tw#spambrain:-our-most-effective-solution-against-spam) 是我們杜絕垃圾內容的核心，我們在 2022 年採取了許多改善措施，藉此提升 SpamBrain 的涵蓋率。SpamBrain 能偵測到的垃圾網站數量是 2021 年的 5 倍，與當初剛推出相比則是 200 倍。多虧了 SpamBrain 的協助，我們得以確保經由 Google 搜尋而造訪網站的訪客中，有超過 99% 的人會完全不受垃圾內容干擾。

### 處理濫用連結與遭入侵並植入垃圾內容的網站

此外，我們也讓 SpamBrain 進一步成為功能強大且用途廣泛的平台，可透過多種解決方案涵蓋更多不同類型的濫用行為，例如垃圾連結。正如我們在[去年 12 月發布](https://developers.google.com/search/blog/2022/12/december-22-link-spam-update?hl=zh-tw)內容所說，我們訓練 SpamBrain 偵測建立垃圾連結的網站，以及為了將垃圾連結傳送到其他網站而建立的網站。多虧了 SpamBrain 優秀的學習能力，我們偵測到含有垃圾連結的網站數量，比[先前的連結垃圾內容更新](https://developers.google.com/search/blog/2021/07/link-tagging-and-link-spam-update?hl=zh-tw)多出 50 倍。同樣地，我們也讓 SpamBrain 學習更多網站遭到入侵並值入垃圾內容的相關知識，使偵測遭入侵網站的成效提升了 10 倍。

### 更快速地處理垃圾內容

SpamBrain 也是能在[檢索時](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=zh-tw#crawling)更有效地偵測垃圾內容的重要因素。這表示當我們初次造訪某個網頁且尚未將其編入索引時，能更有效地偵測內容，將資源更妥善地用在為實用網頁建立索引。

## 強化使用者安全

除了防範垃圾內容，我們也推出新的反詐騙解決方案，為使用者提供更完善的 Google 搜尋服務安全。這些新的解決方案不僅擴大了涵蓋範圍，也首次將詐騙防護功能擴及所有語言的網站。與 2021 年相比，詐騙網站的點擊次數減少了 50%。

### 網站擁有者指南更新

除了抵禦垃圾內容之外，我們也在[搜尋基礎入門](https://developers.google.com/search/blog/2022/10/search-essentials?hl=zh-tw)中對[垃圾內容政策](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw)進行部分更新。這些垃圾內容政策涵蓋了最常見的垃圾內容類型和濫用行為，這類內容可能導致網站在搜尋結果中的排名降低，甚至完全無法顯示在結果中。我們更新了垃圾內容政策，除了使用更相關且精確的語言外，還加入了新的範例，有助於避免網站擁有者製作有害內容。

我們也發現，許多人對 AI 產生內容和 AI 輔助內容很感興趣，因此發布了「[AI 產生內容相關指引](https://developers.google.com/search/blog/2023/02/google-search-and-ai-content?hl=zh-tw)」。我們希望該指南能協助您瞭解 AI 和自動化技術的實用之處，幫助您製作實用內容。不過，如果使用 AI 技術的主要目的是操控搜尋排名，則違反我們防範[自動產生的垃圾內容](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#scaled-content)的長期政策。

我們不斷努力偵測並移除垃圾內容，讓使用者可透過 Google 搜尋找到最實用的內容。我們無法獨力實現此一目標；感謝您為使用者製作實用內容和有用網站，並向我們提供關於垃圾內容和濫用行為的意見回饋與深入分析報告。如果發現垃圾內容或操弄行為，請[向我們檢舉](https://support.google.com/websearch/answer/3338405?hl=zh-tw)或造訪[搜尋中心產品討論社群](https://support.google.com/webmasters/community?hl=zh-tw)。

發文者：[Google 搜尋品質分析師 Duy Nguyen](https://developers.google.com/search/blog/authors/duy-nguyen?hl=zh-tw)
