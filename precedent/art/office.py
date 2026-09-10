"""The records office, drawn as data.

Same method as the clerk: every pixel placed here, in the same palette, at the
same scale. Shop-bought sprite packs were considered and rejected - they carry
their own palette and their own light source, and a room assembled from two
sources reads as assembled.

    python -m precedent.art.office

writes web/sprites/office.png, office@4x.png and office.json.

Each piece is furniture the interface actually needs: the desk the clerk works
at, the cabinet that holds the docket, the chart on the wall, the lamp over the
case file. Nothing here is scenery for its own sake.
"""
from __future__ import annotations

import json

from PIL import Image

from .clerk import Canvas, OUT

# name -> (w, h, draw fn). Sizes chosen against the clerk at 48x74 so the room
# is in proportion when both are shown at the same scale.
PIECES: dict[str, tuple] = {}


def piece(name: str, w: int, h: int):
    def wrap(fn):
        PIECES[name] = (w, h, fn)
        return fn
    return wrap


# ---- the desk ------------------------------------------------------------

@piece("desk", 148, 46)
def desk(cv: Canvas):
    """Front view. A working desk: top, apron, a bank of drawers, four legs."""
    # top, with a lighter front edge
    cv.rect(0, 0, 147, 5, "T")
    cv.frame(0, 0, 147, 5, "K")
    cv.hline(1, 146, 1, "t")
    cv.hline(1, 146, 4, "t")

    # apron
    cv.rect(4, 6, 143, 11, "t")
    cv.frame(4, 6, 143, 11, "K")

    # drawer bank, left
    cv.rect(6, 12, 54, 38, "T")
    cv.frame(6, 12, 54, 38, "K")
    for i, y in enumerate((14, 23, 32)):
        cv.rect(9, y, 51, y + 6, "t")
        cv.frame(9, y, 51, y + 6, "K")
        cv.rect(26, y + 2, 34, y + 4, "C")      # pull handle
        cv.frame(26, y + 2, 34, y + 4, "K")

    # knee hole
    cv.rect(56, 12, 100, 38, "K")
    cv.rect(58, 12, 98, 36, "N")           # knee hole: the room shows through

    # drawer bank, right
    cv.rect(102, 12, 141, 38, "T")
    cv.frame(102, 12, 141, 38, "K")
    for y in (14, 23, 32):
        cv.rect(105, y, 138, y + 6, "t")
        cv.frame(105, y, 138, y + 6, "K")
        cv.rect(117, y + 2, 125, y + 4, "C")
        cv.frame(117, y + 2, 125, y + 4, "K")

    # legs
    for x in (6, 48, 102, 137):
        cv.rect(x, 38, x + 5, 45, "t")
        cv.frame(x, 38, x + 5, 45, "K")


# ---- the filing cabinet --------------------------------------------------

@piece("cabinet", 60, 96)
def cabinet(cv: Canvas):
    """Four drawers: binding, advisory, overruled, all."""
    cv.rect(0, 0, 59, 95, "O")
    cv.frame(0, 0, 59, 95, "K")
    cv.hline(1, 58, 1, "C")                     # top highlight
    cv.vline(1, 2, 94, "C")
    cv.vline(58, 2, 94, "k")

    for i in range(4):
        y = 4 + i * 23
        cv.rect(4, y, 55, y + 19, "O")
        cv.frame(4, y, 55, y + 19, "K")
        cv.hline(5, 54, y + 1, "C")
        cv.hline(5, 54, y + 18, "k")
        # pull
        cv.rect(22, y + 8, 37, y + 12, "C")
        cv.frame(22, y + 8, 37, y + 12, "K")
        cv.hline(23, 36, y + 9, "H")
        # label holder
        cv.rect(8, y + 4, 18, y + 7, "W")
        cv.frame(8, y + 4, 18, y + 7, "K")


# ---- the wall chart ------------------------------------------------------

@piece("chart", 76, 56)
def chart(cv: Canvas):
    """A framed chart. The bars are drawn by the page, not baked in here."""
    cv.rect(0, 0, 75, 55, "T")
    cv.frame(0, 0, 75, 55, "K")
    cv.hline(1, 74, 1, "t")
    cv.rect(4, 4, 71, 51, "W")
    cv.frame(4, 4, 71, 51, "K")
    cv.hline(6, 69, 47, "k")                    # axis
    cv.vline(7, 8, 47, "k")
    for x in (14, 26, 38, 50, 62):              # tick marks
        cv.set(x, 48, "k")


# ---- the desk lamp -------------------------------------------------------

@piece("lamp", 26, 44)
def lamp(cv: Canvas):
    """Bankers' lamp: a shade that flares, a stem, a weighted base.

    The shade is a trapezoid, not a block. A rectangle reads as a brick and the
    whole piece stops looking like a lamp.
    """
    for i, y in enumerate(range(0, 9)):         # flared shade
        inset = 4 - i // 2
        cv.hline(4 + inset, 21 - inset, y, "R")
        cv.set(4 + inset - 1, y, "K")
        cv.set(21 - inset + 1, y, "K")
    cv.hline(6, 19, 1, "W")                     # highlight along the crown
    cv.hline(1, 24, 9, "K")                     # rim
    cv.hline(2, 23, 10, "A")                    # the light itself
    cv.hline(4, 21, 11, "A")
    cv.hline(7, 18, 12, "A")

    cv.rect(11, 12, 14, 35, "B")                # stem
    cv.frame(11, 12, 14, 35, "K")
    cv.vline(12, 13, 34, "t")
    cv.rect(5, 36, 20, 43, "B")                 # base
    cv.frame(5, 36, 20, 43, "K")
    cv.hline(6, 19, 37, "t")


# ---- paperwork -----------------------------------------------------------

@piece("papers", 34, 20)
def papers(cv: Canvas):
    """A short stack, slightly fanned. What arrives on the desk."""
    for i, (dx, dy) in enumerate(((0, 4), (2, 2), (4, 0))):
        cv.rect(dx, dy, dx + 27, dy + 14, "W")
        cv.frame(dx, dy, dx + 27, dy + 14, "K")
    for y in (4, 7, 10, 13):
        cv.hline(8, 27, y, "w")


@piece("intray", 40, 18)
def intray(cv: Canvas):
    """A wire in-tray. Empty until a change lands."""
    cv.rect(0, 6, 39, 17, "C")
    cv.frame(0, 6, 39, 17, "K")
    cv.hline(1, 38, 7, "H")
    cv.vline(0, 0, 6, "K")
    cv.vline(39, 0, 6, "K")
    cv.hline(0, 39, 0, "K")


# ---- a little life -------------------------------------------------------

@piece("plant", 26, 38)
def plant(cv: Canvas):
    """One plant. The office would be a morgue without it.

    Leaves are little clusters rather than single strokes - a one-pixel line
    reads as a wire, and a wire in a pot is not a plant.
    """
    cv.rect(6, 27, 19, 37, "R")                 # pot, tapered
    cv.frame(6, 27, 19, 37, "K")
    cv.hline(7, 18, 28, "W")
    cv.hline(8, 17, 36, "K")
    cv.rect(7, 24, 18, 27, "R")                 # rim
    cv.frame(7, 24, 18, 27, "K")
    cv.rect(8, 25, 17, 26, "t")                 # soil

    def leaf(x, y, h, tone):
        cv.vline(x, y, y + h, tone)
        for d in range(1, h, 3):
            cv.set(x - 1, y + d, tone)
            cv.set(x + 1, y + d + 1, tone)
        cv.set(x, y - 1, tone)

    leaf(12, 4, 20, "O")
    leaf(8, 9, 15, "O")
    leaf(16, 9, 15, "O")
    leaf(6, 15, 9, "C")
    leaf(18, 15, 9, "C")


@piece("mug", 16, 16)
def mug(cv: Canvas):
    cv.rect(1, 4, 11, 15, "W")
    cv.frame(1, 4, 11, 15, "K")
    cv.rect(2, 5, 10, 7, "B")                   # coffee
    cv.rect(12, 7, 14, 12, "W")                 # handle
    cv.frame(12, 7, 14, 12, "K")
    cv.set(13, 9, "K")
    cv.set(13, 10, "K")


# ---- sheet ---------------------------------------------------------------

def sheet() -> tuple[Image.Image, dict]:
    """One row, pieces laid left to right, each padded to the tallest."""
    built = []
    for name, (w, h, fn) in PIECES.items():
        cv = Canvas(w, h)
        fn(cv)
        built.append((name, cv))

    total_w = sum(cv.w for _, cv in built)
    max_h = max(cv.h for _, cv in built)
    im = Image.new("RGBA", (total_w, max_h))
    meta: dict = {"pieces": {}, "sheet": {"w": total_w, "h": max_h}}
    x = 0
    for name, cv in built:
        im.paste(cv.image(), (x, 0))
        meta["pieces"][name] = {"x": x, "y": 0, "w": cv.w, "h": cv.h}
        x += cv.w
    return im, meta


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    im, meta = sheet()
    im.save(OUT / "office.png")
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(OUT / "office@4x.png")
    (OUT / "office.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  {len(meta['pieces'])} pieces -> {OUT / 'office.png'} "
          f"({meta['sheet']['w']}x{meta['sheet']['h']})")
    for name, box in meta["pieces"].items():
        print(f"    {name:<9} {box['w']:>3}x{box['h']:<3} at x={box['x']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
