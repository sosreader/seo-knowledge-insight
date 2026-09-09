"""正式環境發現的分頁／抽樣／排程回歸；不呼叫外部服務。"""
import json
import os
import subprocess
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
import yaml

from scripts import ingest_gsc_url_inspection as ingestion


class Response:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.rows).encode()


def test_postgrest_1000_row_cap_does_not_hide_later_pages():
    first = [{"page": f"https://vocus.cc/article/{i}"} for i in range(1000)]
    with patch.dict(os.environ, {"SUPABASE_URL": "https://db.example", "SUPABASE_SERVICE_KEY": "test"}), \
         patch("urllib.request.urlopen", side_effect=[Response(first), Response([{"page": "https://vocus.cc/last"}])]) as request:
        result = ingestion.fetch_pages_with_any_impressions(pages=["https://vocus.cc/last"])
    assert "https://vocus.cc/last" in result
    assert len(result) == 1001
    assert request.call_args.args[0].get_header("Range") == "1000-1999"


def test_exposure_lookup_has_explicit_property_web_window_and_stable_order():
    today = date(2026, 9, 7)
    with patch.dict(os.environ, {"SUPABASE_URL": "https://db.example", "SUPABASE_SERVICE_KEY": "test"}), \
         patch("urllib.request.urlopen", return_value=Response([])) as request:
        ingestion.fetch_pages_with_any_impressions(pages=["https://vocus.cc/article/a"], today=today, property="https://vocus.cc/")
    url = request.call_args.args[0].full_url
    query = parse_qs(urlparse(url).query)
    assert urlparse(url).path == "/rest/v1/gsc_page_daily"
    assert query["property"] == ["eq.https://vocus.cc/"]
    assert query["search_type"] == ["eq.web"]
    assert query["date"] == ["gte.2026-08-10", "lt.2026-09-07"]
    assert query["impressions"] == ["gt.0"]
    assert query["order"] == ["date.asc,page.asc,device.asc"]
    assert query["page"] == ['in.("https://vocus.cc/article/a")']


@pytest.mark.parametrize("rows", [{"error": "unexpected"}, [None], [{}], [{"page": None}]])
def test_lookup_rejects_invalid_response_instead_of_claiming_no_exposure(rows):
    with patch.dict(os.environ, {"SUPABASE_URL": "https://db.example", "SUPABASE_SERVICE_KEY": "test"}), \
         patch("urllib.request.urlopen", return_value=Response(rows)):
        with pytest.raises(ValueError, match="曝光"):
            ingestion.fetch_pages_with_any_impressions(pages=["https://vocus.cc/article/a"])


def test_twenty_calls_cover_all_three_cohorts():
    pools = [[f"{prefix}{i}" for i in range(100)] for prefix in ("c", "o", "n")]
    sample = ingestion.build_sample(*pools, budget=20)
    assert len(sample) == len(set(sample)) == 20
    assert [sum(url.startswith(prefix) for url in sample) for prefix in ("c", "o", "n")] == [4, 12, 4]


def test_daily_rotation_keeps_controls_stable_and_is_reproducible():
    pools = [[f"{prefix}{i}" for i in range(100)] for prefix in ("c", "o", "n")]
    today = date(2026, 9, 7)
    first = ingestion.build_sample(*pools, budget=20, today=today)
    repeated = ingestion.build_sample(*pools, budget=20, today=today)
    following = ingestion.build_sample(*pools, budget=20, today=today + timedelta(days=1))
    assert first == repeated
    assert first[:4] == following[:4]
    assert first[4:] != following[4:]
    assert set(first) == set(ingestion.build_sample(pools[0], list(reversed(pools[1])), list(reversed(pools[2])), budget=20, today=today))


@pytest.mark.parametrize("budget", [1, 2, 3, 4, 5, 20, 100])
def test_small_or_empty_cohorts_fill_available_budget_without_duplicates(budget):
    result = ingestion.build_sample(["shared", "control"], ["shared", "old"], ["new"], budget=budget)
    assert len(result) == min(budget, 4)
    assert len(result) == len(set(result))


def test_run_passes_date_and_property_to_candidate_lookup():
    with patch.object(ingestion, "fetch_sitemap_pool", return_value=([], [])), \
         patch.object(ingestion, "fetch_pages_with_any_impressions", return_value=set()) as lookup:
        ingestion._build_candidates(date(2026, 9, 7), property="sc-domain:vocus.cc")
    lookup.assert_called_once_with(pages=[], today=date(2026, 9, 7), property="sc-domain:vocus.cc")


def test_lookup_batches_only_candidate_urls_and_never_scans_unfiltered_window():
    candidates = [f'https://vocus.cc/article/{i}?q="甲,乙"' for i in range(95)]
    with patch.dict(os.environ, {"SUPABASE_URL": "https://db.example", "SUPABASE_SERVICE_KEY": "test"}), \
         patch("urllib.request.urlopen", side_effect=lambda *args, **kwargs: Response([])) as request:
        assert ingestion.fetch_pages_with_any_impressions(pages=candidates) == set()
    queried = []
    for call in request.call_args_list:
        url = call.args[0].full_url
        values = parse_qs(urlparse(url).query)["page"][0]
        queried.extend(json.loads("[" + values[4:-1] + "]"))
        assert len(url.encode()) < 4000
        assert call.args[0].get_header("Range") == "0-999"
    assert sorted(queried) == sorted(candidates)
    assert request.call_count >= 3


def test_empty_candidate_list_makes_no_database_request():
    with patch("urllib.request.urlopen") as request:
        assert ingestion.fetch_pages_with_any_impressions(pages=[]) == set()
    request.assert_not_called()


def test_exact_full_page_reads_terminal_empty_page():
    page = [{"page": "https://vocus.cc/a"}] * 1000
    with patch.dict(os.environ, {"SUPABASE_URL": "https://db.example", "SUPABASE_SERVICE_KEY": "test"}), \
         patch("urllib.request.urlopen", side_effect=[Response(page), Response([])]) as request:
        assert ingestion.fetch_pages_with_any_impressions(pages=["https://vocus.cc/a"]) == {"https://vocus.cc/a"}
    assert request.call_count == 2


def test_offset_restarts_for_next_candidate_batch():
    candidates = [f"https://vocus.cc/a{i:03}" for i in range(41)]
    replies = [Response([{"page": candidates[0]}] * 1000), Response([]), Response([{"page": candidates[-1]}])]
    with patch.dict(os.environ, {"SUPABASE_URL": "https://db.example", "SUPABASE_SERVICE_KEY": "test"}), \
         patch("urllib.request.urlopen", side_effect=replies) as request:
        result = ingestion.fetch_pages_with_any_impressions(pages=candidates)
    assert result == {candidates[0], candidates[-1]}
    assert [call.args[0].get_header("Range") for call in request.call_args_list] == ["0-999", "1000-1999", "0-999"]


@pytest.mark.parametrize("pages", [[None, "https://vocus.cc/a"], [" "], ["https://vocus.cc/" + "甲" * 1000]])
def test_invalid_candidates_fail_before_http(pages):
    with patch.dict(os.environ, {"SUPABASE_URL": "https://db.example", "SUPABASE_SERVICE_KEY": "test"}), \
         patch("urllib.request.urlopen") as request:
        with pytest.raises(ValueError, match="曝光候選"):
            ingestion.fetch_pages_with_any_impressions(pages=pages)
    request.assert_not_called()


@pytest.mark.parametrize("event,dry_run,expected", [
    ("schedule", "", "--execute"),
    ("workflow_dispatch", "true", "--dry-run"),
    ("workflow_dispatch", "", "--dry-run"),
    ("workflow_dispatch", "false", "--execute"),
])
def test_workflow_mode_runs_shell_with_mock_python(event, dry_run, expected):
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/gsc-url-inspection.yml").read_text())
    steps = workflow["jobs"]["ingest"]["steps"]
    step = next(s for s in steps if s.get("name") == "Sample-inspect GSC URLs")
    # 模擬 Actions 注入的 env，實際執行 workflow shell；python 函式只輸出參數。
    command = 'python() { printf "%s\\n" "$*"; };\n' + step["run"]
    result = subprocess.run(["bash", "-c", command], env={
        **os.environ, "GITHUB_EVENT_NAME": event, "DRY_RUN": dry_run or "true",
        "SAMPLE_SIZE": "20", "QUOTA_BUDGET": "500",
    }, capture_output=True, text=True, check=True)
    assert expected in result.stdout
    assert "--sample-size 20 --quota-budget 500" in result.stdout
