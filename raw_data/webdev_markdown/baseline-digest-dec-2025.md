# December 2025 Baseline monthly digest
- **發佈日期**: 2026-01-26
- **作者**: web.dev
- **來源 URL**: https://web.dev/blog/baseline-digest-dec-2025?hl=en
- **來源類型**: article
- **來源集合**: web-dev
---
Published: January 26, 2026

As expected, December 2025 was a bit of a slow month for [Baseline](/baseline) with the developer community taking some well-deserved time off to decompress for the year's end. While this will be a quick update compared to other months in 2025, there are still plenty of highlights!

## Baseline Newly available features

The following features became Baseline Newly available in December of 2025. As a result, all of these features will become Baseline Widely available in July of 2028.

### `document.caretPositionFromPoint()`

[`document.caretPositionFromPoint()`](https://developer.mozilla.org/docs/Web/API/Document/caretPositionFromPoint) is a helpful method for finding the precise insertion point (DOM node and offset) for given viewport coordinates. This method reduces the guesswork that was often involved in finding the position of the caret in the document.

### Event Timing API

The Event Timing API is used to detect interactions with the document, and can be used to calculate the latency of user interactions. This API is used to calculate the [Interaction to Next Paint (INP) Core Web Vital metric](/articles/inp). [Now that this API is Baseline Newly available](/blog/lcp-and-inp-are-now-baseline-newly-available), it's possible to calculate the INP metric across all of the core browsers, and when it eventually reaches Baseline Widely available, it will be possible to calculate this important user-centric metric across even more browsers in use for Real User Monitoring (RUM) purposes.

### Largest Contentful Paint API

[Largest Contentful Paint (LCP)](/articles/lcp) is a Core Web Vital metric that calculates when [the largest piece of content](/articles/lcp#what-elements-are-considered) in the document is rendered. Now that the [Largest Contentful Paint API is Baseline Newly available](/blog/lcp-and-inp-are-now-baseline-newly-available)—and will cover even more users as it reaches Baseline Widely available—it will be possible to calculate this important user-centric metric as experienced by real users for data collection purposes.

### CSS `scrollbar-color`

Styling scrollbars consistently across browsers was previously impossible. Now that [the CSS `scrollbar-color`](https://developer.mozilla.org/docs/Web/CSS/Reference/Properties/scrollbar-color) property is Baseline Newly available, you have access to a better method for styling the document's scrollbar color.

### `scrollend` event

The [`scrollend` event](https://developer.chrome.com/blog/scrollend-a-new-javascript-event) provides a reliable way to detect when a scroll operation has finished, replacing messy `setTimeout` hacks. The introduction of this feature as Baseline Newly available means that users will be able to detect when scroll operations are complete in a way that doesn't compromise performance and readability of code through the use of `setTimeout` callbacks.

### CSS `@scope`

The [CSS `@scope` at-rule](https://developer.mozilla.org/docs/Web/CSS/Reference/At-rules/@scope) makes it easier for you to target elements in document subtrees in a way that reduces the need for complex selectors. With `@scope` becoming Baseline Newly available, you now have a robust tool for scoping styles.

### Math font family

If you've ever had to display mathematical equations on a page, you’ll know that such content has specific rendering needs. With `font-family: math` becoming Baseline Newly available, you’ll no longer need to use hacks to display mathematical equations.

### Invoker commands

[Invoker commands](https://developer.mozilla.org/docs/Web/API/Invoker_Commands_API) are useful for assigning behaviors to `<button>` elements on a page. In particular, they're useful for controlling the use of dialogs and popovers, and help you to handle many of the underlying requirements for using these APIs, such as accessibility concerns. To see how these work, read [`<dialog>` and `popover`: Baseline layered UI patterns](/articles/baseline-in-action-dialog-popover), an entry in our recently debuted [Baseline in action series](/series/baseline-in-action).

## Baseline Widely available features

A few features recently became Baseline Widely available in December of 2025, meaning that these features are now considered to be broadly usable in all major browsers.

### `calc()` keywords

As `calc()` performs mathematical operations in CSS, it became more necessary to introduce [keywords](https://developer.mozilla.org/docs/Web/CSS/Reference/Values/calc-keyword) for commonly used mathematical formulas. The `e`, `pi`, `infinity`, and `NaN` keywords represent well-defined constants accepted in CSS math functions in `calc()`.

### JavaScript modules in workers

Web workers exist in their own scope by design, and are instantiated through the `Worker()` constructor. The ability to use the `{ type: "module" }` argument when starting up a web worker allows you to use ES modules in the worker scope, giving you access to `import` and `export`. With this functionality now reaching Baseline Widely available, you'll be able to use this feature across more of the browsers in use today.

### `window.print()`

While [`window.print()`](https://developer.mozilla.org/docs/Web/API/Window/print) is a well-established web feature, the cross-browser Baseline Widely available clock for certain modern implementations of the print dialog completed this month, allowing it to be used more reliably across more browsers in use.

## That's a wrap

With the end of 2025 behind us, we're beginning a new year with Baseline in 2026! As usual, [let us know](https://issuetracker.google.com/issues/new?component=1400680&template=1857359) if we missed anything Baseline-related, and we'll make sure it gets captured in a future edition!
