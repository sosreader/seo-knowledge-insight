"""Deterministic stable ID generation for QA items.

Shared across pipeline scripts to avoid ID drift from duplicated implementations.
Formula: sha256(f"{source_file}::{question[:120]}")[:16]
"""
from __future__ import annotations

import hashlib


def compute_stable_id(source_file: str, question: str) -> str:
    """Generate a 16-char hex stable ID from source file and question."""
    content = f"{source_file}::{question[:120]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
