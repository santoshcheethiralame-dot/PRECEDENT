"""Arm B is the whole point of the project, and it has silently been a no-op.

If the prose arm receives an empty prompt, it is not a weaker treatment - it is
NO treatment, and any comparison against the gate is void while flattering it.
These tests exist so that can never happen again without a red suite.
"""
import subprocess

import pytest

from precedent import recall, serve, verbs
from precedent.db import Ledger, ledger_path


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "proj"
    (r / "models").mkdir(parents=True)
    (r / "migrations").mkdir()
    (r / "models" / "patient.py").write_text('FIELDS = ["id"]\n', encoding="utf-8")
    (r / "migrations" / "001_init.sql").write_text("-- init\n", encoding="utf-8")
    for c in (["git", "init", "-q"], ["git", "add", "-A"],
              ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "s"]):
        subprocess.run(c, cwd=r, capture_output=True)
    verbs.rule(r, "models/*.py needs migrations/")
    serve._ledgers.clear()
    return r


def test_arm_b_says_something_even_when_no_word_matches(repo):
    """The killer case: the task and the rule share no token, so a similarity
    filter returns nothing and the treatment vanishes."""
    out = serve.advise(str(repo), "add an email field to the patient record",
                       everything=True)
    assert out["text"], "arm B received an empty prompt - it is not a treatment"
    assert "migrations" in out["text"]


def test_arm_b_is_told_about_every_rule_the_gate_would_apply(repo):
    """The gate evaluates all rules regardless of wording. If the prose arm is
    filtered by relevance, the comparison is full knowledge against partial."""
    verbs.rule(repo, "never touch vendor/")
    led = Ledger(ledger_path(repo))
    in_force = [h for h in led.holdings(repo=str(repo.resolve()))
                if h["status"] in ("binding", "persuasive")]
    led.close()
    text = serve.advise(str(repo), "something entirely unrelated", everything=True)["text"]
    for h in in_force:
        assert h["says"] in text, f"arm B was never told about: {h['says']}"


def test_arm_b_prose_is_marked_as_optional(repo):
    """It has to read as advice. If it reads as a command the arm is measuring
    something other than what Autopsy actually does."""
    text = serve.advise(str(repo), "add a field", everything=True)["text"]
    assert "not enforced" in text.lower()


def test_the_three_arms_are_actually_different(repo):
    off = serve.advise(str(repo), "add a field", everything=False)["text"]
    advise = serve.advise(str(repo), "add a field", everything=True)["text"]
    assert off == "", "arm A must receive nothing"
    assert advise, "arm B must receive the rules"
    assert off != advise


def test_everything_returns_rules_even_at_zero_similarity(repo):
    led = Ledger(ledger_path(repo))
    rows = recall.everything(led, str(repo.resolve()), "zzzz qqqq no shared words")
    assert rows, "a zero score must not drop a rule"
    assert all("score" in r for r in rows)
    led.close()


def test_similar_still_filters_for_retrieval(repo):
    """everything() is for arm B. similar() keeps its threshold, because a
    halt card citing an irrelevant precedent is worse than none."""
    led = Ledger(ledger_path(repo))
    assert recall.similar(led, str(repo.resolve()), "zzzz qqqq") == []
    led.close()
