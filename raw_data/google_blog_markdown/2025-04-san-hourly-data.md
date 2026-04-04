# The Search Analytics API now supports hourly data
- **發佈日期**: 2025-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/04/san-hourly-data
- **來源類型**: article
- **來源集合**: google-search-central
---
Wednesday, April 9, 2025

A few months ago, we announced an improved way to view
[recent performance data in Search Console](/search/blog/2024/12/recent-data-search-console).
The "24 hours" view includes data from the last available 24 hours and appears with a delay of
only a few hours. This view can help you find information about which pages and queries are
performing in this recent timeframe and how content you recently published is picking up.

Today, we're adding support for hourly data to the
[Search Analytics API](/webmaster-tools/v1/searchanalytics/query),
we heard ecosystem requests to make this data more accessible loud and clear. As a result, we're
adding hourly data to the API and with a wider scope than the product interface: while the product
displays hourly data only for the past 24 hours, the API will return data for up to 10 days with
an hourly breakdown. This will allow developers to create solutions to show not only hourly data
for the latest day, but also to compare the most recent day to the same day in the previous week,
which can be useful when analyzing patterns for the days of the week.

## How to pull hourly data from the Search Analytics API

In order to make hourly data available in the Search Analytics API, we're introducing 2 changes to
the [API request body](/webmaster-tools/v1/searchanalytics/query#request-body):

* New `ApiDimension` named `HOUR` for you to group the response by
  hour.
* New `dataState` value named `HOURLY_ALL`, which should be used when
  grouping by HOUR. This will indicate that hourly data might be partial.

In the following section we provide a sample API request and a sample response for reference.

### Sample API request

```
{
  "startDate": "2025-04-07",
  "endDate": "2025-04-07",
  "dataState": "HOURLY_ALL",
  "dimensions": [
    "HOUR"
  ]
}
```

### Sample API response

```
{
  "rows": [
    {
      "keys": [
        "2025-04-07T00:00:00-07:00"
      ],
      "clicks": 17610,
      "impressions": 1571473,
      "ctr": 0.011206046810858348,
      "position": 10.073871456906991
    },
    {
      "keys": [
        "2025-04-07T01:00:00-07:00"
      ],
      "clicks": 18289,
      "impressions": 1662252,
      "ctr": 0.011002543537321658,
      "position": 9.5440029550272758
    },
    {
      "keys": [
        "2025-04-07T02:00:00-07:00"
      ],
      "clicks": 18548,
      "impressions": 1652038,
      "ctr": 0.011227344649457216,
      "position": 9.81503633693656
    },
    {
      "keys": [
        "2025-04-07T03:00:00-07:00"
      ],
      "clicks": 18931,
      "impressions": 1592716,
      "ctr": 0.01188598595104212,
      "position": 9.4956935197486558
    },
    {
      "keys": [
        "2025-04-07T04:00:00-07:00"
      ],
      "clicks": 20519,
      "impressions": 1595636,
      "ctr": 0.012859449147549943,
      "position": 9.4670100198290843
    },
    …
  ],
  "responseAggregationType": "byProperty"
}
```

We hope that this new data will help you better monitor your recently published content in a more
effective way and help you take action in a timely manner. We would love to hear your thoughts on
how this new view works for you and to hear any suggestions on how to make it even better. If you
have any feedback, questions, or comments, you can find us on
[LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/)
or post in the [Google Search Central Community](https://support.google.com/webmasters/threads?thread_filter=(category:search_console)).

Posted by [Tali Pruss](https://www.linkedin.com/in/talipruss/),
Software Engineer, and [Daniel Waisberg](/search/blog/authors/daniel-waisberg), Search
Advocate
