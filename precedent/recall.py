"""Retrieval. Cosine over a few hundred rows, in the standard library.

sentence-transformers is a drop-in upgrade and deliberately not a requirement:
at this n a bag-of-words cosine returns the same neighbours and costs nothing.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .db import Ledger

_WORD = re.compile(r"[a-z0-9_]+")


def _vec(text: str) -> Counter:
    return Counter(_WORD.findall((text or "").lower()))


def _cos(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


def similar(led: Ledger, repo: str, task: str, k: int = 5,
            statuses: tuple[str, ...] = ("binding", "persuasive")) -> list[dict]:
    q = _vec(task)
    scored = []
    for h in led.holdings(repo=repo):
        if h["status"] not in statuses:
            continue
        case = led.case(h["case_id"]) or {}
        score = _cos(q, _vec(f"{h['says']} {case.get('summary','')} {' '.join(case.get('touched', []))}"))
        scored.append((score, h))
    scored.sort(key=lambda x: -x[0])
    return [dict(h, score=round(s, 3)) for s, h in scored[:k] if s > 0]


def everything(led: Ledger, repo: str, task: str, cap: int = 40) -> list[dict]:
    """Every rule in force, most relevant first - but none dropped.

    similar() filters on score > 0, which silently returns NOTHING when the task
    wording shares no token with the rule. For a prose arm that is the whole
    treatment disappearing, and the comparison against the gate becomes void.
    """
    q = _vec(task)
    rows = [h for h in led.holdings(repo=repo)
            if h["status"] in ("binding", "persuasive")]
    for h in rows:
        case = led.case(h["case_id"]) or {}
        h["score"] = round(_cos(q, _vec(
            f"{h['says']} {case.get('summary','')} {' '.join(case.get('touched', []))}")), 3)
    rows.sort(key=lambda h: -h["score"])
    return rows[:cap]


def briefing(led: Ledger, repo: str, task: str, k: int = 5) -> str:
    """Persuasive authority, as text, for arm B. Binding holdings do not need words."""
    rows = similar(led, repo, task, k=k, statuses=("persuasive",))
    if not rows:
        return ""
    lines = ["Past failures on tasks like this one:"]
    lines += [f"- {r['says']}" for r in rows]
    return "\n".join(lines)
