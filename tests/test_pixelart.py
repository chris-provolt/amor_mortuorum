"""The pixel art grids are data: check their shape, palette and coverage."""
from amormortuorum.data import GameData
from amormortuorum.ui import pixelart as px

px.Image = px.Image  # PIL module re-exported for the mirror check


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
    data = GameData.load()
    for name in list(data.enemies) + list(px.PARTY):  # every battler is native 32 px
        assert px.grid_size(name) == px.RENDER_PX, name
        assert px.render(name).size == (px.RENDER_PX, px.RENDER_PX)
        assert px.image(name, native=False).size == (px.SIZE, px.SIZE)
    assert px.render("chest").size == (px.RENDER_PX, px.RENDER_PX)
    # the idle frame lifts the body: the top row of frame 1 is what was below it
    a, b = px.render("hero", 0), px.render("hero", 1)
    assert a.getpixel((16, 3)) == b.getpixel((16, 1))
    variants = {px.floor_variant(x, y) for x in range(8) for y in range(8)}
    assert variants == set(px.FLOOR_VARIANTS)


def test_party_sprites_turn_and_walk():
    for name in px.PARTY:
        assert px.has_facings(name)
        down, up, left, right = (px.image(name, facing=f) for f in px.FACINGS)
        assert down.tobytes() != up.tobytes() != left.tobytes()
        assert right.tobytes() == left.transpose(px.Image.FLIP_LEFT_RIGHT).tobytes()
        for facing in px.FACINGS:
            stand = px.render(name, 0, facing)
            a, b = px.render(name, 2, facing), px.render(name, 3, facing)
            assert stand.size == a.size == (px.RENDER_PX, px.RENDER_PX)
            assert a.tobytes() != stand.tobytes() and b.tobytes() != a.tobytes()
            # the lifted foot leaves the bottom row of its half empty
            top, bottom = px.LEG_ROWS
            assert any(a.getpixel((x, bottom - 1))[3] for x in range(px.RENDER_PX))
    assert not px.has_facings("ghoul")
    assert px.render("ghoul", 2).tobytes() != px.render("ghoul", 0).tobytes()  # a walker
    assert px.render("wraith", 2).tobytes() == px.render("wraith", 0).tobytes()  # floats


def test_walk_cycle_and_facing_helpers():
    assert [px.walk_frame(t) for t in (0.0, 0.1, 0.2, 0.3)] == list(px.WALK_CYCLE)
    assert px.walk_frame(0.4) == px.WALK_CYCLE[0]
    assert px.facing_from(1, 0) == "right" and px.facing_from(-1, 0) == "left"
    assert px.facing_from(0, 1) == "up" and px.facing_from(0, -1) == "down"
    assert px.facing_from(0, 0, "left") == "left"


def test_battle_poses_and_weapons():
    for name in px.PARTY:
        assert px.has_poses(name)
        stand = px.render(name, 0, "left")
        raised, strike, cast = (px.render(name, f, "left") for f in (4, 5, 6))
        assert len({img.tobytes() for img in (stand, raised, strike, cast)}) == 4
        # the strike template holds the body back so the blade has room
        assert px.pose_shift(name, 5) == 7 and px.pose_shift(name, 4) == 0
        # an equipped blade appears in the hand; unarmed hands stay empty
        armed = px.render(name, 4, "left", weapon="sword_bone")
        assert armed.tobytes() != raised.tobytes()
        assert armed.getpixel((5, 7))[3] == 255 and raised.getpixel((5, 7))[3] == 0
        thrust = px.render(name, 5, "left", weapon="dagger")
        assert thrust.getpixel((4, 19))[3] == 255 and strike.getpixel((4, 19))[3] == 0
        # mirrored for the right facing, weapon and all
        right = px.image(name, facing="right", frame=5, weapon="dagger")
        assert right.tobytes() == px.image(
            name, facing="left", frame=5, weapon="dagger"
        ).transpose(px.Image.FLIP_LEFT_RIGHT).tobytes()
    assert px.weapon_art(None) is None and px.weapon_art("dagger_rust") == "dagger"
    assert px.weapon_art("blade_mystery") == "sword_bone"
    for kind in px.WEAPONS:
        for direction in ("up", "left"):
            pixels = px.weapon_pixels(kind, direction)
            assert set(pixels.values()) <= set(px.PALETTE)
            assert (0, 0) not in pixels  # the grip is the hand's own
    # monsters lean instead: the strike shifts the upper body right
    assert not px.has_poses("ghoul") and px.pose_shift("ghoul", 5) == 0
    stand, strike = px.render("ghoul", 0), px.render("ghoul", 5)
    assert strike.tobytes() != stand.tobytes()
    assert px.render("ghoul", 4).tobytes() != stand.tobytes()


def test_tile_palettes_change_with_the_floor_tier():
    from amormortuorum.ui import tiles

    assert tiles.style_for("rooms", "T1") == "rooms"
    assert tiles.style_for("nonsense", "T1") == "rooms"
    keys = [tiles.style_for("rooms", t) for t in ("T2", "T3", "T4", "T5")]
    assert keys == ["rooms/T2", "rooms/T3", "rooms/T4", "rooms/T5"]
    assert tiles.style_for("rooms", "T3") == "rooms/T3"  # built once, reused
    palettes = [tiles.STYLES[k] for k in ["rooms"] + keys]
    assert len({p["floor"] for p in palettes}) == 5
    # the deepest tier is darkest, the ossuary warm, the crypt cold
    assert sum(palettes[4]["floor"]) < sum(palettes[0]["floor"])
    rust, crypt = palettes[2]["floor"], palettes[3]["floor"]
    assert rust[0] > rust[2] and crypt[2] > crypt[1]
    floors = [tiles.floor_image(k, 0).getpixel((5, 5)) for k in ["rooms"] + keys]
    assert len(set(floors)) == 5
    cavern = tiles.style_for("cavern", "T4")
    assert tiles.wall_image(cavern, True, (False,) * 4).size == (tiles.PX, tiles.PX)
    tinted, plain = tiles.floor_image(cavern, 1), tiles.floor_image("cavern", 1)
    assert tinted.getpixel((3, 3)) != plain.getpixel((3, 3))
    assert tiles.tint((100, 100, 100), 0.0, 1.0, 0.5, 0.0) != (100, 100, 100)
