"""Restore a working tree in place.

Never delete the directory: on Windows a running server holds it open, and the
ledger lives beside it.
"""
from __future__ import annotations

import shutil
from pathlib import Path

SKIP = {"__pycache__", ".precedent", ".git"}


def files(root: Path) -> set[str]:
    return {str(p.relative_to(root)).replace("\\", "/") for p in Path(root).rglob("*")
            if p.is_file() and not SKIP & set(p.parts)}


def restore(seed: Path, dst: Path) -> None:
    seed, dst = Path(seed), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    want = files(seed)
    for rel in files(dst) - want:
        (dst / rel).unlink(missing_ok=True)
    for rel in want:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(seed / rel, target)
