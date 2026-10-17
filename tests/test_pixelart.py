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
            assert size == px.SIZE or (native and size in (px.RENDER_PX, px.HD_PX)), (name, size)
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
    img = px.image("chest", 3, native=False)
    assert img.size == (48, 48)
    small = px.image("chest", native=False)
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
    for native in (False, True):
        base = px.hd_grid("humanoid") if native else px.ART["humanoid"]
        for name in px.PARTY:
            g = px.grid(name, native)
            assert len(g) == len(base)
            if native and (name in px.OVERLAYS or name in px.OVERLAY_PATCHES64):
                continue  # a hood or beard is drawn over the body by design
            assert all(a == b or a in px.TEMPLATE_KEYS for a, b in zip(base, g)), name


def test_native_art_renders_without_upscaling_and_shares_the_16px_fallback():
    assert px.grid_size("hero") == px.HD_PX and px.grid_size("chest") == px.HD_PX
    assert px.grid_size("gravestone") == px.SIZE  # graveyard props stay small
    data = GameData.load()
    for name in list(data.enemies) + list(px.PARTY):  # every battler renders at 64 px
        assert px.grid_size(name) == px.HD_PX, name
        assert px.render(name).size == (px.HD_PX, px.HD_PX)
        assert px.image(name, native=False).size == (px.SIZE, px.SIZE)
    assert px.render("chest").size == (px.HD_PX, px.HD_PX)
    assert px.render("gravestone").size == (px.RENDER_PX, px.RENDER_PX)
    # the idle frame bobs the head: a head row of frame 1 is the row below it in
    # frame 0, while the feet stay planted
    a, b = px.render("hero", 0), px.render("hero", 1)

    def close(p, q):  # the volume gradient shifts tones a touch between rows
        return all(abs(i - j) <= 8 for i, j in zip(p, q))

    assert close(a.getpixel((32, 6)), b.getpixel((32, 4)))
    assert a.getpixel((24, 58)) == b.getpixel((24, 58))
    # floaters rise whole
    a, b = px.render("wraith", 0), px.render("wraith", 1)
    assert close(a.getpixel((32, 6)), b.getpixel((32, 2)))
    variants = {px.floor_variant(x, y) for x in range(8) for y in range(8)}
    assert variants == set(px.FLOOR_VARIANTS)


def test_companions_wear_their_own_overlays():
    for who in ("ossian", "sister_vel", "pale_cassia", "brother_moss"):
        assert who in px.OVERLAYS
        for facing in px.FACINGS:
            g = px.grid(who, facing=facing)
            assert len(g.split("\n")) == px.HD_PX
        # the overlay changes the head region beyond a palette swap of the hero
        hero = px.image("hero")
        them = px.image(who)
        differs = sum(1 for x in range(64) for y in range(4, 34)
                      if (hero.getpixel((x, y))[3] == 0) != (them.getpixel((x, y))[3] == 0)
                      or hero.getpixel((x, y)) != them.getpixel((x, y)))
        assert differs > 80, who
    # overlays follow the strike pose's body shift
    strike = px.image("pale_cassia", frame=5, facing="left")
    assert strike.getpixel((40, 4))[3] == 255 and strike.getpixel((26, 4))[3] == 0


def test_party_sprites_turn_and_walk():
    for name in px.PARTY:
        assert px.has_facings(name)
        down, up, left, right = (px.image(name, facing=f) for f in px.FACINGS)
        assert down.tobytes() != up.tobytes() != left.tobytes()
        assert right.tobytes() == left.transpose(px.Image.FLIP_LEFT_RIGHT).tobytes()
        for facing in px.FACINGS:
            stand = px.render(name, 0, facing)
            a, b = px.render(name, 2, facing), px.render(name, 3, facing)
            assert stand.size == a.size == (px.HD_PX, px.HD_PX)
            assert a.tobytes() != stand.tobytes() and b.tobytes() != a.tobytes()
            # the lifted foot leaves the bottom row of its half empty
            k = px.HD_PX // px.RENDER_PX
            bottom = px.LEG_ROWS[1] * k
            assert any(a.getpixel((x, bottom - 1))[3] for x in range(px.HD_PX))
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
        assert armed.getpixel((10, 14))[3] == 255 and raised.getpixel((10, 14))[3] == 0
        thrust = px.render(name, 5, "left", weapon="dagger")
        assert thrust.getpixel((8, 38))[3] == 255 and strike.getpixel((8, 38))[3] == 0
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


def test_every_item_has_an_icon():
    data = GameData.load()
    icons = {px.item_icon(item) for item in data.items.values()}
    assert icons <= set(px.names())
    assert len(icons) >= 10  # flasks, scrolls, weapons, armour pieces, keys, tokens
    assert px.item_icon(data.item("potion_small")) == "icon_potion"
    assert px.item_icon(data.item("tonic_mind")) == "icon_tonic"
    assert px.item_icon(data.item("dagger_rust")) == "icon_dagger"
    assert px.item_icon(data.item("blade_bone")) == "icon_sword"
    assert px.item_icon(data.item("boots_silent")) == "icon_boots"
    assert px.item_icon(data.item("key_catacomb")) == "key"
    assert px.item_icon(data.item("res_token")) == "icon_token"
    for name in icons:
        assert px.image(name).getpixel((0, 0))[3] == 0, name
    assert "icon_flask" not in px.names()


def test_death_dissolve_crumbles_from_the_top_down():
    base = px.render("ghoul")
    early, late = px.dissolve(base, 0.25), px.dissolve(base, 0.8)

    n = base.size[0]

    def alive(img):
        return sum(1 for x in range(n) for y in range(n) if img.getpixel((x, y))[3])

    assert alive(base) > alive(early) > alive(late) > 0
    assert alive(px.dissolve(base, 1.0)) == 0
    # the top rows go first: nothing left in the top quarter at 80 %
    assert all(late.getpixel((x, y))[3] == 0 for x in range(n) for y in range(n // 4))
    # what remains has drained towards grey
    px_late = [late.getpixel((x, y))[:3] for x in range(n) for y in range(n)
               if late.getpixel((x, y))[3]]
    spread = sum(max(c) - min(c) for c in px_late) / len(px_late)
    px_base = [base.getpixel((x, y))[:3] for x in range(n) for y in range(n)
               if base.getpixel((x, y))[3]]
    assert spread < sum(max(c) - min(c) for c in px_base) / len(px_base)
    assert px.dissolve(base, 0.5).tobytes() == px.dissolve(base, 0.5).tobytes()  # deterministic


def test_ghost_hems_are_translucent_and_shading_darkens_downwards():
    wraith = px.render("wraith")
    alphas = {wraith.getpixel((x, y))[3] for x in range(64) for y in range(48, 64)}
    assert any(0 < a < 255 for a in alphas)  # the tattered hem
    skel = px.render("skel_basic")
    assert skel.getpixel((24, 16))[0] > 150  # the eye glows red
    # the same fill colour ends up darker lower down the sprite (volume gradient)
    img = px.Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for y in range(4, 28):
        for x in range(8, 24):
            img.putpixel((x, y), px.PALETTE["e"])
    shaded = px.shade(img)
    assert sum(shaded.getpixel((16, 6))[:3]) > sum(shaded.getpixel((16, 24))[:3])


def test_hd_grids_upscale_cleanly_and_hero_wears_his_gear():
    rows = px.hd_grid("skel_basic").split("\n")
    assert len(rows) == px.HD_PX and all(len(r) == px.HD_PX for r in rows)
    # EPX keeps the letters of the source: nothing new is invented
    source = {ch for r in px.ART32["skel_basic"].split("\n") for ch in r}
    assert {ch for r in rows for ch in r} <= source
    grown = px.epx_rows(["aaaa"] * 3)  # a straight edge stays straight, corners round
    assert len(grown) == 6 and grown[2] == "a" * 8 and grown[0] == ".aaaaaa."
    assert px.apply_patches(["....", "...."], [(1, 0, ("x_",))]) == [".x..", "...."]
    hero = px.image("hero")
    red = px.PALETTE["r"]
    # headband across the brow, cape at the sides, steel plate on the chest
    assert hero.getpixel((30, 14)) == red
    assert hero.getpixel((7, 40)) == red or hero.getpixel((7, 40)) == px.PALETTE["R"]
    assert hero.getpixel((30, 38)) == px.PALETTE["l"]
    back = px.image("hero", facing="up")
    assert back.getpixel((30, 46)) in (red, px.PALETTE["R"])
    # a sprite is still one world tile however fine its texture
    import arcade  # noqa: F401
    assert px.texture("hero").width == px.HD_PX


def test_hd_tiles_are_64_px_and_opaque():
    from amormortuorum.ui import tiles

    assert tiles.PX == 64
    for img in (tiles.floor_image("rooms", 0), tiles.floor_image("cavern", 2, True, True, 1),
                tiles.wall_image("rooms", True, (False,) * 4),
                tiles.wall_image("rooms", False, (True,) * 4),
                tiles.door_image(True), tiles.door_image(False), tiles.stairs_image()):
        assert img.size == (64, 64)
        assert all(img.getpixel((x, y))[3] == 255 for x in range(0, 64, 7) for y in range(0, 64, 7))
    portal = tiles.portal_image(0)
    assert portal.size == (64, 64) and portal.getpixel((0, 0))[3] == 0
    assert portal.getpixel((32, 32))[3] == 255
    # flagstone courses: two-pixel grout lines run across the tile
    floor = tiles.floor_image("rooms", 0)
    grout = tiles.STYLES["rooms"]["grout"]
    for y in (20, 21):  # the grain pass jitters tones a little
        assert all(abs(a - b) <= 8 for a, b in zip(floor.getpixel((10, y))[:3], grout))


def test_ambient_fx_are_deterministic_and_bounded():
    from amormortuorum.ui import fx

    assert fx.jitter(3, 1) == fx.jitter(3, 1) and 0 <= fx.jitter(3, 1) < 1
    values = [fx.flicker(t / 10, 2) for t in range(600)]
    assert 0.6 < min(values) < 1.0 < max(values) < 1.1
    assert fx.light_pulse(0.0, 0.0) == 0.5
    assert fx.tint((200, 100, 50), 0.5) == (100, 50, 25)
    assert px.render("sconce").size == (px.HD_PX, px.HD_PX)
