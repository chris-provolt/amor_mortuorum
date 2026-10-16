# Amor Mortuorum
_A re-imagining of Lufia II's Ancient Cave as a modern, dark roguelite built with Python + Arcade._

> **Scope:** Action on the map with **turn-based, FF1-style combat**, a **Graveyard** hub, a **99-floor** procedurally generated dungeon, **Relics of the Veil** (9+1 meta collectibles), and a **Crypt** that stores up to 3 items persistently. **Graveyard access is not constant**: a **portal** may spawn on each floor with a **decreasing chance by depth**.

---

## Current status: playable vertical slice

What works today, end to end:

- Title screen with **New Run** / **Continue** / **Quit**.
- **Graveyard hub**: rest, a limited-stock **Shop** that restocks each visit, a 3-slot **Crypt** (deposit/withdraw, persists across runs), and the stairs down. Entering the Graveyard writes the save.
- **Bag & Equipment** screen (Tab anywhere): equip and unequip the five slots, use potions outside combat, see effective stats and XP to the next level.
- **XP and levelling** from a data-driven curve (`xp_curve.json`): stats grow per level, speed every third level.
- **Dungeon floors**: BSP rooms and corridors generated from `(seed, floor)`, tile movement, chests with depth-scaled loot or gold, stairs to the next floor, and the depth-decaying **portal** back to the Graveyard.
- **Hazards**: hidden one-shot **spike and dart traps** that scale with depth, and from floor 2 some floors **lock the stairs room** behind doors whose **Catacomb Key** is hidden elsewhere on the floor.
- **Fog of war and minimap**: shadowcast line of sight (walls and locked doors block), remembered tiles drawn dimmed, and a toggleable minimap (M) with icons for stairs, chests, portals, keys and sprung traps you have seen.
- **Bosses**: mini-bosses guard the stairs on B20/40/60/80 (each drops a Relic of the Veil), and **The Oblivion Heart** waits on B99; beating it awards the final relic and ends the run in victory. Bosses enrage below half HP.
- **Relics of the Veil**: the five non-boss relics turn up in chests (2% of chests on T1 up to 8% on T5), the collection screen lives on the title and in the Graveyard, and every relic grants a light passive (ATK/DEF/SPD, sight radius, gold or XP percent) that applies to every future run.
- **Wandering monsters** roam each floor in plain sight, and each group behaves by its kind. **Hunters** (triangles) wander until they spot the party, then hunt them down corridors with grid pathfinding (slow ones only move every other step, so a quick party can outrun them). **Guards** (squares) stand watch beside a chest, key or the stairs, give chase only when the party comes close, and return to their post after a short pursuit. **Skittish** groups (diamonds) keep their distance and run when seen; corner one and it drops a gold bounty on top of the usual rewards. Some hunters and skittish groups start asleep and only wake when the party comes within two tiles in plain sight, so they can be slipped past or struck first. Monsters react to each other: a roused guard bellows and idle hunters within earshot join the chase, a hunter that spots you howls for its kin, and the din of a battle or a sprung trap wakes sleepers and draws hunters to investigate. Bumping into one, or being caught, opens **turn-based combat**: Attack / Skill / Item / Defend / Flee, SPD-ordered turns, a combat log, target cycling. Fleeing dazes the monster for a few steps. Rare ambushes still lunge from the dark.
- **Death**: a carried **Resurrection Token** is consumed and the party wakes in the Graveyard; without one the run ends and meta progression (Crypt, relics, deepest floor) persists.
- **Skills**: six spells learned by level (`skills.json`) and cast for MP from the combat Skill menu: single-target, all-enemy, and healing. Resting and the Tonic of Clear Mind restore MP.
- **Party of up to four**: recruit companions at the Graveyard for gold; they level with you, share the leader's bag and gold, carry their own equipment, act in SPD order, and every survivor earns full XP. Heals target the most wounded ally.
- **Audio**: named sound hooks (menus, steps, chests, combat, level-ups, relics, bosses) and ambient loops for the Graveyard, dungeon and combat. Placeholder tones are synthesized with the standard library on first run; drop real `.wav` files into `resources/audio/` to replace them.
- **Settings screen** (title menu and pause menu): fullscreen, music and SFX volume, VSync, a view of the key bindings, and Save to a per-user `settings.json` that the game loads automatically.
- **Controller support**: any pyglet-recognised gamepad, hot-pluggable. D-pad or left stick moves, A confirms, B cancels, Y opens the bag, X toggles the map, Start pauses.
- **Records and achievements**: lifetime counters (runs, deaths, floors, battles, chests, gold, steps) with fourteen data-driven achievements (`achievements.json`) announced on the HUD when unlocked.
- **Profiles**: switch or create save profiles from the title menu; the choice is remembered in `settings.json` and `--profile` still overrides it.
- **Save & Quit** from the pause menu: a one-shot mid-run save that resumes at the start of the current floor and is consumed on load.
- Deterministic replays: the same `--seed` produces the same floors, chests and encounters.

Every epic from the original design has a first implementation. See [Roadmap](#roadmap) for what would make it a finished game.

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
- **Actions:** Attack, Skill (MP spells learned by level), Item, Defend, Flee.
- **Turn Order:** Per round, sort all living battlers by **SPD** (descending). Ties break deterministically (players first, then index).
- **Damage:** `dmg = max(1, atk - df + small_rng)`; defending halves incoming damage; defeat sets HP to 0. Items apply immediately: potions heal, scrolls deal flat damage. Skills deal `damage + level` ignoring DEF, or heal an ally, and cost MP.
- **Flee:** `clamp(0.5 + 0.05 * (party_spd - max_enemy_spd), 0.1, 0.9)`.
- **Party:** 1-4 members; companions are hired in the Graveyard (`companions.json`). Enemy formations vary by floor tier.

## Items, Loot & Economy
- **Equip Slots:** `weapon, armor, helm, shield, accessory`.
- **Consumables:** Potions (heal), Scrolls (damage), Keys (open doors, planned).
- **Token:** **Resurrection Token**: revive at the Graveyard on death, consume the token.
- **Chests:** Depth-based **quality weights**; a quarter of chests hold gold instead.
- **Gold:** Dropped from fights and chests; used at the shop (limited stock per visit).

## Relics of the Veil (Meta Progression)
- **Set:** 9 relics + **Final Relic** ("**Heart of Oblivion**").
- **Sources:** four from the mini-bosses, the final one from The Oblivion Heart, five from rare chest finds.
- **Passives:** each relic adds a small permanent bonus (see `relics.json`); totals show on the collection screen.
- **Persistence:** Stored in the meta save; completion survives across runs.
- **Names:** Lamplight of the Veil, Thorn of Epitaph, Obol of Passage, Votive Ashes, Mortis Dial, Widow's Knot, Catacomb Key, Lacrimosa Phial, Ossuary Crown, **Heart of Oblivion**.

## Balance Model
- **Enemies scale per floor** (`balance.json`): ATK +0.45, DEF +0.15, HP +2.5%, XP and gold +3% per floor below B1. Tier bases in `enemies.json` are the stats at B1 and rise gently across tiers; depth does the rest.
- **Players** gain +6 HP, +1 MP and +1 ATK per level, +1 DEF every second level and +1 SPD every third (`xp_curve.json`, 40 levels). The stairs restore 10% HP and 15% MP on every descent.
- **Encounters**: each floor spawns `monsters_base` roaming groups (+`monsters_per_floor` per floor of depth, jittered by one) at least 10 steps from the start, drawn from the tier's formations; the floor slowly respawns groups out of sight while under strength. Ambushes add a small per-step chance (the tier's `step_chance`, 1-2%, growing 5% per quiet step, capped at 20%). Together that is roughly 4-6 fights per floor.
- **Measured with** `python tools/balance/simulate.py --runs 80 --party N`, which plays whole runs with an auto-policy, walking every floor tile by tile against the real monster rules. Current numbers: solo runs end around B20-35 (the Warden on B20 is the first wall) with a couple of escapes per run, pairs around B40 with a long tail to B80, full parties reach the mid-nineties and clear B99 only a few percent of the time at most. Re-run it after touching any number.

## Procedural Generation
- **Algorithms:** BSP split into leaves, one room per leaf, L-shaped corridors joining sibling subtrees; the whole floor is connected. From B6, 30% of floors are **cellular-automata caverns** instead: one connected open region with the stairs at the far end of the cave (no rooms, so no key doors).
- **Features:** Start room, stairs in the room farthest from the start, 1-5 chests scaling with depth, a portal on a chance roll, 0-4 hidden traps, and (35% of floors from B2) locked doors on every entrance of the stairs room with a key placed somewhere still reachable.
- **Determinism:** Floor layout derives from `floor_rng(seed, floor)`; chest contents from `chest_rng(seed, floor)`; encounters and each battle from named streams (see [Testing & Determinism](#testing--determinism)).

## Portals to Graveyard (Depth-Scaling)
- **Design:** Players cannot always warp out; a portal may spawn **randomly** on each floor. **Deeper = rarer**.
- **Formula** (`systems/procgen.py`):
  ```py
  PORTAL_BASE_CHANCE = 0.30     # 30% on Floor 1
  PORTAL_DECAY       = 0.99     # multiplicative decay per floor
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
  - **Bag & Equipment:** Tab (Left / Right switches party member)
  - **Minimap toggle:** M (red markers show monsters currently in sight, shaped by kind: triangle hunter, hollow square guard, diamond skittish; on the floor, dull markers sleep, red ones idle, bright red ones are hunting you and amber ones are running away)
  - **Controller:** D-pad / left stick move, A confirm, B back, Y bag, X map, Start pause
  - **Combat target:** Left / Right
- **Accessibility:** minimap icons are shape-coded as well as coloured (hollow square stairs, filled square chest, ring portal, diamond key, cross trap, dot player); a **UI scale** setting (80-160%) resizes every menu and panel; keys can be **rebound in-game** from Settings. Planned: a screen-shake toggle once effects exist.

## Tech Stack
- **Language:** Python **3.10+** (tested on 3.11 and 3.13)
- **Renderer/UI:** [Arcade 3.3+](https://api.arcade.academy/)
- **Assets:** Placeholder solid-colour sprites and synthesized placeholder audio; real art and sound can be dropped in under `resources/`
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
│   ├── audio.py           # AudioManager: sfx/music hooks, synthesized placeholders
│   ├── controller.py      # gamepad -> actions (pyglet ControllerManager)
│   ├── input.py           # action-based key mapping
│   ├── settings.py        # JSON settings with user overrides
│   └── scenes/            # BaseScene + stack-based SceneManager (arcade-free)
├── data/                  # JSON content + GameData loader/validator
│   ├── items.json  enemies.json  loot_tables.json  floor_tiers.json
│   ├── relics.json  encounters.json  shop.json  xp_curve.json
│   ├── bosses.json  skills.json  companions.json
│   └── balance.json  achievements.json
├── systems/               # pure-Python game rules (no arcade)
│   ├── rng.py             # seeded streams
│   ├── procgen.py         # BSP floors, portal chance
│   ├── loot.py            # chest quality / item / gold rolls
│   ├── entities.py        # Stats, Equipment, Inventory, Player, Enemy
│   ├── combat.py          # Battle: actions, turn order, damage, outcome
│   ├── encounters.py      # ambush rolls and formations
│   ├── monsters.py        # roaming groups: hunters, guards, skittish; chase, noise, rally
│   ├── run.py             # Run state, death/resurrection, persistence bridge
│   ├── progression.py     # XP curve, level-ups
│   ├── fov.py             # shadowcasting field of view, explored memory
│   ├── relics.py          # relic passives and collection rows
│   ├── party.py           # recruiting, shared bag, most-wounded targeting
│   ├── stats.py           # lifetime counters and achievement checks
│   ├── hub.py  shop.py  crypt.py
├── persistence/           # SaveManager, SaveGame/MetaState/RunState, atomic writes
├── ui/                    # VerticalMenu model + MenuView, Hud, Minimap
├── resources/audio/       # optional real .wav assets (override placeholders)
└── scenes/                # boot, main_menu, graveyard, dungeon, combat, inventory, relics,
                           #   records, profiles, settings, run_summary
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
`step_chance` is the ambush rate; most fights come from the visible wandering monsters, which draw their groups from the same `formations` list. A formation's map behaviour defaults to its lead enemy's combat `behavior` (`chase` hunts, `tank` guards, `ranged` is skittish) and can be overridden with `"behaviour": "hunter" | "guard" | "skittish"`. Per step the ambush chance is `min(encounter_cap, step_chance * (1 + encounter_growth_per_step * steps_since_last))`.

### `relics.json`
Ten entries `{"id":"veil_1".."veil_9" | "veil_final", "name", "desc", "passive": {...}}`. Passive keys: `atk, df, spd, fov, gold_pct, xp_pct`. Relics referenced by `bosses.json` are boss-only; the rest can drop from chests.

### `skills.json`
```json
[{"id": "ember", "name": "Ember", "mp": 3, "damage": 12, "target": "enemy", "learn_level": 1},
 {"id": "mend", "name": "Mend", "mp": 4, "heal": 20, "target": "ally", "learn_level": 2}]
```
Targets: `enemy`, `all_enemies`, `ally`. Exactly one of `damage` or `heal`.

### `companions.json`
`{"id": "ossian", "name": "Ossian", "cost": 60, "desc": "...", "stats": {"max_hp": 55, "max_mp": 2, "atk": 9, "df": 4, "spd": 3}}`; recruits are levelled to the leader's XP.

### `bosses.json`
```json
{"20": {"name": "The Warden of Ash", "enemies": ["warden_of_ash"], "relic_id": "veil_3"},
 "99": {"name": "The Oblivion Heart", "enemies": ["oblivion_heart"], "relic_id": "veil_final", "final": true}}
```
Boss enemies carry `"boss": true` and an `"enrage"` ATK bonus that switches on below half HP.

### `shop.json`
`{"potion_small": {"price": 20, "qty_range": [2, 5]}, ...}`; stock per Graveyard visit is drawn from `(meta_seed, hub_cycle)`.

---

## Save System
- **Location:** per-profile folder under the platform data dir (`%APPDATA%\AmorMortuorum\profiles\<profile>` on Windows, `~/Library/Application Support/AmorMortuorum` on macOS, `~/.local/share/amormortuorum` on Linux). Choose a profile with `--profile`.
- **Files:** `meta.json` (relics, crypt, hub cycle, lifetime stats) and `run.json` (floor, seed, party, inventory). Writes are atomic with a `.bak` copy and corruption recovery.
- **Rules:** A full save (meta + run) is written only in the **Graveyard**. In the dungeon only meta changes are saved, except **Save & Quit** from the pause menu, which writes a one-shot mid-run save. **Continue** resumes at the Graveyard on the floor you were about to enter, or at the start of the saved floor after a Save & Quit (that save is cleared as soon as it loads). Dying without a token clears the run and keeps meta.
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

Flags: `--seed N` (reproducible run), `--profile NAME` (separate saves), `--settings PATH` (JSON overrides; defaults to the file the Settings screen saves), `--debug`, `--smoke FRAMES` (boot, start a run, render the first floor, exit; used by CI). `AMOR_HEADLESS=1` enables Arcade's headless mode, which needs EGL and only works on Linux.

**Requirements:** `arcade>=3.3,<4`, Python 3.10+. Windows, macOS and Linux.

---

## Testing & Determinism
- **Seeds:** all randomness in a run derives from one seed:
  - `floor_rng(seed, floor) = Random(seed + floor * 1013)` (layout, chests placement, portal roll)
  - `chest_rng(seed, floor) = Random(seed + floor * 13)` (chest contents)
  - `stream_rng(seed, floor, name)` for `encounters`, `monsters` and `combat:<n>` streams
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
Design notes for each epic live in `docs/epics/`. Every epic now has a first implementation; what remains is polish:
1. Hand playtesting against the simulator's numbers (see Balance Model); the auto-policy only flees when the maths says a fight is lost and never misjudges a potion, so real runs still end a little earlier.
2. Real art and audio assets (sprites, tiles, SFX, music) replacing the placeholders.
3. Deeper monster ecology on top of the current kinds, calls and noise: flanking packs, monsters that use doors, and ranged harassment on the map.

---

## License
TBD. (During development, assume **source-available for contributors** and **no redistribution of third-party assets**. Replace this section before release.)

---

### Credits / Notes
- Inspired by the **Ancient Cave** concept from _Lufia II: Rise of the Sinistrals_ (1995). This is an **original** work re-imagining the idea, not a recreation of any proprietary assets.
- Title, theme, and narrative by the project owner.
