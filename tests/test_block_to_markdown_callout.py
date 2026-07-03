"""tests/test_block_to_markdown_callout.py — callout block icon 邊界測試

2026-07-03 實際 fetch 踩到：callout 的 icon 欄位可為 null（無 icon 的 callout），
`content.get("icon", {})` 對「key 存在但值為 None」仍回傳 None → AttributeError。
"""
from __future__ import annotations

import asyncio

from utils.block_to_markdown import _block_to_md


def _callout_block(icon) -> dict:
    return {
        "type": "callout",
        "id": "blk-1",
        "has_children": False,
        "callout": {
            "icon": icon,
            "rich_text": [{"plain_text": "重點提醒", "annotations": {}, "type": "text", "text": {"content": "重點提醒"}}],
        },
    }


class TestCalloutIcon:
    def test_null_icon_does_not_crash(self) -> None:
        md = asyncio.run(_block_to_md(_callout_block(None), client=None, images_dir=None))
        assert "重點提醒" in md

    def test_emoji_icon_is_rendered(self) -> None:
        md = asyncio.run(_block_to_md(_callout_block({"type": "emoji", "emoji": "!"}), client=None, images_dir=None))
        assert "! 重點提醒" in md
