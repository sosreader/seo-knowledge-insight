"""候選向量來源追溯，只使用暫存與 mock。"""
import json
from unittest.mock import Mock

import numpy as np
import pytest

from scripts import migrate_to_supabase as migration
from utils.embedding_manifest import build_manifest as _build_manifest, validate_manifest


def build_manifest(path, items, **kwargs):
    """測試 fixture 的已知生成來源，不對真實 legacy 產物補認證。"""
    return _build_manifest(path, items, vectors=np.load(path / "qa_embeddings.npy"),
                           index=json.loads((path / "qa_embeddings_index.json").read_text()), **kwargs)


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    items = [{"id": 1, "stable_id": "a", "question": "問題", "answer": "答案"}]
    (tmp_path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    (tmp_path / "qa_embeddings_index.json").write_text('{"a": 0}')
    np.save(tmp_path / "qa_embeddings.npy", np.ones((1, 1536)))
    manifest = build_manifest(tmp_path, items, model="text-embedding-3-small", dimension=1536)
    (tmp_path / "qa_embeddings_manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(migration, "OUTPUT_DIR", tmp_path)
    return tmp_path, items, manifest


def test_valid_bundle_passes_without_network(bundle, monkeypatch):
    path, items, manifest = bundle
    assert manifest["schema_version"] == 1
    assert manifest["run_id"]
    validate_manifest(path, items)
    post = Mock()
    monkeypatch.setattr(migration.requests, "post", post)
    migration.migrate("", "", dry_run=True)
    post.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "model", "dimension", "schema", "run", "rule", "body", "npy", "index", "malformed"])
def test_corrupt_bundle_blocks_before_write(bundle, monkeypatch, kind):
    path, items, manifest = bundle
    target = path / "qa_embeddings_manifest.json"
    if kind == "missing":
        target.unlink()
    elif kind == "body":
        items[0]["answer"] = "changed"
        (path / "qa_final.json").write_text(json.dumps({"qa_database": items}))
    elif kind == "npy":
        np.save(path / "qa_embeddings.npy", np.zeros((1, 1536)))
    elif kind == "index":
        (path / "qa_embeddings_index.json").write_text('{ "a": 0 }')
    elif kind == "malformed":
        target.write_text("[]")
    else:
        key = {"model": "model", "dimension": "dimension", "schema": "schema_version", "run": "run_id", "rule": "input_rule"}[kind]
        manifest[key] = None
        target.write_text(json.dumps(manifest))
    post = Mock()
    monkeypatch.setattr(migration.requests, "post", post)
    with pytest.raises(ValueError, match="manifest"):
        migration.migrate("url", "key")
    post.assert_not_called()


def test_manifest_does_not_include_body(bundle):
    _, _, manifest = bundle
    assert "問題" not in json.dumps(manifest, ensure_ascii=False)


def test_workflow_uploads_manifest():
    from pathlib import Path
    assert "output/qa_embeddings_manifest.json" in Path(".github/workflows/etl-and-deploy.yml").read_text()


def test_body_boundary_changes_rejected(bundle):
    path, items, _ = bundle
    original = [{**items[0], "question": "a b", "answer": "c"}]
    manifest = build_manifest(path, original, model="text-embedding-3-small", dimension=1536)
    (path / "qa_embeddings_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest"):
        validate_manifest(path, [{**items[0], "question": "a", "answer": "b c"}])


@pytest.mark.parametrize("items", [[], [{"stable_id": "a"}], [{"stable_id": "a", "question": "q", "answer": "a"}] * 2])
def test_invalid_source_not_certified(bundle, items):
    with pytest.raises(ValueError, match="manifest"):
        build_manifest(bundle[0], items, model="text-embedding-3-small", dimension=1536)


def test_invalid_model_not_certified(bundle):
    with pytest.raises(ValueError, match="manifest"):
        build_manifest(bundle[0], bundle[1], model="", dimension=1536)


@pytest.mark.parametrize("local", [False, True])
def test_generation_records_actual_input_and_model(bundle, monkeypatch, local):
    import importlib
    from utils import openai_helper
    mod = importlib.import_module("scripts.03_dedupe_classify")
    path, items, _ = bundle
    monkeypatch.setattr(mod.config, "OUTPUT_DIR", path)
    monkeypatch.setattr(openai_helper, "_has_openai_key", lambda: not local)
    monkeypatch.setattr(mod.config, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    dim = 256 if local else 1536
    generate = Mock(return_value=np.ones((1, dim)).tolist())
    monkeypatch.setattr(mod, "get_embeddings", generate)
    mod._persist_embeddings(items)
    generate.assert_called_once_with(["問題 答案"])
    manifest = json.loads((path / "qa_embeddings_manifest.json").read_text())
    assert manifest["model"] == ("local-embed-v1" if local else "text-embedding-3-small")
    assert manifest["dimension"] == dim
    assert json.loads((path / "qa_embeddings_index.json").read_text()) == {"a": 0}
    if local:
        with pytest.raises(ValueError, match="manifest"):
            validate_manifest(path, items)
    else:
        validate_manifest(path, items)


def test_concurrent_rebuild_cannot_validate_different_loaded_vectors(bundle, monkeypatch):
    path, items, _ = bundle
    original_loader = migration._load_embeddings
    def replace_after_load():
        loaded = original_loader()
        np.save(path / "qa_embeddings.npy", np.zeros((1, 1536)))
        manifest = build_manifest(path, items, model="text-embedding-3-small", dimension=1536)
        (path / "qa_embeddings_manifest.json").write_text(json.dumps(manifest))
        return loaded
    monkeypatch.setattr(migration, "_load_embeddings", replace_after_load)
    post = Mock()
    monkeypatch.setattr(migration.requests, "post", post)
    with pytest.raises(ValueError, match="manifest"):
        migration.migrate("url", "key")
    post.assert_not_called()


def test_invalid_generation_inputs_do_not_call_provider(bundle, monkeypatch):
    import importlib
    mod = importlib.import_module("scripts.03_dedupe_classify")
    monkeypatch.setattr(mod.config, "OUTPUT_DIR", bundle[0])
    generate = Mock(return_value=np.ones((2, 1536)))
    monkeypatch.setattr(mod, "get_embeddings", generate)
    with pytest.raises(ValueError, match="manifest"):
        mod._persist_embeddings(bundle[1] * 2)
    generate.assert_not_called()
