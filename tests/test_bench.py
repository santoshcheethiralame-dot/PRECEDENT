"""The benchmark makes a claim about itself: same seed, same behaviour, and the
only difference between arms is enforcement. That claim gets tested."""
import random

from precedent.bench import agent, run
from precedent.bench.tasks import all_tasks


def test_the_suite_is_what_it_says():
    tasks = all_tasks()
    assert len(tasks) == 30
    assert sum(1 for t in tasks if not t.trap) == 7, "controls measure false positives"
    assert {t.repo for t in tasks} == {"clinic", "typegen", "registry"}
    for t in tasks:
        assert t.primary, t.id
        for c in t.companions:
            assert c["actions"] and c["produces"], t.id


def test_the_agent_is_identical_across_arms_for_one_seed():
    task = [t for t in all_tasks() if t.trap == "schema_without_migration"][0]
    a, _ = agent.script(task, random.Random(11), 0.5)
    b, _ = agent.script(task, random.Random(11), 0.5)
    assert a == b, "arms must differ by enforcement, not by the agent"


def test_recall_is_the_only_knob():
    task = [t for t in all_tasks() if t.trap == "schema_without_migration"][0]
    never, skipped = agent.script(task, random.Random(3), 0.0)
    assert skipped == [0] and len(never) == 2
    always, skipped = agent.script(task, random.Random(3), 1.0)
    assert skipped == [] and len(always) == 3


def test_a_run_is_reproducible(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "WORK", tmp_path)
    subset = [t for t in all_tasks() if t.repo == "clinic"]
    first = run.run_arm("A", 7, 0.5, subset)
    second = run.run_arm("A", 7, 0.5, subset)
    assert [r["task"] for r in first] == [r["task"] for r in second]
    assert [r["passed"] for r in first] == [r["passed"] for r in second]


def test_arm_a_never_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "WORK", tmp_path)
    rows = run.run_arm("A", 2, 0.5, [t for t in all_tasks() if t.repo == "clinic"])
    assert sum(r["blocked"] for r in rows) == 0
    assert all(r["passed"] for r in rows if not r["trap"]), "controls must pass unaided"


def test_repeat_failure_only_counts_traps_already_seen():
    rows = [
        {"arm": "X", "seed": 1, "order": 0, "trap": "t", "passed": False, "blocked": 0},
        {"arm": "X", "seed": 1, "order": 1, "trap": "t", "passed": False, "blocked": 0},
        {"arm": "X", "seed": 1, "order": 2, "trap": "t", "passed": True, "blocked": 0},
        {"arm": "X", "seed": 1, "order": 3, "trap": "", "passed": True, "blocked": 1},
    ]
    m = run.metrics(rows)["X"]
    assert m["repeat_seen"] == 2, "the first failure of a class is not a repeat"
    assert m["repeat_failure_rate"] == 0.5
    assert m["false_positive_rate"] == 1.0, "a control that was blocked is a false positive"


def test_regressions_are_a_passed_c_failed():
    rows = [
        {"arm": "A", "seed": 1, "order": 0, "task": "x", "trap": "t", "passed": True, "blocked": 0},
        {"arm": "C", "seed": 1, "order": 0, "task": "x", "trap": "t", "passed": False, "blocked": 1},
        {"arm": "A", "seed": 1, "order": 1, "task": "y", "trap": "t", "passed": False, "blocked": 0},
        {"arm": "C", "seed": 1, "order": 1, "task": "y", "trap": "t", "passed": True, "blocked": 1},
    ]
    assert [r["task"] for r in run.regressions(rows)] == ["x"]
