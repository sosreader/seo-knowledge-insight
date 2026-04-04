# New in structured data: Pros and cons
- **發佈日期**: 2022-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/08/pros-and-cons-structured-data
- **來源類型**: article
- **來源集合**: google-search-central
---
Friday, August 5, 2022

Product reviews are a valuable resource for users researching which product to buy.
Product reviews often contain a list of pros and cons, which our research has shown
to be popular with shoppers when making their purchasing decisions.
Because of their importance to users, Google Search may highlight
[pros and cons](/search/docs/appearance/structured-data/product#pros-cons)
in the product review snippet in Search results.

![Example search results snippet highlighting pros and cons from an editorial review](/static/search/blog/images/pros-and-cons-structured-data.png "Example search results snippet highlighting pros and cons from an editorial review")

You can tell Google about your pros and cons by supplying
[pros and cons structured data](/search/docs/appearance/structured-data/product#pros-cons)
on editorial review pages. When you're adding structured data to your web pages, you can use
[Rich Results Test](https://search.google.com/test/rich-results)
to make sure it's correct and valid for Google Search.
The tool has been recently extended to check for pros and cons structured data in addition to
all the other structured data types supported by Google Search.

If you do not provide structured data,
Google may try to automatically identify pros and cons listed on the web page.
Google will prioritize supplied structured data provided by you over automatically extracted data.
We tested this with website owners, and received positive feedback on this capability.

Here is an example web page with JSON-LD encoded structured data that could be used for the
above search results experience.
Note that the text in the structured data must match the text on your page.

```
<html>
  <head>
    <title>Cheese Knife Pro review</title>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Cheese Knife Pro",
        "review": {
          "@type": "Review",
          "name": "Cheese Knife Pro review",
          "author": {
            "@type": "Person",
            "name": "Pascal Van Cleeff"
          },
          "positiveNotes": {
            "@type": "ItemList",
            "itemListElement": [
              {
                "@type": "ListItem",
                "position": 1,
                "name": "Consistent results"
              },
              {
                "@type": "ListItem",
                "position": 2,
                "name": "Still sharp after many uses"
              }
            ]
          },
          "negativeNotes": {
            "@type": "ItemList",
            "itemListElement": [
              {
                "@type": "ListItem",
                "position": 1,
                "name": "No child protection"
              },
              {
                "@type": "ListItem",
                "position": 2,
                "name": "Lacking advanced features"
              }
            ]
          }
        }
      }
    </script>
  </head>
  <body>
    . . .
    <p>Pros:</p>
    <ul>
      <li>Consistent results</li>
      <li>Still sharp after many uses</li>
    </ul>
    <p>Cons:</p>
    <ul>
      <li>No child protection</li>
      <li>Lacking advanced features</li>
    </ul>
    . . .
  </body>
</html>
```

Currently, only editorial product review pages are eligible for the pros and cons enhancement
in Search, not merchant product pages or customer product reviews.
The experience is available in Dutch, English, French, German, Italian, Japanese, Polish,
Portuguese, Spanish, and Turkish in all countries where Google Search is available.

For more information on how to implement pros and cons structured data, check out the
Google Search Central documentation on
[Product structured data](/search/docs/appearance/structured-data/product#pros-cons).
For additional advice, please check out Google Search Central
[help pages](/search/docs)
and our public
[forum](https://support.google.com/webmasters/community).

Posted by Pascal Van Cleeff (Software Engineer) and
[Alan Kent](https://twitter.com/akent99) (Search Advocate)
