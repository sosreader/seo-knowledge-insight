# Vidio 如何透過 Google 搜尋，為印尼使用者提供更符合當地需求的隨選影片 (VOD) 內容
- **發佈日期**: 
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/case-studies/vidio-case-study?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-case-studies
---
# Vidio 如何透過 Google 搜尋，為印尼使用者提供更符合當地需求的隨選影片 (VOD) 內容

發布日期：2024 年 6 月 4 日

## 關於 Vidio

Vidio 創立於 2014 年，是印尼最大的 [over-the-top (OTT) 媒體服務](https://en.wikipedia.org/wiki/Over-the-top_media_service)之一，隸屬於 Elang Mahkota Teknologi (Emtek) 媒體集團。Vidio 的目錄中收錄了超過 100 萬部影片，期望能增加各種類型的影片，為印尼使用者提供更豐富的內容。

## 導入 `VideoObject` 結構化資料

在這個重視當地語言 (印尼文) 的市場中，Vidio 的目標是在目錄中提供在地內容，並讓印尼使用者能在 Google 搜尋上找到這類內容。為達成目標，Vidio 在現有目錄中導入了 [`VideoObject` 標記](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw)。由於他們原本就採用[支援的影片檔案類型](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#supported-video-files) (M3U8 格式，遵循 [HLS](https://en.wikipedia.org/wiki/HTTP_Live_Streaming) 通訊協定)，因此無需變更。

不過，由於 M3U8 的運作方式，這種檔案格式可能很難讓 Googlebot 正確檢索及剖析。該檔案格式是一種參照圖，會指出組成整部影片物件的各位部分，也就是說，用戶端必須將這些部分拼接起來，才能播放完整影片。難題之一是，Googlebot 可能會遇到 M3U8 檔案參照的檔案無法存取的情況，導致整部影片位元組擷取作業失敗。為避免擷取問題，Vidio 為每個影片檔案[實作穩定網址](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#stable-url)，並確保 Googlebot 可以存取。

他們也採用了其他 [Google 搜尋中心影片最佳做法](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#supported-video-files)，包括：

* 新增適當的 `contentUrl` 屬性
* 使用[網址檢查工具](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)的「影片強化」部分，驗證標記是否已成功導入

![Vidio 透過 Search Console 的「影片強化」部分，驗證一部自家電視劇集的 VideoObject 標記導入情形](https://developers.google.com/static/search/case-studies/images/vidio-contenturl.png?hl=zh-tw)

## 成效

導入 `VideoObject` 標記的一年內，Vidio 發現影片網頁的曝光次數和點擊次數有所提升。Vidio 在 2022 年第 1 季至 2023 年第 1 季發布的影片數量增加了約 30%，新增 `VideoObject` 標記後，影片就有資格在 Google 的多個位置顯示。這使得 Google 搜尋上的影片曝光次數增加了約 3 倍，影片點擊次數增加了近 2 倍。Vidio 也參考了 Search Console 的[影片索引報表](https://support.google.com/webmasters/answer/9495631?hl=zh-tw)和[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)，這有助於他們找出並修正整個平台的問題。

3 倍

Google 搜尋上的影片曝光次數增幅

2倍

Google 搜尋上的影片點擊次數增幅

「Vidio 是印尼首要的 OTT 平台，將我們的影片在 Google 上的能見度最佳化，對影片內容搜尋者來說極為重要。我們的資料顯示，影片曝光次數和點擊次數都有顯著成長，這表示我們在提供一流使用者體驗方面的努力有成。」Vidio 總經理 Hermawan Sutanto 表示。

Google 搜尋「全部」分頁中的 Vidio

![Google 搜尋結果「全部」分頁中的 Vidio](https://developers.google.com/static/search/case-studies/images/vidio-in-all-tab.png?hl=zh-tw)

Google 搜尋「影片」分頁中的 Vidio

![Google 搜尋結果「影片」分頁中的 Vidio](https://developers.google.com/static/search/case-studies/images/vidio-in-video-tab.png?hl=zh-tw)
