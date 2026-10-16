"""The pixel art grids are data: check their shape, palette and coverage."""
from amormortuorum.data import GameData
from amormortuorum.ui import pixelart as px


def test_every_sprite_is_a_square_grid_of_palette_colours():
    assert len(px.names()) >= 40
    for name in px.names():
        for native in (False, True):
            rows = px.grid(name, native).split("\n")
            size = len(rows)
            assert size == px.SIZE or (native and size == px.RENDER_PX), (name, size)
            assert all(len(r) == size for r in rows), name
        rows = px.grid(name).split("\n")
        used = {ch for r in rows for ch in r}
        assert used <= set(px.PALETTE), name
        assert not (used & (set(px.TEMPLATE_KEYS) - set(px.PALETTE))), name


def test_tiles_are_opaque_and_characters_have_transparent_corners():
    for name in px.TILES:
        img = px.image(name)
        assert all(img.getpixel((x, y))[3] == 255 for x in range(16) for y in range(16)), name
    for name in px.PARTY + ("skel_basic", "wraith", "chest", "key"):
        assert px.image(name).getpixel((0, 0))[3] == 0, name


def test_image_scales_with_nearest_neighbour():
    img = px.image("chest", 3)
    assert img.size == (48, 48)
    small = px.image("chest")
    assert img.getpixel((7 * 3 + 1, 7 * 3 + 1)) == small.getpixel((7, 7))


def test_every_enemy_companion_and_boss_has_its_own_art():
    data = GameData.load()
    for enemy in data.enemies.values():
        assert px.enemy_sprite_name(enemy.id) == enemy.id, enemy.id
    for cid in data.companions:
        assert px.party_sprite_name(cid) == cid, cid
    assert px.party_sprite_name(None) == "hero"
    assert px.enemy_sprite_name("dragon") == "skel_basic"


def test_remaps_only_touch_template_letters_and_floor_variants_vary():
    for native, table in ((False, px.ART), (True, px.ART32)):
        base = table["humanoid"]
        for name in px.PARTY:
            g = px.grid(name, native)
            assert len(g) == len(base)
            assert all(a == b or a in px.TEMPLATE_KEYS for a, b in zip(base, g)), name


def test_native_art_renders_without_upscaling_and_shares_the_16px_fallback():
    assert px.grid_size("hero") == px.RENDER_PX and px.grid_size("chest") == px.SIZE
    for name in ("hero", "skel_basic", "ghoul", "wraith", "grave_hound", "bone_guard",
                 "revenant", "warden_of_ash"):
        assert px.grid_size(name) == px.RENDER_PX, name
        assert px.render(name).size == (px.RENDER_PX, px.RENDER_PX)
        assert px.image(name, native=False).size == (px.SIZE, px.SIZE)
    assert px.render("chest").size == (px.RENDER_PX, px.RENDER_PX)
    # the idle frame lifts the body: the top row of frame 1 is what was below it
    a, b = px.render("hero", 0), px.render("hero", 1)
    assert a.getpixel((16, 3)) == b.getpixel((16, 1))
    variants = {px.floor_variant(x, y) for x in range(8) for y in range(8)}
    assert variants == set(px.FLOOR_VARIANTS)
