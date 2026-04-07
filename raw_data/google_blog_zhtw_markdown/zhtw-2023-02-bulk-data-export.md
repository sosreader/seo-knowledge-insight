# 大量資料匯出：透過全新且強大的工具存取 Search Console 資料
- **發佈日期**: 2023-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/02/bulk-data-export?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 2 月 21 日，星期二

今天，我們宣布推出[大量資料匯出](https://support.google.com/webmasters/answer/12918484?hl=zh-tw)這項新功能，可讓您持續將 Search Console 的資料匯出至 [Google BigQuery](https://cloud.google.com/bigquery?hl=zh-tw) (請注意，這項推出作業大約需要一週的時間，因此可能無法立即存取)。

您可以在 Search Console 中設定匯出作業，藉此將每日資料傾印到 BigQuery 專案中。
資料包括除了去識別化查詢 (已基於隱私權原因篩除) 之外的所有成效資料，也就是說，大量資料匯出並不會受[每日資料列限制](https://developers.google.com/search/blog/2022/10/performance-data-deep-dive?hl=zh-tw#daily-data-row-limit)的影響。也就是說，您可以探索自己的資料並充分發揮資料的價值，運用先進的分析和視覺化技術，將資料與其他資料來源加以整合。

這項資料匯出功能特別適合用於具有上萬個網頁的大型網站，或是每天收到數萬次查詢流量的網頁 (或同時出現這兩種情況的網頁！)。小型和中型網站已能透過使用者介面 ([Looker Studio 連接器](https://developers.google.com/search/blog/2022/03/monitoring-dashboard?hl=zh-tw) (舊稱「數據分析」) 或 [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=zh-tw))存取自身的所有資料。

## 設定新的大量資料匯出作業

如要設定新的報表，必須設定 BigQuery 帳戶來接收資料，並在 Search Console 設定中設定您的詳細資料。請查看說明中心的[逐步指南](https://support.google.com/webmasters/answer/12917675?hl=zh-tw)，但一般而言，這項程序會分為兩個階段：

1. **準備您的 Cloud 專案** ([在 Google Cloud Console 中](https://console.cloud.google.com/?hl=zh-tw))：這包括為專案啟用 BigQuery API，以及授予 Search Console 服務帳戶的權限。
2. **設定匯出目的地** ([在 Search Console 中](https://search.google.com/search-console/settings/bulk-data-export?hl=zh-tw))：這包括提供您的 Google Cloud 專案 ID，以及選擇資料集位置。請注意，只有資源擁有者才能設定大量資料匯出。

![Search Console 大量資料匯出設定頁面](https://developers.google.com/static/search/blog/images/search-console-bulk-data-export.png?hl=zh-tw)

提交資訊至 Search Console 後，即可模擬匯出內容。如果匯出成功，系統會透過電子郵件通知所有資源擁有者，而且持續的匯出作業將在 48 小時內開始。如果匯出模擬作業失敗，系統會針對偵測到的問題立即顯示快訊。請參閱[可能的匯出錯誤](https://support.google.com/webmasters/answer/12919198?hl=zh-tw)清單。

## 大量資料匯出中資料

大量資料匯出設定成功後，就可以登入 BigQuery 帳戶並開始查詢資料。

您可以在說明中心參閱詳細的[表格規範與參考資料](https://support.google.com/webmasters/answer/12917991?hl=zh-tw)；也可以另外參閱[依資源匯總資料與依網頁匯總資料](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#urlorsite)兩者之間的差異說明，協助您進一步瞭解資料。以下簡單介紹可供您使用的三個資料表：

* `searchdata_site_impression`：這個資料表包含依資源匯總的資料，包括查詢、國家/地區、類型和裝置。
* `searchdata_url_impression`：這個資料表包含依網址匯總的資料，可讓您更詳細地查看查詢內容與複合式搜尋結果。
* `ExportLog`：這個資料表記錄了系統當天儲存了哪些資料。資料表不會記錄失敗的匯出作業。

![BigQuery 介面中顯示的大量資料匯出資料表](https://developers.google.com/static/search/blog/images/bulk-data-export-bigquery-table.png?hl=zh-tw)

如果您需要查詢資料方面的協助，請參閱說明中心發布的[範例查詢](https://support.google.com/webmasters/answer/12917174?hl=zh-tw)，瞭解如何立即上手使用。以下舉例說明：如果網頁在過去兩週內獲得至少 100 個 FAQ 複合式搜尋結果曝光，我們就會針對網址的組合，擷取這類網址的總查詢數。

```
SELECT
  url,
  query,
  sum(impressions) AS impressions,
  sum(clicks) AS clicks,
  sum(clicks) / sum(impressions) AS ctr,
  /* Added one below, because position is zero-based */
  ((sum(sum_position) / sum(impressions)) + 1.0) AS avg_position
/* Remember to update the table name to your table */
FROM searchconsole.searchdata_url_impression
WHERE search_type = 'WEB'
  AND is_tpf_faq = true
  AND data_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 14 day) AND CURRENT_DATE()
  AND clicks > 100
GROUP BY 1,2
ORDER BY clicks
LIMIT 1000
```

我們希望藉由提供更多 Google 搜尋資料，讓網站擁有者和搜尋引擎最佳化 (SEO) 分析長尾查詢，進而發掘更多內容商機。這個做法還能讓您以更有效、更全面的方式將內部系統網頁層級的資訊整合至搜尋結果。

和往常一樣，如有任何問題或疑慮，歡迎透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：Search Console 團隊的 [Daniel Waisberg](https://www.danielwaisberg.com)、Gaal Yahas 和 Haim Daniel
