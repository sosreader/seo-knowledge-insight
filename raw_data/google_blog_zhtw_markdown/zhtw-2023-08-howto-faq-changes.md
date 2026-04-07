# HowTo 和 FAQ 複合式搜尋結果異動
- **發佈日期**: 2023-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/08/howto-faq-changes?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 8 月 8 日，星期二

**2023 年 9 月 14 日更新**：我們持續致力於簡化 Google 搜尋結果，「How-to」的相關異動也會推展到電腦版。9 月 13 日起，Google 搜尋不會再於電腦上顯示 How-to 複合式搜尋結果，也就是說，這種搜尋結果類型現已淘汰。

這項變更會顯示在[成效報表中的 How-to 搜尋外觀](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#zippy=,search-appearance)指標，以及 [How-to 強化報表](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)中回報的曝光次數。
由於 Google 搜尋已不再顯示 How-to 搜尋結果，因此我們將於 30 天後淘汰 How-to 搜尋外觀、複合式搜尋結果報告和複合式搜尋結果測試中的支援。為保留調整 API 呼叫的時間，Search Console API 中的 How-to 支援功能將在 180 天後移除。

為了提供更簡潔且一致的搜尋體驗，我們將變更部分複合式搜尋結果類型在 Google 搜尋結果中的顯示方式。
具體而言，我們會降低 FAQ 複合式搜尋結果的瀏覽權限，並限制向電腦裝置顯示 How-to 複合式搜尋結果。這項變更將於下週全面推出。

## 異動總覽

對網站擁有者來說，這些異動主要是影響 [FAQ](https://developers.google.com/search/docs/appearance/structured-data/faqpage?hl=zh-tw) 和 [How-To](https://developers.google.com/search/docs/appearance/structured-data/how-to?hl=zh-tw) 結構化資料的使用。

往後，系統只會針對知名的權威性政府和健康網站顯示 [FAQ](https://developers.google.com/search/docs/appearance/structured-data/faqpage?hl=zh-tw) (來自 `FAQPage` 結構化資料) 複合式搜尋結果。
至於所有其他網站，系統將不再定期顯示這項複合式搜尋結果。視網站是否符合資格而定，系統可能會自動為這類網站顯示這項複合式搜尋結果。

雖然您可以直接將這項結構化資料從網站上移除，但不必主動移除。
沒有使用的結構化資料並不會讓 Google 搜尋發生問題，而且在 Google 搜尋中也不會產生任何影響。

![一項搜尋結果顯示完整的 FAQ 複合式搜尋結果，另一項則沒有](https://developers.google.com/static/search/blog/images/faq-snippet-change.png?hl=zh-tw)

[How-to](https://developers.google.com/search/docs/appearance/structured-data/how-to?hl=zh-tw) (來自 `HowTo` 結構化資料) 複合式搜尋結果只會向電腦使用者顯示，不會向行動裝置使用者顯示。
請注意，使用行動版索引系統時，Google 會為行動版網站建立索引，以做為索引基礎：為了在電腦上顯示 How-to 複合式搜尋結果，行動版網站必須包含適當的標記。

## Search Console 報表異動

您可能會在網站的 Search Console 報表中看到上述兩種項目的異動。
特別是，系統針對[成效報表中 FAQ 和 How-to 搜尋外觀](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#zippy=,search-appearance)顯示的指標會有所異動，而且相關[強化報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)回報的曝光次數也會出現異動。
這項異動不會影響強化報告中回報的項目數量。
搜尋外觀和報告會先暫時保留在 Search Console 中。

這項更新將於下週向全世界所有語言和國家/地區推出。這項更新不應視為排名變更，也不會列入搜尋狀態資訊主頁中。
請注意，我們會進行小幅區隔劃分實驗，因此部分使用者可能不會立即看到這些變更。

如有任何問題，歡迎前往[搜尋中心產品討論社群](https://goo.gle/sc-forum)提問，或在[社群媒體](https://twitter.com/googlesearchc)上與我們聯絡。

發文者：Google 瑞士團隊搜尋服務代表 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw)
