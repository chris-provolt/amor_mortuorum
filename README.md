# Amor Mortuorum
_A re-imagining of Lufia II’s Ancient Cave as a modern, dark roguelite built with Python + Arcade._

> **Scope:** Action on the map with **turn-based, FF1‑style combat**, a **Graveyard** hub, a **99‑floor** procedurally generated dungeon, **Relics of the Veil** (9+1 meta collectibles), and a **Crypt** that stores up to 3 items persistently. **Graveyard access is not constant**—a **portal** may spawn on each floor with a **decreasing chance by depth**.

---

## Table of Contents
- [High‑Level Pitch](#high-level-pitch)
- [Core Features](#core-features)
- [Game Loop](#game-loop)
- [World Structure](#world-structure)
- [Combat](#combat)
- [Items, Loot & Economy](#items-loot--economy)
- [Relics of the Veil (Meta Progression)](#relics-of-the-veil-meta-progression)
- [Procedural Generation](#procedural-generation)
- [Portals to Graveyard (Depth‑Scaling)](#portals-to-graveyard-depth-scaling)
- [UI/UX](#uiux)
- [Accessibility](#accessibility)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Files & Schemas](#data-files--schemas)
- [Save System](#save-system)
- [Build & Run](#build--run)
- [Testing & Determinism](#testing--determinism)
- [Contribution Workflow](#contribution-workflow)
- [Roadmap (Epics)](#roadmap-epics)
- [License](#license)

---

## High‑Level Pitch
**Amor Mortuorum** is a 2D top‑down roguelite dungeon crawler with **99 descending floors**. Players begin each run at level 1 in a **Graveyard** hub where they can rest and purchase limited supplies. A **Crypt** lets them bank up to **3 items** between runs. Floors are procedurally generated with rooms, corridors, traps, chests, and occasional **portals** that lead back to the Graveyard. **Mini‑bosses** appear at floors **20/40/60/80** and a **Final Boss** awaits at **B99**. Between runs, players chase the 9 + 1 **Relics of the Veil** to complete the meta collection.

## Core Features
- **Graveyard hub:** Rest (heal), purchase potions/scrolls, manage the **Crypt** (3 persistent slots).
- **Turn‑based combat (FF1‑style):** Classic menu (Attack / Skill(Scroll) / Item / Defend / Flee). Turn order by **SPD**.
- **Dungeon (99 floors):** BSP rooms + corridors (option for caverns), with **traps**, **chests**, and **boss gates**.
- **Chests:** Single “theme” with **variable quality** by depth; items are data‑driven.
- **Relics of the Veil:** 9 relics + a final one for the deepest boss; persist across runs.
- **Resurrection Token:** If carried at death, **revive** at Graveyard and consume the token.
- **Portals to Graveyard:** Random chance per floor, **rarer deeper down** (configurable curve).
- **Minimap & Fog of War:** Auto‑map explored areas; icons for stairs, chests, portals.

## Game Loop
1. **Graveyard:** Rest → buy supplies → optionally manage **Crypt**.
2. **Descend:** Explore floor, avoid traps, open chests, fight encounters.
3. **Portal (if spawned):** Optionally return to **Graveyard** to heal and bank items.
4. **Miniboss floors 20/40/60/80:** Defeat to unlock stairs.
5. **Final Boss (B99):** Win the run and obtain the **final relic**.
6. **Death:** If carrying **Resurrection Token**, revive at Graveyard; otherwise run ends. Meta progression (relics + crypt) persists.

## World Structure
- **Graveyard (hub):** Menu‑based UI: Enter Dungeon, Rest, Crypt, Purchase, Quit.
- **Dungeon:** Procedurally generated grid (tile size **32px**). Floor tiers: 1–20, 21–40, 41–60, 61–80, 81–99.
- **Mini‑boss floors:** 20/40/60/80; stairs are locked until the miniboss is defeated.
- **Final boss:** **The Oblivion Heart** at B99 (multi‑phase).

## Combat
- **Style:** Turn‑based, menu‑driven, classic JRPG feel.
- **Actions:** Attack, Skill(Scroll), Item, Defend, Flee.
- **Turn Order:** Per round, sort all living battlers by **SPD** (descending). Ties break deterministically.
- **Damage:** `dmg = max(1, atk - df + small_rng)`; defeat sets HP to 0. Items & scrolls apply effects immediately.
- **Party:** 1–4 members (solo supported). Enemy formations vary by floor tier.

## Items, Loot & Economy
- **Equip Slots:** `weapon, armor, helm, shield, accessory`.
- **Consumables:** Potions (heal), Scrolls (cast spells), Keys (open doors).
- **Token:** **Resurrection Token** → revive at Graveyard on death, consume token.
- **Chests:** Depth‑based **quality weights**; items are data‑driven via JSON.
- **Gold:** Dropped from fights and rare chests; used at shop (limited stock per run).

## Relics of the Veil (Meta Progression)
- **Set:** 9 relics + **Final Relic** (“**Heart of Oblivion**”).
- **Persistence:** Stored in meta save; completion survives across runs.
- **Examples:** Lamplight of the Veil, Thorn of Epitaph, Obol of Passage, Votive Ashes, Mortis Dial, Widow’s Knot, Catacomb Key, Lacrimosa Phial, Ossuary Crown, **Heart of Oblivion**.

## Procedural Generation
- **Algorithms:** BSP rooms + corridors (default). Optional cellular caverns.
- **Features:** Chests, traps (**spikes/darts**), locked doors (w/ keys), stairs down, **portal** (chance‑based).
- **Determinism:** Floor layout and chest outcomes derived from a **seed** + `floor` (see [Testing & Determinism](#testing--determinism)).

## Portals to Graveyard (Depth‑Scaling)
- **Design:** Players cannot always warp out; instead, a portal may spawn **randomly** on each floor. **Deeper = rarer**.
- **Formula (default):**
  ```py
  # game/constants.py
  PORTAL_BASE_CHANCE = 0.30     # 30% on Floor 1
  PORTAL_DECAY       = 0.985    # multiplicative decay per floor
  PORTAL_MIN_CHANCE  = 0.02     # floor at 2%
  # chance(floor) = max(PORTAL_MIN_CHANCE, PORTAL_BASE_CHANCE * (PORTAL_DECAY ** (floor-1)))
  ```
- **Placement:** Chosen from room interiors; avoids start and (usually) stairs room.
- **Minimap:** Portals render in teal.

## UI/UX
- **HUD:** HP/MP, floor indicator, gold (later), minimap toggle.
- **Menus:** Main (New/Continue/Settings), Graveyard hub, combat command menu, inventory/equip, run summary.
- **Controls (default):**
  - **Movement:** Arrow Keys / WASD
  - **Menus/Confirm:** Enter/Space
  - **Back/Cancel:** Esc
  - **Minimap Toggle:** M
  - **(Planned)** Rebinding + controller support

## Accessibility
- Planned toggles for **screen shake**, **colorblind‑friendly icons**, **font scaling**, **key remapping**. Minimal SFX/music by default; volume sliders in Settings.

## Tech Stack
- **Language:** Python **3.10+** recommended
- **Renderer/UI:** [Arcade 2.6+](https://api.arcade.academy/en/latest/)
- **Assets:** Placeholder geometry; drop in your sprites/audio under `game/resources/`
- **Packaging:** PyInstaller (Win/macOS/Linux)

---

## Project Structure
```
game/
├── __init__.py
├── __main__.py               # python -m game entry
├── main.py                   # window bootstrap
├── settings.py               # runtime flags (fullscreen, vsync, volumes, minimap/fog)
├── constants.py              # sizes, colors, MAX_FLOOR, CRYPT_CAPACITY, portal tuning
├── core/
│   ├── scene_base.py         # base View class & helpers
│   ├── save_system.py        # meta save: crypt & relics
│   └── asset_loader.py       # safe texture/sound helpers
├── systems/
│   ├── procgen.py            # BSP gen, traps, chests, **PORTAL** spawn
│   ├── combat.py             # turn order, basic attacks (skeleton)
│   ├── loot.py               # loot rolls by tier; JSON loaders
│   └── crypt.py              # store/withdraw persistent items
├── scenes/
│   ├── graveyard.py          # hub menu, rest, crypt, shop stub
│   └── dungeon.py            # floor traversal, interactions, portal → hub
├── entities/
│   ├── player.py             # player/party stats, inventory/equipment
│   └── enemy.py              # enemy defs
├── ui/
│   ├── hud.py                # HUD overlay
│   ├── minimap.py            # minimap w/ icons (stairs, chest, portal)
│   └── menus.py              # vertical menu helper
├── utils/
│   ├── path.py               # (placeholder for pathfinding)
│   └── rng.py                # seeded RNG helper
├── data/
│   ├── enemies.json
│   ├── items.json
│   ├── loot_tables.json
│   ├── floor_tiers.json
│   └── relics.json
└── resources/
    ├── sprites/              # add your art here
    └── audio/                # add your SFX/music here
saves/
└── meta.json                 # created at runtime (crypt, relics)
```

---

## Data Files & Schemas

### `data/items.json` (excerpt)
```json
[
  {"id":"res_token","name":"Resurrection Token","quality":"Epic","type":"token","effect":{"revive_to_graveyard":true}},
  {"id":"potion_small","name":"Grave-Touched Draught","quality":"Common","type":"potion","hp_restore":10},
  {"id":"blade_bone","name":"Bone Shard Blade","quality":"Uncommon","type":"weapon","atk":3},
  {"id":"armor_shroud","name":"Shroudmail","quality":"Rare","type":"armor","df":4},
  {"id":"ring_mourning","name":"Ring of Mourning","quality":"Epic","type":"accessory","spd":2}
]
```

### `data/loot_tables.json`
Weights per **tier** used by chests to pick a quality bucket.
```json
{
  "T1": {"quality_weights": {"Common":60, "Uncommon":30, "Rare":9, "Epic":1}},
  "T2": {"quality_weights": {"Common":45, "Uncommon":35, "Rare":16, "Epic":4}},
  "T3": {"quality_weights": {"Common":30, "Uncommon":40, "Rare":24, "Epic":6}},
  "T4": {"quality_weights": {"Common":20, "Uncommon":40, "Rare":30, "Epic":10}},
  "T5": {"quality_weights": {"Common":10, "Uncommon":35, "Rare":40, "Epic":15}}
}
```

### `data/floor_tiers.json`
```json
[
  {"name":"T1","start":1,"end":20},
  {"name":"T2","start":21,"end":40},
  {"name":"T3","start":41,"end":60},
  {"name":"T4","start":61,"end":80},
  {"name":"T5","start":81,"end":99}
]
```

### `data/enemies.json` (excerpt)
```json
[
  {"id":"skel_basic","name":"Skeletal Thrall","hp":12,"mp":0,"atk":5,"df":2,"spd":4,"behavior":"chase"},
  {"id":"wraith","name":"Wraith","hp":9,"mp":6,"atk":6,"df":1,"spd":6,"behavior":"ranged"},
  {"id":"bone_guard","name":"Bone Guard","hp":20,"mp":0,"atk":6,"df":5,"spd":3,"behavior":"tank"}
]
```

### `data/relics.json`
```json
[
  {"id":"veil_1","name":"Lamplight of the Veil","desc":"Faintly parts the darkness."},
  {"id":"veil_2","name":"Thorn of Epitaph","desc":"Wounds that never heal."},
  ...
  {"id":"veil_9","name":"Ossuary Crown","desc":"Ruler of the silent."},
  {"id":"veil_final","name":"Heart of Oblivion","desc":"The final relic, beyond the deepest door."}
]
```

> **Planned:** `data/encounters.json` (enemy formations by tier), `data/xp_curve.json`, `data/shop.json`.

---

## Save System
- **Meta Save:** `saves/meta.json`
  - `crypt` — list of up to 3 items (persist across runs)
  - `relics_found` — ids of collected relics
- **Save Rules:** Only allowed in **Graveyard** (hub). Future: single‑slot “save & quit” mid‑run snapshot.
- **Resurrection Token:** On death, if present, return to **Graveyard**, consume token, continue. Otherwise, run ends.

---

## Build & Run
```bash
# 1) Create & activate a venv
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
. .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run
python -m game
```

**Requirements:** `arcade>=2.6,<3.0`. Python **3.10+** recommended. Runs on Windows/macOS/Linux.

---

## Testing & Determinism
- **Seeds:** A floor’s layout and chest rolls are derived from a reproducible seed:
  - `floor_rng = Random(seed + floor * 1013)` (procgen)
  - `chest_rng = Random(seed + floor * 13)` (loot; see `DungeonView` init)
- **Unit Tests (planned):** loot distribution, crypt persistence, damage math.
- **Debug Overlay (planned):** toggle with F3 to show FPS, floor, seed, entity counts.

---

## Contribution Workflow
1. **Issues/Tasks:** Use the provided GitHub issues pack (EPICs + child issues) and labels (`area/*`, `type/*`, `priority/*`).  
2. **Branches:** feature branches from `main` → PRs with CI (pytest + lint) when added.  
3. **Style:** PEP‑8, `black`, type hints where practical.  
4. **Data‑Driven:** Add/modify content via JSON; keep logic generic, avoid hard‑coding ids.  
5. **Assets:** Put new sprites/audio under `game/resources/` and reference via the asset loader.

---

## Roadmap (Epics)
- **Core:** Foundations, Save System, Graveyard, Dungeon Gen, Fog/Minimap
- **Systems:** Interactables (Chests/Traps/Doors), Loot/Items/Economy, Encounters → Combat
- **Combat:** Full FF1‑style loop, miniboss gates, final boss
- **Meta:** Relics of the Veil, collection UI, final reward
- **UX/Audio:** HUD/Inventory/Settings/Run Summary; ambient + SFX layers
- **Quality:** JSON validation, tests, debug overlay, CI, PyInstaller packaging

---

## License
TBD. (During development, assume **source‑available for contributors** and **no redistribution of third‑party assets**. Replace this section before release.)

---

### Credits / Notes
- Inspired by the **Ancient Cave** concept from _Lufia II: Rise of the Sinistrals_ (1995). This is an **original** work re‑imagining the idea, not a recreation of any proprietary assets.
- Title, theme, and narrative by the project owner. Code scaffold and documentation authored for rapid developer onboarding.
