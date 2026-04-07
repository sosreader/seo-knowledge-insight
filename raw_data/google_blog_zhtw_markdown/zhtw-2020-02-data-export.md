# 從 Search Console 匯出更多優質資料透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/02/data-export?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 2 月 26 日，星期三

一直以來，使用者都向我們大力呼籲要改善 Search Console 的下載功能，所以我們很高興在此宣布，現在大家已經可以從這項服務中匯出更豐富而實用的資料。

現在，您幾乎可以從所有 Search Console 報告中下載完整資訊，下載範圍不僅限於特定表格檢視畫面。我們相信下載的資料將更方便您在 Search Console 以外的地方查閱，以及視需要儲存以備日後參考。在本文的結尾部分，我們也將介紹在 Search Console 以外的地方使用這些資料的其他方式。

## 強化報告和其他功能

現在從 AMP 狀態等報告匯出資料時，您將可以匯出圖表背後的資料，不像以前只能匯出詳細資料表格中的資料。也就是說，除了問題和受影響網頁的清單外，您也將看到網頁的每日細目、狀態以及在 Google 搜尋結果中的曝光次數。如果您從特定的細目檢視畫面匯出資料，匯出的檔案就會包含關於這個檢視畫面的詳細說明。

如果選擇下載為 Google 試算表或 Excel (新功能！)，就會獲得一個包含兩個分頁的試算表；如果選擇下載為 CSV 檔案，則會獲得一個包含兩個 CSV 檔案的 ZIP 檔案。

以下是從 AMP 狀態報告下載的[範例資料集](https://docs.google.com/spreadsheets/d/1aZD7eAqjiIYAPc8PewVsJZnrErvOI5CFXu9x9fubiNY/?hl=zh-tw)。這個試算表的標題是為了配合這篇文章才有所改動，原本的標題包含網域名稱、報告和匯出日期。

![AMP 報告匯出範例](https://developers.google.com/static/search/blog/images/import/f14dc9670dc3e558faf7959126075ad7.png?hl=zh-tw)

## 成效報表

在成效資料方面，我們做出了以下兩點改善：


1. 現在可以一鍵下載所有分頁的內容。也就是說，您可以一次下載 [查詢]、[網頁]、[國家/地區]、[裝置]、[搜尋外觀] 和 [日期] 分頁中的資料。下載內容的輸出格式與前述相同，可以是含有多個分頁的 Google 試算表或 Excel 試算表，也可以是含有多個 CSV 檔案的 ZIP 檔案。
2. 除了成效資料以外，下載內容還會多出一個名為 [篩選器] 的分頁 (或 CSV 檔案)，當中會顯示匯出資料時所套用的篩選器。

以下是從成效報表下載的[範例資料集](https://docs.google.com/spreadsheets/d/1A37a2Pf5mIRY7WvDIFOCWlCrOjsD0ZMzE2FL-6RxmNg/?hl=zh-tw)。

![Google 搜尋成效匯出範例](https://developers.google.com/static/search/blog/images/import/7b0156bffe78c685db50d04bc1705f00.png?hl=zh-tw)

## 在其他地方使用 Search Console 資料的更多方法

既然談到資料匯出事宜，我們想藉機說明目前還能透過哪些方法在 Search Console 以外的地方使用 Search Console 的資料。如果貴公司很重視特定用途，比如將資料與其他資料集彙整、執行進階分析或以其他方式視覺化呈現資料，建議您採用下文介紹的這些方法。以下提供兩種方法，請根據您的技術程度和需要的資料選擇合適的方法。

### Search Console API

如果您有技術背景，或是貴公司的開發人員可提供協助，建議您使用 [Search Console API](https://developers.google.com/webmaster-tools?hl=zh-tw) 來查看、新增或移除屬性和 Sitemap，以及執行進階查詢來獲取 Google 搜尋結果資料。

我們有許多與這個主題相關的說明文件，但如果您想立即行動，下方這些連結或許能幫助您迅速上手：

1. [總覽和事前準備指南](https://developers.google.com/webmaster-tools/v1/prereqs?hl=zh-tw)提供逐步指引，協助您在編寫第一個用戶端應用程式之前完成必要的準備事項。您也可以在這份指南的側欄中找到更多進階指南，例如[查詢所有搜尋資料](https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data?hl=zh-tw)的指南。
2. [參考資料章節](https://developers.google.com/webmaster-tools/v1/api_reference_index?hl=zh-tw)詳細介紹了查詢參數、用量限制及此 API 會傳回的錯誤。
3. [API 範例](https://developers.google.com/webmaster-tools/v1/libraries?hl=zh-tw)提供了多種程式設計語言的程式碼範例連結，方便您立即上手使用。

### Google 數據分析

[Google 數據分析](https://marketingplatform.google.com/about/data-studio/?hl=zh-tw)是資訊主頁解決方案，可協助您整合不同來源的資料、進行探索並運用資料發揮影響力。這項工具提供 [Search Console 連接器](https://support.google.com/datastudio/answer/7314895?hl=zh-tw)，可以將各種指標和維度匯入您的資訊主頁。如果您想讓 Search Console 和其他工具的資料並排顯示，這項功能就能派上用場。

如果想嘗試一下，您可以使用[這個範本](https://datastudio.google.com/c/reporting/0B_U5RNpwhcE6QXg4SXFBVGUwMjg/page/6zXD/preview?hl=zh-tw)視覺化呈現您的資料，只要點選頁面右上角的 [使用範本] 即可連結資料。如要進一步瞭解如何使用這份報告，以及當中提供哪些深入分析資訊，請參閱這份[逐步指南](https://online-behavior.com/analytics/search-console-data-studio)。假如您只是想體驗一下，這裡有一份運用上述範本和範例資料所產生的報告。

如果您對新的下載功能或 Search Console 資料的一般使用方式有任何趣味的應用或意見，歡迎透過 [Twitter](https://twitter.com/googlesearchc) 告訴我們。希望這些更豐富而實用的資料對您有幫助！

發文者：Search Console 團隊的 Sion Schori 和 [Daniel Waisberg](https://www.danielwaisberg.com)
