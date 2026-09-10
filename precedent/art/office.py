"""The records office, drawn as data.

Same method as the clerk: every pixel placed here, in the same palette, at the
same scale. Shop-bought sprite packs were considered and rejected - they carry
their own palette and their own light source, and a room assembled from two
sources reads as assembled.

    python -m precedent.art.office

writes web/sprites/office.png, office@4x.png and office.json.

Two rules hold this together. The light comes from the upper left, so every
solid is drawn with cv.box() and gets a lit edge and a shadowed one - a flat
fill is what makes pixel art look like a placeholder. And nothing here carries
text: labels belong to the page, which can change them, not to a sprite that
cannot.
"""
from __future__ import annotations

import json

from PIL import Image

from .clerk import Canvas, OUT

PIECES: dict[str, tuple] = {}


def piece(name: str, w: int, h: int):
    def wrap(fn):
        PIECES[name] = (w, h, fn)
        return fn
    return wrap


# ---- surfaces: the room itself -------------------------------------------

@piece("brick", 64, 32)
def brick(cv: Canvas):
    """A wall tile. Running bond, mortar lines, and no two bricks quite the
    same tone - a wall of identical rectangles reads as graph paper."""
    cv.rect(0, 0, 63, 31, "R1")
    shades = ("R2", "R4", "R3", "R2", "R4", "R2", "R3", "R4")
    i = 0
    for row, y in enumerate((0, 8, 16, 24)):
        offset = 0 if row % 2 == 0 else -16
        for x in range(offset, 64, 32):
            tone = shades[i % len(shades)]
            i += 1
            cv.rect(x + 1, y + 1, x + 30, y + 6, tone)
            cv.hline(x + 2, x + 29, y + 1, "R1" if tone == "R4" else "R4")
            cv.hline(x + 2, x + 29, y + 6, "R3")
            if i % 3 == 0:
                cv.set(x + 8, y + 4, "R3")
                cv.set(x + 21, y + 3, "R3")


@piece("floor", 64, 24)
def floor(cv: Canvas):
    """Floorboards."""
    cv.rect(0, 0, 63, 23, "F1")
    for y in (0, 8, 16):
        cv.hline(0, 63, y, "F2")
        cv.hline(0, 63, y + 1, "F3")
        cv.grain(0, y + 2, 63, y + 7, "F2", step=4)
    for x in (14, 46):
        cv.vline(x, 0, 7, "F2")
    cv.vline(30, 8, 15, "F2")
    cv.vline(6, 16, 23, "F2")


# ---- the desk ------------------------------------------------------------

@piece("desk", 148, 50)
def desk(cv: Canvas):
    """Front view: top, apron, two drawer banks, four legs."""
    cv.box(0, 0, 147, 6, "W1", "W3", "W2")
    cv.grain(2, 2, 145, 5, "W2", step=2)
    cv.box(4, 7, 143, 12, "W2", "W1", "W4")

    for (bx0, bx1) in ((6, 54), (102, 141)):
        cv.box(bx0, 13, bx1, 40, "W1", "W3", "W2")
        for y in (15, 24, 33):
            cv.box(bx0 + 3, y, bx1 - 3, y + 6, "W2", "W1", "W4")
            cv.grain(bx0 + 4, y + 1, bx1 - 4, y + 5, "W4", step=3)
            mx = (bx0 + bx1) // 2
            cv.box(mx - 5, y + 2, mx + 5, y + 4, "C", "H", "c")

    cv.rect(56, 13, 100, 40, "W4")
    cv.frame(56, 13, 100, 40, "K")
    cv.dither(57, 14, 99, 22, "W2")

    for x in (6, 48, 102, 137):
        cv.box(x, 40, x + 5, 48, "W2", "W1", "W4")
    cv.shadow(4, 49, 143, 49, "F2")


@piece("cabinet", 60, 96)
def cabinet(cv: Canvas):
    """Four drawers. No labels - the page writes those over the top."""
    cv.box(0, 0, 59, 95, "M1", "M3", "M2")
    for i in range(4):
        y = 4 + i * 23
        cv.box(4, y, 55, y + 19, "M1", "M3", "M2")
        cv.dither(5, y + 14, 54, y + 18, "M2")
        cv.box(20, y + 8, 39, y + 12, "C", "H", "c")
        cv.box(8, y + 3, 17, y + 6, "P1", None, "P2")
    cv.shadow(2, 95, 57, 95, "F2")


@piece("chair", 62, 42)
def chair(cv: Canvas):
    """Seen from behind the sitter: backrest, frame, post."""
    cv.box(0, 0, 61, 27, "W2", "W1", "W4")
    cv.box(4, 4, 57, 23, "B", "W2", "W4")
    for y in (9, 15, 21):
        cv.hline(7, 54, y, "W2")
    cv.box(27, 28, 34, 41, "W2", "W1", "W4")


# ---- on the wall ---------------------------------------------------------

@piece("window", 78, 70)
def window(cv: Canvas):
    """Daylight, with greenery over the head. The room's cool light."""
    cv.box(0, 6, 77, 65, "W1", "W3", "W2")
    cv.rect(4, 10, 73, 61, "d1")
    cv.frame(4, 10, 73, 61, "K")
    for (x0, y0) in ((5, 11), (41, 11), (5, 38), (41, 38)):
        cv.rect(x0, y0, min(x0 + 32, 72), min(y0 + 22, 60), "d2" if y0 < 36 else "d1")
        for d in range(0, 13):
            cv.set(x0 + 3 + d, y0 + 14 - d, "d3")
            cv.set(x0 + 4 + d, y0 + 14 - d, "d3")
    cv.box(38, 10, 40, 61, "W1", "W3", "W2")
    cv.box(4, 34, 73, 37, "W1", "W3", "W2")
    cv.box(0, 62, 77, 69, "W1", "W3", "W2")
    for x in range(2, 74, 5):
        cv.rect(x, 0, x + 3, 4, "gr")
        cv.set(x + 1, 5, "g2")
        cv.set(x + 3, 2, "g2")


@piece("shelf", 96, 58)
def shelf(cv: Canvas):
    """Ledgers. Where the colour in this room comes from."""
    cv.box(0, 0, 95, 57, "W2", "W1", "W4")
    tones = ["b1", "b2", "b4", "b3", "b5", "b6", "b2", "b1", "b4", "b3", "b5", "b6"]
    for row, top in enumerate((4, 30)):
        cv.rect(3, top, 92, top + 20, "W4")
        x, i = 5, row * 5          # a different starting colour per row
        while x < 86:
            t = tones[i % len(tones)]
            w = 4 + (i % 3)
            h = 18 - (i % 4)
            cv.box(x, top + (20 - h), x + w, top + 19, t, None, None, "K")
            cv.vline(x + 1, top + (21 - h), top + 18, "P1")
            i += 1
            x += w + 2
        cv.box(1, top + 20, 94, top + 23, "W1", "W3", "W2")
    cv.shadow(2, 57, 93, 57, "R3")


@piece("chart", 84, 60)
def chart(cv: Canvas):
    """A framed chart. The line is drawn by the page, not baked in here."""
    cv.box(0, 0, 83, 59, "W1", "W3", "W2")
    cv.box(4, 4, 79, 55, "P1", None, "P2")
    for y in range(10, 52, 7):
        cv.hline(7, 76, y, "P3")


@piece("clock", 28, 28)
def clock(cv: Canvas):
    """Hands only. Nothing to read."""
    cv.box(0, 0, 27, 27, "W1", "W3", "W2")
    cv.box(3, 3, 24, 24, "P1", None, "P2")
    for (x, y) in ((13, 5), (13, 22), (5, 13), (22, 13)):
        cv.set(x, y, "K")
    cv.vline(13, 8, 13, "K")
    cv.hline(13, 18, 14, "K")
    cv.set(13, 14, "R")


@piece("corkboard", 116, 76)
def corkboard(cv: Canvas):
    """Where a firing rule gets pinned. Big enough to hold the card, so the
    verdict never has to lie across the desk it is judging."""
    cv.box(0, 0, 115, 75, "W1", "W3", "W2")
    cv.box(4, 4, 111, 71, "b4", None, "W2")
    cv.grain(6, 6, 109, 69, "W2", step=3)
    cv.dither(6, 62, 109, 69, "W2")


@piece("pin", 10, 10)
def pin(cv: Canvas):
    """A pushpin. Four of them hold a card to the board."""
    cv.rect(3, 6, 6, 9, "W4")
    cv.box(1, 1, 8, 6, "R", "r", "r")
    cv.set(3, 2, "P1")


# ---- small things ---------------------------------------------------------

@piece("lamp", 30, 48)
def lamp(cv: Canvas):
    """A coral shade with a warm centre, on a wooden stem."""
    for i, y in enumerate(range(0, 12)):
        inset = 6 - i // 2
        cv.hline(5 + inset, 24 - inset, y, "R")
        cv.set(4 + inset, y, "K")
        cv.set(25 - inset, y, "K")
    for i, y in enumerate(range(3, 12)):
        w = i // 2
        cv.hline(14 - w, 15 + w, y, "A")
    cv.hline(8, 21, 1, "P1")
    cv.box(2, 12, 27, 15, "r", "R", "K")
    cv.hline(4, 25, 16, "A")
    cv.box(13, 16, 16, 39, "W2", "W1", "W4")
    cv.box(6, 40, 23, 46, "W2", "W1", "W4")
    cv.shadow(5, 47, 24, 47, "W2")


@piece("papers", 36, 22)
def papers(cv: Canvas):
    for (dx, dy) in ((0, 5), (2, 3), (4, 0)):
        cv.box(dx, dy, dx + 29, dy + 15, "P1", None, "P2")
    for y in (4, 7, 10, 13):
        cv.hline(9, 30, y, "P3")


@piece("intray", 42, 20)
def intray(cv: Canvas):
    cv.box(0, 7, 41, 19, "M1", "M3", "M2")
    cv.vline(0, 0, 7, "K")
    cv.vline(41, 0, 7, "K")
    cv.hline(0, 41, 0, "K")


@piece("outtray", 42, 20)
def outtray(cv: Canvas):
    cv.box(0, 7, 41, 19, "W1", "W3", "W2")
    cv.vline(0, 0, 7, "K")
    cv.vline(41, 0, 7, "K")
    cv.hline(0, 41, 0, "K")


@piece("mug", 18, 18)
def mug(cv: Canvas):
    cv.box(1, 4, 12, 17, "P1", None, "P2")
    cv.rect(3, 6, 10, 8, "W4")
    cv.hline(3, 10, 6, "W2")
    cv.box(13, 8, 16, 13, "P1", None, "P2")
    cv.rect(14, 10, 15, 11, "N")


@piece("plant", 30, 44)
def plant(cv: Canvas):
    """Fuller fronds. A one-pixel stroke reads as wire, not a plant."""
    cv.box(7, 30, 22, 41, "R", "r", "r")
    cv.box(5, 26, 24, 31, "R", "r", "r")
    cv.rect(8, 29, 21, 30, "W4")

    def frond(x, y, h, tone):
        cv.vline(x, y, y + h, tone)
        for d in range(2, h, 3):
            cv.rect(x - 2, y + d, x - 1, y + d + 1, tone)
            cv.rect(x + 1, y + d + 2, x + 2, y + d + 3, tone)
        cv.set(x, y - 1, tone)

    frond(15, 2, 25, "gr")
    frond(9, 8, 19, "g2")
    frond(21, 8, 19, "g2")
    frond(6, 15, 12, "gr")
    frond(24, 15, 12, "gr")
    cv.shadow(6, 42, 23, 42, "F2")


@piece("bin", 24, 28)
def bin_(cv: Canvas):
    for y in range(4, 26):
        inset = (y - 4) // 9
        cv.hline(2 + inset, 21 - inset, y, "M1")
        cv.set(1 + inset, y, "K")
        cv.set(22 - inset, y, "K")
    cv.box(0, 1, 23, 5, "M2", "M3", "M2")
    for x in (7, 12, 17):
        cv.vline(x, 7, 24, "M2")
    cv.shadow(3, 27, 20, 27, "F2")


@piece("rug", 140, 30)
def rug(cv: Canvas):
    cv.box(0, 0, 139, 29, "b1", None, "r")
    cv.frame(4, 4, 135, 25, "b4")
    cv.frame(6, 6, 133, 23, "b1")
    cv.grain(8, 8, 131, 21, "r", step=3)
    for x in range(10, 130, 10):
        cv.vline(x, 9, 20, "b4")


@piece("nameplate", 46, 14)
def nameplate(cv: Canvas):
    cv.box(0, 4, 45, 13, "b4", "A", "W2")
    cv.box(0, 0, 45, 4, "W2", "W1", "W4")


@piece("stamppad", 28, 14)
def stamppad(cv: Canvas):
    cv.box(0, 5, 27, 13, "W4", "W2", "W4")
    cv.box(3, 0, 24, 6, "W2", "W1", "W4")
    cv.rect(5, 2, 22, 4, "R")


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
    # Tileable surfaces need their own files: CSS cannot crop one piece out of
    # an atlas and repeat only that, so a `repeat` background of the sheet tiles
    # the whole sheet - desks and cabinets scattered across the wall.
    for name in ("brick", "floor"):
        w, h, fn = PIECES[name]
        cv = Canvas(w, h)
        fn(cv)
        cv.image().save(OUT / f"{name}.png")
    meta["tiles"] = ["brick", "floor"]
    (OUT / "office.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  {len(meta['pieces'])} pieces -> {OUT / 'office.png'} "
          f"({meta['sheet']['w']}x{meta['sheet']['h']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
