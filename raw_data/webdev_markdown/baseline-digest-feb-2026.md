# February 2026 Baseline monthly digest
- **發佈日期**: 2026-03-30
- **作者**: web.dev
- **來源 URL**: https://web.dev/blog/baseline-digest-feb-2026?hl=en
- **來源類型**: article
- **來源集合**: web-dev
---
Published: March 30, 2026

February has been another eventful month for the web platform. From enhanced security with Trusted types to a more ergonomic CSS syntax for complex shapes, the tools at our disposal continue to mature across all major browser engines.

In this digest, we'll take a look at the features that reached Baseline milestones this month, helping you build a more robust and capable web with interoperability in mind.

## Interop 2026 has launched

Last month, Interop 2026 launched, which is an effort to increase the interoperability of web features. This effort involves representatives from companies that substantially contribute to browser rendering engines:

* [Apple](https://webkit.org/blog/17818/announcing-interop-2026/)
* [Google](/blog/interop-2026)
* [Igalia](https://igalia.com/news/interop-2026.html)
* [Microsoft](https://blogs.windows.com/msedgedev/2026/02/12/microsoft-edge-and-interop-2026/)
* [Mozilla](https://hacks.mozilla.org/2026/02/launching-interop-2026/)

Interop is an important initiative because emerging web features are prioritized, and much effort goes into landing high-priority features in all major browser engines. As with years past, there is [a dashboard available](https://wpt.fyi/interop-2026) to help you understand the pass rates of tests against identified key features.

## Baseline Newly available features

The following features became part of Baseline in February 2026, meaning they are now newly supported across all major browser engines.

### CSS `shape()` function

The `shape()` function is a new addition to the `<basic-shape>` data type, providing a more intuitive way to define complex paths for the `clip-path` and `offset-path` properties. Unlike the `path()` function, which requires a single string of SVG-like commands, `shape()` uses a standard CSS syntax. This lets you use CSS units (like `rem`, `em`, or `%`), math functions like `calc()`, and even CSS variables within your shape definitions. This makes creating responsive, dynamic shapes significantly easier for developers who are more comfortable with CSS than SVG path strings.

Learn more about the [CSS `shape()` function on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/Values/basic-shape/shape).

### Trusted types

Securing web applications against DOM-based cross-site scripting (XSS) attacks gets a major boost with the Baseline arrival of the Trusted Types API. This API requires developers to process data through "policies" before it can be passed into dangerous "sinks"—APIs that can execute code or render HTML, such as `Element.innerHTML` or `eval()`. By enforcing these policies through the Content Security Policy (CSP), you can ensure that only sanitized or "trusted" data is ever used in a way that could lead to an injection vulnerability, moving security checks from a manual review process to a platform-enforced guarantee.

Read the documentation for the [Trusted Types API on MDN](https://developer.mozilla.org/docs/Web/API/Trusted_Types_API).

### Map `getOrInsert()` and `getOrInsertComputed()`

JavaScript `Map` objects have become even more ergonomic with the addition of `getOrInsert()` and `getOrInsertComputed()`. These methods streamline the common pattern of checking if a key exists in a map and, if not, inserting a default value before returning it. `getOrInsert()` is useful for basic default values, while `getOrInsertComputed()` accepts a callback function. The callback is only executed if the key is missing, making it ideal for cases where the default value is computationally expensive to create.

Check out [Map `getOrInsert()` on MDN](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Map/getOrInsert).

### Zstandard compression

Zstandard (or zstd) is now a Baseline Newly available option for HTTP `Content-Encoding`. Known for its high compression ratios and extremely fast decompression speeds, Zstandard offers a modern alternative to Gzip and Brotli. It is particularly effective across a wide range of data types, helping developers reduce the amount of data sent over the wire and improve page load times without taxing the user's CPU during the decompression process.

Explore the [Content-Encoding header and Zstandard on MDN](https://developer.mozilla.org/docs/Web/HTTP/Reference/Headers/Content-Encoding).

## Baseline Widely available features

This month, an internationalization tool became Baseline Widely available.

### The `dirname` HTML attribute

The `dirname` attribute is now Baseline Widely available. This attribute can be added to `<input>` and `<textarea>` elements to automatically capture the directionality (either `ltr` for left-to-right or `rtl` for right-to-left) of the text entered by the user. When the form is submitted, the browser sends an additional field—named after the value of the `dirname` attribute—containing the directionality. This is an essential feature for applications that support multilingual users, ensuring that the server receives the context necessary to display or process text correctly in its intended direction.

Find more details on the [dirname HTML attribute on MDN](https://developer.mozilla.org/docs/Web/HTML/Reference/Elements/input#dirname).

## That's a wrap

As usual, let us know if we missed anything Baseline-related, and we'll make sure it gets captured in a future edition! If you have any questions or want to provide feedback on Baseline, you can file an issue in our [issue tracker](https://github.com/web-platform-dx/web-features/issues).
