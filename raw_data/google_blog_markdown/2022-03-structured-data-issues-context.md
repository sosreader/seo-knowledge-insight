# Adding context to structured data issues in Search Console
- **發佈日期**: 2022-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/03/structured-data-issues-context
- **來源類型**: article
- **來源集合**: google-search-central
---
Monday, March 28, 2022

To help you identify structured data issues more effectively, starting tomorrow Search Console is adding more context to its error reporting.

For example, if a website doesn't provide the name of the author in `Review snippet`
markup, Search Console currently reports an error named **Missing field "name"**. Starting today, that error will be named
**Missing field "name" (in "author")**. The more detailed context in parenthesis can help you find the issues more easily in your structured data.

![Structured data issues context in Search Console](/static/search/blog/images/structured-data-issues-context.png)

This change will impact all [Search Console rich result status reports](https://support.google.com/webmasters/answer/7552505),
the [Search Console URL inspection tool](https://support.google.com/webmasters/answer/9012289) and
[Rich Results Test](https://search.google.com/test/rich-results), even if you haven’t changed your structured data markup:

* All your open issues that refer to nested properties will be automatically closed (for example, the `Missing field "name"` issue
  in the example above).
* You'll see new open issues with more context about what's missing (for example, the issue will say `Missing field "name" (in "author")`.
  To avoid overloading Search Console users with emails, we won't send notifications on the creation of these new issues.

Please note that if you requested Search Console to validate a fix before the change, you will need to revalidate the new issues.

In summary, this is simply a change in the issue name, it will not affect how Search Console detects errors, and all the issues that are being closed
will be replaced by a new issue with the additional context in the issue name.

If you have any questions or concerns, please reach out on the [Google
Search Central Community](https://support.google.com/webmasters/threads?thread_filter=(category:search_console)) or on [Twitter](https://twitter.com/googlesearchc).

Posted by [Moshe Samet](https://www.linkedin.com/in/moshe-samet-5465326/), Search Console Product Manager and [Ryan Levering](/search/blog/authors/ryan-levering), Google Search Engineering
