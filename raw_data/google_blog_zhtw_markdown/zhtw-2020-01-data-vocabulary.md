# 即將停止支援 data-vocabulary
- **發佈日期**: 2020-01-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/01/data-vocabulary?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 1 月 21 日，星期二

所謂結構化資料架構，就是針對網路上以標記為基礎的應用環境，定義出有意義的通用架構，比如 [schema.org](https://schema.org/) 和 [data-vocabulary.org](https://data-vocabulary.org/)。隨著 schema.org 的使用量和普及程度越來越高，我們已決定專注於開發這種結構化資料架構。自 2020 年 4 月 6 日起，data-vocabulary.org 標記將不再適用於 [Google 複合式搜尋結果功能](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=zh-tw)。

為因應相關異動，Search Console 會從今天開始針對使用 data-vocabulary.org 架構的網頁發出警告，幫助大家提前做好準備。只要查看 Search Console，您就能輕鬆找出使用這種標記的網頁，並將 data-vocabulary.org 標記替換成 schema.org 標記。

## 進一步瞭解結構化資料

Google 會運用[結構化資料](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=zh-tw)標準化格式和通用架構，提供網頁本身與其中所述內容的資訊。這項資訊主要有兩個用途：

1. 瞭解網頁內容
2. 提供特殊搜尋結果功能和強化項目

## 什麼是結構化資料格式？

結構化資料格式定義了用來對描述性資料進行編碼的少量固定架構，這些格式包括 JSON-LD、RDFa 和微資料，通常是以 JSON 和 HTML 等較低級別的標準為基礎。如要進一步瞭解支援與建議的格式，請參閱[開發人員指南](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=zh-tw#structured-data-format)。

## 什麼是結構化資料架構？

結構化資料架構類似搭配結構化資料格式使用的字典，負責定義資料的類型 (`Person`、`Event`、`Organization`) 及其屬性和關係 (例如 `name`、`worksFor`)。由於格式和架構有所區別，所以使用者可以利用各種格式來搭配廣泛通用的相同架構。

## data-vocabulary 架構

Google 的「Data Vocabulary」專案是網路結構化資料開發史上的重要里程碑，因為這項專案促使我們與其他搜尋引擎合作打造了 schema.org。不過，由於 data-vocabulary 架構過時已久，所以一般會建議使用更廣泛通用的 schema.org 詞彙。也就是說，data-vocabulary.org 標記將不再適用於 Google 搜尋結果功能和強化項目。

請注意，這是此次異動產生的唯一影響。採用 data-vocabulary 架構的網頁仍然可以實現其他用途。

為了符合 Google 複合式搜尋結果功能的使用條件，建議您將採用 data-vocabulary.org 架構的結構化資料改成 schema.org 架構。

以下是將 data-vocabulary.org 改成 schema.org 的範例。

### data-vocabulary.org

```
<div itemscope itemtype="https://data-vocabulary.org/Breadcrumb">
<a href="https://www.example.com/dresses" itemprop="url">
<span itemprop="title">Dresses</span></a>
>
</div>
<div itemscope itemtype="https://data-vocabulary.org/Breadcrumb">
<a href="https://www.example.com/dresses/real" itemprop="url">
<span itemprop="title">Real Dresses</span></a>
>
</div>
```

### schema.org

```
<ol itemscope itemtype="https://schema.org/BreadcrumbList">
  <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
    <a itemprop="item" href="https://example.com/dresses"><span itemprop="name">Dresses</span></a>
    <meta itemprop="position" content="1" /></li>
  <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
    <a itemprop="item" href="https://example.com/dresses/real"><span itemprop="name">Real Dresses</span></a>
    <meta itemprop="position" content="2" /></li>
</ol>
```

您可以將任何程式碼片段貼到[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)的搜尋框中進行即時測試，快試試看吧！如有任何問題或意見，請造訪 [Google 網站管理員社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)。

發文者：標準開發人員服務代表 Dan Brickley 和 Search Console 產品經理 [Moshe Samet](https://www.linkedin.com/in/moshe-samet-5465326/)

---

**2020 年 4 月 6 日最新消息**：鑒於當前的 COVID-19 疫情事態，我們決定延後實施這項異動，並會在 2020 年 6 月重新評估此事。**2020 年 7 月 6 日最新消息**：我們已經開始淘汰這項功能。
