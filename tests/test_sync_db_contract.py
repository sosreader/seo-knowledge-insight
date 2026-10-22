"""契約測試：sync_db 組出的 payload 必須被 vocus-warehouse 的 sync/models.py 接受。

FakeWarehouse 不驗 schema（extra=forbid、title 長度、正規式），所以另外直接載入倉儲的
models.py（只依賴 pydantic 與標準庫）跑 parse_batch。找不到 vocus-warehouse 原始碼或
pydantic 時 skip（CI 沒有該 repo）；可用 VW_MODELS_PATH 指定 models.py 位置。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync_db_client as client_mod  # noqa: E402
import sync_db_gate as gate  # noqa: E402
import sync_db_sources as src  # noqa: E402

DEFAULT_MODELS = Path.home() / "Documents/vocus-warehouse/src/vocus_warehouse/sync/models.py"
MODELS_PATH = Path(os.environ.get("VW_MODELS_PATH", str(DEFAULT_MODELS)))


@pytest.fixture(scope="module")
def models():
    pytest.importorskip("pydantic")
    if not MODELS_PATH.is_file():
        pytest.skip(f"找不到 vocus-warehouse models.py：{MODELS_PATH}")
    spec = importlib.util.spec_from_file_location("vw_sync_models", MODELS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["vw_sync_models"] = module
    spec.loader.exec_module(module)
    return module


def _entry(filename: str, content: bytes) -> gate.ReviewEntry:
    return gate.ReviewEntry(filename=filename, sha256=hashlib.sha256(content).hexdigest(), status="approved",
                            reviewed_by="r", reviewed_at="2026-10-12", reason="x")


def _roundtrip(items):
    return json.loads(client_mod.encode_body(items))


def test_document_payloads_accepted(models):
    report = b'# r\n<!-- report_meta {"weeks": 1, "model": "m"} -->\n'
    prep = '# p\n```json\n{"meeting_prep_meta": {"date": "2026-10-09"}}\n```\n'.encode("utf-8")
    docs = [
        ("reports", src.LocalDocument("reports", "20261012_900a1937", "report_20261012_900a1937.md", report)),
        ("reports", src.LocalDocument("reports", "20261013", "report_20261013.md", b"no meta")),
        ("meeting_prep", src.LocalDocument("meeting_prep", "20261009_0fc3dcbc",
                                           "meeting_prep_20261009_0fc3dcbc.md", prep)),
    ]
    for table, doc in docs:
        items = models.parse_batch(models.SyncTable(table), _roundtrip([src.build_item(doc, _entry(doc.filename, doc.content))]))
        assert items[0].key() == doc.key


def test_session_payload_accepted(models, tmp_path):
    data = {"id": "0b3c8f4e-1d2a-4b5c-9d8e-7f6a5b4c3d2e", "title": "t" * 200,
            "messages": [{"role": "user", "content": "嗨", "sources": []}], "metadata": {"maturity_level": "L2"},
            "created_at": "2026-10-01T00:00:00.000Z", "updated_at": "2026-10-02T00:00:00+08:00"}
    (tmp_path / "s.json").write_text(json.dumps(data), encoding="utf-8")
    sessions, skipped = src.list_sessions(tmp_path)
    assert skipped == ()
    items = models.parse_batch(models.SyncTable.SESSIONS, _roundtrip([src.build_session_item(sessions[0])]))
    assert items[0].metadata is None  # 不送 metadata：既有列保留原值


def test_limits_match_server(models):
    assert client_mod.MAX_BATCH_ITEMS == models.MAX_BATCH_ITEMS
    assert client_mod.MAX_BODY_BYTES == models.MAX_BODY_BYTES
    assert src.MAX_SESSION_TITLE_LENGTH == models.MAX_TITLE_LENGTH


def test_content_hash_matches_server_pattern(models):
    import re
    pattern = re.compile(models.CONTENT_HASH_PATTERN)
    assert pattern.fullmatch(src.text_content_hash(b"x"))
    assert pattern.fullmatch(src.session_content_hash("t", []))
