# Improved data filtering and comparison on Performance reports
- **發佈日期**: 2021-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/04/performance-report-data-filtering
- **來源類型**: article
- **來源集合**: google-search-central
---
Wednesday, April 07, 2021

The Search Console [Performance reports](https://support.google.com/webmasters/answer/7576553) allow users to
understand how people find their site on Google. Today, we’re introducing two improvements that will make the reports more useful: regular
expression (regex) filters and a revamped comparison mode.

## Filters now support regular expressions

In the Performance reports, you can already use filters to slice and dice your data. Until now, users could filter queries and page URLs
according to three patterns: containing a string, not containing a string, and exactly matching a string. Previously, Search Console
didn't support more complex cases, such as a query containing one out of a few optional strings.

Today, we’re introducing a new way to filter your data: [regular expressions](https://en.wikipedia.org/wiki/Regular_expression),
or regex. This will help you create more complex query and page based filters and answer more questions that interest them. For instance, let's say
your company is called 'cats and dogs' but is sometimes also abbreviated
as 'cats & dogs' or even 'c&d'. You can use a regex filter to capture all of
your branded queries by defining the regex filter: `cats and dogs|cats & dogs|c&d`

To use the new regex filter, create a query or page filter, select the dropdown menu and select **Custom**. To learn more, visit
the [regex filters](https://support.google.com/webmasters/answer/7576553#regex_filter) help center page.

![Search Console Performance regex filter](/static/search/blog/images/performance-regex-filter.png "Search Console Performance regex filter")

Sometimes, queries and pages are not available in the reports [to
protect user privacy](https://support.google.com/webmasters/answer/7576553#aboutdata) or due to storage limitations. In order to make sure our users are aware of this, we added a reminder that shows each time
a relevant filter is applied on queries or pages.

## Revamped comparison mode

You may have already been using the [compare mode](https://support.google.com/webmasters/answer/7576553#comparingdata) to
answer comparison based questions. Previously, if more than one metric was selected, the table wouldn’t contain a comparison column with the relative
difference in percentage.

Starting today, the comparison mode fully supports cases where more than a single metric is selected, and we’ve improved the interface to make it easier
to view those results side-by-side, almost doubling the area available for the data table. In addition, the comparison mode now supports the new
regex filter for queries and pages.

![Search Console Performance comparison mode](/static/search/blog/images/performance-comparison-mode.png "Search Console Performance comparison mode")

We hope that these new improvements will help you get more value from the Performance reports and identify valuable insights about your site’s performance data on Google.
If you have any questions or concerns, please reach out on the [Google
Search Central Community](https://support.google.com/webmasters/threads?thread_filter=(category:search_console)) or on [Twitter](https://twitter.com/googlesearchc).

Posted by [Ziv Hodak](/search/blog/authors/ziv-hodak), Search Console Product Manager
