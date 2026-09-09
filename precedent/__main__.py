from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .change import Change
from .db import Ledger, ledger_path
from .harvest import human_reject
from . import gate, overrule, record, render


def _led(path: Path) -> tuple[Ledger, str]:
    repo = Path(path).resolve()
    return Ledger(ledger_path(repo)), str(repo)


def cmd_gate(a) -> int:
    led, repo = _led(a.path)
    ch = Change.from_git(Path(repo))
    verdicts = gate.evaluate(led, repo, ch)
    if a.json:
        print(json.dumps([v.__dict__ for v in verdicts], indent=2))
    elif verdicts:
        for v in verdicts:
            print(render.halt_card(v))
    else:
        print(render.clear_line())
    return 1 if verdicts else 0


def cmd_reject(a) -> int:
    led, repo = _led(a.path)
    ch = Change.from_git(Path(repo))
    run_id = led.open_run(repo, a.reason, arm="live")
    led.close_run(run_id, "fail")
    out = record.file_case(led, run_id, repo, human_reject(a.reason), ch,
                           use_model=not a.no_model)
    print(f"case {out['case_id']} filed. holding {out['holding_id']} is {out['status'].upper()}.")
    print(f"  {out['says']}")
    if out.get("template"):
        from . import templates
        print(f"  {templates.render(out['template'], out['params'])}")
    print(f"  empanelment: {json.dumps(out['receipt'])}")
    return 0


def cmd_docket(a) -> int:
    led, repo = _led(a.path)
    counts = led.counts(repo)
    print(f"\n  DOCKET  {counts['cases']} cases   {counts['binding']} binding   "
          f"{counts['persuasive']} advisory   {counts['overruled']} overruled\n")
    for h in led.holdings(repo=repo):
        print(render.docket_line(h, led.case(h["case_id"]) or {}))
    print()
    return 0


def cmd_sweep(a) -> int:
    led, repo = _led(a.path)
    done = overrule.sweep(led, repo)
    print(f"overruled {len(done)} holding(s): {done}" if done else "no holding lost its authority.")
    return 0


def cmd_dump(a) -> int:
    led, repo = _led(a.path)
    data = {
        "repo": repo,
        "counts": led.counts(repo),
        "holdings": led.holdings(repo=repo),
        "cases": led.cases(repo=repo),
    }
    for h in data["holdings"]:
        h["citations"] = led.citations(h["id"])
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="precedent")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate", help="does any binding precedent fire on this tree?")
    g.add_argument("path", nargs="?", default=".")
    g.add_argument("--json", action="store_true")
    g.set_defaults(fn=cmd_gate)

    r = sub.add_parser("reject", help="file a rejection against the current working tree")
    r.add_argument("reason")
    r.add_argument("path", nargs="?", default=".")
    r.add_argument("--no-model", action="store_true")
    r.set_defaults(fn=cmd_reject)

    d = sub.add_parser("docket", help="list the cases and what they established")
    d.add_argument("path", nargs="?", default=".")
    d.set_defaults(fn=cmd_docket)

    s = sub.add_parser("sweep", help="re-decide every binding holding from its citations")
    s.add_argument("path", nargs="?", default=".")
    s.set_defaults(fn=cmd_sweep)

    u = sub.add_parser("dump", help="write the ledger as JSON for the web surface")
    u.add_argument("path", nargs="?", default=".")
    u.add_argument("--out", default="web/data.json")
    u.set_defaults(fn=cmd_dump)

    m = sub.add_parser("demo", help="the split screen: two apps, one clock")
    m.set_defaults(fn=lambda a: __import__("precedent.demo", fromlist=["main"]).main())

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
