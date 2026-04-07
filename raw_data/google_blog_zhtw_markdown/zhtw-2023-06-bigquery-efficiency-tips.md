# Search Console 大量資料匯出作業的 BigQuery 效率提升要訣
- **發佈日期**: 2023-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/06/bigquery-efficiency-tips?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 6 月 5 日，星期一

Search Console 的[大量資料匯出](https://developers.google.com/search/blog/2023/02/bulk-data-export?hl=zh-tw)功能可將您的網站搜尋效能資料匯入 BigQuery 中，協助您提升儲存空間、分析和報表功能。舉例來說，匯出資料後，您可以執行查詢和網址分群、分析長尾搜尋查詢，以及將搜尋與其他資料來源結合。或者，您也可以視需要設定資料保留期限。

使用大量資料匯出功能時，請務必在管理資料處理和儲存空間費用時做出明智的決定。匯出資料並不會產生任何與 Search Console 相關的費用，不過，請詳閱 [BigQuery 定價](https://cloud.google.com/bigquery/pricing?hl=zh-tw)，瞭解您需要支付哪些費用。**本文將提供一些訣竅，協助您善用新大量資料匯出作業而不會產生高額費用。**

如果您尚未設定大量資料匯出作業，請參閱 Search Console 說明中心的[逐步指南](https://support.google.com/webmasters/answer/12917675?hl=zh-tw)。如需透過匯出作業所取得資料的總覽，請觀看此處嵌入的影片。

## 建立帳單快訊和限制

規劃費用時，最好先考慮您願意支付的金額。這個問題的答案，在儲存空間、分析和監控等方面可能會有所不同。舉例來說，您可能願意支付特定金額來確保所有資料都順利儲存，但對於建立報表平台，卻只願意支付較少的金額。在思考這個問題之際，建議您設定每月預算以投資搜尋資料。

確定預算金額後，就可以建立 [Google Cloud 預算快訊](https://cloud.google.com/billing/docs/how-to/budgets?hl=zh-tw)來避免產生意外的帳單費用。您還可以設定門檻規則，讓系統在即將達到預算金額時觸發電子郵件通知。

![Cloud 控制台螢幕截圖，顯示如何建立帳單快訊](https://developers.google.com/static/search/blog/images/bigquery-budget-alert.png?hl=zh-tw)

您也可以[限制查詢的計費位元組數](https://cloud.google.com/bigquery/docs/best-practices-costs?hl=zh-tw#limit_query_costs_by_restricting_the_number_of_bytes_billed)，藉此進一步保護資料。如果這樣做，系統就會在查詢執行前預估查詢讀取的位元組數。如果預估的位元組數超過限制，查詢就會失敗，不會產生費用。

## 不要直接在原始資料上建構資訊主頁

BigQuery 的運作速度快，接下來您可能會將資訊主頁直接連結至 Search Console 匯出的資料表。但對大型網站而言，這個資料集非常龐大 (尤其是長期查詢)。如果您建構的資訊主頁會重新計算每次檢視的摘要資訊，並在貴公司內共用這些資訊，這將迅速導致查詢費用大幅增加。

為了避免產生這類費用，建議預先匯總每一項日常推送資料，並將一或多個摘要資料表實體化。這樣一來，資訊主頁就能查詢擷取時間較短的時間序列資料表，進而降低處理成本。

請檢查 BigQuery 中的[安排查詢](https://cloud.google.com/bigquery/docs/scheduling-queries?hl=zh-tw)功能；如需自動化解決方案，也可以考慮使用 [BI Engine](https://cloud.google.com/bigquery/docs/bi-engine-intro?hl=zh-tw)。

## 最佳化資料儲存成本

根據預設，開始進行大量資料匯出作業後，資料會保留在 BigQuery 資料集中。不過，您可以[更新預設的分區到期時間](https://cloud.google.com/bigquery/docs/updating-datasets?hl=zh-tw#partition-expiration)，讓日期分區在一年、16 個月或任何想保留的時間長度後自動刪除。

請勿為資料表設定到期時間，因為這樣會在指定日期刪除整個資料表！

匯出的資料對您來說很重要，但可能相當龐大。請運用您業務的知識，並考慮將資料保留夠長 (但又不至於太長而造成負擔) 的時間以進行深入分析。其中一個選項是保留舊版表格的取樣版本，同時保留日期較近的整個資料表。

## 最佳化 SQL 查詢

查詢 Search Console 資料時，請務必最佳化查詢以提升效能。如果您是 BigQuery 新手，請參閱說明中心的[指南和查詢範例](https://support.google.com/webmasters/answer/12917174?hl=zh-tw)。建議您嘗試以下三種技巧。

### 1. 限制輸入掃描

首先，[避免使用 `SELECT *`](https://cloud.google.com/bigquery/docs/best-practices-costs?hl=zh-tw#avoid_select_)，這是查詢資料最昂貴的方法，BigQuery 會完整掃描資料表中的每個資料欄。套用 `LIMIT` 子句**不會**影響讀取的資料量。

由於匯出的資料表是依日期分區，因此您可以將輸入掃描作業限制在需要的日期，尤其是在測試及使用資料時。使用 `WHERE` 子句限制日期分區資料表中的日期範圍，這樣就會大幅節省查詢費用。舉例來說，只要使用下列子句，就可以只查看最近 14 天的資料：

```
WHERE data_date between DATE_SUB(CURRENT_DATE(), INTERVAL 14 day)
```

針對您執行的每項查詢，建議盡快使用任何已知的篩選器以減少輸入掃描作業。舉例來說，如要分析查詢，建議篩除[匿名查詢](https://developers.google.com/search/blog/2022/10/performance-data-deep-dive?hl=zh-tw#privacy-filtering)資料列。匿名查詢在資料表中會記錄為長度為零的字串。如要篩除匿名查詢資料列，可以新增下列項目：

```
WHERE query != ''
```

### 2. 進行資料取樣

BigQuery 提供[資料表取樣](https://cloud.google.com/bigquery/docs/table-sampling?hl=zh-tw)功能，可讓您查詢大型 BigQuery 資料表中的隨機資料子集。取樣功能會傳回多種記錄，同時避免在掃描及處理整個資料表時產生相關的費用，因此在開發查詢或不需要取得精準結果時特別實用。

### 3. 使用不需要取得精準結果的近似函式

BigQuery 支援許多[近似匯總函式](https://cloud.google.com/bigquery/docs/reference/standard-sql/approximate_aggregate_functions?hl=zh-tw)，可以提供預估結果，而且計算費用也比精準函式計算費用更低。舉例來說，如果您想根據特定條件的曝光次數來搜尋熱門網址，就可以使用

```
SELECT APPROX_TOP_SUM(url, impressions, 10) WHERE datadate=...;
```

而不是使用

```
SELECT url, SUM(impressions) WHERE datadate=... GROUP BY url ORDER BY 2 DESC LIMIT 10;
```

## 資源

這裡列出幾個可以用來開始管理費用的提示，詳情請參閱 [BigQuery 費用最佳化最佳做法](https://cloud.google.com/blog/products/data-analytics/cost-optimization-best-practices-for-bigquery?hl=zh-tw)。

和往常一樣，如有任何問題或疑慮，歡迎透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com) 和軟體工程師 Gaal Yahas
