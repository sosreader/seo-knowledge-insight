"""Tests for get_capabilities() and format_capability_tag() in openai_helper."""
from __future__ import annotations

import os
from unittest import mock

import pytest


def test_get_capabilities_with_openai_key():
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        from utils.openai_helper import get_capabilities
        caps = get_capabilities()
        assert caps["runtime"] == "cli"
        assert caps["llm"] == "openai"
        assert caps["store"] == "file"
        assert caps["agent"] == "disabled"


def test_get_capabilities_without_openai_key():
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        from utils.openai_helper import get_capabilities
        caps = get_capabilities()
        assert caps["llm"] == "claude-code"


def test_get_capabilities_no_key_env():
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    with mock.patch.dict(os.environ, env, clear=True):
        from utils.openai_helper import get_capabilities
        caps = get_capabilities()
        assert caps["llm"] == "claude-code"


def test_format_capability_tag():
    from utils.openai_helper import format_capability_tag
    tag = format_capability_tag({
        "runtime": "cli",
        "llm": "openai",
        "store": "file",
        "agent": "disabled",
    })
    assert tag == "[runtime:cli | llm:openai | store:file | agent:disabled]"


def test_format_capability_tag_claude_code():
    from utils.openai_helper import format_capability_tag
    tag = format_capability_tag({
        "runtime": "cli",
        "llm": "claude-code",
        "store": "file",
        "agent": "disabled",
    })
    assert tag == "[runtime:cli | llm:claude-code | store:file | agent:disabled]"
