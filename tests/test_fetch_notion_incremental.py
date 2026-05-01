from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_fetch_notion_module():
    module_path = Path(__file__).resolve().parent.parent / "scripts" / "01_fetch_notion.py"
    spec = importlib.util.spec_from_file_location("fetch_notion_script", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_derive_incremental_since_time_returns_latest_timestamp() -> None:
    module = _load_fetch_notion_module()

    existing_index = {
        "page-1": {"last_edited_time": "2026-05-01T08:00:00.000Z"},
        "page-2": {"last_edited_time": "2026-05-02T09:30:00.000Z"},
        "page-3": {"last_edited_time": "2026-04-30T22:15:00.000Z"},
    }

    assert module._derive_incremental_since_time(existing_index) == "2026-05-02T09:30:00.000Z"


def test_derive_incremental_since_time_ignores_empty_values() -> None:
    module = _load_fetch_notion_module()

    existing_index = {
        "page-1": {"last_edited_time": ""},
        "page-2": {},
        "page-3": {"last_edited_time": "2026-05-02T09:30:00.000Z"},
    }

    assert module._derive_incremental_since_time(existing_index) == "2026-05-02T09:30:00.000Z"


def test_derive_incremental_since_time_returns_none_without_timestamps() -> None:
    module = _load_fetch_notion_module()

    existing_index = {
        "page-1": {"last_edited_time": ""},
        "page-2": {},
    }

    assert module._derive_incremental_since_time(existing_index) is None