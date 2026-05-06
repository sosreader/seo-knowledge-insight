from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def test_extract_qa_main_runs_without_openai_key(tmp_path: Path) -> None:
    mod = importlib.import_module("scripts.02_extract_qa")
    import config as cfg

    raw_md_dir = tmp_path / "markdown"
    qa_per_meeting_dir = tmp_path / "qa_per_meeting"
    qa_per_article_dir = tmp_path / "qa_per_article"
    output_dir = tmp_path / "output"

    raw_md_dir.mkdir(parents=True, exist_ok=True)
    qa_per_meeting_dir.mkdir(parents=True, exist_ok=True)
    qa_per_article_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (raw_md_dir / "SEO_會議_20260427.md").write_text(
        "# SEO 會議_20260427\n\n"
        "- **Notion URL**: https://www.notion.so/example\n\n"
        "本週討論 canonical 指向與 Search Console 檢查結果。\n\n"
        "也提到 Discover 流量波動，需要持續觀察。\n",
        encoding="utf-8",
    )

    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False),
        patch.object(cfg, "RAW_MD_DIR", raw_md_dir),
        patch.object(cfg, "RAW_MEDIUM_MD_DIR", tmp_path / "medium_markdown"),
        patch.object(cfg, "RAW_ITHELP_MD_DIR", tmp_path / "ithelp_markdown"),
        patch.object(cfg, "RAW_GOOGLE_CASES_MD_DIR", tmp_path / "google_cases_markdown"),
        patch.object(cfg, "RAW_AHREFS_MD_DIR", tmp_path / "ahrefs_markdown"),
        patch.object(cfg, "RAW_SEJ_MD_DIR", tmp_path / "sej_markdown"),
        patch.object(cfg, "RAW_GROWTHMEMO_MD_DIR", tmp_path / "growthmemo_markdown"),
        patch.object(cfg, "RAW_GOOGLE_BLOG_MD_DIR", tmp_path / "google_blog_markdown"),
        patch.object(cfg, "RAW_WEBDEV_MD_DIR", tmp_path / "webdev_markdown"),
        patch.object(cfg, "RAW_SCREAMINGFROG_MD_DIR", tmp_path / "screamingfrog_markdown"),
        patch.object(cfg, "QA_PER_MEETING_DIR", qa_per_meeting_dir),
        patch.object(cfg, "QA_PER_ARTICLE_DIR", qa_per_article_dir),
        patch.object(cfg, "OUTPUT_DIR", output_dir),
        patch.object(mod, "init_laminar"),
        patch.object(mod, "flush_laminar"),
        patch.object(mod, "record_artifact", return_value={"version_id": "v-local"}),
        patch("time.sleep"),
    ):
        mod.main(SimpleNamespace(limit=0, file="", force=True, check=False))

    artifact = json.loads((qa_per_meeting_dir / "SEO_會議_20260427_qa.json").read_text(encoding="utf-8"))
    assert artifact["qa_pairs"]
    assert artifact["qa_pairs"][0]["extraction_model"] == "claude-code-heuristic"

    merged = json.loads((output_dir / "qa_all_raw.json").read_text(encoding="utf-8"))
    assert merged["total_qa_count"] >= 1


def test_extract_qa_from_text_falls_back_without_openai_key() -> None:
    from utils import openai_helper

    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        result = openai_helper.extract_qa_from_text(
            "- **會議日期**: 2026-04-27\n- **Notion URL**: https://www.notion.so/example\n\n"
            "本次會議討論 canonical 指向錯誤造成索引訊號分散，也提到要用 Search Console 驗證。",
            "SEO 會議",
            "2026-04-27",
        )

    assert result["qa_pairs"]
    assert result["qa_pairs"][0]["keywords"]
    assert result["extraction_model"] == "claude-code-heuristic"
    assert "Notion URL" not in result["qa_pairs"][0]["answer"]