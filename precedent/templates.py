"""The eight things a holding is allowed to be.

The LLM never writes a checker. It picks one of these and fills the blanks, so
every verdict in the system is a deterministic function of the working tree.
"""
from __future__ import annotations

import fnmatch
import re
from typing import Callable

from .change import Change


def _braces(pattern: str) -> list[str]:
    """fnmatch has no brace expansion, so `*.{js,ts}` matches literally nothing."""
    i = pattern.find("{")
    if i == -1:
        return [pattern]
    j = pattern.find("}", i)
    if j == -1:
        return [pattern]
    head, body, tail = pattern[:i], pattern[i + 1:j], pattern[j + 1:]
    return [v for opt in body.split(",") for v in _braces(head + opt.strip() + tail)]


def _variants(pattern: str) -> list[str]:
    """`**/*.py` has to match `app.py` as well as `src/app.py`.

    fnmatch reads `**/` as requiring a slash, so a pattern written the way every
    tool writes it silently skips every file at the repository root - which is
    where app.py, main.py and index.ts usually live.
    """
    out = []
    for pat in _braces(pattern):
        out += [pat, f"{pat.rstrip('/')}/**"]
        if pat.startswith("**/"):
            out.append(pat[3:])
    return out


def _hits(paths: list[str], pattern: str) -> list[str]:
    pats = _variants(pattern)
    return [p for p in paths if any(fnmatch.fnmatch(p, q) for q in pats)]


# Each check returns None when it is satisfied, or a one-line reason when it fires.

def co_change(ch: Change, p: dict) -> str | None:
    trig, req = p["trigger"], p["required"]
    if _hits(ch.touched, trig) and not _hits(ch.touched, req):
        return f"{', '.join(_hits(ch.touched, trig))} changed, nothing under {req} did"
    return None


def required_command(ch: Change, p: dict) -> str | None:
    if _hits(ch.touched, p["glob"]) and ch.run(p["cmd"]) != 0:
        return f"`{p['cmd']}` fails after touching {p['glob']}"
    return None


def forbidden_edit(ch: Change, p: dict) -> str | None:
    hit = _hits(ch.touched, p["glob"])
    return f"{', '.join(hit)} may not be edited" if hit else None


def must_not_appear(ch: Change, p: dict) -> str | None:
    rx = re.compile(p["regex"])
    for path in _hits(ch.touched, p["glob"]):
        for line in ch.added.get(path, []):
            if rx.search(line):
                return f"{path} adds a line matching /{p['regex']}/"
    return None


def must_not_remove(ch: Change, p: dict) -> str | None:
    """Deleting the thing that was failing is the oldest trick there is."""
    rx = re.compile(p["regex"])
    for path in _hits(ch.touched, p["glob"]):
        for line in ch.removed.get(path, []):
            if rx.search(line):
                return f"{path} deletes a line matching /{p['regex']}/"
    return None


def must_appear(ch: Change, p: dict) -> str | None:
    rx = re.compile(p["regex"])
    for path in _hits(ch.touched, p["glob"]):
        if not rx.search(ch.text(path)):
            return f"{path} is missing /{p['regex']}/"
    return None


def must_run(ch: Change, p: dict) -> str | None:
    """Touching this means running that.

    A generated file is the case in point: editing it by hand and regenerating
    it touch exactly the same path, so no structural rule can tell them apart.
    The difference is whether the generator ran.

    Where commands are invisible - a bare `git` view of a tree - this abstains
    rather than guessing. A gate that fires on missing evidence is a gate that
    fires on everything.
    """
    if ch.commands is None:
        return None
    hit = _hits(ch.touched, p["glob"])
    if hit and not any(p["cmd"] in c for c in ch.commands):
        return f"{', '.join(hit)} was written by hand; `{p['cmd']}` never ran"
    return None


def regression_test(ch: Change, p: dict) -> str | None:
    if ch.run(f"python -m pytest -q {p['path']}") != 0:
        return f"the regression test {p['path']} fails"
    return None


TEMPLATES: dict[str, Callable[[Change, dict], str | None]] = {
    "co_change": co_change,
    "required_command": required_command,
    "forbidden_edit": forbidden_edit,
    "must_not_appear": must_not_appear,
    "must_not_remove": must_not_remove,
    "must_appear": must_appear,
    "regression_test": regression_test,
    "must_run": must_run,
}

REQUIRED_PARAMS = {
    "co_change": ("trigger", "required"),
    "required_command": ("glob", "cmd"),
    "forbidden_edit": ("glob",),
    "must_not_appear": ("regex", "glob"),
    "must_not_remove": ("regex", "glob"),
    "must_appear": ("regex", "glob"),
    "regression_test": ("path",),
    "must_run": ("glob", "cmd"),
}


def render(template: str, p: dict) -> str:
    """The rule as a machine reads it, for the halt card's mono line."""
    return {
        "co_change": lambda: f"co_change( {p.get('trigger')} -> {p.get('required')} )",
        "required_command": lambda: f"required_command( {p.get('glob')} : {p.get('cmd')} )",
        "forbidden_edit": lambda: f"forbidden_edit( {p.get('glob')} )",
        "must_not_appear": lambda: f"must_not_appear( /{p.get('regex')}/ in {p.get('glob')} )",
        "must_not_remove": lambda: f"must_not_remove( /{p.get('regex')}/ in {p.get('glob')} )",
        "must_appear": lambda: f"must_appear( /{p.get('regex')}/ in {p.get('glob')} )",
        "regression_test": lambda: f"regression_test( {p.get('path')} )",
        "must_run": lambda: f"must_run( {p.get('glob')} : {p.get('cmd')} )",
    }[template]()


def valid(template: str, p: dict) -> bool:
    return template in TEMPLATES and all(p.get(k) for k in REQUIRED_PARAMS[template])


def fires(template: str, p: dict, ch: Change) -> str | None:
    if not valid(template, p):
        return None
    return TEMPLATES[template](ch, p)
