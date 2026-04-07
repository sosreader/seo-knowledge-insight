# 在 Looker Studio 中混合 Search Console 和內部資料
- **發佈日期**: 2023-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/03/gsc-data-blending-looker-studio?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 3 月 22 日，星期三

Search Console 會提供您網站在 Google 搜尋中的成效相關資料。這些資料可在 [Looker Studio (先前稱為數據分析) 中存取](https://developers.google.com/search/blog/2022/03/connecting-data-studio?hl=zh-tw)，您可以在此處建立資訊主頁來[監控](https://developers.google.com/search/blog/2022/03/monitoring-dashboard?hl=zh-tw)及[探索](https://developers.google.com/search/blog/2022/04/performance-optimization-bubble-chart?hl=zh-tw)成效。

在 Search Console 以外的地方分析成效資料的好處之一，是您可以在報表中加入更多背景資訊，並以任何來源 (例如網站的相關技術和商家資訊) 來充實這些資料。分析成效時，您結合的資料來源越多，就越能瞭解哪些元素有助於達成理想成效，進而協助您運用資料做出更明智的決策。

Looker Studio 提供[資料混合功能](https://support.google.com/looker-studio/answer/9061420?hl=zh-tw)，可讓您根據多種資料來源 (包括 Search Console) 建立圖表、資料表和控制項。此處嵌入的[在 Looker Studio 中監控 Search Console 資料監控](https://www.youtube.com/watch?v=gm3YiEZVOts&hl=zh-tw)中，我舉了一個例子示範如何充實資料 (參閱影片 [4:42 處](https://youtu.be/gm3YiEZVOts?t=282))。

請參閱 Looker Studio 說明中心，取得[建立資料組合](https://support.google.com/looker-studio/answer/9061421?hl=zh-tw)的完整逐步指南。以下是主要步驟的摘要：

1. 針對 Search Console 資源和要在 Looker Studio 中混合的資料建立資料來源。
2. 前往內含您建立的任一資料來源的報表，然後選取資料表或圖表。在設定選單中，您會看到混合資料的選項。點選該按鈕後，您會看到一個介面，可供您將資料表彙整到現有的資料來源。
3. 按一下即可彙整表格，並選擇您剛建立的資料來源。然後再按一下，設定彙整作業。系統會顯示多個聯結運算子選項，詳情請參閱 [BigQuery 說明文件](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax?hl=zh-tw#join_types)。
4. 選擇相符的欄位來彙整資料表。

![Looker Studio 介面，顯示 Search Console 資料混合](https://developers.google.com/static/search/blog/images/google-search-console-data-blending.png?hl=zh-tw)

您也可以針對多個資料表執行同樣的操作，引進無法透過 Search Console 取得的資訊來充實資訊主頁，盡情發揮您的想像力！

您可以利用下列建議來充實不同的維度：

* **新增更多網址相關資訊**。提供網頁類別、已導入的結構化資料、網頁範本、內容類型、作者等有關網址的資料。
* **建立查詢叢集**。如果您按照主旨監控查詢，可以彙整用來定義哪個查詢屬於哪個群組的資料表；這可讓您根據內部定義監控查詢。
* **追蹤各國家/地區的預算**。如果您的目標對象遍布全球，而且每個國家/地區的預算不同，不妨一併監控成效結果和預算。

如有任何問題，歡迎隨時透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Looker Studio 社群](https://support.google.com/datastudio/threads?thread_filter=%28category%3Aconnect_to_data%29&hl=zh-tw)提問。

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com)
