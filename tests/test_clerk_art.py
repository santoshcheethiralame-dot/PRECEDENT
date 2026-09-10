"""The clerk is generated, not drawn by hand, so it can be asserted about.

These exist because "it looks half built" is a real failure mode and a vague
one. Each test turns one part of that judgement into something checkable: the
character is one connected body, the screen actually displays the record, and
the sheet regenerates byte-identically.
"""
import pytest

from precedent.art import clerk


def frames():
    return [clerk.build_frame(spec) for spec in clerk.FRAMES]


def solid(cv, x0, y0, x1, y1):
    """How many pixels in a region are not transparent."""
    return sum(1 for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
               if cv.px[y][x] != "_")


def test_every_declared_state_has_frames():
    _, meta = clerk.sheet()
    assert set(meta["states"]) == {"dormant", "watching", "reading", "halt", "cleared"}
    for state, idx in meta["states"].items():
        assert idx, f"{state} has no frames"


def test_the_sheet_is_the_size_it_claims():
    im, meta = clerk.sheet()
    assert im.size == (clerk.W * meta["count"], clerk.H)
    assert meta["frame"] == {"w": clerk.W, "h": clerk.H}


def test_generation_is_deterministic():
    """A sprite sheet that changes between runs cannot be reviewed in a diff."""
    assert clerk.sheet()[0].tobytes() == clerk.sheet()[0].tobytes()


@pytest.mark.parametrize("i", range(len(clerk.FRAMES)))
def test_no_frame_is_half_drawn(i):
    """Head, torso and legs must all carry pixels. An earlier pass shipped a
    frame whose body was missing and it read as a floating head."""
    cv = frames()[i]
    assert solid(cv, 8, 2, 40, 25) > 400, "the head is missing"
    assert solid(cv, 13, 31, 35, 47) > 200, "the torso is missing"
    assert solid(cv, 15, 50, 33, 67) > 150, "the legs are missing"
    assert solid(cv, 12, 67, 36, 71) > 60, "the shoes are missing"


@pytest.mark.parametrize("i", range(len(clerk.FRAMES)))
def test_the_head_is_joined_to_the_body(i):
    """The neck column must be solid from the casing to the shoulders, or the
    head floats - which is exactly how the first version looked."""
    cv = frames()[i]
    for y in range(26, 31):
        assert cv.px[y][24] != "_", f"neck gap at row {y}"


@pytest.mark.parametrize("spec", clerk.FRAMES, ids=lambda s: f"{s[0]}-{s[1]}")
def test_the_screen_displays_the_record(spec):
    """The only justification for a mascot here is that its face is a readout.
    Assert the label's colour actually appears inside the glass."""
    cv = clerk.build_frame(spec)
    colour = spec[2]
    found = sum(1 for y in range(6, 22) for x in range(12, 32) if cv.px[y][x] == colour)
    assert found > 0, "nothing is on the screen"


def test_the_halt_frames_carry_a_stamp():
    halt = [clerk.build_frame(s) for s in clerk.FRAMES if s[0] == "halt"]
    for cv in halt:
        red = sum(1 for row in cv.px for p in row if p == "R")
        assert red > 40, "the stamp is missing from a halt frame"


def test_only_states_that_should_loop_do():
    _, meta = clerk.sheet()
    assert meta["loop"]["halt"] is False, "a halt must hold, not replay forever"
    assert meta["loop"]["dormant"] is False
    assert meta["loop"]["watching"] is True


def test_no_colour_outside_the_palette():
    """Every pixel must be a named token, so the art cannot drift from
    docs/DESIGN.md by someone typing a hex value."""
    for cv in frames():
        for row in cv.px:
            for p in row:
                assert p in clerk.P, f"unknown colour {p!r}"
