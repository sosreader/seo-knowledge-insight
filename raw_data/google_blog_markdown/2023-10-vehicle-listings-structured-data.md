# Vehicle listing structured data for car dealerships
- **發佈日期**: 2023-10-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/10/vehicle-listings-structured-data
- **來源類型**: article
- **來源集合**: google-search-central
---
Monday, October 16, 2023

Vehicle listings on Google allows car dealerships to show their for-sale inventory on Google Search and other
Google surfaces. It is currently available in the US and US territories. Today, we're announcing
a new and simpler way to provide for-sale vehicle inventory data to Google.

![Image showing how vehicle listing rich results can be shown on Google Search](/static/search/blog/images/vehicle-listing-rich-resut.png)

Now, car dealerships of all sizes can be eligible for vehicle listings on Google by using the
[vehicle listing markup](/search/docs/appearance/structured-data/vehicle-listing). The existing
[feed method](https://developers.google.com/vehicle-listings/reference/feed-specification)
remains a good option for car dealerships that are comfortable with creating and maintaining feed files.
We recommend using the markup for those who haven't yet signed up for vehicle listings on Google and prefer
a simpler setup via markup.

You can implement vehicle listing markup on your car details pages to provide basic car information along with
their availability. See our [documentation](/search/docs/appearance/structured-data/vehicle-listing)
for more details.

We're also making it easier to monitor and fix the structured data needed for this feature using the Search Console
reports and tools.

## Rich result reports in Search Console

To help you monitor markup issues, we are also beginning to support vehicle listing structured data in a new
[Rich result report](https://support.google.com/webmasters/answer/7552505)
in Search Console that shows valid and invalid items for pages with structured data.

![Screenshot of the new Vehicle listings rich result report in Search Console](/static/search/blog/images/vehicle-listings-status-report.png)

## Rich Results Test

You can also test your structured data using the [Rich Results Test](https://search.google.com/test/rich-results)
by submitting the URL of a page or a code snippet. Using the tool, you can confirm whether or not your markup
is valid instantly without waiting for Rich result reports to be updated.

![Screenshot of the new Vehicle listings validation in the rich results test](/static/search/blog/images/vehicle-listing-rich-resut-test.png)

We hope these additions will make it easier for car dealerships to connect with potential customers on Search. If you have any
questions or concerns, please reach out to us via the [Google Search Central Community](https://support.google.com/webmasters/threads?thread_filter=(category%3Astructured_data))
or on [Twitter](https://twitter.com/googlesearchc).

Posted by Daniel Yosef and Alexander Ikonomidis, Google Search software engineers
