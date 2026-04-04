# List your courses with new course info structured data
- **發佈日期**: 2023-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/11/new-course-info-markup
- **來源類型**: article
- **來源集合**: google-search-central
---
Wednesday, November 15, 2023

As people continue to search for courses on Google, the desire for more detailed course
information has grown. Today, we are announcing a new set of recommendations to provide
course structured data to Google. Publishers now have the opportunity to surface supplemental
course information on Google Search by providing detailed information like pricing, educational
level, ratings, and length with structured data. This data can appear in the course info rich
result, which is a new carousel feature in Google Search that helps learners discover and compare
courses that fit their unique needs.

## Displaying your courses within course structured data features

![An illustration of how course info may show up on Google Search](/static/search/docs/images/course-info-rich-result.png)

For the past few years, Google has been supporting a [course list](/search/docs/appearance/structured-data/course)
markup feature (previously called "Course"), where a single publisher could provide course
structured data (name, description, and publisher). The course list rich result will continue to
be supported, and your traffic will not be affected regardless of whether you decide to add the
new course info markup. We will continue to use the same [schema.org structured data type](https://schema.org/Course)
for both features.

The new [course info developer documentation](/search/docs/appearance/structured-data/course-info)
explains how to fill required and recommended fields. Your courses can then be eligible to show in
both the existing course listing feature and the new course info feature if you meet the
[feature guidelines and eligibility criteria](/search/docs/appearance/structured-data/course-info#guidelines).

## Verifying and monitoring your structured data with Search Console

To help you monitor and fix your structured data, we're adding a new course info
[Rich result report](https://support.google.com/webmasters/answer/7552505)
in Search Console. It shows valid and invalid structured data items for pages with course info
structured data, and the issues causing items to become invalid. You can use the report to debug,
fix, and validate your structured data issues.

![Course info rich result report in Search Console](/static/search/blog/images/course-info-report.png)

Additionally, you can use the [Rich result test](https://search.google.com/test/rich-results)
in Search Console to test the validity of your course info markup by submitting the URL of a page
or a code snippet. Using the tool, you can confirm whether or not your markup is valid instantly
without waiting for the rich result report to be updated.

![Course info in the Rich Results Test](/static/search/blog/images/course-info-rrt.png)

We hope this new markup makes it easier for you to show your course information on Google. If you
have any questions or concerns, please reach out to us through the
[Google Search Central Community](https://support.google.com/webmasters/threads?thread_filter=(category%3Astructured_data)).

Posted by [Candice Denic](/search/blog/authors/candice-denic),
Google Learning Product Manager and Ashwin Vaidyanathan, Google Learning Software Engineer
