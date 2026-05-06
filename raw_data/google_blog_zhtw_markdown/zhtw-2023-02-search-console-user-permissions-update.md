# 更新 Search Console 的使用者和權限管理功能
- **發佈日期**: 2023-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/02/search-console-user-permissions-update?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 2 月 22 日，星期三

即日起，我們將更新 [Search Console 的使用者和權限](https://search.google.com/search-console/users?hl=zh-tw)，以加入與擁有權和使用者管理相關的功能。過去，只有舊版網站管理員工具服務才提供這些功能。

多年來，網站管理員驗證工具一直為我們的社群提供良好的服務。我們推出這項功能，進一步朝著[將各項功能遷移至 Search Console](https://developers.google.com/search/blog/2018/01/introducing-new-search-console?hl=zh-tw) 的目標邁進，確保使用者享有更優質、快速、現代化的使用體驗。

## Search Console 中的全新使用者管理功能

Search Console 的使用者權限和權限管理中加入的功能包括：

* 區分已驗證擁有者和委派擁有者
* 更輕鬆地立即移除已驗證擁有者 (無需移除擁有權權杖)
* 能夠變更委派擁有者的權限等級 (擁有者、完整、限制)
* 可查看所有目前和先前使用者的資源驗證權杖，特別是查看之前擁有者的剩餘權杖
* 擁有權事件記錄

## 最佳做法

提醒您，以下是在 Search Console 中管理使用者權限的一些最佳做法。

首先，僅授予使用者完成工作所需的[權限等級](https://support.google.com/webmasters/answer/7687615?hl=zh-tw#permissions)。您可以透過「更多動作」選單來變更未驗證擁有者的權限等級。請務必撤銷或變更不再使用資源的使用者權限等級，以及定期透過 Search Console 中的[使用者和權限](https://search.google.com/search-console/users?hl=zh-tw)頁面稽核及更新權限。

![Search Console 使用者和權限設定頁面](https://developers.google.com/static/search/blog/images/search-console-users-and-permissions.png?hl=zh-tw)

移除之前通過驗證的擁有者時，請務必[移除該使用者的所有驗證權杖](https://support.google.com/webmasters/answer/7687615?hl=zh-tw#manage-users)。這是今天我們推出的其中一個更新功能。您現在可以查看剩餘的擁有權權杖，讓已移除的擁有者無法重新取得資源的存取權。

![Search Console 設定頁面顯示剩餘擁有權權杖](https://developers.google.com/static/search/blog/images/search-console-leftover-ownership-tokens.png?hl=zh-tw)

提醒您，如果您只想要一次性分享特定 Search Console 報表，只要在該頁面上按一下「分享連結」即可，不必將使用者加入 Search Console。

我們將在未來幾個月內停用獨立的網站管理員中心驗證工具。一如往常，我們樂於聆聽使用者的意見。您可以透過 Search Console 或[說明論壇](https://support.google.com/webmasters/go/community?hl=zh-tw)中的意見回饋表單提出問題或提交意見回饋。

發文者：產品經理 [Nir Kalush](https://developers.google.com/search/blog/authors/nir-kalush?hl=zh-tw) 和 Search Console 團隊的軟體工程師 Itai Raz
