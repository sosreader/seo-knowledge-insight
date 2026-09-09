"""在向量生成當下記錄來源；hash 偵測混批，不是簽章或原子交易。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import numpy as np

INPUT_RULE = "question + U+0020 + answer; UTF-8; no normalization"
MANIFEST_NAME = "qa_embeddings_manifest.json"
ARTIFACTS = ("qa_embeddings.npy", "qa_embeddings_index.json")


def embedding_text(qa: dict) -> str:
    return f"{qa['question']} {qa['answer']}"


def embedding_inputs(items: list[dict]) -> list[str]:
    """先驗完整候選，再交給可能付費的 provider。"""
    _input_hashes(items)
    return [embedding_text(qa) for qa in items]


def _input_hashes(items: list[dict]) -> dict[str, dict[str, str]]:
    hashes = {}
    for qa in items:
        key = qa.get("stable_id")
        if (not isinstance(key, str) or not key.strip() or key in hashes
                or any(not isinstance(qa.get(field), str) or not qa[field].strip()
                       for field in ("question", "answer"))):
            raise ValueError("Embedding manifest requires unique stable IDs and nonempty text")
        body = json.dumps([qa["question"], qa["answer"]], ensure_ascii=False, separators=(",", ":"))
        hashes[key] = {
            "text": hashlib.sha256(embedding_text(qa).encode("utf-8")).hexdigest(),
            "body": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        }
    if not hashes:
        raise ValueError("Embedding manifest requires nonempty candidates")
    return hashes


def _file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _loaded_hashes(vectors: np.ndarray, index: dict) -> dict[str, str]:
    # 與 migration 的 float32 轉換一致，固定 little endian 與 C row order。
    vector_bytes = np.asarray(vectors, dtype="<f4").tobytes(order="C")
    index_bytes = json.dumps(index, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "vectors_float32_le": hashlib.sha256(vector_bytes).hexdigest(),
        "index_canonical_json": hashlib.sha256(index_bytes).hexdigest(),
    }


def build_manifest(directory: Path, items: list[dict], *, model: str, dimension: int,
                   vectors: np.ndarray, index: dict) -> dict:
    """僅供生成流程在 npy/index 完成後呼叫，不推測舊產物的模型。"""
    if not isinstance(model, str) or not model.strip() or type(dimension) is not int or dimension < 1:
        raise ValueError("Invalid embedding manifest model or dimension")
    return {
        "schema_version": 1,
        "run_id": str(uuid4()),
        "model": model,
        "dimension": dimension,
        "input_rule": INPUT_RULE,
        "input_sha256": _input_hashes(items),
        "loaded_sha256": _loaded_hashes(vectors, index),
        "artifact_sha256": {name: _file_hash(directory / name) for name in ARTIFACTS},
    }


def validate_manifest(directory: Path, items: list[dict], *,
                      vectors: np.ndarray | None = None, index: dict | None = None) -> None:
    """正式庫只接受具生成紀錄的 1536 維 OpenAI 候選向量。"""
    try:
        manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
        if vectors is None:
            vectors = np.load(directory / "qa_embeddings.npy", allow_pickle=False)
        if index is None:
            index = json.loads((directory / "qa_embeddings_index.json").read_text(encoding="utf-8"))
        valid = (
            isinstance(manifest, dict)
            and type(manifest.get("schema_version")) is int and manifest["schema_version"] == 1
            and isinstance(manifest.get("run_id"), str) and bool(manifest["run_id"].strip())
            and manifest.get("model") == "text-embedding-3-small"
            and type(manifest.get("dimension")) is int and manifest["dimension"] == 1536
            and manifest.get("input_rule") == INPUT_RULE
            and manifest.get("input_sha256") == _input_hashes(items)
            and manifest.get("loaded_sha256") == _loaded_hashes(vectors, index)
            and manifest.get("artifact_sha256") == {
                name: _file_hash(directory / name) for name in ARTIFACTS
            }
        )
    except (OSError, ValueError):
        raise ValueError("Embedding manifest missing or invalid; regenerate candidate artifacts") from None
    if not valid:
        raise ValueError("Embedding manifest mismatch; regenerate candidate artifacts")
