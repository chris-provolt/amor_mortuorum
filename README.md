# Amor Mortuorum
_A re-imagining of Lufia II's Ancient Cave as a modern, dark roguelite built with Python + Arcade._

> **Scope:** Action on the map with **turn-based, FF1-style combat**, a **Graveyard** hub, a **99-floor** procedurally generated dungeon, **Relics of the Veil** (9+1 meta collectibles), and a **Crypt** that stores up to 3 items persistently. **Graveyard access is not constant**: a **portal** may spawn on each floor with a **decreasing chance by depth**.

---

## Current status: playable vertical slice

What works today, end to end:

- Title screen with **New Run** / **Continue** / **Quit**.
- **Graveyard hub**: rest, 3-slot **Crypt** (deposit/withdraw, persists across runs), and the stairs down. Entering the Graveyard writes the save.
- **Dungeon floors**: BSP rooms and corridors generated from `(seed, floor)`, tile movement, chests with depth-scaled loot or gold, stairs to the next floor, and the depth-decaying **portal** back to the Graveyard.
- **Random encounters** that open **turn-based combat**: Attack / Item / Defend / Flee, SPD-ordered turns, a combat log, target cycling.
- **Death**: a carried **Resurrection Token** is consumed and the party wakes in the Graveyard; without one the run ends and meta progression (Crypt, relics, deepest floor) persists.
- Deterministic replays: the same `--seed` produces the same floors, chests and encounters.

Not yet built (see [Roadmap](#roadmap)): shop UI, equipment screen, traps/doors/keys, fog of war and minimap, mini-bosses and the final boss, relic drops and the collection screen, XP curve and levelling, audio, settings screen, controller support.

---

## Table of Contents
- [High-Level Pitch](#high-level-pitch)
- [Core Features](#core-features)
- [Game Loop](#game-loop)
- [World Structure](#world-structure)
- [Combat](#combat)
- [Items, Loot & Economy](#items-loot--economy)
- [Relics of the Veil (Meta Progression)](#relics-of-the-veil-meta-progression)
- [Procedural Generation](#procedural-generation)
- [Portals to Graveyard (Depth-Scaling)](#portals-to-graveyard-depth-scaling)
- [UI/UX](#uiux)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Files & Schemas](#data-files--schemas)
- [Save System](#save-system)
- [Build & Run](#build--run)
- [Testing & Determinism](#testing--determinism)
- [Contribution Workflow](#contribution-workflow)
- [Roadmap](#roadmap)
- [License](#license)

---

## High-Level Pitch
**Amor Mortuorum** is a 2D top-down roguelite dungeon crawler with **99 descending floors**. Players begin each run at level 1 in a **Graveyard** hub where they can rest and purchase limited supplies. A **Crypt** lets them bank up to **3 items** between runs. Floors are procedurally generated with rooms, corridors, traps, chests, and occasional **portals** that lead back to the Graveyard. **Mini-bosses** appear at floors **20/40/60/80** and a **Final Boss** awaits at **B99**. Between runs, players chase the 9 + 1 **Relics of the Veil** to complete the meta collection.

## Core Features
- **Graveyard hub:** Rest (heal), purchase potions/scrolls, manage the **Crypt** (3 persistent slots).
- **Turn-based combat (FF1-style):** Classic menu (Attack / Skill(Scroll) / Item / Defend / Flee). Turn order by **SPD**.
- **Dungeon (99 floors):** BSP rooms + corridors (option for caverns), with **traps**, **chests**, and **boss gates**.
- **Chests:** Single "theme" with **variable quality** by depth; items are data-driven.
- **Relics of the Veil:** 9 relics + a final one for the deepest boss; persist across runs.
- **Resurrection Token:** If carried at death, **revive** at Graveyard and consume the token.
- **Portals to Graveyard:** Random chance per floor, **rarer deeper down** (configurable curve).
- **Minimap & Fog of War:** Auto-map explored areas; icons for stairs, chests, portals.

## Game Loop
1. **Graveyard:** Rest, buy supplies, optionally manage the **Crypt**.
2. **Descend:** Explore the floor, avoid traps, open chests, fight encounters.
3. **Portal (if spawned):** Optionally return to the **Graveyard** to heal and bank items.
4. **Miniboss floors 20/40/60/80:** Defeat to unlock the stairs.
5. **Final Boss (B99):** Win the run and obtain the **final relic**.
6. **Death:** With a **Resurrection Token**, revive at the Graveyard; otherwise the run ends. Meta progression (relics + crypt) persists.

## World Structure
- **Graveyard (hub):** Menu-based UI: Enter Dungeon, Rest, Crypt, Purchase, Quit.
- **Dungeon:** Procedurally generated grid (tile size **32px**). Floor tiers: 1-20, 21-40, 41-60, 61-80, 81-99.
- **Mini-boss floors:** 20/40/60/80; stairs are locked until the miniboss is defeated.
- **Final boss:** **The Oblivion Heart** at B99 (multi-phase).

## Combat
- **Style:** Turn-based, menu-driven, classic JRPG feel.
- **Actions:** Attack, Skill(Scroll), Item, Defend, Flee.
- **Turn Order:** Per round, sort all living battlers by **SPD** (descending). Ties break deterministically (players first, then index).
- **Damage:** `dmg = max(1, atk - df + small_rng)`; defending halves incoming damage; defeat sets HP to 0. Items apply immediately: potions heal, scrolls deal flat damage.
- **Flee:** `clamp(0.5 + 0.05 * (party_spd - max_enemy_spd), 0.1, 0.9)`.
- **Party:** 1-4 members (the slice plays solo). Enemy formations vary by floor tier.

## Items, Loot & Economy
- **Equip Slots:** `weapon, armor, helm, shield, accessory`.
- **Consumables:** Potions (heal), Scrolls (damage), Keys (open doors, planned).
- **Token:** **Resurrection Token**: revive at the Graveyard on death, consume the token.
- **Chests:** Depth-based **quality weights**; a quarter of chests hold gold instead.
- **Gold:** Dropped from fights and chests; used at the shop (limited stock per visit).

## Relics of the Veil (Meta Progression)
- **Set:** 9 relics + **Final Relic** ("**Heart of Oblivion**").
- **Persistence:** Stored in the meta save; completion survives across runs.
- **Names:** Lamplight of the Veil, Thorn of Epitaph, Obol of Passage, Votive Ashes, Mortis Dial, Widow's Knot, Catacomb Key, Lacrimosa Phial, Ossuary Crown, **Heart of Oblivion**.

## Procedural Generation
- **Algorithm:** BSP split into leaves, one room per leaf, L-shaped corridors joining sibling subtrees; the whole floor is connected.
- **Features:** Start room, stairs in the room farthest from the start, 1-5 chests scaling with depth, and a portal on a chance roll.
- **Determinism:** Floor layout derives from `floor_rng(seed, floor)`; chest contents from `chest_rng(seed, floor)`; encounters and each battle from named streams (see [Testing & Determinism](#testing--determinism)).

## Portals to Graveyard (Depth-Scaling)
- **Design:** Players cannot always warp out; a portal may spawn **randomly** on each floor. **Deeper = rarer**.
- **Formula** (`systems/procgen.py`):
  ```py
  PORTAL_BASE_CHANCE = 0.30     # 30% on Floor 1
  PORTAL_DECAY       = 0.985    # multiplicative decay per floor
  PORTAL_MIN_CHANCE  = 0.02     # floor at 2%
  # chance(floor) = max(PORTAL_MIN_CHANCE, PORTAL_BASE_CHANCE * (PORTAL_DECAY ** (floor-1)))
  ```
- **Placement:** A room interior cell outside the start room (and usually the stairs room).
- **Rendering:** Portals are teal, stairs white, chests gold.

## UI/UX
- **HUD:** HP, level, gold, floor, seed, and a three-line message log.
- **Menus:** Title, Graveyard hub, crypt sub-menu, combat command menu, pause menu, run summary.
- **Controls (default, rebindable in `config/default_settings.json`):**
  - **Movement / menu cursor:** Arrow Keys / WASD
  - **Confirm / interact (stairs, portal):** Enter / Space
  - **Back / pause:** Esc
  - **Combat target:** Left / Right
- **Planned:** screen-shake and colourblind toggles, font scaling, controller support, minimap toggle (`M`).

## Tech Stack
- **Language:** Python **3.10+** (tested on 3.11 and 3.13)
- **Renderer/UI:** [Arcade 3.3+](https://api.arcade.academy/)
- **Assets:** Placeholder solid-colour sprites; art and audio are not yet part of the project
- **Packaging:** PyInstaller via `tools/ci/build_binary.py` (tagged releases)

---

## Project Structure
```
src/amormortuorum/
├── __main__.py            # python -m amormortuorum
├── cli.py                 # argument parsing, headless env, app start
├── app.py                 # GameApp(arcade.Window): scene stack, input, shared state
├── errors.py              # domain exceptions
├── config/default_settings.json
├── core/
│   ├── context.py         # GameContext: settings, save manager, data, meta, run, seed
│   ├── input.py           # action-based key mapping
│   ├── settings.py        # JSON settings with user overrides
│   └── scenes/            # BaseScene + stack-based SceneManager (arcade-free)
├── data/                  # JSON content + GameData loader/validator
│   ├── items.json  enemies.json  loot_tables.json  floor_tiers.json
│   └── relics.json  encounters.json  shop.json
├── systems/               # pure-Python game rules (no arcade)
│   ├── rng.py             # seeded streams
│   ├── procgen.py         # BSP floors, portal chance
│   ├── loot.py            # chest quality / item / gold rolls
│   ├── entities.py        # Stats, Equipment, Inventory, Player, Enemy
│   ├── combat.py          # Battle: actions, turn order, damage, outcome
│   ├── encounters.py      # step rolls and formations
│   ├── run.py             # Run state, death/resurrection, persistence bridge
│   ├── hub.py  shop.py  crypt.py
├── persistence/           # SaveManager, SaveGame/MetaState/RunState, atomic writes
├── ui/                    # VerticalMenu model + MenuView, Hud
└── scenes/                # boot, main_menu, graveyard, dungeon, combat, run_summary
tests/                     # pytest; GL-marked tests open a window (opt-in)
tools/ci/build_binary.py   # PyInstaller one-file build
docs/                      # design notes per epic, CI, save system
```

---

## Data Files & Schemas
All content lives in `src/amormortuorum/data/*.json` and is validated at boot by `GameData.load()`; a typo fails fast with a `DataError`.

### `items.json` (excerpt)
```json
[
  {"id":"res_token","name":"Resurrection Token","quality":"Epic","type":"token","revive":true,"max_stack":3},
  {"id":"potion_small","name":"Grave-Touched Draught","quality":"Common","type":"potion","hp_restore":15},
  {"id":"scroll_embers","name":"Scroll of Embers","quality":"Common","type":"scroll","damage":10},
  {"id":"blade_bone","name":"Bone Shard Blade","quality":"Uncommon","type":"weapon","atk":3,"stackable":false},
  {"id":"armor_shroud","name":"Shroudmail","quality":"Rare","type":"armor","df":4,"stackable":false},
  {"id":"ring_mourning","name":"Ring of Mourning","quality":"Epic","type":"accessory","spd":2,"stackable":false}
]
```
Fields: `id, name, type, quality` (Common/Uncommon/Rare/Epic), `stackable, max_stack, hp_restore, damage, atk, df, spd, max_hp, revive`. Equipment types are `weapon, armor, helm, shield, accessory`.

### `loot_tables.json`
Weights per **tier** used by chests to pick a quality bucket.
```json
{
  "T1": {"quality_weights": {"Common":60, "Uncommon":30, "Rare":9, "Epic":1}},
  "T5": {"quality_weights": {"Common":10, "Uncommon":35, "Rare":40, "Epic":15}}
}
```

### `floor_tiers.json`
```json
[{"name":"T1","start":1,"end":20}, {"name":"T2","start":21,"end":40}, {"name":"T3","start":41,"end":60},
 {"name":"T4","start":61,"end":80}, {"name":"T5","start":81,"end":99}]
```

### `enemies.json` (excerpt)
```json
[
  {"id":"skel_basic","name":"Skeletal Thrall","hp":12,"mp":0,"atk":5,"df":2,"spd":4,"behavior":"chase","xp":6,"gold":4},
  {"id":"wraith","name":"Wraith","hp":9,"mp":6,"atk":6,"df":1,"spd":6,"behavior":"ranged","xp":7,"gold":5}
]
```

### `encounters.json` (excerpt)
```json
{"T1": {"step_chance": 0.05,
        "formations": [{"enemies": ["skel_basic"], "weight": 6},
                       {"enemies": ["skel_basic", "wraith"], "weight": 2}]}}
```
Per step the chance is `min(0.35, step_chance * (1 + 0.1 * steps_since_last_encounter))`.

### `relics.json`
Ten entries `{"id":"veil_1".."veil_9" | "veil_final", "name", "desc"}`.

### `shop.json`
`{"potion_small": {"price": 20, "qty_range": [2, 5]}, ...}`; stock per Graveyard visit is drawn from `(meta_seed, hub_cycle)`.

---

## Save System
- **Location:** per-profile folder under the platform data dir (`%APPDATA%\AmorMortuorum\profiles\<profile>` on Windows, `~/Library/Application Support/AmorMortuorum` on macOS, `~/.local/share/amormortuorum` on Linux). Choose a profile with `--profile`.
- **Files:** `meta.json` (relics, crypt, hub cycle, lifetime stats) and `run.json` (floor, seed, party, inventory). Writes are atomic with a `.bak` copy and corruption recovery.
- **Rules:** A full save (meta + run) is written only in the **Graveyard**. In the dungeon only meta changes are saved. **Continue** resumes at the Graveyard on the floor you were about to enter. Dying without a token clears the run and keeps meta.
- **Schema:** versioned (`schema_version`) with a migration hook in `persistence/codec.py`.

---

## Build & Run
```bash
# 1) Create and activate a venv
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: . .venv/bin/activate

# 2) Install the game plus dev tools
pip install -e ".[dev]"

# 3) Play
python -m amormortuorum            # or simply: amor
python -m amormortuorum --seed 1234 --profile alt --debug
python -m amormortuorum --settings my_settings.json
```

Flags: `--seed N` (reproducible run), `--profile NAME` (separate saves), `--settings PATH` (JSON overrides), `--debug`, `--smoke FRAMES` (boot, start a run, render the first floor, exit; used by CI). `AMOR_HEADLESS=1` enables Arcade's headless mode, which needs EGL and only works on Linux.

**Requirements:** `arcade>=3.3,<4`, Python 3.10+. Windows, macOS and Linux.

---

## Testing & Determinism
- **Seeds:** all randomness in a run derives from one seed:
  - `floor_rng(seed, floor) = Random(seed + floor * 1013)` (layout, chests placement, portal roll)
  - `chest_rng(seed, floor) = Random(seed + floor * 13)` (chest contents)
  - `stream_rng(seed, floor, name)` for `encounters` and `combat:<n>` streams
- **Unit tests** (`pytest`, no window needed): data validation, rng, procgen (determinism, connectivity, portal rate), loot distributions, entities, combat rules, encounters, run/death rules, hub/shop/crypt, persistence, settings, input, scene stack, menu model, and guards that scenes never import `random` and systems never import `arcade`.
- **GL tests** (`AMOR_GL_TESTS=1 pytest -m gl`): open a real window and script a playthrough with synthetic key presses: menu, Graveyard, walking, chests, encounters, stairs, pause, and both death paths.
- **Lint:** `flake8 .` (max line 100, bugbear enabled).

---

## Contribution Workflow
1. Branch from `main`; CI runs flake8 and pytest on Python 3.11 and 3.13 for every PR.
2. Keep game rules in `systems/` and content in `data/*.json`; scenes stay thin and never roll their own randomness.
3. Add a unit test next to any new rule; add a GL test only when a scene changes behaviour.
4. Tagged pushes (`v*`) build one-file binaries for the three platforms (see `docs/ci.md`).

---

## Roadmap
Design notes for each epic live in `docs/epics/`. Rough order after the slice:
1. Shop UI in the Graveyard (service and data already exist).
2. Equipment and inventory screen (`Equipment.equip` already aggregates stats).
3. XP curve and levelling; party of up to four.
4. Traps, locked doors and keys in procgen.
5. Fog of war and minimap.
6. Mini-bosses at 20/40/60/80 with locked stairs; final boss at B99.
7. Relic drops, collection screen, final relic award, relic passives.
8. Scrolls as skills, audio, settings screen, controller support, save-and-quit mid-run.

---

## License
TBD. (During development, assume **source-available for contributors** and **no redistribution of third-party assets**. Replace this section before release.)

---

### Credits / Notes
- Inspired by the **Ancient Cave** concept from _Lufia II: Rise of the Sinistrals_ (1995). This is an **original** work re-imagining the idea, not a recreation of any proprietary assets.
- Title, theme, and narrative by the project owner.
