# Clarifications about the SharedArrayBuffer object message
- **發佈日期**: 2021-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/03/sharedarraybuffer-notes
- **來源類型**: article
- **來源集合**: google-search-central
---
Friday, March 19, 2021

**Update on May 6, 2021**: Due to unexpected circumstances, the Chrome team decided to postpone the restriction on the `SharedArrayBuffer` object on desktop to Chrome 92 (originally Chrome 91).

Some of you might have received an email from Google Search Console with the subject "New requirements for `SharedArrayBuffers`".
We received feedback that the message was confusing, and wanted to give some more insight into the issue, so that you can decide which next steps are appropriate.
We also updated [the guide on enabling cross-origin isolation](https://web.dev/articles/cross-origin-isolation-guide) to include additional details.

## Why did I receive the message?

You received the message because we've detected that JavaScript on your website was using the [`SharedArrayBuffer`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer) object at the time of the message.
The usage might be due to frameworks, libraries, or other third-party content included within your website.

## What is the `SharedArrayBuffer`?

`SharedArrayBuffer` is a JavaScript object to share a memory space across threads on a website.
It was used by websites before the vulnerability called [Spectre](/web/updates/2018/02/meltdown-spectre) was found.
However, because Spectre was a CPU level vulnerability and it's unlikely to be fixed in the foreseeable future, browsers decided to disable the `SharedArrayBuffer` object.

While Chrome re-enabled it on desktop with [Site Isolation](https://security.googleblog.com/2018/07/mitigating-spectre-with-site-isolation.html) as a temporary remedy, [cross-origin isolation](https://web.dev/articles/coop-coep) was standardized as a way to safely enable the `SharedArrayBuffer` object.
Starting with version 92, planned to be released in late May 2021, Chrome will gate the `SharedArrayBuffer` object behind cross-origin isolation.
Firefox enabled the `SharedArrayBuffer` object on a cross-origin isolated environment as well in version 76.
We hope other browsers will follow soon.

## Finding `SharedArrayBuffer` object usage on your site

You have two options:

1. Use [Chrome DevTools](/web/tools/chrome-devtools) and inspect important pages.- (Advanced) Use the [Reporting API](/web/updates/2018/09/reportingapi) to send deprecation reports to a reporting endpoint.

Learn how to take the above approaches at [Determine where the `SharedArrayBuffer` object is used on your website](https://web.dev/articles/cross-origin-isolation-guide).

## Next steps

For next steps, we recommend:

1. Determine where the `SharedArrayBuffer` object is used on your website.- Decide if the usage is necessary.- Fix the issue by either removing the functionality, or by [enabling cross-origin isolation](https://web.dev/articles/cross-origin-isolation-guide).

If you haven't heard about the `SharedArrayBuffer` object, and you received a Search Console message about it, it's highly likely a third-party resource on your website is using it.
Once you determine which pages are affected, and who the owner of the resource is, reach out to the resource provider and ask them to fix the issue.

After Chrome 92 is released, the `SharedArrayBuffer` object without cross-origin isolation will no longer be functional.
In practice, this means that Chrome users on your site may experience degraded performance similar to other situations where the `SharedArrayBuffer` object is not supported.

We hope this clarification was useful, even if you didn't receive the message.
If you have any questions, we'd recommend posting in the [Search Central help community](https://support.google.com/webmasters/community) to get input from other experts.

Posted by [Eiji Kitamura](https://blog.agektmr.com/), Chrome Developer Advocate
