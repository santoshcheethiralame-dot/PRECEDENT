"""Freeze the ledger and the benchmark into two JSON files, then serve them.

The board is static on purpose: no framework, no build step, and it deploys to
any free static host exactly as it runs locally.
"""
from __future__ import annotations

import json
import shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

from .db import Ledger

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def _pick_ledger() -> Path | None:
    for c in (ROOT / ".bench" / "C" / "1" / "ledger.db",
              ROOT / ".live" / "trial" / ".precedent" / "ledger.db",
              ROOT / ".demo" / "ledger.db"):
        if c.is_file():
            return c
    return None


def dump(ledger: Path | None = None) -> dict:
    ledger = Path(ledger) if ledger else _pick_ledger()
    WEB.mkdir(parents=True, exist_ok=True)

    data: dict = {"counts": {"cases": 0, "binding": 0, "persuasive": 0, "overruled": 0},
                  "holdings": [], "cases": []}
    if ledger and ledger.is_file():
        led = Ledger(ledger)
        holdings = led.holdings()
        for h in holdings:
            h["citations"] = led.citations(h["id"])
            h["case"] = led.case(h["case_id"])
        data = {"counts": led.counts(None), "holdings": holdings, "cases": led.cases(),
                "source": ledger.as_posix()}
        led.close()
    (WEB / "data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    report = ROOT / "bench" / "report.json"
    if report.is_file():
        # rows are the bulk and the tape needs only the ordered outcomes
        full = json.loads(report.read_text(encoding="utf-8"))
        slim = {k: v for k, v in full.items() if k != "rows"}
        slim["tape"] = {}
        for arm in full.get("arms", []):
            # every seed, in sequence: the tape is all 300 runs, not a sample
            rows = sorted((r for r in full["rows"] if r["arm"] == arm),
                          key=lambda r: (r["seed"], r["order"]))
            slim["tape"][arm] = [{"p": int(r["passed"]), "b": int(bool(r["blocked"])),
                                  "t": r["trap"] or "", "task": r["task"]} for r in rows]
        (WEB / "report.json").write_text(json.dumps(slim, indent=2), encoding="utf-8")
    return data


def main(port: int = 8850, ledger: Path | None = None) -> int:
    d = dump(ledger)
    print(f"  docket: {d['counts']['cases']} cases, {d['counts']['binding']} binding")
    print(f"  board:  http://127.0.0.1:{port}/board.html")
    handler = partial(SimpleHTTPRequestHandler, directory=str(WEB))
    try:
        HTTPServer(("127.0.0.1", port), handler).serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
