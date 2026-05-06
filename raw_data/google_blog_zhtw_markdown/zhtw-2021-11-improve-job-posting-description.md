# 提供完整說明以便求職者瞭解徵人啟事內容透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2021-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/11/improve-job-posting-description?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 11 月 1 日，星期一

我們發現只要調整 `description` 欄位內容，即可讓您的徵人啟事頁面更臻完善。

在 Google 搜尋的求職服務中，每則徵人啟事的 `description` 部分只會顯示 [`description`](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=zh-tw#description) 屬性中的文字。因此，請務必在 `description` 欄位中提供應徵資格、技能要求、福利等資訊。

以下螢幕截圖就是正確應用 `description` 欄位的例子：由於這則徵人啟事包含所有相關資料，因此使用者可以根據充分的資訊決定是否要應徵工作。

![Google 搜尋結果中的徵人啟事說明](https://developers.google.com/static/search/blog/images/job-posting-in-search.png?hl=zh-tw "Google 搜尋中的徵人啟事說明")

為了協助您比對完整的徵人啟事標記和不完整的徵人啟事標記有何不同，我們在下方提供了兩個實作例子。

以下例子呈現的是**完整的 `description` 欄位**。職缺的 `description` 欄位包含所有工作相關資訊，應徵資格也在其內。

```
{
   {
    "@context" : "https://schema.org/",
    "@type" : "JobPosting",
    "title" : "Software Engineer",
    "description" : "Software Engineer responsible for creating web applications. Knowledge of HTML, Javascript, APIs, and relational databases. Must have 2-5 years of experience.", // this description was shortened for this example
    "qualifications": "Knowledge of HTML, Javascript, APIs, and relational databases. Must have 2-5 years of experience." // this is an optional property
    }
  }
```

以下例子呈現的是**不完整的 `description` 欄位**。`description` 只包含職缺的簡短 `description`，而且只有 `qualifications` 屬性列出應徵資格。修正方式是在 `description` 欄位中納入 `qualifications` 欄位提供的所有資訊。

```
{
  {
  "@context" : "https://schema.org/",
  "@type" : "JobPosting",
  "title" : "Software Engineer",
  "description" : "Software Engineer responsible for creating web applications",
  "qualifications": "Knowledge of HTML, Javascript, APIs, and relational databases. Must have 2-5 years of experience."
  }
}
```

為了確保使用者可以在 Google 搜尋的求職服務中查看完整的職缺說明，請務必將您可能只在特定欄位 (例如 `qualifications` 屬性) 中提供的資訊全都補充到 `description` 欄位中。您不必移除那些提供更多細節的欄位，只要確保在 `description` 屬性中包含相同資訊即可。

如有任何疑問，歡迎前往[搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)與專家交流，或是透過 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：軟體工程師 Bobby Panczer
