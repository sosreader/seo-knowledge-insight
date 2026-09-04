"""Tests for scripts/ai_sov_providers.py（S6.2）。

三個重點：
  1. citation 解析——rank 的定義（依出現順序、URL 去重）必須被鎖住，
     它是 migration 024 citation_rank 欄位語意的實作。
  2. 「零 citation」是合法結果、「沒有 output_text 區塊」是錯誤。
     兩者混為一談會讓「API 換了、解析器沒跟上」偽裝成 provider 行為變動。
  3. 失敗路徑不得靜默——重試耗盡要拋 ProviderError，不可回一個空回應。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ai_sov_providers as providers  # noqa: E402
from ai_sov_providers import (  # noqa: E402
    Citation,
    FakeProvider,
    OpenAIProvider,
    ProviderAnswer,
    ProviderError,
    ProviderFatalError,
    dedupe_citations,
    first_target_rank,
    is_target_domain,
    normalize_domain,
    parse_openai_response,
    response_digest,
)


def _text_block(text: str, annotations: list[dict]) -> dict:
    return {"type": "output_text", "text": text, "annotations": annotations}


def _citation(url: str, start: int) -> dict:
    return {"type": "url_citation", "url": url, "start_index": start, "title": "t"}


def _payload(blocks: list[dict], *, extra_items: list[dict] | None = None, usage: dict | None = None) -> dict:
    output = list(extra_items or []) + [{"type": "message", "content": blocks}]
    payload: dict = {"output": output}
    if usage:
        payload["usage"] = usage
    return payload


class TestNormalizeDomain:
    @pytest.mark.parametrize("url,expected", [
        ("https://vocus.cc/article/1", "vocus.cc"),
        ("https://WWW.Vocus.CC/a", "vocus.cc"),
        ("http://vocus.cc:8080/a", "vocus.cc"),
        ("https://sub.vocus.cc/a", "sub.vocus.cc"),
        ("https://vocus.cc./a", "vocus.cc"),
        ("https://www.medium.com/x", "medium.com"),
    ])
    def test_normalizes(self, url: str, expected: str) -> None:
        assert normalize_domain(url) == expected

    @pytest.mark.parametrize("url", ["", "not-a-url", "ftp://vocus.cc/a", "mailto:a@b.c", "https://"])
    def test_returns_none_for_unusable(self, url: str) -> None:
        assert normalize_domain(url) is None


class TestIsTargetDomain:
    def test_exact_match(self) -> None:
        assert is_target_domain("vocus.cc", "vocus.cc")

    def test_subdomain_counts(self) -> None:
        assert is_target_domain("m.vocus.cc", "vocus.cc")

    def test_suffix_lookalike_does_not_count(self) -> None:
        """『notvocus.cc』只是字尾像，不是子網域——endswith 沒有加點就會誤判。"""
        assert not is_target_domain("notvocus.cc", "vocus.cc")

    def test_unrelated_domain(self) -> None:
        assert not is_target_domain("medium.com", "vocus.cc")


class TestDedupeCitations:
    def test_preserves_order_and_dedupes_by_url(self) -> None:
        result = dedupe_citations([
            "https://a.test/1", "https://b.test/1", "https://a.test/1", "https://a.test/2",
        ])
        assert [c.url for c in result] == ["https://a.test/1", "https://b.test/1", "https://a.test/2"]

    def test_same_domain_different_urls_both_kept(self) -> None:
        """去重的鍵是 URL 不是 domain——同站兩篇文章是兩個 citation。"""
        result = dedupe_citations(["https://a.test/1", "https://a.test/2"])
        assert [c.domain for c in result] == ["a.test", "a.test"]

    def test_drops_unparseable(self) -> None:
        result = dedupe_citations(["not-a-url", "https://a.test/1", None])  # type: ignore[list-item]
        assert [c.url for c in result] == ["https://a.test/1"]


class TestFirstTargetRank:
    def test_rank_is_one_based_first_occurrence(self) -> None:
        citations = (Citation("https://a.test/1", "a.test"),
                     Citation("https://vocus.cc/x", "vocus.cc"),
                     Citation("https://vocus.cc/y", "vocus.cc"))
        assert first_target_rank(citations, "vocus.cc") == 2

    def test_none_when_absent(self) -> None:
        assert first_target_rank((Citation("https://a.test/1", "a.test"),), "vocus.cc") is None

    def test_none_for_empty(self) -> None:
        assert first_target_rank((), "vocus.cc") is None


class TestResponseDigest:
    def test_is_sha256_hex(self) -> None:
        digest = response_digest("hello")
        assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)

    def test_stable_and_distinct(self) -> None:
        assert response_digest("a") == response_digest("a") != response_digest("b")


class TestParseOpenAIResponse:
    def test_extracts_text_and_citations_in_appearance_order(self) -> None:
        payload = _payload([_text_block("答案", [
            _citation("https://b.test/1", 50),
            _citation("https://a.test/1", 10),
        ])])
        answer = parse_openai_response(payload)
        assert answer.text == "答案"
        assert [c.url for c in answer.citations] == ["https://a.test/1", "https://b.test/1"]

    def test_dedupes_repeated_url_across_blocks(self) -> None:
        payload = _payload([
            _text_block("一", [_citation("https://a.test/1", 5)]),
            _text_block("二", [_citation("https://a.test/1", 20), _citation("https://b.test/1", 30)]),
        ])
        answer = parse_openai_response(payload)
        assert answer.text == "一二"
        assert [c.url for c in answer.citations] == ["https://a.test/1", "https://b.test/1"]

    def test_skips_non_url_citation_annotations(self) -> None:
        payload = _payload([_text_block("x", [
            {"type": "file_citation", "url": "https://z.test/1", "start_index": 1},
            _citation("https://a.test/1", 2),
        ])])
        assert [c.url for c in parse_openai_response(payload).citations] == ["https://a.test/1"]

    def test_ignores_non_message_output_items(self) -> None:
        """帶工具的回應會先出現 web_search_call；硬取 output[0] 會拿到錯的東西。"""
        payload = _payload([_text_block("x", [_citation("https://a.test/1", 1)])],
                           extra_items=[{"type": "web_search_call", "status": "completed"}])
        assert [c.url for c in parse_openai_response(payload).citations] == ["https://a.test/1"]

    def test_zero_citations_is_legal_not_an_error(self) -> None:
        answer = parse_openai_response(_payload([_text_block("沒有引用來源的回答", [])]))
        assert answer.citations == () and answer.is_grounded is False

    def test_missing_output_text_raises(self) -> None:
        """『API 換了、解析器沒跟上』必須是錯誤，不能靜默變成 ungrounded。"""
        with pytest.raises(ProviderError, match="脫節"):
            parse_openai_response({"output": [{"type": "web_search_call"}]})

    def test_empty_payload_raises(self) -> None:
        with pytest.raises(ProviderError):
            parse_openai_response({})

    def test_usage_tokens_parsed(self) -> None:
        payload = _payload([_text_block("x", [])], usage={"input_tokens": 11, "output_tokens": 22})
        answer = parse_openai_response(payload)
        assert (answer.input_tokens, answer.output_tokens) == (11, 22)

    def test_usage_absent_defaults_to_zero(self) -> None:
        answer = parse_openai_response(_payload([_text_block("x", [])]))
        assert (answer.input_tokens, answer.output_tokens) == (0, 0)


class TestOpenAIProvider:
    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
            OpenAIProvider(api_key="", model="m")

    def test_body_requests_web_search_without_forcing_it(self) -> None:
        """不強制 tool_choice：模型『認為不需要檢索』本身是 ungrounded 想量到的訊號。"""
        body = OpenAIProvider(api_key="k", model="m")._body("問題")
        assert body["tools"] == [{"type": "web_search"}]
        assert "tool_choice" not in body
        assert body["input"] == "問題"

    def test_api_key_only_in_authorization_header(self) -> None:
        provider = OpenAIProvider(api_key="secret-value", model="m")
        assert provider._headers()["Authorization"].endswith("secret-value")
        assert "secret-value" not in str(provider._body("問題"))

    def test_retries_on_429_then_succeeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []
        payload = _payload([_text_block("ok", [_citation("https://a.test/1", 1)])])

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            return (429, "rate limited") if len(calls) == 1 else (200, __import__("json").dumps(payload))

        monkeypatch.setattr(providers, "_post_json", fake_post)
        monkeypatch.setattr(providers.time, "sleep", lambda _s: None)
        answer = OpenAIProvider(api_key="k", model="m").answer("問題")
        assert len(calls) == 2 and answer.text == "ok"

    def test_non_retryable_status_fails_immediately(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            return 400, "bad request"

        monkeypatch.setattr(providers, "_post_json", fake_post)
        monkeypatch.setattr(providers.time, "sleep", lambda _s: None)
        with pytest.raises(ProviderError, match="400"):
            OpenAIProvider(api_key="k", model="m").answer("問題")
        assert len(calls) == 1

    def test_exhausted_retries_raise_not_return_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """重試耗盡必須拋——回一個空回應會被記成『沒引用』，讓 API 故障
        偽裝成可見度下降（ingest 設計決定 4）。"""
        calls: list[int] = []

        def fake_post(url, body, headers, timeout):
            calls.append(1)
            return 503, "unavailable"

        monkeypatch.setattr(providers, "_post_json", fake_post)
        monkeypatch.setattr(providers.time, "sleep", lambda _s: None)
        with pytest.raises(ProviderError, match="503"):
            OpenAIProvider(api_key="k", model="m").answer("問題")
        assert len(calls) == providers.MAX_ATTEMPTS

    def test_backoff_table_matches_attempt_count(self) -> None:
        assert len(providers.RETRY_BACKOFF_SECONDS) == providers.MAX_ATTEMPTS - 1

    def test_insufficient_quota_429_is_fatal_and_not_retried(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """實例：run 33862967625，108 次呼叫全部這個 body，卻各重試 3 次
        白耗 21 分鐘。額度耗盡重試沒有意義，必須不重試、拋 ProviderFatalError。"""
        import json as _json

        calls: list[int] = []
        body = _json.dumps({"error": {
            "type": "insufficient_quota",
            "code": "credit_balance_exhausted",
            "message": "You have no credits remaining...",
        }})

        def fake_post(url, req_body, headers, timeout):
            calls.append(1)
            return 429, body

        monkeypatch.setattr(providers, "_post_json", fake_post)
        monkeypatch.setattr(providers.time, "sleep", lambda _s: None)
        with pytest.raises(ProviderFatalError, match="不可重試"):
            OpenAIProvider(api_key="k", model="m").answer("問題")
        assert len(calls) == 1

    def test_rate_limit_429_still_retries_to_the_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """速率限制是暫時性的（type=rate_limit_error），不該被歸類為 fatal。"""
        import json as _json

        calls: list[int] = []
        body = _json.dumps({"error": {
            "type": "rate_limit_error",
            "code": "rate_limit_exceeded",
            "message": "Rate limit reached",
        }})

        def fake_post(url, req_body, headers, timeout):
            calls.append(1)
            return 429, body

        monkeypatch.setattr(providers, "_post_json", fake_post)
        monkeypatch.setattr(providers.time, "sleep", lambda _s: None)
        with pytest.raises(ProviderError) as exc_info:
            OpenAIProvider(api_key="k", model="m").answer("問題")
        assert not isinstance(exc_info.value, ProviderFatalError)
        assert len(calls) == providers.MAX_ATTEMPTS

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_errors_are_fatal_and_not_retried(self, status: int, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_post(url, req_body, headers, timeout):
            calls.append(1)
            return status, '{"error": {"message": "invalid api key"}}'

        monkeypatch.setattr(providers, "_post_json", fake_post)
        monkeypatch.setattr(providers.time, "sleep", lambda _s: None)
        with pytest.raises(ProviderFatalError):
            OpenAIProvider(api_key="k", model="m").answer("問題")
        assert len(calls) == 1

    def test_provider_fatal_error_is_a_provider_error(self) -> None:
        """run_panel 若只 except ProviderError 也要能接住——但它必須先被辨識
        出來才能觸發早停，這條只鎖繼承關係，早停行為在 test_ingest_ai_sov.py 驗。"""
        assert issubclass(ProviderFatalError, ProviderError)

    def test_unparseable_429_body_is_not_fatal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """body 解析不出來時寧可當成可重試，不要誤判成 fatal 而漏掉可能自癒的失敗。"""
        calls: list[int] = []

        def fake_post(url, req_body, headers, timeout):
            calls.append(1)
            return 429, "not json"

        monkeypatch.setattr(providers, "_post_json", fake_post)
        monkeypatch.setattr(providers.time, "sleep", lambda _s: None)
        with pytest.raises(ProviderError) as exc_info:
            OpenAIProvider(api_key="k", model="m").answer("問題")
        assert not isinstance(exc_info.value, ProviderFatalError)
        assert len(calls) == providers.MAX_ATTEMPTS


class TestIsFatalOpenAIError:
    def test_401_403_are_fatal(self) -> None:
        assert providers._is_fatal_openai_error(401, "") is True
        assert providers._is_fatal_openai_error(403, "") is True

    def test_insufficient_quota_type_is_fatal(self) -> None:
        body = '{"error": {"type": "insufficient_quota", "code": "credit_balance_exhausted"}}'
        assert providers._is_fatal_openai_error(429, body) is True

    def test_rate_limit_type_is_not_fatal(self) -> None:
        body = '{"error": {"type": "rate_limit_error", "code": "rate_limit_exceeded"}}'
        assert providers._is_fatal_openai_error(429, body) is False

    def test_non_429_non_auth_status_is_not_fatal(self) -> None:
        assert providers._is_fatal_openai_error(500, "") is False
        assert providers._is_fatal_openai_error(503, "") is False

    def test_malformed_body_is_not_fatal(self) -> None:
        assert providers._is_fatal_openai_error(429, "{not valid json") is False
        assert providers._is_fatal_openai_error(429, '{"error": "not-a-mapping"}') is False
        assert providers._is_fatal_openai_error(429, "{}") is False


class TestFakeProvider:
    def test_scripted_answers_cycle_in_order(self) -> None:
        scripted = [ProviderAnswer(text="a"), ProviderAnswer(text="b")]
        fake = FakeProvider(scripted=scripted)
        assert [fake.answer("q").text for _ in range(4)] == ["a", "b", "a", "b"]

    def test_call_counter_advances(self) -> None:
        fake = FakeProvider()
        for _ in range(3):
            fake.answer("q")
        assert fake.calls == 3

    def test_deterministic_for_same_seed(self) -> None:
        a = [FakeProvider(seed="x").answer(f"q{i}") for i in range(5)]
        b = [FakeProvider(seed="x").answer(f"q{i}") for i in range(5)]
        assert [x.citations for x in a] == [y.citations for y in b]

    def test_produces_all_three_shapes(self) -> None:
        """整條鏈需要 grounded+cited / grounded 未 cited / ungrounded 三種分支都出現。"""
        fake = FakeProvider()
        answers = [fake.answer(f"問題 {i}") for i in range(60)]
        assert any(not a.is_grounded for a in answers)
        assert any(a.is_grounded and first_target_rank(a.citations, "vocus.cc") is None for a in answers)
        assert any(first_target_rank(a.citations, "vocus.cc") is not None for a in answers)

    def test_always_ungrounded_when_rate_is_one(self) -> None:
        fake = FakeProvider(ungrounded_rate=1.0)
        assert all(not fake.answer(f"q{i}").is_grounded for i in range(10))


class TestPostJsonTransport:
    """_post_json 是唯一真的碰網路的地方——連線層的失敗必須變成 ProviderError，
    不能是一個會往上冒到 ingest 迴圈外、讓整批中斷的裸 URLError。"""

    class _FakeResponse:
        def __init__(self, status: int, body: str) -> None:
            self.status = status
            self._body = body

        def read(self) -> bytes:
            return self._body.encode()

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> None:
            return None

    def test_returns_status_and_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["method"] = request.method
            captured["auth"] = request.headers.get("Authorization")
            return self._FakeResponse(200, '{"ok": true}')

        monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
        status, body = providers._post_json("https://api.test/x", {"a": 1},
                                            {"Authorization": "Bearer k"}, 5)
        assert (status, body) == (200, '{"ok": true}')
        assert captured["method"] == "POST" and captured["auth"] == "Bearer k"

    def test_http_error_returned_not_raised(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        error = urllib.error.HTTPError("u", 429, "too many", {}, None)
        error.read = lambda: b"rate limited"  # type: ignore[method-assign]

        def fake_urlopen(request, timeout=None):
            raise error

        monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
        status, body = providers._post_json("https://api.test/x", {}, {}, 5)
        assert status == 429 and "rate limited" in body

    def test_url_error_becomes_provider_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        def fake_urlopen(request, timeout=None):
            raise urllib.error.URLError("dns fail")

        monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(ProviderError, match="連線失敗"):
            providers._post_json("https://api.test/x", {}, {}, 5)


class TestNormalizeDomainMalformedInput:
    def test_unparseable_url_returns_none_instead_of_raising(self) -> None:
        """urlsplit 對某些形狀會拋 ValueError；讓它冒出去會殺掉整條 panel 的迴圈。"""
        assert normalize_domain("http://[not-an-ipv6/") is None
