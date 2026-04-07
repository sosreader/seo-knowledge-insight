# Search Analytics API 現已支援每小時資料
- **發佈日期**: 2025-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/04/san-hourly-data?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 4 月 9 日，星期三

幾個月前，我們宣布推出改良版 [Search Console 近期成效資料](https://developers.google.com/search/blog/2024/12/recent-data-search-console?hl=zh-tw)查看方式。「24 小時」檢視畫面會顯示過去 24 小時內的資料，延遲時間只有幾小時。這個檢視畫面可協助您瞭解哪些網頁和查詢在最近這段期間成效良好，以及您最近發布的內容有何進展。

今天，我們在 [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=zh-tw) 中新增了每小時資料支援功能，這是因為我們發現整體環境強烈要求更方便存取的資料。因此，我們會在 API 中新增每小時資料，且範圍比產品介面更廣：產品介面只會顯示過去 24 小時的每小時資料，但 API 會傳回最多 10 天的資料，並提供每小時的細目資料。這麼做可讓開發人員建立解決方案，不僅顯示過去一天的每小時資料，還能比較最近一天與前一週同一天的資料，這在分析每週各天模式時相當實用。

## 如何從 Search Analytics API 提取每小時資料

為了在 Search Analytics API 中取得每小時資料，我們會在 [API 要求主體](https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=zh-tw#request-body)中導入 2 項變更：

* 新增名為 `HOUR` 的新 `ApiDimension`，以便按小時分組回應。
* 新增名為 `HOURLY_ALL` 的 `dataState` 值，應在按 HOUR 分組時使用。這表示每小時資料可能不完整。

在下一個部分，我們會提供 API 要求範例和回應範例供您參考。

### API 要求範例

```
{
  "startDate": "2025-04-07",
  "endDate": "2025-04-07",
  "dataState": "HOURLY_ALL",
  "dimensions": [
    "HOUR"
  ]
}
```

### API 回應範例

```
{
  "rows": [
    {
      "keys": [
        "2025-04-07T00:00:00-07:00"
      ],
      "clicks": 17610,
      "impressions": 1571473,
      "ctr": 0.011206046810858348,
      "position": 10.073871456906991
    },
    {
      "keys": [
        "2025-04-07T01:00:00-07:00"
      ],
      "clicks": 18289,
      "impressions": 1662252,
      "ctr": 0.011002543537321658,
      "position": 9.5440029550272758
    },
    {
      "keys": [
        "2025-04-07T02:00:00-07:00"
      ],
      "clicks": 18548,
      "impressions": 1652038,
      "ctr": 0.011227344649457216,
      "position": 9.81503633693656
    },
    {
      "keys": [
        "2025-04-07T03:00:00-07:00"
      ],
      "clicks": 18931,
      "impressions": 1592716,
      "ctr": 0.01188598595104212,
      "position": 9.4956935197486558
    },
    {
      "keys": [
        "2025-04-07T04:00:00-07:00"
      ],
      "clicks": 20519,
      "impressions": 1595636,
      "ctr": 0.012859449147549943,
      "position": 9.4670100198290843
    },
    …
  ],
  "responseAggregationType": "byProperty"
}
```

我們希望這項新資料能協助您以更有效的方式監控近期發布的內容，並及時採取適當行動。歡迎提供您對這項新檢視畫面的想法和使用體驗，並提供任何建議，協助讓這項功能更臻完美。如有任何意見回饋、問題或評論，歡迎前往 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 與我們交流，或是在 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)發文提問。

發文者：軟體工程師 [Tali Pruss](https://www.linkedin.com/in/talipruss/) 和搜尋服務代表 [Daniel Waisberg](https://developers.google.com/search/blog/authors/daniel-waisberg?hl=zh-tw)
