"""
html_to_markdown.py — 共用 HTML → Markdown 轉換器

支援任何 HTML 來源（Medium、iThome、未來新來源）。
使用 markdownify 做核心轉換，加上清理後處理。
"""
from __future__ import annotations

import re


def html_to_markdown(html: str, strip_tags: tuple[str, ...] = ("script", "style", "nav", "footer")) -> str:
    """Convert HTML to clean Markdown.

    Args:
        html: Raw HTML string
        strip_tags: HTML tags to completely remove before conversion

    Returns:
        Cleaned Markdown string
    """
    from bs4 import BeautifulSoup
    import markdownify

    # Pre-process: remove unwanted tags entirely (including content)
    extra_dangerous = ("iframe", "object", "embed", "form", "input", "button")
    soup = BeautifulSoup(html, "html.parser")
    for tag_name in (*strip_tags, *extra_dangerous):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove Medium accessibility UI elements
    # e.g. <a ...>Press enter or click to view image in full size</a>
    _MEDIUM_UI_TEXTS = frozenset({
        "press enter or click to view image in full size",
        "get gene hong, 還是黑貘's stories in your inbox",
    })
    for tag in soup.find_all(True):
        if tag.get_text(strip=True).lower() in _MEDIUM_UI_TEXTS:
            tag.decompose()

    # Strip event handler attributes and javascript: URLs
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.startswith("on"):
                del tag[attr]
            elif attr in ("href", "src", "action") and str(tag.get(attr, "")).strip().lower().startswith("javascript:"):
                del tag[attr]

    md = markdownify.markdownify(
        str(soup),
        heading_style="ATX",
        wrap=False,
    )
    return _cleanup(md)


# Medium-specific UI strings that appear as inline or standalone noise.
# Order matters: inline substitutions before line-level cleanups.
_MEDIUM_INLINE_NOISE = re.compile(
    r'Press enter or click to view image in full size',
    re.IGNORECASE,
)
_MEDIUM_LINE_NOISE = re.compile(
    r'^\s*(Get .+?[\u2018\u2019\u0027]s stories in your inbox'
    r'|Join Medium for free to get updates from this writer'
    r')\s*$',
    re.IGNORECASE | re.MULTILINE,
)


def _cleanup(md: str) -> str:
    """Post-process Markdown: remove excess blank lines, fix formatting."""
    # 1. Strip inline Medium UI noise (may appear before image refs on same line)
    md = _MEDIUM_INLINE_NOISE.sub('', md)
    # 2. Strip full-line Medium promo noise
    md = _MEDIUM_LINE_NOISE.sub('', md)
    # 3. Collapse 3+ consecutive blank lines to 2
    md = re.sub(r'\n{3,}', '\n\n', md)
    # 4. Remove trailing whitespace per line
    md = '\n'.join(line.rstrip() for line in md.splitlines())
    # 5. Ensure single trailing newline
    return md.strip() + '\n'


def add_metadata_header(
    content: str,
    *,
    title: str,
    published: str,
    author: str,
    source_url: str,
    source_type: str = "article",
    source_collection: str = "",
) -> str:
    """Prepend a metadata header to Markdown content.

    Args:
        content: Markdown body
        title: Article title
        published: Publication date (YYYY-MM-DD)
        author: Author name
        source_url: Original URL
        source_type: "article" | "meeting" | ...
        source_collection: Collection identifier

    Returns:
        Markdown with metadata header prepended
    """
    lines = [
        f"# {title}",
        f"- **發佈日期**: {published}",
        f"- **作者**: {author}",
        f"- **來源 URL**: {source_url}",
        f"- **來源類型**: {source_type}",
    ]
    if source_collection:
        lines.append(f"- **來源集合**: {source_collection}")
    lines.append("---")
    lines.append("")

    return '\n'.join(lines) + content
