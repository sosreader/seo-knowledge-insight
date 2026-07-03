"""tests/test_notion_multi_source.py — Notion multi-source database（API 2025-09-03）測試

Notion API 2025-09-03 起 database 拆成多個 data source：
- GET /databases/{id} 回應含 data_sources 陣列
- 查詢 rows 改走 POST /data_sources/{id}/query（舊 /databases/{id}/query 對 multi-source 回 400）
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from utils import notion_client


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.notion.com/v1/databases/xxx")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


def _page_record(page_id: str, title: str) -> dict:
    return {
        "object": "page",
        "id": page_id,
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": title}]},
        },
    }


# ── list_child_pages：multi-source database ──────────────

class TestListChildPagesMultiSource:
    def test_queries_every_data_source_and_dedupes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        queried_urls: list[str] = []

        async def fake_api_get(client, url, params=None, retries=3):
            return {
                "object": "database",
                "data_sources": [{"id": "ds-a"}, {"id": "ds-b"}],
            }

        async def fake_api_post(client, url, body=None, retries=3):
            queried_urls.append(url)
            if "ds-a" in url:
                return {
                    "results": [_page_record("p1", "第一頁"), _page_record("p2", "第二頁")],
                    "has_more": False,
                }
            return {
                # p2 與 ds-a 重複，需去重
                "results": [_page_record("p2", "第二頁"), _page_record("p3", "第三頁")],
                "has_more": False,
            }

        monkeypatch.setattr(notion_client, "_api_get", fake_api_get)
        monkeypatch.setattr(notion_client, "_api_post", fake_api_post)

        pages, server_filtered = asyncio.run(
            notion_client.list_child_pages(None, "db-id", since_time="2026-05-12T00:00:00.000Z")
        )

        assert [u.split("/v1/")[1] for u in queried_urls] == [
            "data_sources/ds-a/query",
            "data_sources/ds-b/query",
        ]
        assert [p["id"] for p in pages] == ["p1", "p2", "p3"]
        assert server_filtered is True

    def test_missing_data_sources_raises_clear_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def fake_api_get(client, url, params=None, retries=3):
            # 舊版 API 回應形狀（無 data_sources）
            return {"object": "database"}

        monkeypatch.setattr(notion_client, "_api_get", fake_api_get)

        with pytest.raises(RuntimeError, match="data_sources"):
            asyncio.run(notion_client.list_child_pages(None, "db-id"))

    @pytest.mark.parametrize("status_code", [400, 404])
    def test_falls_back_to_page_children_on_type_mismatch(
        self, monkeypatch: pytest.MonkeyPatch, status_code: int
    ) -> None:
        async def fake_api_get(client, url, params=None, retries=3):
            raise _http_status_error(status_code)

        async def fake_list_page_children(client, page_id):
            return [{"id": "child-1", "title": "子頁"}]

        monkeypatch.setattr(notion_client, "_api_get", fake_api_get)
        monkeypatch.setattr(notion_client, "_list_page_children", fake_list_page_children)

        pages, server_filtered = asyncio.run(
            notion_client.list_child_pages(None, "page-id", since_time="2026-05-12T00:00:00.000Z")
        )

        assert pages == [{"id": "child-1", "title": "子頁"}]
        assert server_filtered is False

    @pytest.mark.parametrize("status_code", [401, 403, 500])
    def test_auth_and_server_errors_are_reraised(
        self, monkeypatch: pytest.MonkeyPatch, status_code: int
    ) -> None:
        async def fake_api_get(client, url, params=None, retries=3):
            raise _http_status_error(status_code)

        async def fake_list_page_children(client, page_id):
            raise AssertionError("401/403/500 不應 fallback 到頁面模式")

        monkeypatch.setattr(notion_client, "_api_get", fake_api_get)
        monkeypatch.setattr(notion_client, "_list_page_children", fake_list_page_children)

        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(notion_client.list_child_pages(None, "db-id"))


# ── _list_data_source_pages：filter 與分頁 ────────────────

class TestListDataSourcePages:
    def test_since_time_builds_last_edited_filter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict = {}

        async def fake_api_post(client, url, body=None, retries=3):
            captured["url"] = url
            captured["body"] = body
            return {"results": [_page_record("p1", "頁")], "has_more": False}

        monkeypatch.setattr(notion_client, "_api_post", fake_api_post)

        pages = asyncio.run(
            notion_client._list_data_source_pages(
                None, "ds-a", since_time="2026-05-12T00:00:00.000Z"
            )
        )

        assert captured["url"].endswith("/data_sources/ds-a/query")
        assert captured["body"]["filter"] == {
            "timestamp": "last_edited_time",
            "last_edited_time": {"on_or_after": "2026-05-12T00:00:00.000Z"},
        }
        assert pages == [{"id": "p1", "title": "頁"}]

    def test_pagination_follows_cursor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []

        async def fake_api_post(client, url, body=None, retries=3):
            calls.append(body)
            if len(calls) == 1:
                return {
                    "results": [_page_record("p1", "一")],
                    "has_more": True,
                    "next_cursor": "cur-2",
                }
            return {"results": [_page_record("p2", "二")], "has_more": False}

        monkeypatch.setattr(notion_client, "_api_post", fake_api_post)

        pages = asyncio.run(notion_client._list_data_source_pages(None, "ds-a"))

        assert len(calls) == 2
        assert "start_cursor" not in calls[0]
        assert calls[1]["start_cursor"] == "cur-2"
        assert [p["id"] for p in pages] == ["p1", "p2"]
