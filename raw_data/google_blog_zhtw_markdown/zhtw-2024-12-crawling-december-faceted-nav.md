# 檢索 12 月：多面向導覽
- **發佈日期**: 2024-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/12/crawling-december-faceted-nav?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 12 月 17 日，星期二

我們剛發布[關於多面向導覽最佳做法的全新文件](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation?hl=zh-tw)，這份文件[最初是以網誌文章形式發布](https://developers.google.com/search/blog/2014/02/faceted-navigation-best-and-5-of-worst?hl=zh-tw)。以下是新說明文件頁面中一些重要部分的摘要。

多面向導覽是協助使用者在網站上找到所需內容的絕佳方式，但如果導入不當，可能會導致 SEO 災難。原因在於這種網站導覽方式可以產生近乎無限的網址數量，造成以下問題：

* **過度檢索：**搜尋引擎浪費時間檢索對搜尋使用者毫無價值的無數網址。
* **發現新內容的速度變慢：**過度檢索會導致發現重要新內容的速度變慢。

事實上，網站擁有者目前最常回報的過度檢索問題，多半是多面向導覽造成的。在多數情況下，只要遵守一些最佳做法，就能避免這個情形。不過，讓我們先回顧一下。

## 網址問題

多面向導覽中的每個篩選器組合，通常會產生不重複的網址。例如：

```
https://example.com/items.shtm?products=fish&color=radioactive_green&size=tiny
```

變更任何參數 (`product`、`color` 或 `size`) 都會建立新的網址，導致網址數量可能激增。這就是問題所在：有近乎無限的新網址等待發現。該如何解決這個問題呢？

## 兩種解決方法

1. **封鎖多面向導覽網址：**
   * 如果不需要將這些網址編入索引，請使用 `robots.txt` 禁止檢索。
   * 您也可以使用網址片段 (`#`) 做為篩選器，因為搜尋引擎通常會忽略這些片段。
2. **最佳化多面向導覽網址 (如果無論如何都需要檢索這些網址)：**
   * 使用標準 `&` 分隔符設定網址參數。💩 不是理想的參數分隔符號字元。
   * 在網址路徑中維持一致的篩選器順序。
   * 針對沒有任何結果的篩選器組合，傳回 `404` 狀態碼。
   * 除非沒有其他選擇 (例如[您有單頁應用程式](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=zh-tw#avoid-soft-404s))，否則請勿將空白結果重新導向至一般「找不到」頁面。

## 重要注意事項

* 您也可以使用 `rel="canonical"`，將變化版本指向主頁面，以便整合信號。這種做法需要一段時間才會生效。
* 在篩選器連結中使用 `rel="nofollow"` 可禁止檢索作業，但必須一致套用。也就是說，指向這些頁面的每個連結 (內部和外部) 都必須具有 `rel="nofollow"` 屬性。
* 檢索多面向導覽網址一律會耗用伺服器資源，且可能會影響新內容的探索。

如果您對[關於多面向導覽最佳做法的全新文件](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation?hl=zh-tw)有任何建議或需要說明，請使用該文件的意見回饋工具。如果您對多面向導覽很有興趣，希望與其他人討論相關主題，歡迎加入[搜尋中心社群](https://goo.gle/sc-forum)；此外，您也可以在 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 上找到我們。

發文者：[Gary Illyes](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw)

---

## 想進一步瞭解檢索嗎？請觀看完整的「檢索 12 月」系列影片：
