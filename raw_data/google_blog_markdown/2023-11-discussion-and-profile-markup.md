# New in structured data: discussion forum and profile page markup
- **發佈日期**: 2023-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/11/discussion-and-profile-markup
- **來源類型**: article
- **來源集合**: google-search-central
---
Monday, November 27, 2023

Today we're announcing support for [profile page](/search/docs/appearance/structured-data/profile-page)
and [discussion forum](/search/docs/appearance/structured-data/discussion-forum)
structured data for use in Google Search, including new reports in Search Console. This markup
works with Google Search features that are designed to show first-person perspectives from social
media platforms, forums, and other communities. Implementing this structured data will help
ensure what Search shows in these features is as accurate and complete as possible.

![An illustration of a Perspectives filter in search results](/static/search/blog/images/perspectives-social.png)

## Highlighting creator information and identifying forum content

![An illustration of creator information in search results](/static/search/blog/images/social-profile-search-result.png)

[`ProfilePage`
markup](/search/docs/appearance/structured-data/profile-page) is designed for any site where creators (either people or organizations) share
first-hand perspectives. It allows Google Search to better identify information about the creator,
such as their name or social handle, profile photo, follower count, or the popularity of their
content. Our [Perspectives](https://blog.google/products/search/google-search-perspectives/)
and [Discussions and forums](https://blog.google/products/search/google-search-discussions-forums-news/)
features both make use of `ProfilePage` markup.

![An illustration of the Discussions and Forums feature](/static/search/docs/images/discussions-and-forums-rich-result.png)

[`DiscussionForumPosting` markup](/search/docs/appearance/structured-data/discussion-forum)
is designed for any forum-style site where people collectively share first-hand perspectives. It
allows Google Search to better identify forum sites and online discussions across the web. Forums
with this markup are considered for having their content appear in the Perspective and "Discussions
and forums" features. However, the use of the markup does not guarantee appearance.

## Q&A markup vs. forum markup

If you're already using Q&A markup for your question and answer themed user forum, we are also
updating the [Q&A structured data documentation](/search/docs/appearance/structured-data/qapage)
to be more in line with the richness of the new discussion forum guidelines.

You don't need to use both types of structured data on the same page; instead, we recommend that
you use the one that's best suited to your use case:

* **Q&A forums**: If your forum is structured by a question that's followed by
  answers, use [Q&A markup](/search/docs/appearance/structured-data/qapage).* **For general forums**: If your forum structure is more general and isn't strictly question
    and answer content, use [`DiscussionForumPosting`](/search/docs/appearance/structured-data/discussion-forum).

## Verifying and monitoring your structured data with Search Console

To help you monitor discussion threads and profile page markup issues, we're launching profile
page and discussion forum [rich result reports in Search Console](https://support.google.com/webmasters/answer/7552505)
that show errors, warnings, and valid items related to your marked-up pages. We're also providing
support for both features in the Rich Results Test to help you test and validate your markup.

![Profile page rich result status report](/static/search/blog/images/profile-page-report.png)
![Discussion forum rich result status report](/static/search/blog/images/discussion-forum-report.png)

We would love to hear your thoughts on how discussion thread and profile page structured data works
for you. Send us any feedback either through [social media](https://twitter.com/googlesearchc)
or [our forum](https://support.google.com/webmasters/threads?thread_filter=(category:structured_data)).

Posted by [Thomas Han](/search/blog/authors/thomas-han),
Google Search
