from __future__ import annotations

import importlib
import json
import logging
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def _import_extract_qa():
    return importlib.import_module("scripts.02_extract_qa")


def _import_list_pipeline_state():
    return importlib.import_module("scripts.list_pipeline_state")


def _write_markdown(directory: Path, filename: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(
        "# Sample Title\n\n**來源 URL**: https://example.com/source\n\ncontent",
        encoding="utf-8",
    )


def test_extract_qa_includes_all_source_directories(tmp_path: Path):
    mod = _import_extract_qa()
    import config as cfg

    raw_md_dir = tmp_path / "markdown"
    raw_medium_dir = tmp_path / "medium_markdown"
    raw_ithelp_dir = tmp_path / "ithelp_markdown"
    raw_google_cases_dir = tmp_path / "google_cases_markdown"
    raw_ahrefs_dir = tmp_path / "ahrefs_markdown"
    raw_sej_dir = tmp_path / "sej_markdown"
    raw_growthmemo_dir = tmp_path / "growthmemo_markdown"
    raw_google_blog_dir = tmp_path / "google_blog_markdown"
    raw_google_blog_zhtw_dir = tmp_path / "google_blog_zhtw_markdown"
    raw_webdev_dir = tmp_path / "webdev_markdown"
    raw_screamingfrog_dir = tmp_path / "screamingfrog_markdown"
    qa_per_meeting_dir = tmp_path / "qa_per_meeting"
    qa_per_article_dir = tmp_path / "qa_per_article"
    output_dir = tmp_path / "output"

    qa_per_meeting_dir.mkdir(parents=True, exist_ok=True)
    qa_per_article_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_markdown(raw_md_dir, "meeting.md")
    _write_markdown(raw_medium_dir, "medium.md")
    _write_markdown(raw_ithelp_dir, "ithelp.md")
    _write_markdown(raw_google_cases_dir, "google.md")
    _write_markdown(raw_ahrefs_dir, "ahrefs.md")
    _write_markdown(raw_sej_dir, "sej.md")
    _write_markdown(raw_growthmemo_dir, "growthmemo.md")
    _write_markdown(raw_google_blog_dir, "google_blog.md")
    _write_markdown(raw_google_blog_zhtw_dir, "google_blog_zhtw.md")
    _write_markdown(raw_webdev_dir, "webdev.md")
    _write_markdown(raw_screamingfrog_dir, "screamingfrog.md")

    processed_dirs: list[str] = []

    def _fake_process(md_path: Path) -> dict:
        processed_dirs.append(md_path.parent.name)
        return {
            "qa_pairs": [{"question": f"Q from {md_path.stem}", "answer": "A"}],
            "meeting_summary": "ok",
        }

    with (
        patch.object(cfg, "RAW_MD_DIR", raw_md_dir),
        patch.object(cfg, "RAW_MEDIUM_MD_DIR", raw_medium_dir),
        patch.object(cfg, "RAW_ITHELP_MD_DIR", raw_ithelp_dir),
        patch.object(cfg, "RAW_GOOGLE_CASES_MD_DIR", raw_google_cases_dir),
        patch.object(cfg, "RAW_AHREFS_MD_DIR", raw_ahrefs_dir),
        patch.object(cfg, "RAW_SEJ_MD_DIR", raw_sej_dir),
        patch.object(cfg, "RAW_GROWTHMEMO_MD_DIR", raw_growthmemo_dir),
        patch.object(cfg, "RAW_GOOGLE_BLOG_MD_DIR", raw_google_blog_dir),
        patch.object(cfg, "RAW_GOOGLE_BLOG_ZHTW_MD_DIR", raw_google_blog_zhtw_dir),
        patch.object(cfg, "RAW_WEBDEV_MD_DIR", raw_webdev_dir),
        patch.object(cfg, "RAW_SCREAMINGFROG_MD_DIR", raw_screamingfrog_dir),
        patch.object(cfg, "QA_PER_MEETING_DIR", qa_per_meeting_dir),
        patch.object(cfg, "QA_PER_ARTICLE_DIR", qa_per_article_dir),
        patch.object(cfg, "OUTPUT_DIR", output_dir),
        patch.object(cfg, "OPENAI_MODEL", "test-model"),
        patch.object(mod, "preflight_check"),
        patch.object(mod, "init_laminar"),
        patch.object(mod, "flush_laminar"),
        patch.object(mod, "record_artifact", return_value={"version_id": "v-test"}),
        patch.object(mod, "process_single_meeting", side_effect=_fake_process),
        patch("time.sleep"),
    ):
        mod.main(SimpleNamespace(limit=0, file="", force=True, check=False))

    assert set(processed_dirs) == {
        "markdown",
        "medium_markdown",
        "ithelp_markdown",
        "google_cases_markdown",
        "ahrefs_markdown",
        "sej_markdown",
        "growthmemo_markdown",
        "google_blog_markdown",
        "google_blog_zhtw_markdown",
        "webdev_markdown",
        "screamingfrog_markdown",
    }


def test_extract_qa_check_allows_external_only_sources(
    tmp_path: Path,
    caplog,
    monkeypatch,
):
    mod = _import_extract_qa()
    import config as cfg

    raw_data_dir = tmp_path / "raw_data"
    external_dir = raw_data_dir / "google_blog_zhtw_markdown"
    _write_markdown(external_dir, "google_blog_zhtw.md")

    caplog.set_level(logging.INFO)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with patch.object(cfg, "ROOT_DIR", tmp_path):
        mod.main(SimpleNamespace(limit=0, file="", force=False, check=True))

    assert "[Step 2: Q&A 萃取] 依賴檢查失敗" not in caplog.text
    assert "[Step 2: Q&A 萃取] 依賴檢查通過" in caplog.text


def test_list_pipeline_state_recognizes_article_output_dirs(tmp_path: Path):
    mod = _import_list_pipeline_state()
    import config as cfg

    raw_md_dir = tmp_path / "markdown"
    raw_medium_dir = tmp_path / "medium_markdown"
    raw_ithelp_dir = tmp_path / "ithelp_markdown"
    raw_google_cases_dir = tmp_path / "google_cases_markdown"
    raw_ahrefs_dir = tmp_path / "ahrefs_markdown"
    raw_sej_dir = tmp_path / "sej_markdown"
    raw_growthmemo_dir = tmp_path / "growthmemo_markdown"
    raw_google_blog_dir = tmp_path / "google_blog_markdown"
    raw_google_blog_zhtw_dir = tmp_path / "google_blog_zhtw_markdown"
    raw_webdev_dir = tmp_path / "webdev_markdown"
    raw_screamingfrog_dir = tmp_path / "screamingfrog_markdown"
    qa_per_meeting_dir = tmp_path / "qa_per_meeting"
    qa_per_article_dir = tmp_path / "qa_per_article"

    qa_per_meeting_dir.mkdir(parents=True, exist_ok=True)
    qa_per_article_dir.mkdir(parents=True, exist_ok=True)

    _write_markdown(raw_ahrefs_dir, "ahrefs.md")
    _write_markdown(raw_sej_dir, "sej.md")
    _write_markdown(raw_google_blog_dir, "google_blog.md")
    _write_markdown(raw_google_blog_zhtw_dir, "google_blog_zhtw.md")
    _write_markdown(raw_webdev_dir, "webdev.md")
    _write_markdown(raw_screamingfrog_dir, "screamingfrog.md")

    (qa_per_article_dir / "ahrefs_qa.json").write_text(
        json.dumps({"qa_pairs": [], "meeting_summary": "non-seo article"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (qa_per_meeting_dir / "sej_qa.json").write_text(
        json.dumps({"qa_pairs": [{"question": "Q", "answer": "A"}], "meeting_summary": "ok"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (qa_per_article_dir / "google_blog_qa.json").write_text(
        json.dumps({"qa_pairs": [{"question": "Q", "answer": "A"}], "meeting_summary": "ok"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (qa_per_article_dir / "google_blog_zhtw_qa.json").write_text(
        json.dumps({"qa_pairs": [{"question": "Q", "answer": "A"}], "meeting_summary": "ok"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (qa_per_article_dir / "webdev_qa.json").write_text(
        json.dumps({"qa_pairs": [{"question": "Q", "answer": "A"}], "meeting_summary": "ok"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (qa_per_article_dir / "screamingfrog_qa.json").write_text(
        json.dumps({"qa_pairs": [{"question": "Q", "answer": "A"}], "meeting_summary": "ok"}, ensure_ascii=False),
        encoding="utf-8",
    )

    with (
        patch.object(cfg, "RAW_MD_DIR", raw_md_dir),
        patch.object(cfg, "RAW_MEDIUM_MD_DIR", raw_medium_dir),
        patch.object(cfg, "RAW_ITHELP_MD_DIR", raw_ithelp_dir),
        patch.object(cfg, "RAW_GOOGLE_CASES_MD_DIR", raw_google_cases_dir),
        patch.object(cfg, "RAW_AHREFS_MD_DIR", raw_ahrefs_dir),
        patch.object(cfg, "RAW_SEJ_MD_DIR", raw_sej_dir),
        patch.object(cfg, "RAW_GROWTHMEMO_MD_DIR", raw_growthmemo_dir),
        patch.object(cfg, "RAW_GOOGLE_BLOG_MD_DIR", raw_google_blog_dir),
        patch.object(cfg, "RAW_GOOGLE_BLOG_ZHTW_MD_DIR", raw_google_blog_zhtw_dir),
        patch.object(cfg, "RAW_WEBDEV_MD_DIR", raw_webdev_dir),
        patch.object(cfg, "RAW_SCREAMINGFROG_MD_DIR", raw_screamingfrog_dir),
        patch.object(cfg, "QA_PER_MEETING_DIR", qa_per_meeting_dir),
        patch.object(cfg, "QA_PER_ARTICLE_DIR", qa_per_article_dir),
    ):
        already_done, unprocessed = mod._classify_extract_qa()

    assert {path.name for path in already_done} == {
        "ahrefs.md",
        "sej.md",
        "google_blog.md",
        "google_blog_zhtw.md",
        "webdev.md",
        "screamingfrog.md",
    }
    assert not unprocessed


def test_extract_ahrefs_timeout_uses_heuristic_fallback(tmp_path: Path):
    mod = importlib.import_module("scripts.extract_ahrefs_slice_local")

    source_dir = tmp_path / "ahrefs_markdown"
    output_dir = tmp_path / "qa_per_meeting"
    source_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    article_path = source_dir / "ai-bias.md"
    article_path.write_text(
        "# AI Assistant Bias Revealed\n"
        "- **發佈日期**: 2025-06-19\n"
        "- **來源 URL**: https://example.com/ai-bias\n"
        "- **來源類型**: article\n"
        "- **來源集合**: ahrefs-blog\n"
        "---\n"
        "AI assistants are changing visibility rules.\n\n"
        "## Key takeaways\n\n"
        "* **Google AI Overviews** favor UGC sites.\n"
        "* **ChatGPT** under-represents Wikipedia.\n",
        encoding="utf-8",
    )

    with (
        patch.object(mod, "SOURCE_DIR", source_dir),
        patch.object(mod, "OUTPUT_DIR", output_dir),
        patch.object(mod, "_call_claude", side_effect=RuntimeError("claude 執行逾時（>90s）: claude")),
    ):
        status, name = mod._process_file(
            article_path,
            timeout_seconds=90,
            model_name="haiku",
            max_markdown_chars=2500,
            fast_retry=True,
            heuristic_fallback_on_timeout=True,
        )

    written = json.loads((output_dir / "ai-bias_qa.json").read_text(encoding="utf-8"))
    assert status == "processed"
    assert name == "ai-bias.md"
    assert written["qa_pairs"]
    assert written["qa_pairs"][0]["extraction_model"] == "claude-code-heuristic"