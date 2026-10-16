"""Procedural 32x32 dungeon tiles with autotiling, in the 16-bit style.

Everything here is generated at startup with PIL from deterministic integer
hash noise (no ``random``: tiles must look the same every run and the UI
package never draws from the game's RNG). Walls know which sides face floor
so they get a lit rim there and a brick face where the floor is below them;
floor tiles under a wall get a soft shadow band, and a few carry decals.

The public surface is :func:`floor_texture`, :func:`wall_texture`,
:func:`texture` for the one-off tiles (doors, stairs) and
:func:`portal_frames`.
"""
from __future__ import annotations

import colorsys
from typing import Dict, List, Optional, Tuple

import arcade
from PIL import Image, ImageDraw

PX = 64
RGBA = Tuple[int, int, int, int]
RGB = Tuple[int, int, int]

# Base palettes per dungeon style
STYLES: Dict[str, Dict[str, RGB]] = {
    "rooms": {
        "floor": (96, 94, 112), "grout": (70, 68, 84), "floor_hi": (116, 114, 134),
        "wall_top": (44, 42, 56), "wall_top_hi": (62, 60, 76),
        "brick": (84, 80, 100), "brick_hi": (108, 104, 124), "brick_lo": (62, 58, 76),
        "mortar": (36, 33, 44), "rim": (128, 124, 146), "rim_lo": (90, 88, 108),
    },
    "cavern": {
        "floor": (98, 86, 72), "grout": (72, 62, 52), "floor_hi": (120, 106, 90),
        "wall_top": (46, 40, 36), "wall_top_hi": (66, 58, 50),
        "brick": (84, 72, 60), "brick_hi": (108, 94, 78), "brick_lo": (60, 50, 42),
        "mortar": (34, 28, 24), "rim": (130, 112, 92), "rim_lo": (92, 78, 64),
    },
}

DECAL_CHANCE = 0.08  # share of floor tiles that carry a decal

# Floor tiers recolour the base palettes: (target hue, how far to pull the hue
# towards it, saturation change, value change, optional HSV for grout/mortar).
# T1 keeps the base stone of the upper catacombs.
TIER_TINTS: Dict[str, Tuple[float, float, float, float, Optional[Tuple[float, float, float]]]] = {
    "T2": (0.26, 1.0, 0.10, -0.02, None),            # mossy, damp green
    "T3": (0.06, 1.0, 0.22, -0.02, None),            # rust and ochre ossuary
    "T4": (0.75, 1.0, 0.20, -0.06, None),            # cold violet crypt
    "T5": (0.02, 0.5, -0.15, -0.12, (0.0, 0.6, 0.22)),  # ash, ember-red seams
}


def hash32(*values: int) -> int:
    """A small integer hash, stable across runs and platforms."""
    h = 0x811C9DC5
    for v in values:
        h ^= (v + 0x9E3779B9) & 0xFFFFFFFF
        h = (h * 0x01000193) & 0xFFFFFFFF
        h ^= h >> 15
    return h


def noise(x: int, y: int, seed: int = 0) -> float:
    """Deterministic white noise in [0, 1) for a pixel or cell."""
    return (hash32(x, y, seed) % 10007) / 10007.0


def shift(c: RGB, dv: float, ds: float = 0.0) -> RGB:
    """Lighten/darken a colour by ``dv`` in HSV value, nudging saturation by ``ds``."""
    h, s, v = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
    v = max(0.0, min(1.0, v + dv))
    s = max(0.0, min(1.0, s + ds))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def tint(c: RGB, hue: float, blend: float, ds: float = 0.0, dv: float = 0.0) -> RGB:
    """Pull a colour's hue ``blend`` of the way towards ``hue`` (0..1 on the wheel)
    and nudge its saturation and value."""
    h, s, v = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
    delta = ((hue - h + 0.5) % 1.0) - 0.5  # shortest way round the wheel
    h = (h + delta * blend) % 1.0
    s = max(0.0, min(1.0, s + ds))
    v = max(0.0, min(1.0, v + dv))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def style_for(base: str, tier: str) -> str:
    """The style key for ``base`` ("rooms"/"cavern") recoloured for a floor tier;
    the palette is built on first use. Unknown tiers keep the base style."""
    if base not in STYLES:
        base = "rooms"
    if tier not in TIER_TINTS:
        return base
    key = f"{base}/{tier}"
    if key not in STYLES:
        hue, blend, ds, dv, accent = TIER_TINTS[tier]
        palette = {k: tint(c, hue, blend, ds, dv) for k, c in STYLES[base].items()}
        if accent is not None:
            ah, as_, av = accent
            for k in ("grout", "mortar"):
                r, g, b = colorsys.hsv_to_rgb(ah, as_, av)
                palette[k] = (int(r * 255), int(g * 255), int(b * 255))
        STYLES[key] = palette
    return key


def _is_cavern(style_name: str) -> bool:
    return style_name.split("/")[0] == "cavern"


def _rgba(c: RGB, a: int = 255) -> RGBA:
    return (c[0], c[1], c[2], a)


def _speckle(img: Image.Image, base: RGB, seed: int, amount: float = 0.05, strength: int = 7):
    """Per-pixel brightness jitter plus sparse speckles, for a stone grain."""
    px = img.load()
    for y in range(PX):
        for x in range(PX):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            n = noise(x, y, seed)
            d = int((n - 0.5) * 2 * strength)
            if noise(x, y, seed + 7) < amount:
                d += 10 if n > 0.5 else -10
            px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)),
                        max(0, min(255, b + d)), a)


def _darken(img: Image.Image, x: int, y: int, amount: int) -> None:
    px = img.load()
    if 0 <= x < PX and 0 <= y < PX:
        r, g, b, a = px[x, y]
        px[x, y] = (max(0, r - amount), max(0, g - amount), max(0, b - amount), a)


# --- Floors ------------------------------------------------------------------

def _flagstones(style: Dict[str, RGB], variant: int) -> Image.Image:
    """Three courses of flagstones with two-pixel grout, a lit top-left edge, a
    shadowed bottom-right edge, per-stone tone and the odd crack or chip."""
    img = Image.new("RGBA", (PX, PX), _rgba(style["floor"]))
    d = ImageDraw.Draw(img)
    grout = _rgba(style["grout"])
    hi = _rgba(style["floor_hi"])
    lo = _rgba(shift(style["floor"], -0.08))
    courses = ((0, 21), (22, 42), (43, PX - 1))
    for ci, (top, bottom) in enumerate(courses):
        offset = (variant * 9 + ci * 23) % 26
        joints = sorted({0, (offset + 19) % PX, (offset + 41) % PX})
        edges = joints + [PX]
        for a, b in zip(edges, edges[1:]):
            if b - a < 4:
                continue
            tone = shift(style["floor"], (noise(a, ci, 50 + variant) - 0.5) * 0.10)
            d.rectangle([a, top, b - 1, bottom], fill=_rgba(tone))
            # lit edge top/left, shadow edge bottom/right
            d.line([(a + 2, top + 2), (b - 3, top + 2)], fill=hi)
            d.line([(a + 2, top + 2), (a + 2, bottom - 2)], fill=hi)
            d.line([(a + 2, bottom - 2), (b - 3, bottom - 2)], fill=lo)
            d.line([(b - 3, top + 2), (b - 3, bottom - 2)], fill=lo)
        # grout: two pixels wide, darker inner line
        d.rectangle([0, bottom - 1, PX - 1, bottom], fill=grout)
        for jx in joints:
            d.rectangle([jx, top, jx + 1, bottom], fill=grout)
    _speckle(img, style["floor"], seed=100 + variant, amount=0.04, strength=6)
    if variant % 4 == 3:  # a crack across one stone
        pts = [(8, 40), (14, 46), (19, 45), (26, 52), (31, 54)]
        d.line(pts, fill=grout, width=1)
        d.line([(p[0] + 1, p[1]) for p in pts], fill=hi, width=1)
    if variant % 4 == 1:  # a chipped corner
        d.polygon([(44, 22), (52, 22), (44, 30)], fill=grout)
    return img


def _cavern_floor(style: Dict[str, RGB], variant: int) -> Image.Image:
    """Packed earth: heavy grain, darker blotches, pebbles with a lit side."""
    img = Image.new("RGBA", (PX, PX), _rgba(style["floor"]))
    _speckle(img, style["floor"], seed=200 + variant, amount=0.10, strength=9)
    d = ImageDraw.Draw(img)
    for i in range(2 + variant % 2):  # dark blotches
        cx, cy = int(noise(i, variant, 33) * 48) + 8, int(noise(variant, i, 34) * 48) + 8
        r = 6 + int(noise(i, variant, 35) * 8)
        d.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2],
                  fill=_rgba(shift(style["floor"], -0.06), 255))
    for i in range(4 + variant % 3):  # pebbles
        n = noise(i, variant, 31)
        x, y = int(n * 56) + 4, int(noise(variant, i, 32) * 56) + 4
        r = 2 + int(noise(i, variant, 36) * 2)
        d.ellipse([x - r, y - r + 1, x + r, y + r], fill=_rgba(style["grout"]))
        d.ellipse([x - r, y - r, x + r, y + r - 1], fill=_rgba(shift(style["floor"], -0.04)))
        d.point((x - 1, y - r + 1), fill=_rgba(style["floor_hi"]))
        d.point((x, y - r + 1), fill=_rgba(style["floor_hi"]))
    return img


def _decal(img: Image.Image, kind: int, style: Dict[str, RGB]) -> None:
    """Small story-telling marks: bones, a skull, moss, a dark stain."""
    d = ImageDraw.Draw(img)
    bone = (214, 208, 190, 255)
    bone_lo = (160, 154, 140, 255)
    dark = (30, 26, 36, 255)
    if kind == 0:  # crossed bones
        d.line([(18, 44), (44, 22)], fill=bone, width=3)
        d.line([(18, 22), (44, 44)], fill=bone, width=3)
        for x, y in ((16, 20), (46, 20), (16, 46), (46, 46)):
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=bone_lo)
            d.ellipse([x - 2, y - 3, x + 1, y], fill=bone)
    elif kind == 1:  # skull
        d.ellipse([22, 20, 42, 40], fill=bone)
        d.rectangle([27, 38, 37, 44], fill=bone_lo)
        for x in (29, 32, 35):
            d.line([(x, 39), (x, 43)], fill=dark)
        d.ellipse([26, 27, 30, 31], fill=dark)
        d.ellipse([34, 27, 38, 31], fill=dark)
        d.polygon([(32, 33), (30, 36), (34, 36)], fill=bone_lo)
        d.arc([22, 20, 42, 40], 200, 340, fill=(236, 232, 220, 255))
    elif kind == 2:  # moss
        moss = (84, 112, 60, 210)
        moss_hi = (112, 142, 80, 210)
        for cx, cy, r in ((20, 40, 8), (30, 46, 6), (40, 38, 6), (26, 30, 4), (44, 46, 3)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=moss)
            d.ellipse([cx - r + 1, cy - r + 1, cx, cy], fill=moss_hi)
    else:  # dark stain
        stain = _rgba(shift(style["floor"], -0.18, 0.1), 220)
        d.ellipse([16, 24, 48, 48], fill=stain)
        d.ellipse([28, 16, 44, 32], fill=stain)
        d.ellipse([12, 36, 24, 46], fill=stain)


def _shadow_bands(img: Image.Image, top: bool, left: bool) -> None:
    """Ambient occlusion where a wall stands above (screen-up) or to the left."""
    px = img.load()
    depth = 14
    for i in range(depth):
        a = int(110 * (1 - i / depth) ** 1.4)
        if top:
            for x in range(PX):
                r, g, b, _ = px[x, i]
                px[x, i] = (r * (255 - a) // 255, g * (255 - a) // 255, b * (255 - a) // 255, 255)
        if left:
            for y in range(PX):
                r, g, b, _ = px[i, y]
                px[i, y] = (r * (255 - a) // 255, g * (255 - a) // 255, b * (255 - a) // 255, 255)


def floor_image(
    style_name: str, variant: int, shadow_top: bool = False, shadow_left: bool = False,
    decal: Optional[int] = None,
) -> Image.Image:
    style = STYLES[style_name]
    img = _cavern_floor(style, variant) if _is_cavern(style_name) else _flagstones(style, variant)
    if decal is not None:
        _decal(img, decal, style)
    _shadow_bands(img, shadow_top, shadow_left)
    return img


# --- Walls -------------------------------------------------------------------

def _wall_top(style: Dict[str, RGB], rims: Tuple[bool, bool, bool, bool], seed: int) -> Image.Image:
    """The flat top of a wall; ``rims`` = (up, right, down, left) sides that face floor."""
    img = Image.new("RGBA", (PX, PX), _rgba(style["wall_top"]))
    _speckle(img, style["wall_top"], seed=300 + seed, amount=0.03, strength=5)
    d = ImageDraw.Draw(img)
    rim = _rgba(style["rim"])
    rim_lo = _rgba(style["rim_lo"])
    top_hi = _rgba(style["wall_top_hi"])
    up, right, down, left = rims
    if up:
        d.rectangle([0, 0, PX - 1, 1], fill=rim)
        d.rectangle([0, 2, PX - 1, 3], fill=rim_lo)
    if left:
        d.rectangle([0, 0, 1, PX - 1], fill=rim)
        d.rectangle([2, 0, 3, PX - 1], fill=rim_lo)
    if right:
        d.rectangle([PX - 2, 0, PX - 1, PX - 1], fill=rim_lo)
        d.rectangle([PX - 4, 0, PX - 3, PX - 1], fill=top_hi)
    if down:
        d.rectangle([0, PX - 2, PX - 1, PX - 1], fill=rim_lo)
        d.rectangle([0, PX - 4, PX - 1, PX - 3], fill=top_hi)
    # faint paving lines across the top so it is not a flat slab
    for k in range(2):
        y = 20 + k * 22 + (seed * 5) % 6
        d.line([(4, y), (PX - 5, y)], fill=_rgba(shift(style["wall_top"], -0.05)))
    return img


def _wall_face(style: Dict[str, RGB], seed: int, cavern: bool) -> Image.Image:
    """A wall seen from the front: a lit cap, bricks (or rock strata) and a dark foot."""
    img = Image.new("RGBA", (PX, PX), _rgba(style["mortar"]))
    d = ImageDraw.Draw(img)
    cap = 8
    d.rectangle([0, 0, PX - 1, cap - 1], fill=_rgba(style["rim_lo"]))
    d.rectangle([0, 0, PX - 1, 1], fill=_rgba(style["rim"]))
    d.line([(0, cap - 1), (PX - 1, cap - 1)], fill=_rgba(shift(style["rim_lo"], -0.1)))
    if cavern:
        y = cap
        band = 0
        while y < PX:
            h = 10 + int(noise(band, seed, 41) * 8)
            tone = shift(style["brick"], (noise(band, seed, 42) - 0.5) * 0.16)
            d.rectangle([0, y, PX - 1, min(PX - 1, y + h - 1)], fill=_rgba(tone))
            d.rectangle([0, y, PX - 1, y + 1], fill=_rgba(shift(tone, 0.08)))
            # a wavy crack between strata
            for x in range(PX):
                wob = int(noise(x // 3, band, seed + 43) * 3)
                yy = min(PX - 1, y + h - 1 - wob)
                d.point((x, yy), fill=_rgba(style["mortar"]))
                if noise(x, band, seed + 44) < 0.3:
                    d.point((x, yy - 1), fill=_rgba(shift(tone, -0.08)))
            y += h
            band += 1
    else:
        brick_h, brick_w = 14, 32
        row = 0
        y = cap
        while y < PX:
            offset = (brick_w // 2) if row % 2 else 0
            x = -offset
            col = 0
            while x < PX:
                tone = shift(style["brick"], (noise(col, row, seed) - 0.5) * 0.18)
                depth_fade = -0.10 * (y - cap) / (PX - cap)  # lower bricks sit in shadow
                tone = shift(tone, depth_fade)
                x0, x1 = max(0, x), min(PX - 1, x + brick_w - 3)
                y1 = min(PX - 1, y + brick_h - 3)
                if x1 >= x0:
                    d.rectangle([x0, y, x1, y1], fill=_rgba(tone))
                    d.line([(x0, y), (x1, y)], fill=_rgba(shift(tone, 0.10)))
                    d.line([(x0, y1), (x1, y1)], fill=_rgba(shift(tone, -0.12)))
                    d.line([(x1, y), (x1, y1)], fill=_rgba(shift(tone, -0.08)))
                    if x >= 0:
                        d.line([(x0, y), (x0, y1)], fill=_rgba(shift(tone, 0.06)))
                    # weathering: a chipped corner or a hairline crack now and then
                    n = noise(col, row, seed + 9)
                    if n < 0.18:
                        d.polygon([(x1 - 4, y1), (x1, y1), (x1, y1 - 4)],
                                  fill=_rgba(style["mortar"]))
                    elif n > 0.86:
                        cx = x0 + 6 + int(noise(col, row, seed + 10) * (x1 - x0 - 12))
                        d.line([(cx, y + 2), (cx + 2, y + 6), (cx + 1, y1 - 2)],
                               fill=_rgba(shift(tone, -0.16)))
                x += brick_w
                col += 1
            y += brick_h
            row += 1
    d.rectangle([0, PX - 2, PX - 1, PX - 1], fill=_rgba(shift(style["mortar"], -0.08)))
    return img


def wall_image(
    style_name: str, face: bool, rims: Tuple[bool, bool, bool, bool], seed: int = 0
) -> Image.Image:
    style = STYLES[style_name]
    if face:
        return _wall_face(style, seed, cavern=_is_cavern(style_name))
    return _wall_top(style, rims, seed)


# --- One-off tiles -----------------------------------------------------------

def door_image(locked: bool, style_name: str = "rooms") -> Image.Image:
    style = STYLES[style_name]
    img = Image.new("RGBA", (PX, PX), _rgba(style["mortar"]))
    d = ImageDraw.Draw(img)
    frame = (70, 48, 30, 255)
    frame_hi = (96, 68, 42, 255)
    d.rectangle([0, 0, PX - 1, PX - 1], outline=frame, width=2)
    d.rectangle([2, 2, PX - 3, PX - 3], outline=frame_hi, width=2)
    if locked:
        wood, wood_hi, wood_lo = (142, 96, 52), (166, 118, 70), (104, 68, 36)
        d.rectangle([4, 4, PX - 5, PX - 5], fill=_rgba(wood))
        for px_ in (16, 30, 44):  # planks
            d.rectangle([px_, 4, px_ + 1, PX - 5], fill=_rgba(wood_lo))
            d.line([(px_ + 2, 4), (px_ + 2, PX - 5)], fill=_rgba(wood_hi))
        for gx in range(6, PX - 6, 5):  # wood grain
            for gy in range(6, PX - 6, 9):
                if noise(gx, gy, 61) < 0.5:
                    d.line([(gx, gy + (gx % 3)), (gx, gy + 3 + (gx % 3))], fill=_rgba(wood_lo))
        for y in (14, 46):  # iron bands
            d.rectangle([4, y, PX - 5, y + 5], fill=(70, 70, 82, 255))
            d.line([(4, y), (PX - 5, y)], fill=(118, 118, 132, 255))
            d.line([(4, y + 5), (PX - 5, y + 5)], fill=(44, 44, 54, 255))
            for bx in (10, 26, 40, 55):
                d.rectangle([bx, y + 2, bx + 1, y + 3], fill=(170, 170, 186, 255))
                d.point((bx, y + 2), fill=(220, 220, 236, 255))
        d.rectangle([26, 26, 37, 37], fill=(222, 184, 70, 255))  # lock plate
        d.rectangle([26, 26, 37, 37], outline=(150, 110, 30, 255))
        d.ellipse([30, 29, 33, 32], fill=(60, 40, 10, 255))
        d.rectangle([31, 32, 32, 35], fill=(60, 40, 10, 255))
    else:
        floor = floor_image(style_name, 0)
        img.paste(floor.crop((4, 4, PX - 4, PX - 4)), (4, 4))
        d.rectangle([0, 0, PX - 1, PX - 1], outline=frame, width=2)
        d.rectangle([2, 2, PX - 3, PX - 3], outline=frame_hi, width=2)
        # open leaf folded against the left jamb, with hinges
        d.rectangle([4, 4, 11, PX - 5], fill=(142, 96, 52, 255))
        d.line([(6, 4), (6, PX - 5)], fill=(166, 118, 70, 255))
        d.line([(10, 4), (10, PX - 5)], fill=(104, 68, 36, 255))
        for hy in (12, 50):
            d.rectangle([4, hy, 11, hy + 3], fill=(70, 70, 82, 255))
    return img


def stairs_image(style_name: str = "rooms") -> Image.Image:
    """A stairwell cut into the floor, steps fading into darkness."""
    style = STYLES[style_name]
    img = floor_image(style_name, 1)
    d = ImageDraw.Draw(img)
    pit = (18, 16, 24, 255)
    d.rectangle([4, 4, PX - 5, PX - 5], fill=pit)
    d.rectangle([4, 4, PX - 5, PX - 5], outline=_rgba(style["rim_lo"]), width=2)
    steps = 7
    for i in range(steps):
        y0 = 8 + i * 7
        inset = 6 + i * 2
        tone = shift((150, 146, 160), -0.12 * i)
        d.rectangle([inset, y0, PX - 1 - inset, y0 + 4], fill=_rgba(tone))
        d.line([(inset, y0), (PX - 1 - inset, y0)], fill=_rgba(shift(tone, 0.14)))
        d.line([(inset, y0 + 4), (PX - 1 - inset, y0 + 4)], fill=_rgba(shift(tone, -0.18)))
        d.rectangle([inset, y0 + 5, PX - 1 - inset, y0 + 6], fill=pit)
        # side walls of the well catch a little light
        d.line([(inset - 1, y0), (inset - 1, y0 + 6)], fill=_rgba(shift(tone, -0.3)))
        d.line([(PX - inset, y0), (PX - inset, y0 + 6)], fill=_rgba(shift(tone, -0.35)))
    return img


def portal_image(frame: int, frames: int = 4) -> Image.Image:
    """A turning teal ring with an inner swirl and rune ticks; ``frame`` picks the phase."""
    img = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = PX / 2 - 0.5
    import math
    for r in range(26, 11, -1):
        t = (26 - r) / 15
        tone = (int(40 + 60 * t), int(150 + 90 * t), int(150 + 90 * t), 255)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tone)
    d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=(236, 252, 252, 255))
    d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(255, 255, 255, 255))
    d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], outline=(20, 90, 95, 255), width=2)
    phase = frame / frames * 2 * math.pi
    for k in range(12):  # rune ticks turning with the ring
        ang = phase / 3 + k * math.pi / 6
        x0, y0 = cx + math.cos(ang) * 22, cy + math.sin(ang) * 22
        x1, y1 = cx + math.cos(ang) * 25, cy + math.sin(ang) * 25
        d.line([(x0, y0), (x1, y1)], fill=(20, 70, 75, 255), width=2)
    for k in range(4):  # swirl sparks around the ring
        ang = phase + k * math.pi / 2
        for rr, size in ((20, 3), (15, 2), (10, 1)):
            x = cx + math.cos(ang + rr * 0.15) * rr
            y = cy + math.sin(ang + rr * 0.15) * rr
            d.ellipse([x - size, y - size, x + size, y + size], fill=(255, 255, 255, 230))
    return img


# --- Texture cache -----------------------------------------------------------

_cache: Dict[Tuple, arcade.Texture] = {}


def _tex(key: Tuple, make) -> arcade.Texture:
    """Cached texture for ``key``; ``make`` builds the image only on a miss."""
    tex = _cache.get(key)
    if tex is None:
        tex = arcade.Texture(make(), hash="tiles:" + ":".join(str(k) for k in key))
        _cache[key] = tex
    return tex


def floor_texture(
    style_name: str, x: int, y: int, shadow_top: bool, shadow_left: bool, *, decals: bool = True
) -> arcade.Texture:
    """Floor at map cell (x, y): variant and decal are picked from the position."""
    variant = hash32(x, y, 1) % 4
    decal = hash32(x, y, 2) % 4 if decals and noise(x, y, 3) < DECAL_CHANCE else None
    key = ("floor", style_name, variant, shadow_top, shadow_left, decal)
    return _tex(key, lambda: floor_image(style_name, variant, shadow_top, shadow_left, decal))


def wall_texture(
    style_name: str, face: bool, rims: Tuple[bool, bool, bool, bool], x: int = 0, y: int = 0
) -> arcade.Texture:
    """Wall at a cell: ``face`` when floor lies below it on screen, ``rims`` per side."""
    seed = hash32(x, y, 4) % 3  # three brick layouts so faces are not identical
    key = ("wall", style_name, face, rims if not face else (), seed)
    return _tex(key, lambda: wall_image(style_name, face, rims, seed))


def texture(name: str, style_name: str = "rooms") -> arcade.Texture:
    """Doors and stairs: ``door_locked``, ``door_open``, ``stairs``."""
    if name == "door_locked":
        return _tex(("door", True, style_name), lambda: door_image(True, style_name))
    if name == "door_open":
        return _tex(("door", False, style_name), lambda: door_image(False, style_name))
    if name == "stairs":
        return _tex(("stairs", style_name), lambda: stairs_image(style_name))
    raise KeyError(name)


def portal_frames(frames: int = 4) -> List[arcade.Texture]:
    return [_tex(("portal", i, frames), lambda i=i: portal_image(i, frames)) for i in range(frames)]


__all__ = [
    "PX",
    "STYLES",
    "TIER_TINTS",
    "tint",
    "style_for",
    "hash32",
    "noise",
    "shift",
    "floor_image",
    "wall_image",
    "door_image",
    "stairs_image",
    "portal_image",
    "floor_texture",
    "wall_texture",
    "texture",
    "portal_frames",
]
