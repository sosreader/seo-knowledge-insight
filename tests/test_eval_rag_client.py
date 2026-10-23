"""Unit tests for evals/rag_client.py (URL / header assembly, llm_disabled skip, helpers)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evals import rag_client as rc  # noqa: E402

ONLINE_BASE = "https://warehouse-api.vocus.cc/internal/rag"
CF_ENV = {"CF_ACCESS_CLIENT_ID": "id", "CF_ACCESS_CLIENT_SECRET": "sec"}


def _resp(status: int, body: object = None, *, json_error: bool = False) -> MagicMock:
    resp = MagicMock(status_code=status)
    if json_error:
        resp.json.side_effect = ValueError("not json")
    else:
        resp.json.return_value = body
    return resp


class TestBaseAndUrl:
    def test_default_is_online_rag_api(self):
        assert rc.rag_api_base({}) == ONLINE_BASE

    def test_override_strips_trailing_slash(self):
        assert rc.rag_api_base({"RAG_API_BASE": "http://localhost:8080/"}) == "http://localhost:8080"

    def test_blank_override_falls_back_to_default(self):
        assert rc.rag_api_base({"RAG_API_BASE": "  "}) == ONLINE_BASE

    def test_legacy_eval_api_base_is_ignored_with_warning(self, caplog):
        with caplog.at_level("WARNING"):
            base = rc.rag_api_base({"EVAL_API_BASE": "http://localhost:8002"})
        assert base == ONLINE_BASE
        assert "RAG_API_BASE" in caplog.text

    def test_endpoint_url_has_no_api_v1_prefix(self):
        assert rc.endpoint_url("/search", {}) == f"{ONLINE_BASE}/search"
        assert "api/v1" not in rc.endpoint_url("pipeline/crawled-not-indexed", {})

    def test_endpoint_url_local_base(self):
        env = {"RAG_API_BASE": "http://localhost:8080"}
        assert rc.endpoint_url("/chat", env) == "http://localhost:8080/chat"

    def test_reads_process_env_when_env_not_given(self, monkeypatch):
        monkeypatch.setenv("RAG_API_BASE", "http://x:1")
        assert rc.endpoint_url("/qa") == "http://x:1/qa"


class TestBuildHeaders:
    def test_no_auth_by_default(self):
        assert rc.build_headers({}) == {"Content-Type": "application/json"}

    def test_cf_access_pair(self):
        headers = rc.build_headers(CF_ENV)
        assert headers["CF-Access-Client-Id"] == "id"
        assert headers["CF-Access-Client-Secret"] == "sec"
        assert "X-API-Key" not in headers

    def test_cf_pair_needs_both_values(self):
        assert "CF-Access-Client-Id" not in rc.build_headers({"CF_ACCESS_CLIENT_ID": "id"})
        assert "CF-Access-Client-Secret" not in rc.build_headers({"CF_ACCESS_CLIENT_SECRET": "s"})

    def test_api_key_mode(self):
        headers = rc.build_headers({"SEO_API_KEY": "k"})
        assert headers["X-API-Key"] == "k"
        assert "CF-Access-Client-Id" not in headers

    def test_cf_pair_wins_over_api_key(self):
        headers = rc.build_headers({**CF_ENV, "SEO_API_KEY": "k"})
        assert "CF-Access-Client-Id" in headers
        assert "X-API-Key" not in headers

    def test_incomplete_cf_pair_falls_back_to_api_key(self):
        headers = rc.build_headers({"CF_ACCESS_CLIENT_ID": "id", "SEO_API_KEY": "k"})
        assert headers["X-API-Key"] == "k"
        assert "CF-Access-Client-Id" not in headers


class TestLlmDisabled:
    def test_501_with_llm_disabled(self):
        assert rc.is_llm_disabled(501, {"error": "llm_disabled"}) is True

    @pytest.mark.parametrize(
        ("status", "body"),
        [
            (200, {"error": "llm_disabled"}),
            (501, {"error": "run_locally"}),
            (501, None),
            (501, ["llm_disabled"]),
            (500, {"error": "llm_disabled"}),
        ],
    )
    def test_other_responses_are_not_llm_disabled(self, status, body):
        assert rc.is_llm_disabled(status, body) is False

    def test_response_helper_reads_json(self):
        assert rc.response_is_llm_disabled(_resp(501, {"error": "llm_disabled"})) is True

    def test_response_helper_tolerates_non_json_body(self):
        assert rc.response_is_llm_disabled(_resp(501, json_error=True)) is False


class TestRequests:
    def test_post_json_assembles_url_headers_payload(self):
        with patch.object(rc.requests, "post", return_value=_resp(200, {})) as post:
            rc.post_json("/search", {"query": "q"}, timeout=7, env=CF_ENV)
        assert post.call_args.args[0] == f"{ONLINE_BASE}/search"
        assert post.call_args.kwargs["json"] == {"query": "q"}
        assert post.call_args.kwargs["timeout"] == 7
        assert post.call_args.kwargs["headers"]["CF-Access-Client-Id"] == "id"

    def test_get_json_passes_params(self):
        with patch.object(rc.requests, "get", return_value=_resp(200, {})) as get:
            rc.get_json("/qa", params={"limit": 1}, timeout=3, env={})
        assert get.call_args.args[0] == f"{ONLINE_BASE}/qa"
        assert get.call_args.kwargs["params"] == {"limit": 1}


class TestSearchResults:
    def test_returns_results_and_omits_mode(self):
        body = {"data": {"results": [{"id": "a"}]}}
        with patch.object(rc.requests, "post", return_value=_resp(200, body)) as post:
            out = rc.search_results("q", top_k=10, timeout=5, extra={"extraction_model": "m"}, env={})
        assert out == [{"id": "a"}]
        sent = post.call_args.kwargs["json"]
        assert sent == {"query": "q", "top_k": 10, "extraction_model": "m"}
        assert "mode" not in sent

    def test_non_200_returns_none(self):
        with patch.object(rc.requests, "post", return_value=_resp(403, {})):
            assert rc.search_results("q", top_k=5, timeout=5, env={}) is None

    def test_network_error_returns_none(self):
        with patch.object(rc.requests, "post", side_effect=requests.ConnectionError("boom")):
            assert rc.search_results("q", top_k=5, timeout=5, env={}) is None

    def test_malformed_body_returns_none(self):
        with patch.object(rc.requests, "post", return_value=_resp(200, {"data": {"results": "x"}})):
            assert rc.search_results("q", top_k=5, timeout=5, env={}) is None
        with patch.object(rc.requests, "post", return_value=_resp(200, json_error=True)):
            assert rc.search_results("q", top_k=5, timeout=5, env={}) is None


class TestFetchQaItem:
    def test_returns_item(self):
        with patch.object(rc.requests, "get", return_value=_resp(200, {"data": {"id": "ab", "category": "c"}})) as get:
            assert rc.fetch_qa_item("ab", env={}) == {"id": "ab", "category": "c"}
        assert get.call_args.args[0].endswith("/qa/ab")

    def test_missing_item(self):
        with patch.object(rc.requests, "get", return_value=_resp(404, {})):
            assert rc.fetch_qa_item("zz", env={}) is None

    def test_network_error(self):
        with patch.object(rc.requests, "get", side_effect=requests.Timeout()):
            assert rc.fetch_qa_item("ab", env={}) is None

    def test_non_dict_data(self):
        with patch.object(rc.requests, "get", return_value=_resp(200, {"data": None})):
            assert rc.fetch_qa_item("ab", env={}) is None


class TestPreflight:
    def test_ok(self):
        with patch.object(rc.requests, "get", return_value=_resp(200, {})):
            assert rc.preflight({}) == (True, "ok")

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_failure(self, status):
        with patch.object(rc.requests, "get", return_value=_resp(status, {})):
            ok, reason = rc.preflight({})
        assert ok is False
        assert str(status) in reason

    def test_other_status(self):
        with patch.object(rc.requests, "get", return_value=_resp(502, {})):
            assert rc.preflight({}) == (False, "rag-api preflight returned HTTP 502")

    def test_unreachable(self):
        with patch.object(rc.requests, "get", side_effect=requests.ConnectionError()):
            ok, reason = rc.preflight({})
        assert ok is False
        assert "unreachable" in reason


class TestLlmAvailableAndSkip:
    def test_disabled_501_means_unavailable(self):
        with patch.object(rc.requests, "post", return_value=_resp(501, {"error": "llm_disabled"})):
            assert rc.llm_available({}) is False

    def test_200_means_available(self):
        with patch.object(rc.requests, "post", return_value=_resp(200, {})):
            assert rc.llm_available({}) is True

    def test_auth_error_does_not_mask_as_skip(self):
        with patch.object(rc.requests, "post", return_value=_resp(403, {})):
            assert rc.llm_available({}) is True

    def test_network_error_does_not_mask_as_skip(self):
        with patch.object(rc.requests, "post", side_effect=requests.ConnectionError()):
            assert rc.llm_available({}) is True

    def test_skip_exits_zero_when_disabled(self, capsys):
        with patch.object(rc, "llm_available", return_value=False):
            with pytest.raises(SystemExit) as exc:
                rc.skip_if_llm_disabled("eval_chat", {})
        assert exc.value.code == 0
        assert "SKIP" in capsys.readouterr().err

    def test_skip_is_noop_when_available(self):
        with patch.object(rc, "llm_available", return_value=True):
            rc.skip_if_llm_disabled("eval_chat", {})
