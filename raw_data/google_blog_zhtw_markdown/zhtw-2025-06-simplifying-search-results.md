# 簡化搜尋結果網頁
- **發佈日期**: 2025-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/06/simplifying-search-results?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 6 月 12 日

為了[持續簡化 Google 搜尋結果頁面](https://developers.google.com/search/blog/2025/01/simplifying-breadcrumbs?hl=zh-tw)，我們將逐步淘汰 Google 搜尋中部分[結構化資料](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=zh-tw)功能。我們會定期評估搜尋結果功能對使用者和網站擁有者的實用性。

我們將逐步淘汰這些特定的結構化資料類型，因為分析結果顯示這些類型在 Google 搜尋中不常使用，而且我們發現這些特定顯示項目不再為使用者提供重大額外價值。移除這些功能有助於簡化搜尋結果頁面，並著重於更實用且廣泛使用的其他體驗。

這項更新不會影響網頁的排名。簡化後，部分結果將不再顯示由這些較少使用的標記提供的特定視覺強化效果，呈現方式會更加簡潔。在 Google 搜尋 (和相關功能) 以外使用這些結構化資料類型則不受影響。

Google 搜尋結果將不再支援以下結構化資料類型，並會在未來幾週至幾個月內逐步淘汰：

* [書籍動作](https://developers.google.com/search/docs/appearance/structured-data/book?hl=zh-tw)
* [課程資訊](https://developers.google.com/search/docs/appearance/structured-data/course-info?hl=zh-tw)
* [聲明審查](https://developers.google.com/search/docs/appearance/structured-data/factcheck?hl=zh-tw)
* [預估薪酬](https://developers.google.com/search/docs/appearance/structured-data/estimated-salary?hl=zh-tw)
* [教學影片](https://developers.google.com/search/docs/appearance/structured-data/learning-video?hl=zh-tw)
* [特殊公告](https://developers.google.com/search/docs/appearance/structured-data/special-announcements?hl=zh-tw)
* [車輛資訊](https://developers.google.com/search/docs/appearance/structured-data/vehicle-listing?hl=zh-tw)

結構化資料是網站擁有者描述內容並啟用實用搜尋結果功能的絕佳方式。雖然我們會淘汰一些較少使用的顯示資訊，但仍會持續積極支援各種結構化資料類型，讓使用者在評估要造訪的內容時，能利用這些實用的功能。

我們相信這項異動可讓所有使用者享有更簡潔、更聚焦的搜尋結果網頁。我們會持續尋找簡化搜尋結果網頁的方法，為使用者和網站擁有者提供最佳體驗。持續進行這項工作的過程中，我們會隨時分享最新消息。如果您有任何問題或疑慮，請透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)或 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 與我們聯絡。

發文者：Google 搜尋產品經理 Henry Hsu

---

## 更新

### 2025 年 9 月 8 日更新內容
:   我們將移除 Search Console 對下列結構化資料類型的支援，因為這些類型已從搜尋結果中淘汰：課程資訊、聲明審查、預估薪資、學習影片、特別公告和車輛資訊。自 9 月 9 日起，這些類型將從 Search Console 複合式搜尋結果報表、複合式搜尋結果測試和[搜尋外觀篩選器清單](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#by_search_appearance&zippy=,search-appearance)中移除 (如適用)。[Search Console API](https://developers.google.com/webmaster-tools?hl=zh-tw) 將繼續支援這些類型，直到 2025 年 12 月為止。

    [大量資料匯出使用者](https://support.google.com/webmasters/answer/12918484?hl=zh-tw)請注意，自 2025 年 10 月 1 日起，系統會將已淘汰的[搜尋外觀欄位](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#by_search_appearance&zippy=,search-appearance)回報為 `NULL`。如果查詢設有條件，可能需要更新。

    舉例來說，下列查詢應更新，因為未考量搜尋外觀可能已淘汰：

    ```
    SELECT data_date, SUM(clicks) FROM `myproject.searchconsole.searchdata_url_impressions`

    WHERE data_date > DATE('2025-09-01') AND NOT is_learning_videos -- skips rows where is_learning_videos is NULL

    GROUP BY 1;
    ```

    建議改用 `IS` 運算子編寫符合未來趨勢的查詢，確保即使外觀變成 `NULL`，查詢仍能繼續運作。

    ```
    SELECT data_date, SUM(clicks) FROM `myproject.searchconsole.searchdata_url_impressions`

    WHERE data_date > DATE('2025-09-01') AND is_learning_videos IS NOT TRUE -- works whether is_learning_videos is false or NULL

    GROUP BY 1;
    ```

    詳情請參閱 Google Cloud [關於 `IS` 運算子的 BigQuery 說明文件](https://cloud.google.com/bigquery/docs/reference/standard-sql/operators?hl=zh-tw#is_operators)。
