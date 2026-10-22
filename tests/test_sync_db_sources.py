"""scripts/sync_db_sources.py：本機檔解析、metadata 移植、content_hash 演算法、payload 組裝。"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync_db_gate as gate  # noqa: E402
import sync_db_sources as src  # noqa: E402

UUID = "0b3c8f4e-1d2a-4b5c-9d8e-7f6a5b4c3d2e"


class TestContentHash:
    def test_text_hash_is_prefixed_sha256_of_utf8(self):
        text = "週報內容\n"
        expected = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert src.text_content_hash(text.encode("utf-8")) == expected

    def test_session_hash_is_canonical_json_of_title_and_messages(self):
        messages = [{"role": "user", "content": "嗨", "created_at": "2026-10-01T00:00:00Z"}]
        canonical = json.dumps({"title": "標題", "messages": messages},
                               sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        expected = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert src.session_content_hash("標題", messages) == expected

    def test_session_hash_ignores_key_order(self):
        a = [{"role": "user", "content": "x"}]
        b = [{"content": "x", "role": "user"}]
        assert src.session_content_hash("t", a) == src.session_content_hash("t", b)


class TestReportMeta:
    def test_parses_and_normalises(self):
        content = 'x\n<!-- report_meta {"weeks": 2, "generated_at": "2026-10-12", "generation_mode": "claude-code",' \
                  ' "generation_label": "L", "model": "m", "experiment_tag": "e"} -->\n'
        assert src.parse_report_meta(content) == {
            "weeks": 2, "generated_at": "2026-10-12", "generation_mode": "claude-code",
            "generation_label": "L", "model": "m", "experiment_tag": "e",
        }

    def test_defaults_and_drops_non_string_model(self):
        content = '<!-- report_meta {"weeks": true, "model": 3} -->'
        assert src.parse_report_meta(content) == {
            "weeks": 1, "generated_at": "", "generation_mode": "template", "generation_label": "",
        }

    @pytest.mark.parametrize("content", ["no meta", "<!-- report_meta {broken} -->"])
    def test_missing_or_broken_returns_none(self, content):
        assert src.parse_report_meta(content) is None

    @pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
    def test_nan_rejected_like_json_parse(self, constant):
        assert src.parse_report_meta(f'<!-- report_meta {{"weeks": {constant}}} -->') is None


class TestMeetingPrepMeta:
    def _wrap(self, meta: dict) -> str:
        return "# 會議\n```json\n" + json.dumps({"meeting_prep_meta": meta}, ensure_ascii=False) + "\n```\n"

    def test_canonical_scores(self):
        meta = {
            "date": "2026-10-09", "source_report": "output/report_20261012_900a1937.md",
            "scores": {"eeat": {"experience": 3, "expertise": 4, "authoritativeness": 2, "trustworthiness": 1},
                       "maturity": {"strategy": "L2", "process": "L3", "keywords": "L1", "metrics": "L4"}},
            "alert_down_count": 2, "question_count": 5, "generation_mode": "x",
        }
        assert src.parse_meeting_prep_meta(self._wrap(meta)) == {
            "date": "2026-10-09",
            "scores": {"eeat": {"experience": 3, "expertise": 4, "authoritativeness": 2, "trustworthiness": 1},
                       "maturity": {"strategy": "L2", "process": "L3", "keywords": "L1", "metrics": "L4"}},
            "alert_down_count": 2, "question_count": 5, "generation_mode": "x",
            "source_report_date": "20261012",
        }

    def test_shorthand_eeat_and_top_level_maturity_and_s9(self):
        meta = {"date": "d", "eeat_e": 1, "eeat_a": 2, "maturity": {"strategy": "L3"}, "s9_questions": 7,
                "source_report_date": "20261001"}
        parsed = src.parse_meeting_prep_meta(self._wrap(meta))
        assert parsed["scores"]["eeat"] == {"experience": 1, "expertise": 0, "authoritativeness": 2, "trustworthiness": 0}
        assert parsed["scores"]["maturity"] == {"strategy": "L3", "process": "L1", "keywords": "L1", "metrics": "L1"}
        assert parsed["question_count"] == 7
        assert parsed["alert_down_count"] == 0
        assert parsed["generation_mode"] == "claude-code-semantic"
        assert parsed["source_report_date"] == "20261001"

    def test_eeat_avg_fallback_and_null_scores(self):
        meta = {"date": "d", "eeat_avg": 2.5, "scores": {"eeat": None, "maturity": {"strategy": None}}}
        parsed = src.parse_meeting_prep_meta(self._wrap(meta))
        assert parsed["scores"]["eeat"] == {"experience": 2.5, "expertise": 2.5, "authoritativeness": 2.5,
                                            "trustworthiness": 2.5}
        assert parsed["scores"]["maturity"]["strategy"] == "L1"
        assert "source_report_date" not in parsed

    def test_canonical_eeat_non_numbers_become_zero(self):
        meta = {"date": "d", "scores": {"eeat": {"experience": None, "expertise": True}}}
        parsed = src.parse_meeting_prep_meta(self._wrap(meta))
        assert parsed["scores"]["eeat"] == {"experience": 0, "expertise": 0, "authoritativeness": 0,
                                            "trustworthiness": 0}

    def test_truthy_non_object_eeat_yields_zeros_like_ts(self):
        meta = {"date": "d", "scores": {"eeat": 5}, "eeat_e": 4}
        parsed = src.parse_meeting_prep_meta(self._wrap(meta))
        assert parsed["scores"]["eeat"] == {"experience": 0, "expertise": 0, "authoritativeness": 0,
                                            "trustworthiness": 0}

    def test_empty_object_eeat_is_truthy_like_js(self):
        parsed = src.parse_meeting_prep_meta(self._wrap({"date": "d", "scores": {"eeat": {}}, "eeat_avg": 3}))
        assert parsed["scores"]["eeat"]["experience"] == 0

    def test_truthy_non_object_meta_does_not_fall_back(self):
        content = '```json\n{"meeting_prep_meta": "x"}\n```\n<!-- meeting_prep_meta {"date": "d2"} -->'
        assert src.parse_meeting_prep_meta(content) is None

    def test_falsy_meta_falls_back_to_html_comment(self):
        content = '```json\n{"meeting_prep_meta": null}\n```\n<!-- meeting_prep_meta {"date": "d3"} -->'
        assert src.parse_meeting_prep_meta(content)["date"] == "d3"

    def test_legacy_html_comment(self):
        content = '<!-- meeting_prep_meta {"date": "d"} -->'
        assert src.parse_meeting_prep_meta(content)["date"] == "d"

    def test_broken_json_block_falls_back_to_html_comment(self):
        content = '```json\n{"meeting_prep_meta": oops}\n```\n<!-- meeting_prep_meta {"date": "d2"} -->'
        assert src.parse_meeting_prep_meta(content)["date"] == "d2"

    @pytest.mark.parametrize("content", [
        "nothing", '<!-- meeting_prep_meta {bad} -->', '<!-- meeting_prep_meta {"date": 1} -->',
    ])
    def test_unparseable_returns_none(self, content):
        assert src.parse_meeting_prep_meta(content) is None


class TestListLocal:
    def test_lists_only_matching_reports_and_meeting_preps(self, tmp_path):
        for name in ["report_20261012_900a1937.md", "report_20260101.md", "report_bad.md",
                     "meeting_prep_20261009_0fc3dcbc.md", "meeting_prep_20260220_v33.md", "notes.md"]:
            (tmp_path / name).write_text("c", encoding="utf-8")
        reports = src.list_documents(tmp_path, "reports")
        preps = src.list_documents(tmp_path, "meeting_prep")
        assert [d.key for d in reports] == ["20260101", "20261012_900a1937"]
        assert [d.key for d in preps] == ["20261009_0fc3dcbc"]
        assert preps[0].filename == "meeting_prep_20261009_0fc3dcbc.md"
        assert preps[0].content == b"c"

    def test_missing_dir_returns_empty(self, tmp_path):
        assert src.list_documents(tmp_path / "nope", "reports") == ()
        assert src.list_sessions(tmp_path / "nope") == ((), ())

    def test_sessions_validated_and_malformed_skipped(self, tmp_path):
        good = {"id": UUID, "title": "t", "messages": [{"role": "user", "content": "x"}],
                "metadata": {"maturity_level": "L2"},
                "created_at": "2026-10-01T00:00:00.000Z", "updated_at": "2026-10-02T00:00:00+08:00"}
        (tmp_path / "a.json").write_text(json.dumps(good), encoding="utf-8")
        (tmp_path / "b.json").write_text("{broken", encoding="utf-8")
        (tmp_path / "c.json").write_text(json.dumps({**good, "id": "not-a-uuid"}), encoding="utf-8")
        (tmp_path / "d.json").write_text(json.dumps({**good, "messages": "x"}), encoding="utf-8")
        (tmp_path / "e.json").write_text(json.dumps({**good, "updated_at": "2026-10-02T00:00:00"}), encoding="utf-8")
        (tmp_path / "f.json").write_text(json.dumps([1]), encoding="utf-8")
        (tmp_path / "g.json").write_text(json.dumps({**good, "id": UUID + "\n"}), encoding="utf-8")
        (tmp_path / "skip.txt").write_text("x", encoding="utf-8")
        sessions, skipped = src.list_sessions(tmp_path)
        assert [s.id for s in sessions] == [UUID]
        assert sorted(name for name, _ in skipped) == ["b.json", "c.json", "d.json", "e.json", "f.json", "g.json"]

    def test_lone_surrogate_title_is_skipped_not_crash(self, tmp_path):
        # JS 的 "ab😀".slice(0, 3) 存檔後是 "ab\ud83d"
        raw = '{"id": "%s", "title": "ab\\ud83d", "messages": [], "created_at": "2026-10-01T00:00:00Z",' \
              ' "updated_at": "2026-10-01T00:00:00Z"}' % UUID
        (tmp_path / "s.json").write_text(raw, encoding="utf-8")
        sessions, skipped = src.list_sessions(tmp_path)
        assert sessions == () and skipped == (("s.json", "unencodable_text"),)

    def test_title_over_200_is_skipped(self, tmp_path):
        data = {"id": UUID, "title": "&quot;" * 40, "messages": [], "created_at": "2026-10-01T00:00:00Z",
                "updated_at": "2026-10-01T00:00:00Z"}
        (tmp_path / "s.json").write_text(json.dumps(data), encoding="utf-8")
        assert src.list_sessions(tmp_path) == ((), (("s.json", "title_too_long"),))

    def test_document_filename_with_trailing_newline_ignored(self, tmp_path):
        (tmp_path / "report_20261012.md\n").write_text("c", encoding="utf-8")
        assert src.list_documents(tmp_path, "reports") == ()


class TestBuildItems:
    def _entry(self, filename: str, content: bytes) -> gate.ReviewEntry:
        return gate.ReviewEntry(filename=filename, sha256=hashlib.sha256(content).hexdigest(), status="approved",
                                reviewed_by="r", reviewed_at="2026-10-12", reason="x")

    def test_report_item(self):
        content = b'body\n<!-- report_meta {"weeks": 1} -->'
        doc = src.LocalDocument(kind="reports", key="20261012_900a1937", filename="report_20261012_900a1937.md",
                                content=content)
        item = src.build_item(doc, self._entry(doc.filename, content))
        assert item == {
            "date_key": "20261012_900a1937", "filename": "report_20261012_900a1937.md",
            "content": content.decode("utf-8"), "meta": src.parse_report_meta(content.decode("utf-8")),
            "content_hash": src.text_content_hash(content),
            "approved_version": "review:2026-10-12:" + hashlib.sha256(content).hexdigest(),
        }

    def test_meeting_prep_item_defaults_meta_to_empty_object(self):
        content = b"no meta"
        doc = src.LocalDocument(kind="meeting_prep", key="20261009_0fc3dcbc",
                                filename="meeting_prep_20261009_0fc3dcbc.md", content=content)
        item = src.build_item(doc, self._entry(doc.filename, content))
        assert item["meta"] == {}
        assert item["filename"] == doc.filename

    def test_session_item_keeps_old_field_set(self, tmp_path):
        session = src.LocalSession(id=UUID, title="t", messages=({"role": "user", "content": "x"},),
                                   created_at="2026-10-01T00:00:00.000Z", updated_at="2026-10-02T00:00:00Z")
        item = src.build_session_item(session)
        assert item == {
            "id": UUID, "title": "t", "messages": [{"role": "user", "content": "x"}],
            "created_at": "2026-10-01T00:00:00.000Z", "updated_at": "2026-10-02T00:00:00Z",
            "content_hash": src.session_content_hash("t", [{"role": "user", "content": "x"}]),
        }
        assert "metadata" not in item

    def test_non_utf8_document_raises(self):
        doc = src.LocalDocument(kind="reports", key="20261012", filename="report_20261012.md", content=b"\xff")
        with pytest.raises(UnicodeDecodeError):
            src.build_item(doc, self._entry(doc.filename, b"\xff"))
