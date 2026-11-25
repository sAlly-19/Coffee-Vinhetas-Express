#!/usr/bin/env python3
"""Ponto de entrada do Coffee Vinhetas Express."""

from __future__ import annotations

from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    if getattr(sys, "frozen", False):
        return
    src_dir = Path(__file__).resolve().parent / "src"
    if src_dir.is_dir() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_ensure_src_on_path()

from coffee_vinhetas.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
