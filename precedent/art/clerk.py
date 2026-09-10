"""The clerk, drawn as data.

No asset is traced or downloaded: every pixel is placed here, so the sprite
sheet is versionable, diffable, and regenerates at any scale. Run

    python -m precedent.art.clerk

to write web/sprites/clerk.png, clerk@4x.png and clerk.json.

The character is a records clerk with a cathode-ray tube where a face would be.
It never emotes. The screen displays the record - a rule count, a precedent
number, a verdict - which is the only reason a mascot is allowed here at all.
Every frame below corresponds to a state the system actually produces.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

W, H = 48, 74
OUT = Path(__file__).resolve().parents[2] / "web" / "sprites"

# ---- palette -------------------------------------------------------------
# Named so a frame reads as intent rather than hex. Values come from
# docs/DESIGN.md; nothing here invents a colour.
P = {
    "_": (0, 0, 0, 0),                # transparent
    "K": (0x17, 0x12, 0x19, 255),     # ink outline
    "k": (0x2E, 0x24, 0x30, 255),     # soft outline
    "C": (0xA9, 0xB0, 0xA4, 255),     # CRT putty
    "c": (0x8A, 0x92, 0x88, 255),     # CRT shadow side
    "H": (0xC6, 0xCB, 0xC2, 255),     # CRT highlight
    "S": (0x0C, 0x14, 0x10, 255),     # screen glass
    "s": (0x14, 0x1E, 0x18, 255),     # screen scanline
    "G": (0x6F, 0xCF, 0x97, 255),     # phosphor green
    "A": (0xC8, 0xA2, 0x4A, 255),     # amber
    "R": (0xB4, 0x40, 0x2C, 255),     # stamp red
    "W": (0xF2, 0xEA, 0xD8, 255),     # shirt paper
    "w": (0xD8, 0xCD, 0xB6, 255),     # shirt shadow
    "T": (0x6B, 0x4A, 0x32, 255),     # trousers
    "t": (0x54, 0x3A, 0x27, 255),     # trouser shadow
    "B": (0x3A, 0x2C, 0x25, 255),     # shoes / belt
    "D": (0x5E, 0x53, 0x48, 255),     # dormant wash
    "O": (0x7C, 0x8A, 0x72, 255),     # filing-cabinet olive
    "N": (0x17, 0x12, 0x19, 255),     # the room behind, for knee holes

    # Book spines. The office is otherwise brown on brown, and a shelf of
    # ledgers is where colour belongs in a records room - not on the walls.
    "b1": (0x8C, 0x3B, 0x2E, 255),    # oxblood
    "b2": (0x4A, 0x6B, 0x7C, 255),    # slate blue
    "b3": (0x7C, 0x8A, 0x72, 255),    # olive
    "b4": (0xC8, 0xA2, 0x4A, 255),    # tan
    "b5": (0x5E, 0x4A, 0x6B, 255),    # aubergine
    "b6": (0x3F, 0x6B, 0x5A, 255),    # deep green

    # Daylight through the window: the room's second light source, cool
    # against the lamp's warm, which is what gives a flat scene depth.
    "d1": (0x39, 0x4A, 0x5C, 255),    # sky
    "d2": (0x51, 0x66, 0x7A, 255),    # sky, lit
    "d3": (0x6E, 0x85, 0x99, 255),    # glare
}


class Canvas:
    def __init__(self, w: int = W, h: int = H):
        self.w, self.h = w, h
        self.px = [["_"] * w for _ in range(h)]
        # Everything is drawn through this offset. The antenna reaches above the
        # casing at y=-1 and was being clipped by the top edge; shifting the
        # origin is cheaper and safer than renumbering every coordinate.
        self.oy = 0

    def set(self, x, y, c):
        y += self.oy
        if 0 <= x < self.w and 0 <= y < self.h and c != "_":
            self.px[y][x] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, c)

    def frame(self, x0, y0, x1, y1, c):
        for x in range(x0, x1 + 1):
            self.set(x, y0, c)
            self.set(x, y1, c)
        for y in range(y0, y1 + 1):
            self.set(x0, y, c)
            self.set(x1, y, c)

    def hline(self, x0, x1, y, c):
        for x in range(x0, x1 + 1):
            self.set(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(y0, y1 + 1):
            self.set(x, y, c)

    def clear_px(self, x, y):
        y += self.oy
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = "_"

    def chamfer(self, x0, y0, x1, y1):
        """Knock the corners off so the casing reads as moulded plastic."""
        for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            self.clear_px(x, y)

    def shift_above(self, y_floor: int, dy: int):
        """Move everything above the floor line, with what is below held still.

        The floor limits where we WRITE, not where we read. An earlier version
        refused to read past it, so lifting the head pulled in blank rows and
        opened a gap between the neck and the collar instead of sliding the
        torso up behind it.
        """
        if dy == 0:
            return
        rows = [r[:] for r in self.px]
        blank = ["_"] * self.w
        for y in range(0, y_floor):
            src = y - dy
            self.px[y] = rows[src][:] if 0 <= src < self.h else blank[:]

    def image(self) -> Image.Image:
        im = Image.new("RGBA", (self.w, self.h))
        im.putdata([P[self.px[y][x]] for y in range(self.h) for x in range(self.w)])
        return im


# ---- a 3x5 face for the screen ------------------------------------------
FONT = {
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"), "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "111"),
    "N": ("101", "111", "111", "101", "101"), "O": ("111", "101", "101", "101", "111"),
    "K": ("101", "110", "100", "110", "101"), "o": ("000", "110", "101", "101", "110"),
    "-": ("000", "000", "111", "000", "000"), ".": ("000", "000", "000", "000", "100"),
    " ": ("000", "000", "000", "000", "000"), "?": ("111", "001", "011", "000", "010"),
    "X": ("101", "101", "010", "101", "101"), "z": ("000", "111", "010", "100", "111"),
    "*": ("101", "010", "111", "010", "101"), "L": ("100", "100", "100", "100", "111"),
    "E": ("111", "100", "111", "100", "111"), "D": ("110", "101", "101", "101", "110"),
    "F": ("111", "100", "111", "100", "100"), "I": ("111", "010", "010", "010", "111"),
}


def text(cv: Canvas, s: str, x: int, y: int, c: str):
    for ch in s:
        for dy, row in enumerate(FONT.get(ch, FONT[" "])):
            for dx, bit in enumerate(row):
                if bit == "1":
                    cv.set(x + dx, y + dy, c)
        x += 4


def centred(cv: Canvas, s: str, y: int, c: str):
    width = len(s) * 4 - 1
    text(cv, s, 11 + (22 - width) // 2, y, c)


# ---- the body ------------------------------------------------------------

def draw_body(cv: Canvas, dim: bool = False):
    """Everything that never moves: casing, neck, shoulders, torso, legs.

    Proportion matters more than detail here. An earlier pass gave the head 44%
    of the height and it read as a bobblehead with a floating skull; the tube is
    now a third, and the neck carries visible shoulders so head and body are one
    object rather than two.
    """
    shirt = "D" if dim else "W"
    shade = "D" if dim else "w"
    plastic = "D" if dim else "C"
    dark = "D" if dim else "c"

    # ---- CRT casing, lit from the upper left -------------------------------
    cv.rect(8, 2, 40, 25, plastic)
    cv.frame(8, 2, 40, 25, "K")
    cv.chamfer(8, 2, 40, 25)
    if not dim:
        cv.hline(10, 38, 3, "H")
        cv.vline(9, 4, 23, "H")
        cv.hline(10, 38, 24, dark)
        cv.vline(39, 4, 23, dark)
        for y in (9, 12, 15, 18):
            cv.hline(35, 38, y, dark)

    # antenna: a bent whip with a bead on the end. It is the one flourish on an
    # otherwise severe machine, and it gives the idle animation something to do.
    cv.vline(23, -1, 1, "k")
    cv.vline(23, 0, 1, "K")
    cv.set(24, 0, "K")

    cv.rect(34, 21, 37, 24, dark)          # the dial
    cv.frame(34, 21, 37, 24, "K")
    if not dim:
        cv.set(35, 22, "H")

    cv.set(12, 23, "k")                    # power lamp housing
    cv.rect(12, 6, 31, 21, "S")            # screen, inset
    cv.frame(11, 5, 32, 22, "K")
    for y in range(7, 21, 2):
        cv.hline(13, 30, y, "s")

    # ---- neck: short, thick, and clearly joining two solids ----------------
    cv.rect(20, 26, 28, 31, plastic)
    cv.frame(20, 26, 28, 31, "K")
    if not dim:
        cv.vline(21, 27, 30, "H")
        cv.vline(27, 27, 30, dark)

    # ---- shoulders and torso ----------------------------------------------
    cv.rect(14, 31, 34, 33, shirt)         # shoulders, narrower than the waist
    cv.frame(14, 31, 34, 33, "K")
    cv.chamfer(14, 31, 34, 33)
    cv.rect(13, 33, 35, 47, shirt)         # chest
    cv.frame(13, 33, 35, 47, "K")
    cv.hline(15, 33, 33, shirt)            # dissolve the seam
    cv.rect(32, 34, 34, 46, shade)         # shadow down the right side

    cv.hline(19, 22, 32, shade)            # collar
    cv.hline(26, 29, 32, shade)
    cv.set(20, 32, "K")
    cv.set(28, 32, "K")

    if not dim:                            # tie
        cv.rect(23, 32, 25, 34, "R")
        cv.rect(22, 35, 26, 43, "R")
        cv.set(22, 35, "K")
        cv.set(26, 35, "K")
        cv.hline(23, 25, 44, "K")
    for y in (38, 42):                     # buttons
        cv.set(17, y, "k")

    if not dim:                            # breast pocket with two pens
        cv.rect(28, 36, 32, 41, shade)
        cv.frame(28, 36, 32, 41, "k")
        cv.vline(29, 34, 37, "A")
        cv.vline(31, 34, 37, "R")

    if not dim:
        cv.hline(14, 34, 46, shade)        # shirt hem
    cv.rect(13, 47, 35, 50, "B")           # belt
    cv.frame(13, 47, 35, 50, "K")
    if not dim:
        cv.rect(23, 48, 25, 50, "A")

    # ---- legs, with a gap between them -------------------------------------
    cv.rect(15, 50, 22, 67, "T")
    cv.frame(15, 50, 22, 67, "K")
    cv.rect(26, 50, 33, 67, "T")
    cv.frame(26, 50, 33, 67, "K")
    if not dim:
        cv.vline(18, 52, 66, "t")
        cv.vline(29, 52, 66, "t")

    # ---- shoes: wider than the leg, so they read as feet -------------------
    cv.rect(12, 67, 23, 71, "B")
    cv.frame(12, 67, 23, 71, "K")
    cv.rect(25, 67, 36, 71, "B")
    cv.frame(25, 67, 36, 71, "K")
    if not dim:
        cv.hline(13, 22, 68, "k")
        cv.hline(26, 35, 68, "k")


def draw_arm_left(cv: Canvas, dim: bool = False):
    """The idle arm.

    It takes the SHADOW tone, not the shirt tone. Drawn in the same cream as the
    chest the arms vanished into the torso and the whole upper body read as one
    block - a hairline outline is not enough separation at this size.
    """
    sleeve = "D" if dim else "w"
    hand = "D" if dim else "C"
    cv.rect(8, 33, 13, 45, sleeve)
    cv.frame(8, 33, 13, 45, "K")
    cv.hline(9, 12, 33, sleeve)          # erase the seam at the shoulder
    cv.hline(9, 12, 44, "K")             # cuff line
    draw_hand(cv, 8, 46, hand, thumb_right=True)


# Each pose: the upper arm box, the hand box, and where a held stamp sits.
# Arms hang OUTSIDE the torso so the hands fall beside the hips. Tucked in, the
# hands landed on the belt and read as pockets.
ARM_POSES = {
    #          sleeve box              hand x,y
    "down":   ((35, 33, 40, 45), (35, 46)),
    "mid":    ((35, 31, 40, 42), (37, 43)),
    "up":     ((35, 28, 40, 38), (36, 24)),
    "strike": ((35, 33, 40, 44), (37, 47)),
}


def stamp_pos(pose: str) -> tuple[int, int]:
    """Where the stamp sits so the hand closes around its shaft."""
    (_, _, _, _), (hx, hy) = ARM_POSES[pose]
    return hx - 2, hy - 2


def draw_hand(cv: Canvas, x: int, y: int, colour: str, thumb_right: bool = False):
    """Five pixels of hand, with a thumb, so it is not a grey square."""
    cv.rect(x, y, x + 4, y + 4, colour)
    cv.frame(x, y, x + 4, y + 4, "K")
    tx = x + 5 if thumb_right else x - 1
    cv.set(tx, y + 1, colour)
    cv.set(tx, y + 2, "K")


def draw_arm_right(cv: Canvas, pose: str, dim: bool = False):
    sleeve = "D" if dim else "w"
    hand = "D" if dim else "C"
    (ax0, ay0, ax1, ay1), (hx, hy) = ARM_POSES[pose]
    cv.rect(ax0, ay0, ax1, ay1, sleeve)
    cv.frame(ax0, ay0, ax1, ay1, "K")
    cv.hline(max(ax0 + 1, 15), min(ax1 - 1, 34), ay0, sleeve)  # seam into the shoulder
    cv.hline(ax0 + 1, ax1 - 1, ay1 - 1, "K")                   # cuff line
    draw_hand(cv, hx, hy, hand)


def draw_stamp(cv: Canvas, x: int, y: int):
    """A rubber stamp: red pad, wooden handle, gripped rather than floating.

    Deliberately chunky. It is the only object in the frame that carries weight,
    and at this size a delicate one reads as a smudge.
    """
    cv.rect(x + 1, y, x + 8, y + 3, "B")        # handle knob
    cv.frame(x + 1, y, x + 8, y + 3, "K")
    cv.hline(x + 2, x + 7, y + 1, "t")          # grain
    cv.rect(x + 3, y + 4, x + 6, y + 6, "B")    # shaft
    cv.frame(x + 3, y + 4, x + 6, y + 6, "K")
    cv.rect(x, y + 7, x + 9, y + 11, "R")       # pad
    cv.frame(x, y + 7, x + 9, y + 11, "K")
    cv.hline(x + 1, x + 8, y + 8, "W")          # ink face catches the light


def draw_lamp(cv: Canvas, on: bool):
    """The power lamp under the glass. Off in dormant, alive otherwise."""
    cv.set(12, 23, "G" if on else "k")


def draw_antenna_bead(cv: Canvas, lit: bool):
    cv.set(23, -1, "A" if lit else "k")
    cv.set(24, -1, "_")


def draw_card(cv: Canvas, x: int, y: int, mark: str | None = None):
    """An index card. Held while filing, crossed through when withdrawn."""
    cv.rect(x, y, x + 11, y + 8, "W")
    cv.frame(x, y, x + 11, y + 8, "K")
    cv.hline(x + 2, x + 9, y + 2, "w")
    cv.hline(x + 2, x + 7, y + 4, "w")
    cv.hline(x + 2, x + 9, y + 6, "w")
    if mark == "cross":
        for i in range(8):
            cv.set(x + 2 + i, y + 1 + i, "R")
            cv.set(x + 9 - i, y + 1 + i, "R")
    elif mark == "tick":
        for i in range(3):
            cv.set(x + 3 + i, y + 4 + i, "G")
        for i in range(4):
            cv.set(x + 6 + i, y + 6 - i, "G")


def draw_impact(cv: Canvas, x: int, y: int):
    """Three short marks. The only moment anything here has weight."""
    for dx in (-3, 0, 3):
        cv.vline(x + dx, y, y + 1, "A")


# ---- frames --------------------------------------------------------------
# Each entry: (state, screen text, screen colour, arm pose, extras)
# state, screen text, colour, arm pose, extras
#   bob   - pixels the body lifts, feet planted
#   lamp  - the power lamp under the glass
#   bead  - the antenna tip
#   card  - (x, y, mark) an index card in hand
FRAMES = [
    # dormant: the tube is cold. Nothing is watching.
    ("dormant",  ".",     "s", "down", {"lamp": False}),
    ("dormant",  "z",     "k", "down", {"lamp": False}),

    # watching: connected, tree unchanged. A slow breath and a blinking bead.
    ("watching", "-",     "G", "down", {"lamp": True, "bead": True}),
    ("watching", "-",     "G", "down", {"lamp": True, "bob": 1}),
    ("watching", "- -",   "G", "down", {"lamp": True, "scan": True}),
    ("watching", "-",     "G", "down", {"lamp": True, "bob": 1, "bead": True}),

    # reading: a change arrived and the rules are sitting.
    ("reading",  ".",     "A", "mid",  {"lamp": True}),
    ("reading",  "..",    "A", "mid",  {"lamp": True, "scan": True}),
    ("reading",  "19",    "A", "mid",  {"lamp": True, "bead": True}),
    ("reading",  "19",    "A", "mid",  {"lamp": True, "scan": True}),

    # halt: raise, arc, land, hold. It does not loop.
    ("halt",     "No 14", "R", "up",     {"lamp": True, "stamp": True}),
    ("halt",     "No 14", "R", "mid",    {"lamp": True, "stamp": True}),
    ("halt",     "No 14", "R", "strike", {"lamp": True, "stamp": True, "impact": True,
                                          "bob": -1}),
    ("halt",     "No 14", "R", "strike", {"lamp": True, "stamp": True}),

    # cleared: a small hop, then the card is ticked.
    ("cleared",  "OK",    "G", "down", {"lamp": True}),
    ("cleared",  "OK",    "G", "down", {"lamp": True, "bob": 2, "bead": True}),
    ("cleared",  "OK",    "G", "down", {"lamp": True, "bob": 1}),
    ("cleared",  "OK",    "G", "mid",  {"lamp": True, "card": (33, 44, "tick")}),

    # filing: the citation is recorded. The card goes down into the drawer.
    ("filing",   "FILED", "G", "mid",  {"lamp": True, "card": (33, 42, "tick")}),
    ("filing",   "FILED", "G", "down", {"lamp": True, "card": (32, 50, "tick")}),
    ("filing",   "FILED", "G", "down", {"lamp": True, "card": (32, 58, None)}),

    # skip: a rule could not be evaluated. It shrugs rather than pretending.
    ("skip",     "?",     "A", "mid",  {"lamp": True, "bob": 1}),
    ("skip",     "?",     "A", "up",   {"lamp": True}),

    # overruled: a precedent lost its authority. The card is struck through.
    ("overruled", "X",    "R", "mid",  {"lamp": True, "card": (33, 42, None)}),
    ("overruled", "X",    "R", "mid",  {"lamp": True, "card": (33, 42, "cross")}),
    ("overruled", "X",    "R", "down", {"lamp": True, "card": (32, 56, "cross")}),
]


def build_frame(spec) -> Canvas:
    state, label, colour, pose, extra = spec
    cv = Canvas()
    cv.oy = 2
    draw_body(cv)
    draw_arm_left(cv)
    # The stamp goes down BEFORE the hand, so the fingers close over the shaft
    # instead of the tool floating beside an open palm.
    if extra.get("stamp"):
        draw_stamp(cv, *stamp_pos(pose))
    draw_arm_right(cv, pose)

    if extra.get("scan"):
        cv.hline(13, 30, 12, "s")
    centred(cv, label, 11, colour)
    draw_lamp(cv, extra.get("lamp", True))
    draw_antenna_bead(cv, extra.get("bead", False))

    if extra.get("impact"):
        sx, sy = stamp_pos(pose)
        draw_impact(cv, sx + 4, sy + 10)

    bob = extra.get("bob", 0)
    if bob:
        # Only the head and neck move. Lifting the whole body opened a seam at
        # the waist where the torso left the legs behind; a head that rises on
        # its neck reads as a breath and cannot gap, because the torso top sits
        # directly under the neck either way.
        cv.shift_above(32 + cv.oy, -bob)

    if "card" in extra:                   # props ride above the bob
        draw_card(cv, *extra["card"])
    return cv


def sheet() -> tuple[Image.Image, dict]:
    frames = [build_frame(f) for f in FRAMES]
    im = Image.new("RGBA", (W * len(frames), H))
    order: dict[str, list[int]] = {}
    for i, (cv, spec) in enumerate(zip(frames, FRAMES)):
        im.paste(cv.image(), (i * W, 0))
        order.setdefault(spec[0], []).append(i)
    meta = {
        "frame": {"w": W, "h": H},
        "count": len(frames),
        "states": order,
        # milliseconds per frame, per state. Stepped, never eased.
        "timing": {"dormant": 1400, "watching": 620, "reading": 260,
                   "halt": 110, "cleared": 160, "filing": 200,
                   "skip": 400, "overruled": 320},
        "loop": {"dormant": True, "watching": True, "reading": True,
                 "halt": False, "cleared": False, "filing": False,
                 "skip": True, "overruled": False},
    }
    return im, meta


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    im, meta = sheet()
    im.save(OUT / "clerk.png")
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(OUT / "clerk@4x.png")
    (OUT / "clerk.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  {meta['count']} frames -> {OUT / 'clerk.png'} ({im.width}x{im.height})")
    for state, idx in meta["states"].items():
        print(f"    {state:<9} {len(idx)} frame(s)  {idx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
