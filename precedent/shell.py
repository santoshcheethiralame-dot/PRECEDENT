"""Every subprocess we launch, launched the same way.

PYTHONDONTWRITEBYTECODE matters more than it looks. A .pyc records the source
mtime to one-second granularity, and these runs write a file and import it
inside the same second - so Python cannot tell the cache is stale and serves
the PREVIOUS version of the module. A failing run then reads the last run's
field list and its oracle passes. Bytecode caching quietly inverts the result.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def run(cmd: str, cwd: Path | str, timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                          text=True, env=ENV, timeout=timeout,
                          encoding="utf-8", errors="replace")


def run_env(cmd: str, cwd, extra: dict | None = None, timeout: float | None = None):
    """Same launcher, with extra environment - used to select a benchmark arm."""
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True,
                          env={**ENV, **(extra or {})}, timeout=timeout,
                          encoding="utf-8", errors="replace")
