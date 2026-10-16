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

PX = 32
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


# --- Floors ------------------------------------------------------------------

def _flagstones(style: Dict[str, RGB], variant: int) -> Image.Image:
    img = Image.new("RGBA", (PX, PX), _rgba(style["floor"]))
    d = ImageDraw.Draw(img)
    grout = _rgba(style["grout"])
    hi = _rgba(style["floor_hi"])
    # Two rows of stones; the second row is offset so joints do not line up
    rows = ((0, 15), (16, 31))
    for ri, (top, bottom) in enumerate(rows):
        offset = (variant * 5 + ri * 11) % 12
        joints = sorted({0, (offset + 13) % PX, (offset + 24) % PX})
        d.line([(0, bottom), (PX - 1, bottom)], fill=grout)
        for jx in joints:
            d.line([(jx, top), (jx, bottom)], fill=grout)
        # Highlight along the top and left edge of every stone
        edges = joints + [PX]
        for a, b in zip(edges, edges[1:]):
            if b - a < 3:
                continue
            d.line([(a + 1, top), (b - 1, top)], fill=hi)
            d.line([(a + 1, top), (a + 1, bottom - 1)], fill=hi)
    _speckle(img, style["floor"], seed=100 + variant)
    if variant % 4 == 3:  # a crack across one stone
        pts = [(4, 20), (9, 24), (13, 23), (17, 27)]
        d.line(pts, fill=grout)
    return img


def _cavern_floor(style: Dict[str, RGB], variant: int) -> Image.Image:
    img = Image.new("RGBA", (PX, PX), _rgba(style["floor"]))
    _speckle(img, style["floor"], seed=200 + variant, amount=0.12, strength=10)
    d = ImageDraw.Draw(img)
    for i in range(3 + variant % 3):  # pebbles
        n = noise(i, variant, 31)
        x, y = int(n * 28) + 2, int(noise(variant, i, 32) * 28) + 2
        d.ellipse([x - 1, y - 1, x + 1, y], fill=_rgba(style["grout"]))
        d.point((x, y - 1), fill=_rgba(style["floor_hi"]))
    return img


def _decal(img: Image.Image, kind: int, style: Dict[str, RGB]) -> None:
    """Small story-telling marks: bones, a skull, moss, a dark stain."""
    d = ImageDraw.Draw(img)
    bone = (214, 208, 190, 255)
    bone_lo = (160, 154, 140, 255)
    if kind == 0:  # crossed bones
        d.line([(9, 22), (22, 11)], fill=bone, width=2)
        d.line([(9, 11), (22, 22)], fill=bone, width=2)
        for x, y in ((8, 10), (23, 10), (8, 23), (23, 23)):
            d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=bone_lo)
    elif kind == 1:  # skull
        d.ellipse([12, 11, 20, 19], fill=bone)
        d.rectangle([14, 18, 18, 21], fill=bone_lo)
        d.point((14, 14), fill=(30, 26, 36, 255))
        d.point((18, 14), fill=(30, 26, 36, 255))
    elif kind == 2:  # moss
        moss = (84, 112, 60, 200)
        for cx, cy, r in ((10, 20, 4), (15, 23, 3), (20, 19, 3), (13, 15, 2)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=moss)
    else:  # dark stain
        stain = _rgba(shift(style["floor"], -0.18, 0.1), 220)
        d.ellipse([8, 12, 24, 24], fill=stain)
        d.ellipse([14, 8, 22, 16], fill=stain)


def _shadow_bands(img: Image.Image, top: bool, left: bool) -> None:
    """Ambient occlusion where a wall stands above (screen-up) or to the left."""
    px = img.load()
    depth = 7
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
    img = _cavern_floor(style, variant) if style_name == "cavern" else _flagstones(style, variant)
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
    up, right, down, left = rims
    if up:
        d.line([(0, 0), (PX - 1, 0)], fill=rim)
        d.line([(0, 1), (PX - 1, 1)], fill=rim_lo)
    if left:
        d.line([(0, 0), (0, PX - 1)], fill=rim)
        d.line([(1, 0), (1, PX - 1)], fill=rim_lo)
    if right:
        d.line([(PX - 1, 0), (PX - 1, PX - 1)], fill=rim_lo)
        d.line([(PX - 2, 0), (PX - 2, PX - 1)], fill=_rgba(style["wall_top_hi"]))
    if down:
        d.line([(0, PX - 1), (PX - 1, PX - 1)], fill=rim_lo)
        d.line([(0, PX - 2), (PX - 1, PX - 2)], fill=_rgba(style["wall_top_hi"]))
    return img


def _wall_face(style: Dict[str, RGB], seed: int, cavern: bool) -> Image.Image:
    """A wall seen from the front: a lit cap, bricks (or rock strata) and a dark foot."""
    img = Image.new("RGBA", (PX, PX), _rgba(style["mortar"]))
    d = ImageDraw.Draw(img)
    cap = 4
    d.rectangle([0, 0, PX - 1, cap - 1], fill=_rgba(style["rim_lo"]))
    d.line([(0, 0), (PX - 1, 0)], fill=_rgba(style["rim"]))
    if cavern:
        y = cap
        band = 0
        while y < PX:
            h = 5 + int(noise(band, seed, 41) * 4)
            tone = shift(style["brick"], (noise(band, seed, 42) - 0.5) * 0.16)
            d.rectangle([0, y, PX - 1, min(PX - 1, y + h - 1)], fill=_rgba(tone))
            d.line([(0, y), (PX - 1, y)], fill=_rgba(shift(tone, 0.08)))
            # a wavy crack between strata
            for x in range(PX):
                if noise(x, band, seed + 43) < 0.25:
                    d.point((x, min(PX - 1, y + h - 1)), fill=_rgba(style["mortar"]))
            y += h
            band += 1
    else:
        brick_h, brick_w = 7, 16
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
                x0, x1 = max(0, x), min(PX - 1, x + brick_w - 2)
                y1 = min(PX - 1, y + brick_h - 2)
                if x1 >= x0:
                    d.rectangle([x0, y, x1, y1], fill=_rgba(tone))
                    d.line([(x0, y), (x1, y)], fill=_rgba(shift(tone, 0.10)))
                    d.line([(x0, y1), (x1, y1)], fill=_rgba(shift(tone, -0.10)))
                    if x >= 0:
                        d.line([(x0, y), (x0, y1)], fill=_rgba(shift(tone, 0.06)))
                x += brick_w
                col += 1
            y += brick_h
            row += 1
    d.line([(0, PX - 1), (PX - 1, PX - 1)], fill=_rgba(shift(style["mortar"], -0.08)))
    return img


def wall_image(
    style_name: str, face: bool, rims: Tuple[bool, bool, bool, bool], seed: int = 0
) -> Image.Image:
    style = STYLES[style_name]
    if face:
        return _wall_face(style, seed, cavern=style_name == "cavern")
    return _wall_top(style, rims, seed)


# --- One-off tiles -----------------------------------------------------------

def door_image(locked: bool, style_name: str = "rooms") -> Image.Image:
    style = STYLES[style_name]
    img = Image.new("RGBA", (PX, PX), _rgba(style["mortar"]))
    d = ImageDraw.Draw(img)
    frame = (70, 48, 30, 255)
    d.rectangle([0, 0, PX - 1, PX - 1], outline=frame)
    d.rectangle([1, 1, PX - 2, PX - 2], outline=(96, 68, 42, 255))
    if locked:
        wood, wood_hi, wood_lo = (142, 96, 52), (166, 118, 70), (104, 68, 36)
        d.rectangle([2, 2, PX - 3, PX - 3], fill=_rgba(wood))
        for px_ in (8, 15, 22):  # planks
            d.line([(px_, 2), (px_, PX - 3)], fill=_rgba(wood_lo))
            d.line([(px_ + 1, 2), (px_ + 1, PX - 3)], fill=_rgba(wood_hi))
        for y in (7, 23):  # iron bands
            d.rectangle([2, y, PX - 3, y + 2], fill=(70, 70, 82, 255))
            d.line([(2, y), (PX - 3, y)], fill=(118, 118, 132, 255))
            for bx in (5, 13, 20, 27):
                d.point((bx, y + 1), fill=(160, 160, 176, 255))
        d.rectangle([13, 13, 18, 18], fill=(222, 184, 70, 255))
        d.rectangle([15, 15, 16, 17], fill=(60, 40, 10, 255))
    else:
        floor = floor_image(style_name, 0)
        img.paste(floor.crop((2, 2, PX - 2, PX - 2)), (2, 2))
        d.rectangle([0, 0, PX - 1, PX - 1], outline=frame)
        d.rectangle([1, 1, PX - 2, PX - 2], outline=(96, 68, 42, 255))
        # open leaf folded against the left jamb
        d.rectangle([2, 2, 5, PX - 3], fill=(142, 96, 52, 255))
        d.line([(3, 2), (3, PX - 3)], fill=(166, 118, 70, 255))
    return img


def stairs_image(style_name: str = "rooms") -> Image.Image:
    """A stairwell cut into the floor, steps fading into darkness."""
    style = STYLES[style_name]
    img = floor_image(style_name, 1)
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, PX - 3, PX - 3], fill=(18, 16, 24, 255))
    d.rectangle([2, 2, PX - 3, PX - 3], outline=_rgba(style["rim_lo"]))
    steps = 6
    for i in range(steps):
        y0 = 4 + i * 4
        inset = 3 + i
        tone = shift((150, 146, 160), -0.14 * i)
        d.rectangle([inset, y0, PX - 1 - inset, y0 + 2], fill=_rgba(tone))
        d.line([(inset, y0), (PX - 1 - inset, y0)], fill=_rgba(shift(tone, 0.12)))
        d.line([(inset, y0 + 3), (PX - 1 - inset, y0 + 3)], fill=(18, 16, 24, 255))
    return img


def portal_image(frame: int, frames: int = 4) -> Image.Image:
    """A rotating teal ring with inner swirl; ``frame`` picks the rotation phase."""
    img = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = PX / 2 - 0.5
    import math
    for r in range(13, 5, -1):
        t = (13 - r) / 8
        tone = (int(40 + 60 * t), int(150 + 90 * t), int(150 + 90 * t), 255)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tone)
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(236, 252, 252, 255))
    d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], outline=(20, 90, 95, 255))
    phase = frame / frames * 2 * math.pi
    for k in range(4):  # swirl sparks around the ring
        ang = phase + k * math.pi / 2
        for rr, size in ((11, 2), (8, 1)):
            x = cx + math.cos(ang + rr * 0.3) * rr
            y = cy + math.sin(ang + rr * 0.3) * rr
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
