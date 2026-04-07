# 改善 Search Console 擁有權權杖管理作業
- **發佈日期**: 2024-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/04/search-console-ownership-token-management?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 4 月 16 日，星期二

我們將進一步強化 [Search Console 的使用者和權限管理](https://search.google.com/search-console/users?hl=zh-tw)，包括與未使用的擁有權權杖管理作業相關的功能。權杖是一組代碼，可在 Search Console、Merchant Center 和其他 Google 產品中驗證網站擁有權。我們也曾看過一些案例，權杖在擁有者轉移後仍意外保留下來。我們在 2023 年 2 月推出了[使用者和權限管理報表的強化項目](https://developers.google.com/search/blog/2023/02/search-console-user-permissions-update?hl=zh-tw)。最近的變更內容將提高準確率，反映出未使用擁有權權杖的實際狀態。

您現在可以按照以下流程，驗證未使用的擁有權權杖是否已從網站中移除：

1. 前往[使用者和權限介面](https://search.google.com/search-console/users?hl=zh-tw)
2. 按一下「未使用的擁有權權杖」
3. 選擇要移除的權杖，然後按一下「移除」(請參閱下方的螢幕截圖)
4. 按一下「確認移除」，即可取得未使用擁有權權杖的更新資訊

![Search Console 螢幕截圖：顯示擁有權權杖的管理功能](https://developers.google.com/static/search/blog/images/search-console-token-management.png?hl=zh-tw)

提醒您，在 Search Console 中管理使用者權限的最佳做法，是在移除先前的已驗證擁有者時，務必[移除該使用者的所有驗證權杖](https://support.google.com/webmasters/answer/7687615?hl=zh-tw#manage-users)。本次推出的更新內容可讓您確認未使用的驗證權杖是否已移除，讓已移除的擁有者無法重新取得資源存取權。

一如往常，我們樂於聆聽使用者的意見。您可以透過 Search Console 或[說明論壇](https://support.google.com/webmasters/go/community?hl=zh-tw)中的意見回饋表單提出問題或提交意見回饋。

發文者：產品經理 [Nir Kalush](https://developers.google.com/search/blog/authors/nir-kalush?hl=zh-tw) 和 Search Console 團隊軟體工程師 Mohamad Sarsour
