# Search Console API 公告
- **發佈日期**: 2020-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/08/search-console-api-announcements?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 8 月 6 日，星期四

過去一年來，我們一直致力於升級 [Search Console API](https://developers.google.com/webmaster-tools?hl=zh-tw) 的基礎架構，很高興現在這項任務即將大功告成。儘管我們的目標是盡可能讓人察覺不到遷移作業，但也許您已經注意到一些細微變化。Google 將藉由這項異動改進這個 API 的效能，從而應對日益增長的需求。

請注意，**如果您不會自行查詢 Search Console API，則無須採取任何行動**。如果您需要查詢這個 API 以取得自身資料，或是您維護的工具會使用這些資料 (例如 WordPress 外掛程式)，請繼續閱讀本文。以下是大致異動：

1. **Google Cloud Platform 資訊主頁異動**：使用情況報表會顯示舊版 API 的流量減少，新版 API 的流量增加。
2. **API 金鑰限制異動**：如果您已設定 API 金鑰限制，可能需要進行變更。
3. **探索文件異動**：如果您會使用第三方 API 程式庫查詢 API，或是直接查詢 [Webmasters 探索文件](https://www.googleapis.com/discovery/v1/apis/webmasters/v3/rest)，則必須在年底前更新探索文件。

請注意，除了上述異動外，**Search Console API 會回溯相容**，目前範圍和功能都沒有變化。

## Google Cloud Platform (GCP) 異動

在 [Google Cloud Console 資訊主頁](https://cloud.google.com/monitoring/charts/dashboards?hl=zh-tw)中，您會注意到舊版 API 的流量減少，同時新版 API 的呼叫次數有所增加。這兩者其實是同一個 API，只是因為數據都計入新名稱底下，才會出現這樣流量變化。

![Google Cloud Console 中的 Search Console API 異動](https://developers.google.com/static/search/blog/images/import/bf8e53f15fe1c0a8b91a79948c4d163e.jpg?hl=zh-tw)

您可以在[新版 Google Search Console API 頁面](https://console.cloud.google.com/apis/api/searchconsole.googleapis.com/overview?hl=zh-tw)監控上 API 使用情形。

## API 金鑰限制異動

如前文所述，只有在您會自行查詢資料，或是需要為使用者提供資料查詢工具時，才需要查看這些操作說明。

如要檢查您的 API 金鑰是否存在 API 限制，請按照[憑證頁面](https://console.cloud.google.com/apis/credentials?hl=zh-tw)中的[這些步驟](https://cloud.google.com/docs/authentication/api-keys?hl=zh-tw#adding_api_restrictions)，確認 Search Console API 未受到限制。如果您已為 API 金鑰增加 API 限制，**請務必在 8 月 31 日前採取行動**。

為了使您的 API 呼叫自動遷移到新的 API 基礎架構，您必須確保 Google Search Console API 未受到限制。

* 如果您的 API 限制已設為 [不限制金鑰]，您就無須採取任何行動。
* 如果您的 API 限制已設為 [限制金鑰]，**請確認 Search Console API 為下圖顯示的勾選狀態**。

![Google Search Console API 限制設定](https://developers.google.com/static/search/blog/images/import/44efcb3a3364ea8e409ac3171ed1d8d1.png?hl=zh-tw)

## 探索文件異動

我們將停止支援 Webmasters 探索文件，因此如果您會使用[外部 API 程式庫](https://developers.google.com/api-client-library?hl=zh-tw)查詢 Search Console API，或是直接查詢 [Webmasters API 探索文件](https://www.googleapis.com/discovery/v1/apis/webmasters/v3/rest)，就**必須採取行動**。目前我們預計會支援至 2020 年 12 月 31 日，但也會**在未來幾個月中提供更多詳細資料和指引**。

如有任何問題，請前往[產品討論社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 Google 網站管理員的 [Twitter 專頁](https://twitter.com/googlesearchc)提問。

發文者：Search Console 軟體工程師 Nati Yosephian
