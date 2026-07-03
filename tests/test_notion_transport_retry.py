"""_api_get / _api_post 對 transient 網路錯誤（httpx.TransportError）的重試行為

CI run 28660141787：fetch 進行 20 分鐘後單次 httpx.ReadTimeout 直接炸掉整個
ETL job — retry 迴圈原本只接 HTTPStatusError，TransportError 家族會穿透。
"""
import asyncio

import httpx
import pytest

from utils import notion_client


class _FlakyClient:
    """前 failures 次呼叫丟指定例外，之後回傳 200 的 stub client"""

    def __init__(self, failures: int, exc: Exception):
        self._failures = failures
        self._exc = exc
        self.calls = 0

    async def get(self, url, headers=None, params=None):
        return self._respond()

    async def post(self, url, headers=None, json=None):
        return self._respond()

    def _respond(self) -> httpx.Response:
        self.calls += 1
        if self.calls <= self._failures:
            raise self._exc
        request = httpx.Request("GET", "https://api.notion.com/v1/test")
        return httpx.Response(200, json={"ok": True}, request=request)


@pytest.fixture(autouse=True)
def _fast_and_headerless(monkeypatch):
    async def _noop_sleep(_seconds):
        return None

    monkeypatch.setattr(notion_client.asyncio, "sleep", _noop_sleep)
    monkeypatch.setattr(notion_client, "_headers", lambda: {})


@pytest.mark.parametrize(
    "exc",
    [httpx.ReadTimeout("read timed out"), httpx.ConnectError("connect failed")],
)
def test_api_get_retries_transport_error_then_succeeds(exc):
    client = _FlakyClient(failures=2, exc=exc)
    result = asyncio.run(notion_client._api_get(client, "https://api.notion.com/v1/test"))
    assert result == {"ok": True}
    assert client.calls == 3


def test_api_get_raises_after_retries_exhausted():
    client = _FlakyClient(failures=3, exc=httpx.ReadTimeout("read timed out"))
    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(notion_client._api_get(client, "https://api.notion.com/v1/test"))
    assert client.calls == 3


def test_api_post_retries_transport_error_then_succeeds():
    client = _FlakyClient(failures=1, exc=httpx.ReadTimeout("read timed out"))
    result = asyncio.run(
        notion_client._api_post(client, "https://api.notion.com/v1/test", body={})
    )
    assert result == {"ok": True}
    assert client.calls == 2


def test_api_post_raises_after_retries_exhausted():
    client = _FlakyClient(failures=3, exc=httpx.ConnectError("connect failed"))
    with pytest.raises(httpx.ConnectError):
        asyncio.run(notion_client._api_post(client, "https://api.notion.com/v1/test"))
    assert client.calls == 3


def test_api_get_http_error_retry_unchanged():
    """既有 HTTPStatusError 重試路徑不受影響（500 兩次後成功）"""

    class _Http500Then200(_FlakyClient):
        def _respond(self) -> httpx.Response:
            self.calls += 1
            request = httpx.Request("GET", "https://api.notion.com/v1/test")
            if self.calls <= self._failures:
                resp = httpx.Response(500, request=request)
                raise httpx.HTTPStatusError("boom", request=request, response=resp)
            return httpx.Response(200, json={"ok": True}, request=request)

    client = _Http500Then200(failures=2, exc=None)
    result = asyncio.run(notion_client._api_get(client, "https://api.notion.com/v1/test"))
    assert result == {"ok": True}
    assert client.calls == 3
