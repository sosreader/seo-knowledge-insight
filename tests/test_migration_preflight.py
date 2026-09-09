"""遷移候選資料與有限恢復的離線回歸測試。"""
import json
from unittest.mock import Mock

import numpy as np
import pytest
import requests

from scripts import migrate_to_supabase as migration
from utils.embedding_manifest import build_manifest


def _manifest(path, items):
    manifest = build_manifest(path, items, model="text-embedding-3-small", dimension=1536,
                              vectors=np.load(path / "qa_embeddings.npy"),
                              index=json.loads((path / "qa_embeddings_index.json").read_text()))
    (path / "qa_embeddings_manifest.json").write_text(json.dumps(manifest))


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(migration, "OUTPUT_DIR", tmp_path)
    items = [{"id": 1, "stable_id": "a", "question": "問題", "answer": "答案"}]
    (tmp_path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    (tmp_path / "qa_embeddings_index.json").write_text(json.dumps({"a": 0}))
    np.save(tmp_path / "qa_embeddings.npy", np.ones((1, 1536)))
    _manifest(tmp_path, items)
    return tmp_path, items


def test_dry_run_no_credentials_or_content(candidate, monkeypatch, caplog):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["migration", "--dry-run"])
    with caplog.at_level("INFO"):
        migration.main()
    assert "問題" not in caplog.text


@pytest.mark.parametrize("kind", ["empty", "duplicate", "question", "dimension", "nan", "missing", "index"])
def test_invalid_candidates_block_all_writes(candidate, monkeypatch, kind):
    path, items = candidate
    if kind == "empty":
        items = []
        np.save(path / "qa_embeddings.npy", np.ones((0, 1536)))
    elif kind == "duplicate":
        items *= 2
        np.save(path / "qa_embeddings.npy", np.ones((2, 1536)))
    elif kind == "question":
        items[0]["question"] = " "
    elif kind == "dimension":
        np.save(path / "qa_embeddings.npy", np.ones((1, 3)))
    elif kind == "nan":
        np.save(path / "qa_embeddings.npy", np.full((1, 1536), np.nan))
    elif kind == "missing":
        (path / "qa_embeddings.npy").unlink()
    elif kind == "index":
        (path / "qa_embeddings_index.json").write_text('{"other": 0}')
    (path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    post = Mock()
    monkeypatch.setattr(migration.requests, "post", post)
    with pytest.raises(ValueError):
        migration.migrate("url", "key")
    post.assert_not_called()


def test_stale_enriched_cannot_replace_final(candidate):
    path, items = candidate
    enriched = [{**items[0], "answer": "過期", "_enrichment": {"synonyms": ["舊"]}}]
    (path / "qa_enriched.json").write_text(json.dumps({"qa_database": enriched}))
    assert migration._load_qa_data() == items


def test_timeout_split_and_fatal_stop(monkeypatch, caplog):
    timeout = Mock(status_code=500)
    timeout.json.return_value = {"code": "57014", "message": "secret"}
    fatal = Mock(status_code=401, text="secret")
    post = Mock(side_effect=[timeout, fatal])
    monkeypatch.setattr(migration.requests, "post", post)
    assert migration._upsert_batch("url", "key", [{"id": "a"}, {"id": "b"}]) == (0, 2)
    assert post.call_count == 2
    assert "secret" not in caplog.text


def test_network_retry_is_bounded(monkeypatch, caplog):
    post = Mock(side_effect=requests.Timeout("secret"))
    monkeypatch.setattr(migration.requests, "post", post)
    monkeypatch.setattr(migration.time, "sleep", lambda _: None)
    assert migration._upsert_batch("url", "key", [{"id": "a"}]) == (0, 1)
    assert post.call_count <= 3
    assert "secret" not in caplog.text


def test_failure_stops_remaining_batches(candidate, monkeypatch):
    path, items = candidate
    items += [{**items[0], "id": 2, "stable_id": "b"}]
    (path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    (path / "qa_embeddings_index.json").write_text('{"a": 1, "b": 0}')
    np.save(path / "qa_embeddings.npy", np.ones((2, 1536)))
    upsert = Mock(return_value=(0, 1))
    _manifest(path, items)
    monkeypatch.setattr(migration, "_upsert_batch", upsert)
    with pytest.raises(SystemExit):
        migration.migrate("url", "key", batch_size=1)
    assert upsert.call_count == 1


def test_index_alignment_and_successful_split(candidate, monkeypatch):
    path, items = candidate
    items += [{**items[0], "id": 2, "stable_id": "b"}]
    (path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    (path / "qa_embeddings_index.json").write_text('{"a": 1, "b": 0}')
    np.save(path / "qa_embeddings.npy", np.stack([np.zeros(1536), np.ones(1536)]))
    _manifest(path, items)
    timeout = Mock(status_code=500)
    timeout.json.return_value = {"code": "57014"}
    post = Mock(side_effect=[timeout, Mock(status_code=201), Mock(status_code=200)])
    monkeypatch.setattr(migration.requests, "post", post)
    migration.migrate("url", "key", include_extended_fields=True)
    rows = post.call_args_list[0].kwargs["json"]
    assert rows[0]["embedding"] == [1.0] * 1536
    assert rows[1]["embedding"] == [0.0] * 1536
    assert post.call_count == 3


def test_workflow_preflight_precedes_upload():
    from pathlib import Path
    workflow = Path(".github/workflows/etl-and-deploy.yml").read_text()
    assert workflow.index("migrate_to_supabase.py --dry-run") < workflow.index("- name: Upload artifacts")
    assert "output/qa_embeddings_index.json" in workflow


def test_timeout_split_has_depth_limit(monkeypatch):
    response = Mock(status_code=500)
    response.json.return_value = {"code": "57014"}
    post = Mock(return_value=response)
    monkeypatch.setattr(migration.requests, "post", post)
    assert migration._upsert_batch("url", "key", [{"id": str(i)} for i in range(100)]) == (0, 100)
    assert post.call_count == 4


@pytest.mark.parametrize("index", [{"a": True}, {"a": -1}, {"a": 1}, []])
def test_bad_index_values(candidate, index):
    path, _ = candidate
    (path / "qa_embeddings_index.json").write_text(json.dumps(index))
    with pytest.raises(ValueError, match="index"):
        migration.migrate("url", "key", dry_run=True)


def test_matching_enrichment(candidate):
    path, items = candidate
    enriched = [{**items[0], "_enrichment": {"synonyms": ["相關詞"]}}]
    (path / "qa_enriched.json").write_text(json.dumps({"qa_database": enriched}))
    assert migration._load_qa_data() == enriched


@pytest.mark.parametrize("field,value", [("confidence", "bad"), ("keywords", "bad"), ("source_title", {}), ("evergreen", "false"), ("confidence", float("nan"))])
def test_metadata_schema_blocks_before_write(candidate, monkeypatch, field, value):
    path, items = candidate
    items[0][field] = value
    (path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    post = Mock()
    monkeypatch.setattr(migration.requests, "post", post)
    with pytest.raises(ValueError):
        migration.migrate("url", "key")
    post.assert_not_called()


def test_verify_failure_is_nonzero(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake")
    monkeypatch.setattr("sys.argv", ["migration", "--verify"])
    monkeypatch.setattr(migration, "_verify_count", lambda *_: -1)
    with pytest.raises(SystemExit):
        migration.main()


@pytest.mark.parametrize("enrichment", [{"synonyms": "bad"}, {"freshness_score": "bad"}, {"search_hit_count": 0.5}, {"maturity_relevance": "L9"}])
def test_enrichment_schema_preflight(candidate, monkeypatch, enrichment):
    path, items = candidate
    items[0]["_enrichment"] = enrichment
    (path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    post = Mock()
    monkeypatch.setattr(migration.requests, "post", post)
    with pytest.raises(ValueError):
        migration.migrate("url", "key")
    post.assert_not_called()


def test_invalid_later_batch_prevents_first_write(candidate, monkeypatch):
    path, items = candidate
    items += [{**items[0], "id": 2, "stable_id": "b", "_enrichment": {"freshness_score": "bad"}}]
    (path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    (path / "qa_embeddings_index.json").write_text('{"a": 0, "b": 1}')
    np.save(path / "qa_embeddings.npy", np.ones((2, 1536)))
    post = Mock()
    monkeypatch.setattr(migration.requests, "post", post)
    with pytest.raises(ValueError):
        migration.migrate("url", "key", batch_size=1)
    post.assert_not_called()
