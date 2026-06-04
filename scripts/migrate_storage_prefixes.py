#!/usr/bin/env python3
"""Shim — canonical script lives in backend/scripts/ (Docker-mounted)."""
import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parent.parent / "backend" / "scripts" / "migrate_storage_prefixes.py"
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name="__main__")
