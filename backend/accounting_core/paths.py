"""Filesystem paths for local accounting tools (no real data in git)."""

from __future__ import annotations

import os
from pathlib import Path

# backend/accounting_core/paths.py -> repo root is parent.parent.parent
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def repo_root() -> Path:
    return _REPO_ROOT


def get_finance_db_path() -> Path:
    """SQLite path for books CLI. Override with FINANCE_DB_PATH."""
    raw = os.environ.get("FINANCE_DB_PATH", "").strip()
    if raw:
        return Path(raw)
    return _REPO_ROOT / "backend" / "var" / "finances.db"


def get_schema_path() -> Path:
    raw = os.environ.get("FINANCE_SCHEMA_PATH", "").strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parent / "schema.sql"


def get_samples_dir() -> Path:
    return _REPO_ROOT / "samples"
