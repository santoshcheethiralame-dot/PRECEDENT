"""Enforcement. A binding holding either fires on this working tree or it does not."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .change import Change
from .db import Ledger
from . import templates


@dataclass
class Verdict:
    holding_id: int
    case_id: int
    says: str
    rule: str
    reason: str
    template: str
    cited: int
    empanel: dict
    established: float


def evaluate(led: Ledger, repo: str, ch: Change) -> list[Verdict]:
    """Every binding holding that fires. Empty list means the tree is clear."""
    out: list[Verdict] = []
    for h in led.holdings(repo=repo, status="binding"):
        reason = templates.fires(h["template"], h["params"], ch)
        if reason:
            out.append(Verdict(
                holding_id=h["id"], case_id=h["case_id"], says=h["says"],
                rule=templates.render(h["template"], h["params"]), reason=reason,
                template=h["template"], cited=len(led.citations(h["id"])),
                empanel=h["empanel"], established=h["established"],
            ))
    return out


def advisories(led: Ledger, repo: str) -> list[dict]:
    """Persuasive authority: prose, clearly labelled as the weaker tier."""
    return led.holdings(repo=repo, status="persuasive")


def check(repo: Path, led: Ledger | None = None) -> tuple[list[Verdict], Change]:
    from .db import ledger_path
    repo = Path(repo).resolve()
    led = led or Ledger(ledger_path(repo))
    ch = Change.from_git(repo)
    return evaluate(led, str(repo), ch), ch
