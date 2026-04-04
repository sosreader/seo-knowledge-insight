# Search Console regex filters update and quick tips
- **發佈日期**: 2021-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/06/regex-negative-match
- **來源類型**: article
- **來源集合**: google-search-central
---
Wednesday, June 02, 2021

We recently announced [improved data filtering](/search/blog/2021/04/performance-report-data-filtering)
for Search Console Performance reports, and we were delighted to see the [community
reaction](https://twitter.com/googlesearchc/status/1379775388193320962) to the announcement.

We were also interested in the feedback we received, as always, and we saw many requests to complete the picture by adding a negative match option
to the regular expression (regex) filter.

The good news is that starting today **the Performance report filter supports both matching and not matching regex filters**. The option
is available through a secondary dropdown, which appears after picking the "Custom (regex)" option in the filter selector, as shown in the screenshot
below. Learn more about [filtering search performance data](https://support.google.com/webmasters/answer/7576553#filteringdata).

![Search Console Performance report regex filter](/static/search/blog/images/negative-match-regex.png "Search Console Performance report regex filter")

## Quick tips on using regex on Search Console

We also thought it would be helpful to provide some quick tips if you’re just starting with regex.

First of all, what *is* a regular expression? In a few words, it is a sequence of characters that specifies a search pattern. You can use it
to create advanced filters to include or exclude more than just a word or a phrase. When using regex, you can use a number of metacharacters, which are
characters that have a special meaning, such as defining a search criteria. Check the [RE2 regex
syntax reference](https://github.com/google/re2/blob/main/doc/syntax.txt) for a reference on all metacharacters supported by Search Console.

If you’re wondering when you should use regex as opposed to other filter types, here are a few examples when to use regex instead of other filters:

* **Segment users that already know your brand** - Use regex that specify multiple variants of your company name,
  including misspellings. This will inform you what type of queries each group is using and which section of your website is attracting each audience.
  For example, if your company’s names is `Willow Tree`, you might want to create a filter for all variants like
  this: `willow tree|wilow tree|willowtree|willowtee` (the `|` metacharacter represents an OR statement).
* **Analyze traffic to a website section** - Use regex that focus on specific directories on your website, this can help you
  understand what are common queries for each of your content areas. For example, if your URL structure is `example.com/[product]/[brand]/[size]/[color]`
  and you'd like to view traffic leading to green shoes, but you don't care about the brand or the size, you might use `shoes/.*/green`
  (`.*` matches any character any number of times).
* **Understand user intent** - Use regex to analyze which types of queries are bringing users to different sections of your website.
  For example, you might be interested in queries containing question words; a query filter `what|how|when|why` might
  show results that indicate your content should easily answer questions, maybe through an FAQ. Another example would be queries containing (or not)
  transactional words such as `buy|purchase|order`. This might also show which product names are more commonly or rarely used
  with these expressions.

Check the Search Console help center for [common regular
expressions](https://support.google.com/webmasters/answer/7576553#regexp_glossary). If you have any cool examples of what to use regex for, share them on Twitter using the hashtag `#performanceregex`.

If you have any questions or concerns, please reach out on the [Google Search Central Community](https://support.google.com/webmasters/threads?thread_filter=(category:search_console)) or on [Twitter](https://twitter.com/googlesearchc).

Posted by [Daniel Waisberg](https://www.danielwaisberg.com), Search Advocate
