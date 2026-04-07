# 結構化資料的新功能：優缺點
- **發佈日期**: 2022-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/08/pros-and-cons-structured-data?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 8 月 5 日，星期五

當使用者研究要購買哪項產品時，產品評論提供了寶貴的資源。產品評論通常會同時列出優點和缺點，我們的研究顯示，購物者在做出購買決策時會大量參考這些優缺點。基於這些評論對使用者的重要性，Google 搜尋可能會在搜尋結果的產品評論摘錄中醒目顯示[優缺點](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw#pros-cons)。

![搜尋結果摘要範例醒目顯示編輯性質評論的優缺點](https://developers.google.com/static/search/blog/images/pros-and-cons-structured-data.png?hl=zh-tw "搜尋結果摘要範例醒目顯示編輯性質評論的優缺點")

你可以透過編輯性質的評論頁面提供[優缺點結構化資料](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw#pros-cons)，告知 Google 你的優缺點。在網頁中加入結構化資料時，你可以利用[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來確認結構化資料是否正確無誤，且適用於 Google 搜尋。
除了 Google 搜尋支援的所有其他結構化資料類型外，這項工具最近已擴大檢查是否有優缺點結構化資料。

如果你未提供結構化資料，Google 可能會嘗試自動辨識網頁列出的優缺點。
Google 會優先顯示你提供的結構化資料，而非自動擷取的資料。
我們與網站擁有者合作進行測試這項功能，並收到了正面的意見回饋。

以下是含有 JSON-LD 編碼結構化資料的網頁範例，可用於提供上述搜尋結果體驗。請注意，結構化資料中的文字必須與網頁上的文字一致。

```
<html>
  <head>
    <title>Cheese Knife Pro review</title>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Cheese Knife Pro",
        "review": {
          "@type": "Review",
          "name": "Cheese Knife Pro review",
          "author": {
            "@type": "Person",
            "name": "Pascal Van Cleeff"
          },
          "positiveNotes": {
            "@type": "ItemList",
            "itemListElement": [
              {
                "@type": "ListItem",
                "position": 1,
                "name": "Consistent results"
              },
              {
                "@type": "ListItem",
                "position": 2,
                "name": "Still sharp after many uses"
              }
            ]
          },
          "negativeNotes": {
            "@type": "ItemList",
            "itemListElement": [
              {
                "@type": "ListItem",
                "position": 1,
                "name": "No child protection"
              },
              {
                "@type": "ListItem",
                "position": 2,
                "name": "Lacking advanced features"
              }
            ]
          }
        }
      }
    </script>
  </head>
  <body>
    . . .
    <p>Pros:</p>
    <ul>
      <li>Consistent results</li>
      <li>Still sharp after many uses</li>
    </ul>
    <p>Cons:</p>
    <ul>
      <li>No child protection</li>
      <li>Lacking advanced features</li>
    </ul>
    . . .
  </body>
</html>
```

Google 搜尋的優缺點強化功能目前僅適用於編輯性質的產品評論網頁，不適用於商家產品網頁或消費者產品評論。
這項體驗適用於提供 Google 搜尋服務的所有國家/地區，包括荷蘭文、英文、法文、德文、義大利文、日文、波蘭文、葡萄牙文、西班牙文和土耳其文等語言版本。

如要進一步瞭解如何實作優缺點結構化資料，請參閱 Google 搜尋中心說明文件中的[產品結構化資料](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw#pros-cons)相關文章。
如需其他建議，請參閱 Google 搜尋中心[說明頁面](https://developers.google.com/search/docs?hl=zh-tw)和我們的公開[論壇](https://support.google.com/webmasters/community?hl=zh-tw)。

發文者：軟體工程師 Pascal Van Cleeff 和搜尋服務代表 [Alan Kent](https://twitter.com/akent99)
