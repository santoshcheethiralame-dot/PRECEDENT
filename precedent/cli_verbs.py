"""Terminal output for the everyday commands.

Kept apart from `verbs.py` so the logic stays testable without a terminal, and
apart from `__main__.py` so that file stays a router.
"""
from __future__ import annotations

from pathlib import Path

from . import templates, verbs


def _rule_text(h: dict) -> str:
    return (templates.render(h["template"], h["params"])
            if h["template"] in templates.TEMPLATES else h["template"])


def cmd_init(a) -> int:
    found = verbs.init(Path(a.path))
    if not found:
        print("  nothing to learn yet.")
        print("  no habit in this history is strong enough to be a rule, and")
        print("  inventing one would be worse than saying so.")
        return 0
    print()
    print(f"  {len(found)} rule(s) proposed, all advisory until you confirm them:")
    print()
    for r in found:
        e = r["evidence"]
        detail = (f"seen {e['support']}x, held {e['confidence']:.0%} of the time"
                  if "support" in e else f"declared in {e.get('declared_in')}")
        print(f"  {str(r['id']).rjust(3)}  {r['says']}")
        print(f"       {detail}")
    ids = " ".join(str(r["id"]) for r in found)
    print()
    print(f"  precedent confirm {ids}    to make them binding")
    print()
    return 0


def cmd_confirm(a) -> int:
    for d in verbs.confirm(Path(a.path), a.ids):
        note = "" if d["status"] == "binding" else "   (it would have blocked past work)"
        print(f"  {d['id']}  {d['status'].upper()}{note}")
    return 0


def cmd_rule(a) -> int:
    out = verbs.rule(Path(a.path), a.sentence)
    if not out:
        print("  that did not parse. the three forms are:")
        print()
        print(verbs.HELP)
        return 2
    print(f"  {out['says']}")
    print(f"  {templates.render(out['template'], out['params'])}")
    if out["status"] == "binding":
        print("  BINDING")
    else:
        print("  ADVISORY  - it would have blocked work that already succeeded")
    return 0


def cmd_why(a) -> int:
    rows = verbs.why(Path(a.path), a.file)
    if not rows:
        print(f"  nothing applies to {a.file}.")
        return 0
    print()
    print(f"  {len(rows)} rule(s) apply to {a.file}:")
    print()
    for h in rows:
        print(f"  {str(h['id']).rjust(3)}  {h['status'].upper():<11} {h['says']}")
        print(f"       {_rule_text(h)}")
        print(f"       from a {h['source']} case: {h['reason'][:64]}")
    print()
    return 0


def cmd_off(a) -> int:
    d = verbs.mute(Path(a.path), a.id, on=False)
    if not d:
        print(f"  no rule {a.id}.")
        return 1
    print(f"  {a.id} muted (was {d['was']}). the case stays on the docket.")
    return 0


def cmd_on(a) -> int:
    d = verbs.mute(Path(a.path), a.id, on=True)
    if not d:
        print(f"  no rule {a.id}.")
        return 1
    print(f"  {a.id} is {d['status']} again.")
    return 0


def cmd_status(a) -> int:
    s = verbs.status(Path(a.path), a.days)
    print()
    print(f"  last {s['days']} days")
    print(f"    {s['stopped']} mistake(s) stopped before they landed")
    print(f"    {s['overridden']} time(s) you went ahead anyway")
    print()
    print(f"  {s['binding']} binding   {s['advisory']} advisory   "
          f"{s['muted']} muted   {s['overruled']} overruled   ({s['cases']} cases)")
    print()
    return 0


def cmd_hook(a) -> int:
    t = verbs.hook(Path(a.path))
    if not t:
        print("  not a git repository.")
        return 1
    print(f"  installed {t}")
    print("  `git commit` now refuses anything a binding precedent fires on.")
    return 0


def register(sub) -> None:
    i = sub.add_parser("init", help="learn this repo's habits from its own history")
    i.add_argument("path", nargs="?", default=".")
    i.set_defaults(fn=cmd_init)

    cf = sub.add_parser("confirm", help="promote mined rules to binding")
    cf.add_argument("ids", nargs="+", type=int)
    cf.add_argument("--path", default=".")
    cf.set_defaults(fn=cmd_confirm)

    ru = sub.add_parser("rule", help="teach it a rule in one sentence")
    ru.add_argument("sentence")
    ru.add_argument("path", nargs="?", default=".")
    ru.set_defaults(fn=cmd_rule)

    wy = sub.add_parser("why", help="which rules apply to this file")
    wy.add_argument("file")
    wy.add_argument("path", nargs="?", default=".")
    wy.set_defaults(fn=cmd_why)

    of = sub.add_parser("off", help="mute a rule that is wrong")
    of.add_argument("id", type=int)
    of.add_argument("path", nargs="?", default=".")
    of.set_defaults(fn=cmd_off)

    on = sub.add_parser("on", help="unmute a rule")
    on.add_argument("id", type=int)
    on.add_argument("path", nargs="?", default=".")
    on.set_defaults(fn=cmd_on)

    st = sub.add_parser("status", help="what it caught this week")
    st.add_argument("path", nargs="?", default=".")
    st.add_argument("--days", type=int, default=7)
    st.set_defaults(fn=cmd_status)

    hk = sub.add_parser("hook", help="install the git pre-commit hook")
    hk.add_argument("path", nargs="?", default=".")
    hk.set_defaults(fn=cmd_hook)
