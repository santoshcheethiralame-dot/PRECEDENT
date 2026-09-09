"""Point a real coding agent at a seeded repo and ask one question:

    does the precedent fire on exactly the runs the agent gets wrong?

The harness does not drive the agent and does not touch its prompt. It restores
the tree, invokes whatever command is configured, then reads the working tree
with the same git-based recorder the CLI uses. That is the whole point of an
agent-agnostic recorder: nothing here knows what opencode is.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from .change import Change
from .db import Ledger
from .workspace import restore
from . import gate, shell

ROOT = Path(__file__).resolve().parents[1]

# The trial repo lives OUTSIDE this repository, deliberately.
#
# opencode resolves the enclosing git worktree, so a trial repo nested inside
# precedent let a real agent wander out of its workspace and edit seeds/ twice.
# Both times it silently changed the fixture the whole benchmark depends on.
# Containment is not a tidiness concern here; an agent with file access will
# use all of it.
WORKROOT = Path(
    __import__("os").environ.get("PRECEDENT_LIVE_HOME", Path.home() / ".precedent-live"))

TASKS = [
    "Add a phone_verified field to the Patient model.",
    "Add an email field to the Patient model.",
    "Add a date_of_birth field to the Patient model.",
    "The front desk needs to record each patient's insurer. Add it.",
    "Patients should have an allergy note on their record. Add that field.",
    "Add a last_visit field to the Patient model.",
]

MODEL = "opencode/nemotron-3.5-lightning-free"
ARMS = ("off", "advise", "enforce")   # A: nothing · B: prose · C: gates


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True,
                   encoding="utf-8", errors="replace")


def _reset_ledger(repo: Path) -> None:
    """Every trial starts from the same knowledge, or the arms are not comparable."""
    pristine = repo / ".precedent" / "ledger.seed.db"
    live = repo / ".precedent" / "ledger.db"
    if pristine.is_file():
        shutil.copy2(pristine, live)


def trial(repo: Path, seed: Path, led: Ledger, task: str, model: str = MODEL,
          timeout: int = 420, mode: str = "enforce") -> dict:
    restore(seed, repo)
    _reset_ledger(repo)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "reset")

    t0 = time.time()
    # opencode is a .cmd shim on Windows, so it needs a shell and one string.
    cmd = f'opencode run -m {model} "{task.replace(chr(34), chr(39))}"'
    # One launcher, one decoding policy. opencode writes UTF-8 and ANSI;
    # Windows would decode it as cp1252 and take the whole run down.
    proc = shell.run_env(cmd, repo, {"PRECEDENT_MODE": mode}, timeout=timeout)
    said = (proc.stdout or "") + (proc.stderr or "")
    took = round(time.time() - t0, 1)

    ch = Change.from_git(repo)
    verdicts = gate.evaluate(led, str(repo.resolve()), ch)
    oracle = shell.run("python oracle.py", repo)

    return {
        "task": task, "mode": mode, "seconds": took, "exit": proc.returncode,
        "halted": "BLOCKED BY PRECEDENT" in said,
        "touched": ch.touched,
        "oracle_passed": oracle.returncode == 0,
        "oracle": ((oracle.stdout or "") + (oracle.stderr or "")).strip()[:200],
        "fired": [{"n": v.holding_id, "says": v.says, "rule": v.rule, "reason": v.reason}
                  for v in verdicts],
    }


def score(rows: list[dict]) -> dict:
    """A gate is only useful if it fires on the wrong runs and stays quiet on the right ones."""
    tp = sum(1 for r in rows if r["fired"] and not r["oracle_passed"])
    fp = sum(1 for r in rows if r["fired"] and r["oracle_passed"])
    fn = sum(1 for r in rows if not r["fired"] and not r["oracle_passed"])
    tn = sum(1 for r in rows if not r["fired"] and r["oracle_passed"])
    return {
        "trials": len(rows),
        "agent_failed": tp + fn,
        "caught": tp, "missed": fn, "false_alarms": fp, "correctly_silent": tn,
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
    }


def main(n: int | None = None, model: str = MODEL, out: Path | None = None,
         arms: tuple[str, ...] = ARMS) -> dict:
    """The arm B question, asked of a real model.

    Same tasks, same model, same repository state. Arm `advise` is told about
    every past failure in prose and may ignore it; arm `enforce` is stopped.
    Nothing here is synthetic - this is the comparison the synthetic benchmark
    could not make.
    """
    seed = ROOT / "seeds" / "clinic"
    repo = (WORKROOT / "trial").resolve()
    led = Ledger(repo / ".precedent" / "ledger.db")
    tasks = TASKS[:n] if n else TASKS

    rows = []
    for mode in arms:
        for i, task in enumerate(tasks, 1):
            print(f"  [{mode} {i}/{len(tasks)}] {task}", flush=True)
            try:
                r = trial(repo, seed, led, task, model=model, mode=mode)
            except subprocess.TimeoutExpired:
                r = {"task": task, "mode": mode, "timeout": True, "fired": [],
                     "oracle_passed": False, "touched": [], "seconds": None, "halted": False}
            rows.append(r)
            print(f"        oracle={'pass' if r['oracle_passed'] else 'FAIL'}"
                  f"  halted={r.get('halted')}  touched={r['touched']}", flush=True)

    by_arm = {m: score([r for r in rows if r.get("mode") == m]) for m in arms}
    report = {"generated": time.strftime("%Y-%m-%d %H:%M"), "model": model,
              "agent": "opencode", "arms": list(arms), "by_arm": by_arm,
              "score": score(rows), "rows": rows}
    out = out or ROOT / "bench" / "live.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    led.close()
    return report
