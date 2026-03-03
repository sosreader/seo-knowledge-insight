"""tests/test_report_notion_link.py — 週報 Notion 連結格式測試"""
from __future__ import annotations


class TestReportSourceInfo:
    """測試 04_generate_report.py 中 source_info 組裝邏輯。"""

    @staticmethod
    def _build_source_info(qa: dict) -> str:
        """
        複製 04_generate_report.py 中的 source_info 邏輯，
        用於隔離測試（不需要 OpenAI 依賴）。
        """
        source_title = qa.get("source_title", "")
        source_date = qa.get("source_date", "")
        notion_url = qa.get("_enrichment", {}).get("notion_url", "")
        if source_title or source_date:
            source_text = "、".join(p for p in [source_title, source_date] if p)
            if notion_url:
                return f"來源：[{source_text}]({notion_url})\n"
            return f"來源：{source_text}\n"
        return ""

    def test_with_notion_url(self):
        qa = {
            "source_title": "SEO 0628",
            "source_date": "2023-06-28",
            "_enrichment": {
                "notion_url": "https://www.notion.so/SEO-0628-abc123",
            },
        }
        result = self._build_source_info(qa)
        assert result == "來源：[SEO 0628、2023-06-28](https://www.notion.so/SEO-0628-abc123)\n"

    def test_without_notion_url(self):
        qa = {
            "source_title": "SEO 0628",
            "source_date": "2023-06-28",
            "_enrichment": {},
        }
        result = self._build_source_info(qa)
        assert result == "來源：SEO 0628、2023-06-28\n"

    def test_no_enrichment_field(self):
        qa = {
            "source_title": "SEO 0628",
            "source_date": "2023-06-28",
        }
        result = self._build_source_info(qa)
        assert result == "來源：SEO 0628、2023-06-28\n"

    def test_empty_notion_url(self):
        qa = {
            "source_title": "SEO 0628",
            "source_date": "2023-06-28",
            "_enrichment": {"notion_url": ""},
        }
        result = self._build_source_info(qa)
        assert result == "來源：SEO 0628、2023-06-28\n"

    def test_only_title(self):
        qa = {
            "source_title": "SEO 0628",
            "source_date": "",
            "_enrichment": {"notion_url": "https://www.notion.so/SEO-0628-abc123"},
        }
        result = self._build_source_info(qa)
        assert result == "來源：[SEO 0628](https://www.notion.so/SEO-0628-abc123)\n"

    def test_only_date(self):
        qa = {
            "source_title": "",
            "source_date": "2023-06-28",
            "_enrichment": {"notion_url": "https://www.notion.so/SEO-0628-abc123"},
        }
        result = self._build_source_info(qa)
        assert result == "來源：[2023-06-28](https://www.notion.so/SEO-0628-abc123)\n"

    def test_no_source_info(self):
        qa = {"source_title": "", "source_date": ""}
        result = self._build_source_info(qa)
        assert result == ""

    def test_markdown_link_format(self):
        """確認產出是合法 Markdown 超連結。"""
        qa = {
            "source_title": "SEO 會議_2024/05/02",
            "source_date": "2024-05-02",
            "_enrichment": {
                "notion_url": "https://www.notion.so/SEO-_2024-05-02-052d1af93b5b4de688e0ac006848ed45",
            },
        }
        result = self._build_source_info(qa)
        assert "[" in result and "](" in result and ")" in result


class TestEnrichQaNotionUrl:
    """測試 enrich_qa._enrich_qa 注入 notion_url。"""

    def test_notion_url_injected(self):
        from scripts.enrich_qa import _enrich_qa

        qa = {
            "id": 1,
            "keywords": ["SEO"],
            "source_date": "2024-01-01",
            "source_file": "SEO_0628.md",
            "evergreen": False,
        }
        notion_map = {"SEO_0628.md": "https://www.notion.so/SEO-0628-abc123"}

        result = _enrich_qa(qa, {}, notion_map)

        assert result["_enrichment"]["notion_url"] == "https://www.notion.so/SEO-0628-abc123"

    def test_missing_source_file(self):
        from scripts.enrich_qa import _enrich_qa

        qa = {
            "id": 2,
            "keywords": [],
            "source_date": "2024-01-01",
            "source_file": "unknown.md",
            "evergreen": False,
        }
        result = _enrich_qa(qa, {}, {})

        assert result["_enrichment"]["notion_url"] == ""

    def test_original_qa_not_mutated(self):
        from scripts.enrich_qa import _enrich_qa

        qa = {
            "id": 3,
            "keywords": ["test"],
            "source_date": "2024-01-01",
            "source_file": "A.md",
            "evergreen": False,
        }
        notion_map = {"A.md": "https://www.notion.so/A-123"}

        result = _enrich_qa(qa, {}, notion_map)

        assert "_enrichment" not in qa  # 原始 dict 不被修改
        assert result["_enrichment"]["notion_url"] == "https://www.notion.so/A-123"
