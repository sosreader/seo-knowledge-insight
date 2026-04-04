# Improving Search Console ownership token management
- **發佈日期**: 2024-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/04/search-console-ownership-token-management
- **來源類型**: article
- **來源集合**: google-search-central
---
Tuesday, April 16, 2024

We're rolling out further improvements to [Search Console's user and permission management](https://search.google.com/search-console/users),
incorporating capabilities related to unused ownership tokens management. Tokens are the codes used for website ownership verification
in Search Console, Merchant Center, and other Google products. We have seen cases where these were accidentally left behind after
owners have moved on. In February 2023, we rolled out [improvements
to the user and permissions management report](/search/blog/2023/02/search-console-user-permissions-update). The latest changes will improve the accuracy and reflect the actual state of
unused ownership tokens.

You will now be able to verify whether an unused ownership token has been removed from the site by following this flow:

1. Visit the [Users and permissions interface](https://search.google.com/search-console/users)
2. Click "Unused ownership tokens"
3. Choose the tokens you'd like to remove and click "Remove" (see screenshot below)
4. Click "Verify removal" to get update for the unused ownership token

![Search Console screenshot showing ownership token management management](/static/search/blog/images/search-console-token-management.png)

As a reminder, a best practice for managing user permissions in Search Console: When removing a previous verified owner, be sure to
[remove all verification tokens
for that user](https://support.google.com/webmasters/answer/7687615#manage-users). The update rolled out today lets you verify the removal of the unused verification token so that removed owners
cannot regain access to the property.

As always, we love to hear feedback from you. You can use the feedback form within Search Console or the
[help forums](https://support.google.com/webmasters/go/community) to ask questions or submit feedback.

Posted by [Nir Kalush](/search/blog/authors/nir-kalush), Product Manager and Mohamad Sarsour, software engineer on the Search Console team
