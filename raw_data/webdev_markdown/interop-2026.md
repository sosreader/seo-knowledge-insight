# Interop 2026: Continuing to improve the web for developers
- **發佈日期**: 2026-02-12
- **作者**: web.dev
- **來源 URL**: https://web.dev/blog/interop-2026?hl=en
- **來源類型**: article
- **來源集合**: web-dev
---
Published: February 12, 2026

We're excited to announce **Interop 2026**, an effort to increase the interoperability of key features of the web platform across browsers. Run by a team of representatives from companies that make substantial contributions to browser rendering engines—including Apple, Google, Igalia, Microsoft, and Mozilla—Interop 2026 focuses on features that are high-priority for web developers and end users.

Consistent with earlier Interop efforts, selected tests will be continuously run on automated testing infrastructure, with pass rates displayed on the [Interop 2026 dashboard](https://wpt.fyi/interop-2026).

## Focus Areas

The focus areas for 2026 include several areas identified as top
interop issues in the State of HTML and State of CSS surveys.
We track these issues on [webstatus.dev](https://webstatus.dev).
Many features included this year also appear in the top 20 requested issues in
the [developer signals repository](https://github.com/web-platform-dx/developer-signals/issues?q=is:issue+state:open+sort:reactions-%2B1-desc+label:feature).

### Anchor positioning

*Appears in: Top interop issues, developer signals [anchor positioning](https://github.com/web-platform-dx/developer-signals/issues/245)*

Anchor positioning lets you place an element based on the position of another element, such as placing a tooltip next to the content it references. This focus area continues from Interop 2025 and includes only the tests from 2025.

### Container style queries

*Appears in: Top interop issues, developer signals [container style queries](https://github.com/web-platform-dx/developer-signals/issues/196)*

Container style queries apply styles to an element based on the computed values of custom properties of its container, using the `@container` at-rule together with one or more `style()` functions.

### Dialogs and popovers

*Appears in: Top interop issues, developer signals [closedby](https://github.com/web-platform-dx/developer-signals/issues/279), [hint](https://github.com/web-platform-dx/developer-signals/issues/274)*

For Interop 2026, work on the `<dialog>` element and Popover API focuses on:

* The `<dialog closedby>` attribute, which sets the user actions that close a dialog (for example, clicking outside the dialog).
* The `:open` CSS pseudo-class, which matches elements that have open states.
* The `popover="hint"` global attribute, which creates a popover subordinate to other auto popovers, useful for tooltips.

### Scroll-driven animations

*Appears in: Top interop issues*

This includes the `animation-timeline`, `scroll-timeline`, and `view-timeline` CSS properties, which advance animations based on the user's scroll position.

### View transitions

*Appears in: Top interop issues, developer signals [Cross-document view transitions](https://github.com/web-platform-dx/developer-signals/issues/248)*

Interop 2025 brought same-document view transitions to Baseline Newly available. For Interop 2026, the view transitions work focuses on:

* Improving same-document view transitions.
* The `blocking="render"` attribute for `<link>`, `<script>`, and `<style>`.
* The `<link rel="expect">` attribute.
* The `:active-view-transition-type()` CSS pseudo-class.
* Cross-document view transitions.

### The `attr()` CSS function

*Appears in developer signals [`attr()`](https://github.com/web-platform-dx/developer-signals/issues/293)*

The `attr()` CSS function returns the value of an attribute of an HTML element, with the option to return that value as a specific type or with a specific unit.

---

As well as these key features highlighted by you in the surveys, Interop 2026 includes:

### The `contrast-color()` CSS function

The `contrast-color()` CSS function selects a color that has guaranteed contrast against a specified foreground or background color.

### Custom highlights

Custom highlights let you style arbitrary text ranges without adding extra elements to the DOM.

### Fetch uploads and ranges

Work on the `fetch()` method focuses on `ReadableStream` in the body to stream data to the server, supporting `FormData` and media types for requests and responses, and supporting the `Range` header.

### IndexedDB

The IndexedDB focus area targets the `getAllRecords()` methods of `IDBObjectStore` and `IDBIndex`. These methods speed up read operations on large datasets by returning records and their primary keys in batches.

### JSPI for Wasm

The JavaScript Promise Integration API (JSPI) lets Wasm applications that expect synchronous access to external functionality work in an environment where that functionality is asynchronous.

### Media pseudo-classes

This area includes the `:playing`, `:paused`, `:seeking`, `:buffering`, `:stalled`, `:muted`, and `:volume-locked` CSS pseudo-classes, which match `<audio>` and `<video>` elements based on their state.

### Navigation API

This year, the work will focus on continuing to improve the interoperability of the Navigation API, and on the `precommitHandler` option to `navigateEvent.intercept()`, which defers the commit until a handler has resolved.

### Scoped custom element registries

The `CustomElementRegistry()` constructor creates a new custom element registry separate from the global one, letting multiple custom elements with the same tag name coexist.

### Scroll snap

This focus area covers CSS scroll snap, which controls panning and scrolling behavior within a scroll container.

### The `shape()` CSS function

The `shape()` CSS function creates shapes using commands like line, move, and curve, and can be used with `clip-path` and `shape-outside`.

### Web compat

This area targets specific interoperability issues that cause real-world problems, including:

* ESM module loading.
* The timing of scroll events relative to animation events.
* Unprefixing the `-webkit-user-select` property.

### WebRTC

For Interop 2026, work focuses on fixing the remaining failing tests from the Interop 2025 focus area and continuing to improve WebRTC interoperability.

### The WebTransport API

This area covers the WebTransport API, which transmits data between a client and server using the HTTP/3 protocol.

### The `zoom` CSS property

Continuing from Interop 2025, this area focuses on the `zoom` CSS property, which scales the size of an element and affects page layout.

## Investigation efforts

Interop 2026 also includes investigation efforts to prepare future features for testing and interoperability work:

* **Accessibility testing:** Working to generate consistent accessibility trees across browsers and improving WPT infrastructure.
* **JPEG XL:** Focusing on making the JPEG XL image format testable, including defining requirements for progressive rendering.
* **Mobile testing:** Improving WPT infrastructure to test mobile-specific features like dynamic viewport changes.
* **WebVTT:** Fixing tests and updating documentation to improve understanding of standard conformance.

## Track progress through 2026

Follow along with the project on the [Interop 2026 dashboard](https://wpt.fyi/interop-2026).

## Other announcements

* [Apple](https://webkit.org/blog/17818/announcing-interop-2026/)
* [Igalia](https://igalia.com/news/interop-2026.html)
* [Microsoft](https://blogs.windows.com/msedgedev/2026/02/12/microsoft-edge-and-interop-2026/)
* [Mozilla](https://hacks.mozilla.org/2026/02/launching-interop-2026/)
