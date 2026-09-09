"""Point a real coding agent at a seeded repo and ask one question:

    does the precedent fire on exactly the runs the agent gets wrong?

The harness does not drive the agent and does not touch its prompt. It restores
the tree, invokes whatever command is configured, then reads the working tree
with the same git-based recorder the CLI uses. That is the whole point of an
agent-agnostic recorder: nothing here knows what opencode is.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .change import Change
from .db import Ledger
from .workspace import restore
from . import gate

ROOT = Path(__file__).resolve().parents[1]

TASKS = [
    "Add a phone_verified field to the Patient model.",
    "Add an email field to the Patient model.",
    "Add a date_of_birth field to the Patient model.",
    "The front desk needs to record each patient's insurer. Add it.",
    "Patients should have an allergy note on their record. Add that field.",
    "Add a last_visit field to the Patient model.",
]

MODEL = "cloudflare-workers-ai/@cf/qwen/qwen2.5-coder-32b-instruct"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True)


def trial(repo: Path, seed: Path, led: Ledger, task: str, model: str = MODEL,
          timeout: int = 420) -> dict:
    restore(seed, repo)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "reset")

    t0 = time.time()
    proc = subprocess.run(["opencode", "run", "-m", model, task], cwd=repo,
                          capture_output=True, text=True, timeout=timeout, shell=True)
    took = round(time.time() - t0, 1)

    ch = Change.from_git(repo)
    verdicts = gate.evaluate(led, str(repo.resolve()), ch)
    oracle = subprocess.run("python oracle.py", cwd=repo, shell=True,
                            capture_output=True, text=True)

    return {
        "task": task, "seconds": took, "exit": proc.returncode,
        "touched": ch.touched,
        "oracle_passed": oracle.returncode == 0,
        "oracle": (oracle.stdout + oracle.stderr).strip()[:200],
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


def main(n: int | None = None, model: str = MODEL, out: Path | None = None) -> dict:
    seed = ROOT / "seeds" / "clinic"
    repo = (ROOT / ".live" / "clinic").resolve()
    led = Ledger(repo / ".precedent" / "ledger.db")
    tasks = TASKS[:n] if n else TASKS

    rows = []
    for i, task in enumerate(tasks, 1):
        print(f"  [{i}/{len(tasks)}] {task}", flush=True)
        try:
            r = trial(repo, seed, led, task, model=model)
        except subprocess.TimeoutExpired:
            r = {"task": task, "timeout": True, "fired": [], "oracle_passed": False,
                 "touched": [], "seconds": None}
        rows.append(r)
        print(f"        oracle={'pass' if r['oracle_passed'] else 'FAIL'} "
              f"fired={len(r['fired'])} touched={r['touched']}", flush=True)

    report = {"generated": time.strftime("%Y-%m-%d %H:%M"), "model": model,
              "agent": "opencode", "score": score(rows), "rows": rows}
    out = out or ROOT / "bench" / "live.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    led.close()
    return report
