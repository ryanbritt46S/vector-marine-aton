"""Our own chart-like symbols, drawn with Pillow at 1x, 2x and 3x (icons/<sym>.png, <sym>@2x.png, <sym>@3x.png)
plus icons/icons.json. Simple shapes in the colours sailors expect: green cans, red nuns, pillars with a magenta
light flare, square and triangle daybeacons, a magenta flare on a dot for a light. Original drawings, not NOAA or
IHO artwork.

Every image is CANVAS x CANVAS points with the aid's position at the centre (icon-anchor "center"); the shapes
stand on the position, like the chart's. The status rings (badge-*) use the same frame and go under the symbol.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from .classify import BADGES, SYMBOLS

CANVAS = 48                 # points; the position is at (24, 24)
SS = 4                      # supersampling for smooth edges
RATIOS = (1, 2, 3)

GREEN = (14, 150, 72, 255)
RED = (214, 40, 57, 255)
YELLOW = (247, 200, 20, 255)
WHITE = (255, 255, 255, 255)
BLACK = (28, 30, 34, 255)
ORANGE = (243, 112, 22, 255)
BLUE = (37, 99, 235, 255)
GREY = (138, 148, 158, 255)
MAGENTA = (204, 20, 140, 235)
OUTLINE = (22, 30, 40, 255)
AMBER = (245, 158, 11, 255)
ALERT = (226, 30, 40, 255)
TEMP = (120, 132, 146, 255)

TILT = 16                   # degrees a buoy leans to the right

COL = {"g": GREEN, "r": RED, "y": YELLOW, "w": WHITE, "b": BLACK}


class Pen:
    """Draws in points relative to the position (x right, y down) on a supersampled canvas."""

    def __init__(self, ratio: int):
        self.k = ratio * SS
        self.size = CANVAS * self.k
        self.img = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))

    def p(self, x, y):
        return ((CANVAS / 2 + x) * self.k, (CANVAS / 2 + y) * self.k)

    def pts(self, poly):
        return [self.p(x, y) for x, y in poly]

    def w(self, width):
        return max(1, int(round(width * self.k)))

    def shape(self, poly, fill, outline=OUTLINE, width=1.0):
        """A polygon filled with a colour, or with bands: ("h", [(from, to, colour)...]) across, ("v", ...) down."""
        pts = self.pts(poly)
        mask = Image.new("L", self.img.size, 0)
        ImageDraw.Draw(mask).polygon(pts, fill=255)
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        if isinstance(fill, tuple) and fill and fill[0] in ("h", "v"):
            axis, bands = fill
            for a, b, c in bands:
                if axis == "h":
                    d.rectangle([x0 - 2, y0 + (y1 - y0) * a, x1 + 2, y0 + (y1 - y0) * b], fill=c)
                else:
                    d.rectangle([x0 + (x1 - x0) * a, y0 - 2, x0 + (x1 - x0) * b, y1 + 2], fill=c)
        else:
            d.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], fill=fill)
        self.img = Image.composite(layer, self.img, mask)
        if outline and width:
            ImageDraw.Draw(self.img).line(pts + [pts[0], pts[1]], fill=outline, width=self.w(width), joint="curve")

    def circle(self, cx, cy, r, fill=None, outline=OUTLINE, width=1.0):
        x0, y0 = self.p(cx - r, cy - r)
        x1, y1 = self.p(cx + r, cy + r)
        ImageDraw.Draw(self.img).ellipse([x0, y0, x1, y1], fill=fill, outline=outline if width else None,
                                         width=self.w(width) if width else 0)

    def ring(self, cx, cy, r, color, width, dashes=0):
        if not dashes:
            self.circle(cx, cy, r, fill=None, outline=color, width=width)
            return
        d = ImageDraw.Draw(self.img)
        x0, y0 = self.p(cx - r, cy - r)
        x1, y1 = self.p(cx + r, cy + r)
        step = 360 / dashes
        for i in range(dashes):
            d.arc([x0, y0, x1, y1], i * step, i * step + step * 0.6, fill=color, width=self.w(width))

    def line(self, pts, color=OUTLINE, width=1.0):
        ImageDraw.Draw(self.img).line(self.pts(pts), fill=color, width=self.w(width), joint="curve")

    def flare(self, x, y, length, half, angle_deg=-45):
        """The light flare: a drop from (x, y), its round end `length` away at `angle_deg` (-45 = up and right)."""
        a = math.radians(angle_deg)
        ux, uy = math.cos(a), math.sin(a)
        cx, cy = x + ux * (length - half), y + uy * (length - half)
        poly = [(x, y), (cx - uy * half, cy + ux * half), (cx + uy * half, cy - ux * half)]
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.polygon(self.pts(poly), fill=MAGENTA)
        x0, y0 = self.p(cx - half, cy - half)
        x1, y1 = self.p(cx + half, cy + half)
        d.ellipse([x0, y0, x1, y1], fill=MAGENTA)
        self.img = Image.alpha_composite(self.img, layer)

    def tilt(self, deg: float = TILT):
        """Lean what's drawn so far, about the position (buoys float and lean, like the chart's)."""
        c = self.size / 2
        self.img = self.img.rotate(-deg, resample=Image.BICUBIC, center=(c, c))

    def out(self, ratio: int) -> Image.Image:
        n = CANVAS * ratio
        return self.img.resize((n, n), Image.LANCZOS)


# ------------------------------------------------------------------------------------------- shapes (points)

CAN = [(-5.5, -3), (5.5, -3), (5.5, -16), (-5.5, -16)]
NUN = [(-6.5, -3), (6.5, -3), (0, -18)]
PILLAR = [(-5.5, -3), (5.5, -3), (2.5, -15), (-2.5, -15)]
SQUARE = [(-5.5, -4), (5.5, -4), (5.5, -15), (-5.5, -15)]
TRIANGLE = [(-6.5, -4), (6.5, -4), (0, -16.5)]
DIAMOND = [(0, -17), (6.5, -10.5), (0, -4), (-6.5, -10.5)]
BOARD = [(-5.5, -4), (5.5, -4), (5.5, -16), (-5.5, -16)]
RANGE_BOARD = [(-3, -4), (3, -4), (3, -16), (-3, -16)]


def ellipse_poly(cx, cy, r, n=40):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def octagon(cx, cy, r):
    return [(cx + r * math.cos(math.pi / 8 + i * math.pi / 4), cy + r * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)]


def bands(code: str):
    """Fill for a buoy's colour code."""
    if code == "rw":
        return ("v", [(0, .25, RED), (.25, .5, WHITE), (.5, .75, RED), (.75, 1, WHITE)])
    if code == "rgr":
        return ("h", [(0, .36, RED), (.36, .64, GREEN), (.64, 1, RED)])
    if code == "grg":
        return ("h", [(0, .36, GREEN), (.36, .64, RED), (.64, 1, GREEN)])
    if code == "brb":
        return ("h", [(0, .36, BLACK), (.36, .64, RED), (.64, 1, BLACK)])
    if code == "wo":
        return ("h", [(0, .22, ORANGE), (.22, .78, WHITE), (.78, 1, ORANGE)])
    if code == "wbu":
        return ("h", [(0, .38, WHITE), (.38, .62, BLUE), (.62, 1, WHITE)])
    return COL.get(code, GREY)


def position(pen: Pen):
    pen.circle(0, 0, 1.6, fill=WHITE, outline=OUTLINE, width=0.9)


def reg_mark(pen: Pen, mark: str, cx: float, cy: float, s: float = 3.2):
    if mark in ("danger", "exclusion"):
        pen.shape([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], WHITE, outline=ORANGE, width=1.2)
        if mark == "exclusion":
            pen.line([(cx - s * .55, cy - s * .55), (cx + s * .55, cy + s * .55)], ORANGE, 1.0)
            pen.line([(cx - s * .55, cy + s * .55), (cx + s * .55, cy - s * .55)], ORANGE, 1.0)
    elif mark == "control":
        pen.circle(cx, cy, s * .85, fill=WHITE, outline=ORANGE, width=1.2)
    elif mark == "info":
        q = s * .8
        pen.shape([(cx - q, cy - q), (cx + q, cy - q), (cx + q, cy + q), (cx - q, cy + q)], WHITE, outline=ORANGE, width=1.2)


def topmark(pen: Pen, code: str, top: float):
    if code == "rw":
        pen.circle(0, top - 2.4, 2.3, fill=RED, outline=OUTLINE, width=0.8)
    elif code == "brb":
        pen.circle(0, top - 2.2, 1.9, fill=BLACK, outline=None, width=0)
        pen.circle(0, top - 6.0, 1.9, fill=BLACK, outline=None, width=0)


def leaned(x: float, y: float, deg: float = TILT) -> tuple[float, float]:
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def draw(sym: str, ratio: int) -> Image.Image:
    pen = Pen(ratio)
    fam, _, code = sym.partition("-")
    if fam in ("can", "nun", "sphere", "pillar", "reg", "lb") or sym in ("mooring", "buoy-other"):
        if fam == "can":
            pen.shape(CAN, bands(code))
        elif fam == "nun":
            pen.shape(NUN, bands(code))
        elif fam == "sphere":
            pen.shape(ellipse_poly(0, -9.5, 6.3), bands(code))
        elif fam in ("pillar", "lb"):
            pen.shape(PILLAR, bands(code) if code != "other" else GREY)
            topmark(pen, code, -15)
        elif fam == "reg":
            pen.shape(CAN, bands("wo"))
            reg_mark(pen, code, 0, -9.5)
        elif sym == "mooring":
            pen.shape(ellipse_poly(0, -9.5, 6.3), bands("wbu"))
        else:
            pen.shape(CAN, GREY)
        pen.tilt()
        if fam == "lb":
            fx, fy = leaned(1.5, -13.5)
            pen.flare(fx, fy, 12, 3.1, angle_deg=-40)
        position(pen)
    elif fam == "db":
        pen.line([(0, 0), (0, -4)], OUTLINE, 1.5)
        kind, _, c = code.partition("-")
        if kind == "sq":
            pen.shape(SQUARE, COL[c])
        elif kind == "tri":
            pen.shape(TRIANGLE, COL[c])
        elif kind == "jn":
            if c == "g":
                pen.shape(SQUARE, ("h", [(0, .36, GREEN), (.36, .64, RED), (.64, 1, GREEN)]))
            else:
                pen.shape(TRIANGLE, ("h", [(0, .5, RED), (.5, .75, GREEN), (.75, 1, RED)]))
        elif kind == "dia":
            border = {"w": OUTLINE, "r": RED, "g": GREEN, "y": OUTLINE, "b": BLACK}[c]
            pen.shape(DIAMOND, YELLOW if c == "y" else WHITE, outline=border, width=2.0 if c in "rgb" else 1.0)
        elif kind == "reg":
            pen.shape(BOARD, WHITE)
            reg_mark(pen, "danger", 0, -10, 4.2)
        elif kind == "range":
            pen.shape(RANGE_BOARD, ("v", [(0, .34, RED), (.34, .66, WHITE), (.66, 1, RED)]))
        elif kind == "rw":
            pen.shape(octagon(0, -10, 6.5), ("v", [(0, .5, RED), (.5, 1, WHITE)]))
        else:
            pen.shape([(-3.5, -4), (3.5, -4), (3.5, -11), (-3.5, -11)], GREY)
        position(pen)
    elif fam == "light":
        if code == "major":
            pen.flare(0, 0, 18, 4.6)
            pen.ring(0, 0, 4.6, MAGENTA, 1.6)
            pen.circle(0, 0, 2.8, fill=BLACK, outline=WHITE, width=0.9)
        else:
            pen.flare(0, 0, 14, 3.4)
            pen.circle(0, 0, 2.7, fill=COL[code], outline=OUTLINE, width=1.0)
    elif fam == "range":
        top = -12 if code == "front" else -16
        pen.flare(1.0, top + 1, 10, 2.7)
        pen.shape([(-2.6, -2), (2.6, -2), (2.6, top), (-2.6, top)], ("v", [(0, .34, RED), (.34, .66, WHITE), (.66, 1, RED)]))
        position(pen)
    elif sym == "racon":
        pen.ring(0, 0, 8, MAGENTA, 1.7)
        pen.circle(0, 0, 2, fill=MAGENTA, outline=None, width=0)
    elif sym == "vais":
        pen.shape([(0, -8.5), (8.5, 0), (0, 8.5), (-8.5, 0)], (255, 255, 255, 150), outline=MAGENTA, width=1.6)
        pen.line([(-3.2, -3), (0, 3.4), (3.2, -3)], MAGENTA, 1.5)
    elif sym == "sound":
        for r in (5, 8.5, 12):
            x0, y0 = pen.p(-r, -r)
            x1, y1 = pen.p(r, r)
            ImageDraw.Draw(pen.img).arc([x0, y0, x1, y1], -40, 40, fill=MAGENTA, width=pen.w(1.6))
        pen.circle(0, 0, 2.2, fill=MAGENTA, outline=None, width=0)
    elif fam == "badge":
        cx, cy, r = 2, -8, 13.5
        if code == "temporary":
            pen.ring(cx, cy, r, TEMP, 2.0, dashes=14)
            bx, by, br, fg, col = 11.5, -18.5, 4.6, WHITE, TEMP
        else:
            col = ALERT if code == "missing" else AMBER
            pen.ring(cx, cy, r, (255, 255, 255, 220), 4.2)
            pen.ring(cx, cy, r, col, 2.2)
            bx, by, br, fg = 11.5, -18.5, 4.8, (WHITE if code == "missing" else BLACK)
        pen.circle(bx, by, br, fill=col, outline=WHITE, width=1.0)
        if code == "temporary":
            pen.line([(bx - 2.2, by - 2.2), (bx + 2.2, by - 2.2)], fg, 1.3)
            pen.line([(bx, by - 2.2), (bx, by + 2.6)], fg, 1.3)
        else:
            pen.line([(bx, by - 2.9), (bx, by + 0.7)], fg, 1.5)
            pen.circle(bx, by + 2.4, 0.75, fill=fg, outline=None, width=0)
    else:
        pen.circle(0, 0, 3.4, fill=GREY, outline=OUTLINE, width=1.0)
    return pen.out(ratio)


def write_icons(out_dir: Path) -> dict:
    """Write icons/<sym>[@2x|@3x].png and icons/icons.json; returns the manifest."""
    d = Path(out_dir) / "icons"
    d.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    icons = {}
    for sym, title in {**SYMBOLS, **BADGES}.items():
        files = {}
        for r in RATIOS:
            name = f"{sym}.png" if r == 1 else f"{sym}@{r}x.png"
            img = draw(sym, r)
            img.save(d / name, optimize=True)
            h.update((d / name).read_bytes())
            files[str(r)] = f"icons/{name}"
        icons[sym] = {"title": title, "files": files}
    manifest = {"version": h.hexdigest()[:12], "size": CANVAS, "anchor": "center", "pixel_ratios": list(RATIOS),
                "prefix": "vm-aton-", "icons": icons}
    (d / "icons.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest
