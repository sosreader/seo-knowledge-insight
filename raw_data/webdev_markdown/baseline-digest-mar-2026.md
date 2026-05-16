# March 2026 Baseline monthly digest
- **發佈日期**: 2026-04-14
- **作者**: web.dev
- **來源 URL**: https://web.dev/blog/baseline-digest-mar-2026?hl=en
- **來源類型**: article
- **來源集合**: web-dev
---
Published: April 14, 2026

It's been a busy month for the web platform! In March 2026, several powerful features crossed the interoperability threshold to become Newly available in Baseline, while a massive wave of established tools reached the Widely available milestone.

This month's progress highlights the incredible momentum of the web. From advanced layout controls and internationalization improvements to low-latency networking and sophisticated streaming capabilities, the platform is becoming more capable and robust for developers everywhere.

## Baseline Newly available features

The following features became interoperable across all core browser engines in March 2026.

### Math font family

The `math` value for the `font-family` property is specifically designed for rendering mathematical content. It ensures that MathML elements are displayed using fonts optimized for complex mathematical formulas, providing better spacing and character support for technical documents. [Learn more about the math font family on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/Properties/font-family)

### `Iterator.concat()`

This new static method for iterators lets developers combine multiple iterables (like Arrays, Sets, or custom iterators) into a single iterator. This simplifies code that needs to process sequences of data consecutively without manually nesting loops or creating intermediate arrays. [Learn more about `Iterator.concat()` on MDN](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Iterator/concat)

### Readable byte streams

The Streams API now includes full support for readable byte streams. These are optimized for handling binary data, allowing for efficient memory management by reading data directly into developer-supplied buffers. This is a game-changer for performance-critical applications handling large files or network data. [Learn more about Readable byte streams on MDN](https://developer.mozilla.org/docs/Web/API/Streams_API/Using_readable_byte_streams)

### Reporting API

The Reporting API provides a generic reporting mechanism for web applications to receive notifications about browser-level errors and violations, such as Content Security Policy (CSP) violations, deprecations, and crash reports. It centralizes these reports, sending them to a specified endpoint for easier monitoring. [Learn more about the Reporting API on MDN](https://developer.mozilla.org/docs/Web/API/Reporting_API)

### `WebTransport`

`WebTransport` is a modern API providing low-latency, bidirectional, client-server communication. Built on top of HTTP/3, it supports both reliable data transmission and unreliable datagrams, making it ideal for real-time applications like gaming and live streaming. [Learn more about WebTransport on MDN](https://developer.mozilla.org/docs/Web/API/WebTransport_API)

### `text-indent: each-line` declaration

The `each-line` keyword for `text-indent` extends indentation beyond just the first line of a block. When used, it indents the first line as well as any line following a hard line break (like a `<br>`), offering more granular control over typographic layouts. [Learn more about `text-indent: each-line` on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/Properties/text-indent#each-line)

### `text-indent: hanging` declaration

The `hanging` keyword inverts the default indentation behavior. It leaves the first line of a block at the start of the line while indenting all subsequent lines. This is a common requirement for bibliographies and specific editorial styles. [Learn more about `text-indent: hanging` on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/Properties/text-indent#hanging)

## Baseline Widely available features

In March 2026, these features moved into the Widely available tier, meaning they have been interoperable for 30 months and are safe to use in most production environments without polyfills.

### `contain-intrinsic-size` CSS property

Part of the CSS Containment module, `contain-intrinsic-size` allows developers to specify a placeholder size for elements that are under size containment. This prevents layout shifts when content is lazily loaded or hidden. [Learn more about `contain-intrinsic-size` on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/Properties/contain-intrinsic-size)

### `@counter-style` at-rule

The `@counter-style` rule allows developers to define custom numbering or bullet styles for lists. This goes far beyond the standard decimal or disc styles, allowing for complex, localized, or purely decorative list markers. [Learn more about `@counter-style` on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/At-rules/@counter-style)

### Device orientation events

These events provide data from the device's hardware, such as the gyroscope and accelerometer. Developers can use this information to create immersive experiences that respond to the physical movement and orientation of a user's device.
[Learn more about Device orientation events on MDN](https://developer.mozilla.org/docs/Web/API/Device_orientation_events)

### `hyphenate-character` CSS property

This property lets you define the character used at the end of a line when a word is hyphenated. While a standard hyphen is the default, this property provides the flexibility to use other characters for specific design or language requirements. [Learn more about hyphenate-character on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/Properties/hyphenate-character)

### `hyphens` CSS property

The `hyphens` property controls how the browser handles hyphenation when text wraps. You can set it to `none`, `manual` (using soft hyphens), or `auto` (allowing the browser to use its own hyphenation dictionary). [Learn more about the `hyphens` CSS property on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/Properties/hyphens)

### `image-set()` CSS function

The `image-set()` function allows CSS to deliver the most appropriate image based on the user's device capabilities, such as screen resolution. It functions similarly to the `srcset` attribute for `<img>` tags, ensuring high-quality visuals without wasting bandwidth. [Learn more about the `image-set()` CSS function on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/Values/image/image-set)

### `<link rel="modulepreload">`

This link relation allows developers to tell the browser to fetch and process JavaScript modules (and their dependencies) early in the page load process. This reduces the time spent on the critical path and improves the performance of module-heavy applications. [Learn more about `<link rel="modulepreload">` on MDN](https://developer.mozilla.org/docs/Web/HTML/Reference/Attributes/rel/modulepreload)

### Overflow media queries

The `overflow-block` and `overflow-inline` media features allow you to query how the device handles content that overflows the initial viewport. This is particularly useful for tailoring styles for different types of display devices, like paged media (printers) versus continuous scrolling screens. [Learn more about overflow media queries on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/At-rules/@media/overflow-block)

### `navigator.storage`

The Storage API provides a way to manage and query the storage persistence and quota of a website. It allows developers to check how much space is available and request that the browser keep data persistent rather than clearing it when storage is low. [Learn more about `navigator.storage` on MDN](https://developer.mozilla.org/docs/Web/API/Storage_API)

### `update` media query

The `update` media feature lets you detect how frequently the output device is able to modify the appearance of the content. This helps in distinguishing between fast-refresh screens (like smartphones) and slow-refresh or static displays (like e-ink readers). [Learn more about the `update` media query on MDN](https://developer.mozilla.org/docs/Web/CSS/Reference/At-rules/@media/update)

### CSS subgrid

CSS subgrid is a powerful extension of CSS Grid that allows a nested grid to inherit the track definitions (columns and rows) of its parent grid. This makes it significantly easier to align elements across different levels of the DOM tree, solving a long-standing layout challenge. [Learn more about CSS subgrid on MDN](https://developer.mozilla.org/docs/Web/CSS/Guides/Grid_layout/Subgrid)

## Rachel Andrew goes to Web Day Out

Last month, Chrome's own Rachel Andrew wrote [Look into the future of the web platform](https://rachelandrew.co.uk/archives/2026/03/20/look-into-the-future-of-the-web-platform/), which mentioned a talk she gave at [Web Day Out](https://webdayout.com/). [The presentation covered browser support](https://noti.st/rachelandrew/osjHV8/a-pragmatic-guide-to-browser-support)—not just Baseline targets, but how you might decide to use features that don't meet your Baseline target.

It's a good talk to help you understand how the availability of interoperable features slides one way or the other based on the Baseline target you choose. By choosing a later target, you're gaining more features, but at a cost of broader compatibility. It might make sense to think about setting your Baseline target to line up with your project's launch day, so you're not missing out features you could be safely using on day one.

Pragmatically choosing a Baseline target is a good thing to talk about—and we certainly recommend you check out [Rachel's take on it](https://noti.st/rachelandrew/osjHV8/a-pragmatic-guide-to-browser-support)). When you think about Baseline targets as points in time—rather than specific browsers—that mindset helps you make decisions that aren't merely "safe" today, but decisions that are more forward thinking about emerging interoperable features while maintaining a high standard of compatibility.

## Adding Baseline status to an Eleventy site

[Stu Robson](https://www.alwaystwisted.com/) wrote about how he [added the Baseline status web component to his Eleventy website](https://www.alwaystwisted.com/articles/adding-baseline-status-to-my-eleventy-site) last month. The post goes into some detail about the process, including how the component is conditionally loaded for some articles that are about specific web features. It's an excellent read if you document web features on your website, how you use them, and how to quickly signal to your readers if those features are interoperable.

Of course, the Baseline status web component isn't limited to Eleventy—it's [an open source web component](https://github.com/web-platform-dx/baseline-status) that is independent of any framework or site generator.

## Feedback

If there's a feature you're waiting for that isn't in Baseline, or if you've found an issue with one of the features listed here, [let us know on our tracker](https://github.com/web-platform-dx/web-features/issues). Your feedback helps us prioritize the work that matters most to you.
