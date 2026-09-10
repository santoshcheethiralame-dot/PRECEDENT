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

AGENTS_MD = """# Bengaluru Dental - front desk

`models/patient.py` declares which columns the app reads.
`store.py` builds the database from the files in `migrations/`.
`python oracle.py` checks the app can still read its patients.
"""

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


def setup(seed: Path, repo: Path) -> dict:
    """Build the trial workspace once, and commit it as the baseline.

    The agent's own configuration - its plugin, its permissions, its AGENTS.md -
    is NOT part of the seed, so restoring the seed over the workspace deletes it.
    That is how an earlier run silently disarmed itself: the plugin went away on
    trial one and every arm after that was a bare agent with no memory, printing
    numbers that looked like a result. So the config is installed here, committed,
    and each trial resets with git rather than by restoring the seed again.
    """
    from .demo import teach

    if repo.exists():
        shutil.rmtree(repo, ignore_errors=True)
    restore(seed, repo)

    # Teach first: it dirties the tree, and the baseline must be the seed.
    led = Ledger(repo / ".precedent" / "ledger.db")
    taught = teach(led, repo)
    led.close()
    restore(seed, repo)
    shutil.copy2(repo / ".precedent" / "ledger.db", repo / ".precedent" / "ledger.seed.db")

    # The agent's own configuration goes in LAST, because restore() deletes
    # anything the seed does not contain - which is how the plugin vanished
    # from an earlier run and left every arm identical.
    plugins = repo / ".opencode" / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "plugin" / "precedent.ts", plugins / "precedent.ts")
    (repo / "opencode.json").write_text(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "permission": {"edit": "allow", "bash": "allow", "webfetch": "deny"},
    }, indent=2), encoding="utf-8")
    (repo / "AGENTS.md").write_text(AGENTS_MD, encoding="utf-8")

    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "baseline")
    return taught


def _reset_tree(repo: Path) -> None:
    """Back to the baseline commit, without creating one.

    Committing here instead - which an earlier version did - folds the previous
    trial's work into HEAD, so `git diff HEAD` comes back empty and the recorder
    reports that the agent touched nothing at all.
    """
    _git(repo, "checkout", "--", ".")
    _git(repo, "clean", "-fdq")


def _armed(repo: Path, led: Ledger) -> None:
    """Refuse to start unless the treatment can actually be applied."""
    plugin = repo / ".opencode" / "plugins" / "precedent.ts"
    if not plugin.is_file():
        raise RuntimeError(f"the plugin is not installed at {plugin}")
    binding = [h for h in led.holdings() if h["status"] == "binding"]
    if not binding:
        raise RuntimeError("the ledger holds no binding precedent; there is nothing to enforce")


def trial(repo: Path, seed: Path, led: Ledger, task: str, model: str = MODEL,
          timeout: int = 420, mode: str = "enforce") -> dict:
    _reset_tree(repo)
    _reset_ledger(repo)

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
    taught = setup(seed, repo)
    led = Ledger(repo / ".precedent" / "ledger.db")
    _armed(repo, led)
    print(f"  armed: {taught['status']} - {taught['says']}", flush=True)
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

    # A disarmed run produces numbers that look exactly like a result. The only
    # honest thing to do with one is refuse to report it.
    invalid = []
    if "enforce" in arms:
        e = [r for r in rows if r.get("mode") == "enforce"]
        if not any(r.get("halted") or r.get("fired") for r in e):
            invalid.append("the enforce arm never halted or fired a precedent - "
                           "the treatment was not engaged")
    if all(not r.get("touched") for r in rows):
        invalid.append("the recorder saw no file changes in any trial - "
                       "the workspace reset is wrong")

    report = {"generated": time.strftime("%Y-%m-%d %H:%M"), "model": model,
              "agent": "opencode", "arms": list(arms), "by_arm": by_arm,
              "valid": not invalid, "invalid_because": invalid,
              "score": score(rows), "rows": rows}
    out = out or ROOT / "bench" / "live.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    led.close()
    return report
