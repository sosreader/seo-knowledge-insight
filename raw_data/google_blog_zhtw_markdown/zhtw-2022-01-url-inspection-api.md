# 歡迎使用全新 Search Console URL Inspection API透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2022-01-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/01/url-inspection-api?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 1 月 31 日，星期一

我們在今天推出全新 Google Search Console [URL Inspection API](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect?hl=zh-tw)，讓您以程式輔助的方式存取 Search Console 中所管理資源的網址層級資料。

透過 [Search Console API](https://developers.google.com/webmaster-tools?hl=zh-tw)，您可以在 Search Console 外利用外部應用程式和產品存取資料。開發人員和搜尋引擎最佳化 (SEO) 工具已運用這些 API 打造自訂解決方案，藉此查看、新增或移除資源與 Sitemap，以及執行有關 Google 搜尋成效資料的進階查詢。

我們提供 URL Inspection API 這項新工具，是為了讓開發人員針對自家網頁進行偵錯及最佳化處理。您可以要求 Search Console 的網址索引版本相關資料，此 API 會傳回[網址檢查工具](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)中已建立索引的目前可用資訊。

## 使用全新 API

如要瞭解如何使用新的 API，請參閱 [API 開發人員說明文件](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect?hl=zh-tw)。要求參數包括您想檢查的網址，以及 Search Console 中所定義資源的網址。

回應中的分析結果含有 Search Console 提供的資訊，包括索引狀態、AMP、複合式搜尋結果和行動裝置可用性。詳情請查看[參數清單](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult?hl=zh-tw)和[已建立索引的網址相關說明](https://support.google.com/webmasters/answer/9012289?hl=zh-tw#indexed_inspection)。

發出 API 呼叫後，您會收到包含所有相關結果的回應；如果要求失敗，則會收到錯誤訊息。若回應中缺少特定分析結果，就表示檢查的網址不適用該分析作業。以下是 API 傳送給您的回應示例。

```
  {
  "inspectionResult": {
    "inspectionResultLink": "https://search.google.com/search-console/inspect?resource_id=https://developers.google.com/search/&id=odaUL5Dqq3q8n0EicQzawg&utm_medium=link",
    "indexStatusResult": {
      "verdict": "PASS",
      "coverageState": "Indexed, not submitted in sitemap",
      "robotsTxtState": "ALLOWED",
      "indexingState": "INDEXING_ALLOWED",
      "lastCrawlTime": "2022-01-31T08:39:51Z",
      "pageFetchState": "SUCCESSFUL",
      "googleCanonical": "https://developers.google.com/search/help/site-appearance-faq",
      "userCanonical": "https://developers.google.com/search/help/site-appearance-faq",
      "referringUrls": [
        "https://developers.google.com/search/updates",
        "https://developers.google.com/search/help/crawling-index-faq"
      ],
      "crawledAs": "MOBILE"
    },
    "mobileUsabilityResult": {
      "verdict": "PASS"
    },
    "richResultsResult": {
      "verdict": "PASS",
      "detectedItems": [
        {
          "richResultType": "Breadcrumbs",
          "items": [
            {
              "name": "Unnamed item"
            }
          ]
        },
        {
          "richResultType": "FAQ",
          "items": [
            {
              "name": "Unnamed item"
            }
          ]
        }
      ]
    }
  }
}
```

## 可能的應用方式

建構新的 API 時，我們諮詢過許多搜尋引擎最佳化 (SEO) 專員和發布者，瞭解他們會如何透過該 API 利用相關資料打造解決方案。以下列舉一些值得注意的應用方式：

* 「搜尋引擎最佳化 (SEO) 工具和代理商」可持續監控多個重要網頁和單一網頁的偵錯選項，例如確認使用者宣告的標準網址與 Google 選取的標準網址是否存在差異，或對一組網頁的結構化資料問題進行偵錯。
* 「CMS 和外掛程式開發人員」可新增網頁/範本層級的深入分析資訊和持續檢查現有網頁的程序，例如監控重要網頁的長期變化，以便診斷問題及決定修正作業的優先順序。

## 用量限制

如需更詳細的 Search Console [API 用量限制](https://developers.google.com/webmaster-tools/limits?hl=zh-tw)說明，請參閱開發人員說明文件。就 URL Inspection API 而言，系統會針對每項 Search Console [網站資源](https://support.google.com/webmasters/answer/34592?hl=zh-tw) (查詢同一網站的呼叫) 強制執行下列配額限制：

* 每日 2,000 次查詢
* 每分鐘 600 次查詢

## 意見回饋

我們相信新的 API 能夠讓整個生態系統有機會運用 Google 搜尋資料推動創新，也一向期待看到開發人員和搜尋引擎最佳化 (SEO) 專員透過各種 Search Console API 打造的解決方案。

如有任何疑問或意見，歡迎[透過 Twitter](https://twitter.com/googlesearchc) 與我們聯絡，或是前往 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)提問。

發文者：Search Console 團隊的 [Daniel Waisberg](https://www.danielwaisberg.com) 和 Dori Rosenberg
