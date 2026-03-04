"""Tests for /api/v1/reports endpoints."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


class TestListReports:
    def test_empty_output_dir(self, client, tmp_path):
        with patch("app.routers.reports._REPORT_DIR", tmp_path):
            resp = client.get("/api/v1/reports")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_sorted_reports(self, client, tmp_path):
        (tmp_path / "report_20260301.md").write_text("older report")
        (tmp_path / "report_20260304.md").write_text("newer report content")
        (tmp_path / "not_a_report.md").write_text("ignored")

        with patch("app.routers.reports._REPORT_DIR", tmp_path):
            resp = client.get("/api/v1/reports")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert data["items"][0]["date"] == "20260304"
        assert data["items"][1]["date"] == "20260301"
        assert data["items"][0]["size_bytes"] > 0

    def test_nonexistent_dir_returns_empty(self, client, tmp_path):
        missing = tmp_path / "no_such_dir"
        with patch("app.routers.reports._REPORT_DIR", missing):
            resp = client.get("/api/v1/reports")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0


class TestGetReport:
    def test_valid_date_returns_content(self, client, tmp_path):
        content = "# SEO Weekly Report 2026-03-04\nTest content."
        (tmp_path / "report_20260304.md").write_text(content)

        with patch("app.routers.reports._REPORT_DIR", tmp_path):
            resp = client.get("/api/v1/reports/20260304")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["date"] == "20260304"
        assert data["content"] == content
        assert data["filename"] == "report_20260304.md"
        assert data["size_bytes"] == len(content.encode("utf-8"))

    def test_invalid_date_format_returns_400(self, client):
        resp = client.get("/api/v1/reports/2026-03-04")
        assert resp.status_code == 400

    def test_nonexistent_date_returns_404(self, client, tmp_path):
        with patch("app.routers.reports._REPORT_DIR", tmp_path):
            resp = client.get("/api/v1/reports/20260399")
        assert resp.status_code == 404


class TestGenerateReport:
    def test_ssrf_blocked_bad_scheme(self, client):
        resp = client.post(
            "/api/v1/reports/generate",
            json={"metrics_url": "ftp://evil.com/payload"},
        )
        assert resp.status_code == 400
        assert "http or https" in resp.json()["detail"]

    def test_ssrf_blocked_bad_host(self, client):
        resp = client.post(
            "/api/v1/reports/generate",
            json={"metrics_url": "https://evil.com/steal"},
        )
        assert resp.status_code == 400
        assert "host not allowed" in resp.json()["detail"]

    def test_valid_host_accepted(self, client, tmp_path):
        report_content = "# Generated report"
        report_file = tmp_path / "report_20260304.md"
        report_file.write_text(report_content)

        with (
            patch("app.routers.reports._REPORT_DIR", tmp_path),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            resp = client.post(
                "/api/v1/reports/generate",
                json={"metrics_url": "https://docs.google.com/spreadsheets/d/abc"},
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["date"] == "20260304"

    def test_no_url_also_works(self, client, tmp_path):
        (tmp_path / "report_20260304.md").write_text("# Report")

        with (
            patch("app.routers.reports._REPORT_DIR", tmp_path),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            resp = client.post("/api/v1/reports/generate", json={})

        assert resp.status_code == 200

    def test_subprocess_failure_returns_500(self, client, tmp_path):
        with (
            patch("app.routers.reports._REPORT_DIR", tmp_path),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "some error"
            resp = client.post("/api/v1/reports/generate", json={})

        assert resp.status_code == 500

    def test_subprocess_timeout_returns_504(self, client):
        import subprocess

        from app.core.limiter import limiter
        limiter.reset()

        with patch(
            "app.routers.reports.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="x", timeout=120),
        ):
            resp = client.post("/api/v1/reports/generate", json={})

        assert resp.status_code == 504
