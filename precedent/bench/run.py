"""Run the arms and write the report."""
from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from pathlib import Path

from ..change import Change
from ..db import Ledger
from ..harvest import Signal
from ..workspace import restore
from .. import harness, provider, record
from . import agent
from .tasks import ORACLE, SEEDS, all_tasks

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / ".bench"


def _learn(led: Ledger, res, repo: Path, output: str) -> dict:
    """File the failure. Deliberately does NOT hand over the oracle command:
    a rule that just says 'run the grader' would make the benchmark circular."""
    sig = Signal("command_fail", "high", "the working tree failed its check",
                 json.dumps({"output": output[:400]}))
    return record.file_case(led, res.run_id, str(repo.resolve()), sig,
                            Change.since(repo, res.before, res.commands), use_model=False)


def run_arm(arm: str, seed: int, p_recall: float, tasks) -> list[dict]:
    base = WORK / arm / str(seed)
    led = Ledger(base / "ledger.db")
    led.wipe()
    order = list(tasks)
    random.Random(seed).shuffle(order)
    rng = random.Random(seed * 7919 + 13)

    rows = []
    for n, task in enumerate(order):
        repo = base / task.repo
        restore(SEEDS / task.repo, repo)
        actions, skipped = agent.script(task, rng, p_recall)

        cb = None
        if arm == "C":
            cb = lambda verdicts, t=task, s=skipped: agent.repair(t, s, verdicts)

        res = harness.run(repo, task.id, led, arm=arm, oracle=ORACLE,
                          scripted=list(actions), on_block=cb, seed=seed)
        if arm in ("B", "C"):
            if not res.passed:
                _learn(led, res, repo, "")
            # free signals: the agent contradicting itself, with no human involved
            record.file_free_signals(led, res.run_id, str(repo.resolve()),
                                     res.watch, Change.since(repo, res.before, res.commands))

        rows.append({"arm": arm, "seed": seed, "order": n, "task": task.id,
                     "repo": task.repo, "trap": task.trap or "", "passed": res.passed,
                     "blocked": res.blocked, "fired": sorted(set(res.fired)),
                     "skipped": len(skipped)})
    counts = led.counts(None)
    led.close()
    for r in rows:
        r["ledger"] = counts
    return rows


def metrics(rows: list[dict]) -> dict:
    out: dict = {}
    for arm in sorted({r["arm"] for r in rows}):
        a = [r for r in rows if r["arm"] == arm]
        traps = [r for r in a if r["trap"]]
        controls = [r for r in a if not r["trap"]]

        repeat_total = repeat_failed = 0
        for seed in sorted({r["seed"] for r in a}):
            seen: set[str] = set()
            for r in sorted([x for x in a if x["seed"] == seed], key=lambda x: x["order"]):
                if not r["trap"]:
                    continue
                if r["trap"] in seen:
                    repeat_total += 1
                    repeat_failed += not r["passed"]
                if not r["passed"]:
                    seen.add(r["trap"])

        out[arm] = {
            "runs": len(a),
            "pass_rate": round(sum(r["passed"] for r in a) / len(a), 4),
            "trap_pass_rate": round(sum(r["passed"] for r in traps) / len(traps), 4) if traps else None,
            "repeat_failure_rate": round(repeat_failed / repeat_total, 4) if repeat_total else None,
            "repeat_seen": repeat_total,
            "false_positive_rate": round(sum(r["blocked"] > 0 for r in controls) / len(controls), 4)
            if controls else None,
            "blocks": sum(r["blocked"] for r in a),
        }
    return out


def by_trap(rows: list[dict]) -> dict:
    out: dict = defaultdict(dict)
    for arm in sorted({r["arm"] for r in rows}):
        for trap in sorted({r["trap"] for r in rows if r["trap"]}):
            sel = [r for r in rows if r["arm"] == arm and r["trap"] == trap]
            if sel:
                out[trap][arm] = round(sum(r["passed"] for r in sel) / len(sel), 4)
    return dict(out)


def curve(rows: list[dict], bucket: int = 6) -> dict:
    """Trap pass rate against position in the sequence. This is the tape:
    arm C starts level with arm A and pulls away as precedent accumulates."""
    out: dict = {}
    for arm in sorted({r["arm"] for r in rows}):
        buckets: dict[int, list[bool]] = {}
        for r in rows:
            if r["arm"] != arm or not r["trap"]:
                continue
            buckets.setdefault(r["order"] // bucket, []).append(r["passed"])
        out[arm] = [{"from": b * bucket, "to": b * bucket + bucket - 1,
                     "n": len(v), "pass_rate": round(sum(v) / len(v), 4)}
                    for b, v in sorted(buckets.items())]
    return out


def regressions(rows: list[dict]) -> list[dict]:
    idx = {(r["arm"], r["seed"], r["task"]): r for r in rows}
    out = []
    for (arm, seed, task), r in idx.items():
        if arm != "C":
            continue
        a = idx.get(("A", seed, task))
        if a and a["passed"] and not r["passed"]:
            out.append({"seed": seed, "task": task, "trap": r["trap"]})
    return out


def main(arms=("A", "C"), seeds=(1, 2, 3, 4, 5), p_recall: float = 0.5,
         out: Path | None = None) -> dict:
    tasks = all_tasks()
    rows: list[dict] = []
    t0 = time.time()
    for arm in arms:
        for seed in seeds:
            rows += run_arm(arm, seed, p_recall, tasks)
            print(f"  {arm}/{seed}  done", flush=True)

    report = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "agent": "synthetic" if not provider.available() else provider.MODEL,
        "p_recall": p_recall,
        "arms": list(arms), "seeds": list(seeds),
        "tasks": len(tasks), "runs": len(rows), "seconds": round(time.time() - t0, 1),
        "metrics": metrics(rows), "by_trap": by_trap(rows), "curve": curve(rows),
        "regressions": regressions(rows), "rows": rows,
    }
    out = out or ROOT / "bench" / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
