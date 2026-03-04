"""Tests for utils/execution_log.py."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture()
def log_dir(tmp_path):
    """Redirect execution log to a temp directory."""
    log_path = tmp_path / "execution_log.jsonl"
    with patch("utils.execution_log._LOG_DIR", tmp_path), \
         patch("utils.execution_log._LOG_PATH", log_path):
        yield tmp_path, log_path


def test_log_execution_creates_jsonl(log_dir):
    from utils.execution_log import log_execution

    tmp_dir, log_path = log_dir
    log_execution(
        command="search",
        args={"query": "SEO", "top_k": 5},
        result={"results_count": 3, "status": "ok"},
        duration_ms=42.123,
    )

    assert log_path.exists()
    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["command"] == "search"
    assert entry["args"]["query"] == "SEO"
    assert entry["duration_ms"] == 42.1
    assert entry["result"]["status"] == "ok"
    assert "timestamp" in entry


def test_log_execution_appends(log_dir):
    from utils.execution_log import log_execution

    _, log_path = log_dir
    log_execution("cmd1", {}, {"status": "ok"}, 1.0)
    log_execution("cmd2", {}, {"status": "ok"}, 2.0)

    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["command"] == "cmd1"
    assert json.loads(lines[1])["command"] == "cmd2"


def test_sanitize_strips_cmd_and_long_values(log_dir):
    from utils.execution_log import log_execution

    _, log_path = log_dir
    long_val = "x" * 600
    log_execution("test", {"cmd": "test", "long": long_val}, {}, 0.0)

    entry = json.loads(log_path.read_text().strip())
    assert "cmd" not in entry["args"]
    assert len(entry["args"]["long"]) == 503  # 500 + "..."


def test_sanitize_redacts_url_query_strings(log_dir):
    from utils.execution_log import log_execution

    _, log_path = log_dir
    log_execution(
        "load-metrics",
        {"source": "https://docs.google.com/spreadsheets/d/abc?access_token=secret123", "tab": "vocus"},
        {},
        0.0,
    )
    entry = json.loads(log_path.read_text().strip())
    assert "secret123" not in entry["args"]["source"]
    assert entry["args"]["source"] == "https://docs.google.com/spreadsheets/d/abc?<redacted>"
    # Non-URL source is left as-is
    log_execution("load-metrics", {"source": "/local/file.tsv"}, {}, 0.0)
    lines = log_path.read_text().strip().split("\n")
    entry2 = json.loads(lines[1])
    assert entry2["args"]["source"] == "/local/file.tsv"


def test_log_execution_never_raises(log_dir):
    """Even with a broken path, log_execution should not raise."""
    from utils.execution_log import log_execution

    with patch("utils.execution_log._LOG_PATH", Path("/nonexistent/dir/log.jsonl")), \
         patch("utils.execution_log._LOG_DIR", Path("/nonexistent/dir")):
        # Should silently skip
        log_execution("test", {}, {}, 0.0)
