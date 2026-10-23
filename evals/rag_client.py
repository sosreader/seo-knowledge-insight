"""Shared rag-api access for evals: base URL, auth headers, llm_disabled detection.

Environment (values are never logged):

    RAG_API_BASE
        Full base including route prefix. Default is the online rag-api:
        https://warehouse-api.vocus.cc/internal/rag
        Local rag-api (Ollama mode) has no prefix: http://localhost:8080
    CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET
        Cloudflare Access service token (online). Used only when both are set.
    SEO_API_KEY
        Local api-key mode (X-API-Key). Used only when the CF pair is incomplete.

Auth precedence: CF Access pair > SEO_API_KEY > no auth header.

Online rag-api has no LLM: chat / hybrid / semantic answer 501 {"error": "llm_disabled"}.
LLM-dependent evals call skip_if_llm_disabled() so CI treats that as skip, not failure.
"""
from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_RAG_API_BASE = "https://warehouse-api.vocus.cc/internal/rag"
LLM_DISABLED_ERROR = "llm_disabled"
AUTH_FAILURE_STATUSES = frozenset({401, 403})
PROBE_TIMEOUT_SECONDS = 15


def _env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def rag_api_base(env: Mapping[str, str] | None = None) -> str:
    """Base URL (no trailing slash) including any route prefix."""
    source = _env(env)
    configured = (source.get("RAG_API_BASE") or "").strip()
    if not configured and source.get("EVAL_API_BASE"):
        logger.warning(
            "EVAL_API_BASE is no longer read (old /api/v1 layout); set RAG_API_BASE instead"
        )
    return (configured or DEFAULT_RAG_API_BASE).rstrip("/")


def endpoint_url(path: str, env: Mapping[str, str] | None = None) -> str:
    """Join the base with a route path such as '/search' (no /api/v1 prefix)."""
    return f"{rag_api_base(env)}/{path.lstrip('/')}"


def build_headers(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """JSON headers plus exactly one auth scheme chosen from the environment."""
    source = _env(env)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    client_id = source.get("CF_ACCESS_CLIENT_ID", "")
    client_secret = source.get("CF_ACCESS_CLIENT_SECRET", "")
    api_key = source.get("SEO_API_KEY", "")
    if client_id and client_secret:
        headers["CF-Access-Client-Id"] = client_id
        headers["CF-Access-Client-Secret"] = client_secret
    elif api_key:
        headers["X-API-Key"] = api_key
    return headers


def is_llm_disabled(status_code: int, body: Any) -> bool:
    """True for the rag-api 'LLM not enabled' response (501 + error=llm_disabled)."""
    if status_code != 501 or not isinstance(body, dict):
        return False
    return body.get("error") == LLM_DISABLED_ERROR


def _safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return None


def response_is_llm_disabled(resp: requests.Response) -> bool:
    return is_llm_disabled(resp.status_code, _safe_json(resp))


def post_json(
    path: str,
    payload: Mapping[str, Any],
    *,
    timeout: float,
    env: Mapping[str, str] | None = None,
) -> requests.Response:
    return requests.post(
        endpoint_url(path, env),
        json=dict(payload),
        headers=build_headers(env),
        timeout=timeout,
    )


def get_json(
    path: str,
    *,
    params: Mapping[str, Any] | None = None,
    timeout: float,
    env: Mapping[str, str] | None = None,
) -> requests.Response:
    return requests.get(
        endpoint_url(path, env),
        params=dict(params or {}),
        headers=build_headers(env),
        timeout=timeout,
    )


def search_results(
    query: str,
    *,
    top_k: int,
    timeout: float,
    extra: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
) -> list[dict] | None:
    """POST /search without 'mode' (server falls back to keyword when LLM is off).

    Returns the result list on HTTP 200, otherwise None. Network errors are
    logged without credentials and reported as None.
    """
    payload: dict[str, Any] = {"query": query, "top_k": top_k, **(extra or {})}
    try:
        resp = post_json("/search", payload, timeout=timeout, env=env)
    except requests.RequestException as exc:
        logger.warning("[rag_client] /search request failed: %s", type(exc).__name__)
        return None
    if resp.status_code != 200:
        logger.warning("[rag_client] /search returned %s", resp.status_code)
        return None
    body = _safe_json(resp) or {}
    results = (body.get("data") or {}).get("results")
    return results if isinstance(results, list) else None


def fetch_qa_item(item_id: str, env: Mapping[str, str] | None = None) -> dict | None:
    """GET /qa/{id}; None when missing, unauthorized or unreachable."""
    try:
        resp = get_json(f"/qa/{item_id}", timeout=PROBE_TIMEOUT_SECONDS, env=env)
    except requests.RequestException as exc:
        logger.warning("[rag_client] /qa/%s request failed: %s", item_id, type(exc).__name__)
        return None
    if resp.status_code != 200:
        return None
    data = (_safe_json(resp) or {}).get("data")
    return data if isinstance(data, dict) else None


def preflight(env: Mapping[str, str] | None = None) -> tuple[bool, str]:
    """Cheap reachability and auth check (GET /qa?limit=1). Returns (ok, reason)."""
    try:
        resp = get_json("/qa", params={"limit": 1}, timeout=PROBE_TIMEOUT_SECONDS, env=env)
    except requests.RequestException as exc:
        return False, f"rag-api unreachable ({type(exc).__name__})"
    if resp.status_code in AUTH_FAILURE_STATUSES:
        return False, f"rag-api rejected credentials (HTTP {resp.status_code})"
    if resp.status_code != 200:
        return False, f"rag-api preflight returned HTTP {resp.status_code}"
    return True, "ok"


def llm_available(env: Mapping[str, str] | None = None) -> bool:
    """False only when rag-api explicitly answers llm_disabled to a chat probe.

    Anything else (reachable, unreachable, auth error) returns True so real
    failures still surface in the eval instead of being silently skipped.
    """
    try:
        resp = post_json("/chat", {"message": "ping"}, timeout=PROBE_TIMEOUT_SECONDS, env=env)
    except requests.RequestException:
        return True
    return not response_is_llm_disabled(resp)


def skip_if_llm_disabled(label: str, env: Mapping[str, str] | None = None) -> None:
    """Exit 0 (skip) when the target rag-api has no LLM. Call before evaluate()."""
    if llm_available(env):
        return
    print(
        f"[{label}] SKIP: rag-api answered 501 llm_disabled "
        f"(base={rag_api_base(env)}); run against local Ollama mode via RAG_API_BASE.",
        file=sys.stderr,
    )
    sys.exit(0)
