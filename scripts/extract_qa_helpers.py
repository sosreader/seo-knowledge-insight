"""
從 02_extract_qa.py 抽出的純邏輯函式，方便測試和重用。
"""
from __future__ import annotations

import re


def _extract_date_from_title(title: str) -> str:
    """嘗試從標題中擷取日期"""
    patterns = [
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(\d{4}\d{2}\d{2})',
    ]
    for pattern in patterns:
        m = re.search(pattern, title)
        if m:
            return m.group(1)
    return ""


def _extract_date_from_content(content: str) -> str:
    """從 Markdown metadata 區擷取會議日期"""
    m = re.search(r'\*\*會議日期\*\*:\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})', content)
    if m:
        return m.group(1)
    return ""


def _split_content(content: str, max_chars: int) -> list[str]:
    """
    把長內容依標題分段。
    優先以 ## 標題切分，其次用段落邊界（\\n\\n），保證不會切在語句中間。
    """
    # 以 ## 或 ### 標題為切分點
    sections = re.split(r'(?=\n##\s)', content)

    if len(sections) <= 1:
        # 沒有標題結構，用段落邊界（\n\n）切分
        paragraphs = content.split("\n\n")
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            candidate = (current + "\n\n" + para) if current else para
            if len(candidate) > max_chars and current:
                chunks.append(current)
                current = para
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks if chunks else [content]

    # 合併太小的段落
    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) > max_chars and current:
            chunks.append(current)
            current = section
        else:
            current += section
    if current:
        chunks.append(current)

    return chunks
