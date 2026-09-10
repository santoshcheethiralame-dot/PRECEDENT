"""Seeds are fixtures. If a run ever writes into one, every measurement taken
afterwards is wrong and nothing else in this suite means anything - so this is
checked first and loudly."""
import subprocess
from pathlib import Path

import pytest

from precedent.workspace import restore

SEEDS = Path(__file__).resolve().parents[1] / "seeds"


def test_no_seed_has_uncommitted_changes():
    r = subprocess.run(["git", "status", "--porcelain", "--", str(SEEDS)],
                       capture_output=True, text=True, cwd=SEEDS.parent)
    dirty = [l for l in r.stdout.splitlines() if l.strip()]
    assert not dirty, "a seed fixture has been modified:\n  " + "\n  ".join(dirty)


def test_the_clinic_seed_still_has_the_trap_in_it():
    """Without this exact shape, 'a field with no migration' cannot fail."""
    fields = (SEEDS / "clinic" / "models" / "patient.py").read_text(encoding="utf-8")
    assert '["id", "name", "phone"]' in fields
    migrations = sorted(p.name for p in (SEEDS / "clinic" / "migrations").glob("*.sql"))
    assert migrations == ["001_init.sql"], migrations


def test_restore_refuses_to_write_onto_a_seed():
    with pytest.raises(ValueError, match="refusing to restore onto the seed"):
        restore(SEEDS / "clinic", SEEDS / "clinic")


def test_restore_refuses_to_write_inside_a_seed():
    with pytest.raises(ValueError, match="refusing to restore onto the seed"):
        restore(SEEDS / "clinic", SEEDS / "clinic" / "sub" / "dir")
