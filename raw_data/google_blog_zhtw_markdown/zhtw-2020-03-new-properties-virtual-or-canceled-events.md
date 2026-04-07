# 新增活動屬性：線上舉行、已延後和已取消
- **發佈日期**: 2020-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/03/new-properties-virtual-or-canceled-events?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 3 月 17 日，星期二

由於 COVID-19 目前在全球各地引發疫情，導致許多活動不得不取消、延後，或是改以線上形式舉辦。儘管情況瞬息萬變，Google 仍致力於即時向使用者顯示最準確的活動資訊，所以特別在[開發人員說明文件](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw)中新增了一些選用屬性，希望能派上用場。這些屬性適用於所有地區和語言，是我們為服務發布者和使用者所執行的其中一項[架構更新](https://blog.schema.org/2020/03/schema-for-coronavirus-special)作業。如果您的活動有異動情況，請務必參考以下的提示，協助 Google 即時掌握最新動態。

## 更新活動狀態

schema.org 的 `eventStatus` 屬性可用於設定活動狀態，尤其是活動取消、延後或改期的狀態。這項資訊實用的地方在於，Google 可以據此向使用者顯示目前的活動狀態，而不是從活動搜尋服務中直接排除活動。

* **如果活動已取消**：請將 [`eventStatus`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#eventstatus) 屬性設為 [`EventCancelled`](https://schema.org/EventCancelled)，並保留活動 [`startDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#startdate) 屬性中的原始日期。
* **如果活動已延後 (但日期未知)**：在知道確切的延後日期前，請保留活動 [`startDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#startdate) 屬性中的原始日期，並將 [`eventStatus`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#eventstatus) 屬性更新為 [`EventPostponed`](https://schema.org/EventPostponed)。[`startDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#startdate) 是用於辨識這場活動的必要屬性；此外，在新的舉辦日期確定前，我們也需要 [`startDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#startdate) 屬性中的原始日期。等新的舉辦日期確認後，您就可以將 `eventStatus` 改成 [`EventRescheduled`](https://schema.org/EventRescheduled)，並更新 [`startDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#startdate) 和 [`endDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#enddate) 的日期資訊。
* **如果已確定活動延後的日期**：請將 [`startDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#startdate) 和 [`endDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#enddate) 改成對應的新日期。如有需要，您也可以將 [`eventStatus`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#eventstatus) 欄位標示為 [`EventRescheduled`](https://schema.org/EventRescheduled)，並新增 [`previousStartDate`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#previous-start-date)。
* **如果現場活動改成只在線上舉辦**：您可以視需要將 [`eventStatus`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#eventstatus) 欄位更新為 `EventMovedOnline`，指出活動形式已變更。

如需 `eventStatus` 屬性的詳細實作資訊，請參閱[開發人員說明文件](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#eventstatus)。

## 標示活動只在線上舉辦

隨著越來越多活動改為只在線上舉辦，我們也積極地想辦法在 Google 搜尋中對使用者顯示這項資訊。如果您的活動只開放線上參與，請務必使用下列屬性：

* 將地點設為 [`VirtualLocation`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#virtual-location) 類型。
* 將 [`eventAttendanceMode`](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#event-attendance-mode) 屬性設為 [`OnlineEventAttendanceMode`](https://schema.org/OnlineEventAttendanceMode)。

如需 `VirtualLocation` 類型的詳細實作資訊，請參閱[開發人員說明文件](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#virtual-location)。

**注意**：雖然 `VirtualLocation` 和 `eventAttendanceMode` 在 Schema.org 上仍處於開發階段，但您已經可以使用這些屬性。

## 向 Google 告知活動異動

變更標記後，請務必[通知 Google](https://developers.google.com/search/docs/guides/submit-URLs?hl=zh-tw)。我們建議您[透過伺服器自動產生 Sitemap](https://www.youtube.com/watch?v=y0TPINzAVf0&hl=zh-tw)，這可以有效確保搜尋引擎盡快發現您的新內容和更新內容。

如有任何問題，歡迎透過[網站管理員論壇](https://support.google.com/webmasters/community?hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 告訴我們。

發文者：活動搜尋服務產品經理 Emily Fifer
