"""Wandering monsters: visible enemy groups that roam a floor and hunt the party.

Pure Python. The dungeon is turn-based, so monsters take one move each time
the player takes a step. A monster whose tile is inside the party's field of
view notices them and chases by walking down a BFS distance field centred on
the player; it keeps hunting for ``MONSTER_MEMORY`` steps after losing sight,
then goes back to wandering. Walking into a monster, or being caught by one,
starts a battle with the monster's formation.

Slow monsters (lower SPD than the party leader) only move every other step
while chasing, so a quick party can outrun them.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from random import Random
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ..data import Balance, GameData
from .entities import Enemy
from .procgen import FloorMap, Pos, bfs_reachable
from .rng import stream_rng

MONSTER_MEMORY = 6        # steps a chasing monster keeps hunting after losing sight
WANDER_PAUSE = 0.4        # chance a wandering monster stands still on a given step
SPAWN_MIN_DIST = 10       # BFS distance from the party's start for initial spawns
RESPAWN_MIN_DIST = 12     # BFS distance from the party for later spawns
FLEE_COOLDOWN = 5         # steps a monster stands dazed after the party flees it
NEIGHBOURS: Tuple[Pos, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class Monster:
    """One roaming group, drawn as a single marker on the floor."""

    id: int
    pos: Pos
    enemies: Tuple[str, ...]
    name: str
    spd: int
    state: str = "wander"  # "wander" | "chase"
    memory: int = 0
    cooldown: int = 0
    noticed: bool = False  # the HUD has announced this monster

    @property
    def chasing(self) -> bool:
        return self.state == "chase"


def monster_rng(seed: int, floor: int) -> Random:
    """Stream for spawning and moving monsters on a floor."""
    return stream_rng(seed, floor, "monsters")


def monster_count(floor: int, balance: Balance, rng: Random) -> int:
    """How many groups a floor starts with: a base plus depth, jittered by one."""
    base = balance.monsters_base + balance.monsters_per_floor * max(0, floor - 1)
    return max(1, int(round(base)) + rng.randint(-1, 1))


def distance_field(
    fmap: FloorMap, origin: Pos, limit: int, blocked: Iterable[Pos] = ()
) -> Dict[Pos, int]:
    """BFS steps from ``origin`` to every walkable tile within ``limit`` moves.

    ``blocked`` tiles are not entered (but ``origin`` always is).
    """
    block: Set[Pos] = set(blocked)
    dist: Dict[Pos, int] = {origin: 0}
    queue = deque([origin])
    while queue:
        cur = queue.popleft()
        d = dist[cur]
        if d >= limit:
            continue
        x, y = cur
        for dx, dy in NEIGHBOURS:
            nxt = (x + dx, y + dy)
            if nxt in dist or nxt in block or not fmap.is_walkable(*nxt):
                continue
            dist[nxt] = d + 1
            queue.append(nxt)
    return dist


def _make_monster(mid: int, pos: Pos, floor: int, data: GameData, rng: Random) -> Monster:
    tier = data.tier_for_floor(floor)
    formations = data.encounters[tier.name].formations
    weights = [max(0, f.weight) for f in formations]
    chosen = rng.choices(formations, weights=weights, k=1)[0]
    scaled = [Enemy.from_def(data.enemy(eid), floor, data.balance) for eid in chosen.enemies]
    lead = max(scaled, key=lambda e: e.stats.max_hp)
    name = lead.name if len(scaled) == 1 else f"{lead.name} pack"
    return Monster(
        id=mid,
        pos=pos,
        enemies=tuple(chosen.enemies),
        name=name,
        spd=max(e.stats.spd for e in scaled),
    )


def _spawn_cells(fmap: FloorMap, origin: Pos, min_dist: int, taken: Set[Pos]) -> List[Pos]:
    reserved = {fmap.start, fmap.stairs} | fmap.chests | fmap.keys | taken
    if fmap.portal is not None:
        reserved.add(fmap.portal)
    reachable = bfs_reachable(fmap, fmap.start)
    near = distance_field(fmap, origin, min_dist - 1)
    return sorted(c for c in reachable if c not in reserved and c not in near)


def spawn_monsters(fmap: FloorMap, floor: int, data: GameData, rng: Random) -> List[Monster]:
    """Place the floor's starting groups on reachable tiles well away from the start."""
    count = monster_count(floor, data.balance, rng)
    monsters: List[Monster] = []
    taken: Set[Pos] = set()
    cells = _spawn_cells(fmap, fmap.start, SPAWN_MIN_DIST, taken)
    if not cells:  # tiny or cramped floor: accept anything that is not the start tile
        cells = _spawn_cells(fmap, fmap.start, 2, taken)
    for i in range(count):
        if not cells:
            break
        pos = rng.choice(cells)
        cells.remove(pos)
        taken.add(pos)
        monsters.append(_make_monster(i, pos, floor, data, rng))
    return monsters


def maybe_respawn(
    monsters: List[Monster],
    fmap: FloorMap,
    floor: int,
    player: Pos,
    data: GameData,
    rng: Random,
    *,
    visible: Set[Pos] = frozenset(),
) -> Optional[Monster]:
    """Occasionally add a new group out of sight while the floor is under strength."""
    target = max(1, int(round(data.balance.monsters_base
                              + data.balance.monsters_per_floor * max(0, floor - 1))))
    if len(monsters) >= target or rng.random() >= data.balance.monster_respawn_chance:
        return None
    taken = {m.pos for m in monsters}
    cells = [c for c in _spawn_cells(fmap, player, RESPAWN_MIN_DIST, taken) if c not in visible]
    if not cells:
        return None
    next_id = 1 + max((m.id for m in monsters), default=-1)
    monster = _make_monster(next_id, rng.choice(cells), floor, data, rng)
    monsters.append(monster)
    return monster


def monster_at(monsters: Iterable[Monster], pos: Pos) -> Optional[Monster]:
    for m in monsters:
        if m.pos == pos:
            return m
    return None


def step_monsters(
    monsters: List[Monster],
    fmap: FloorMap,
    player: Pos,
    visible: Set[Pos],
    rng: Random,
    *,
    step: int = 0,
    player_spd: int = 0,
) -> Optional[Monster]:
    """Advance every monster one turn. Returns the monster that caught the party, if any.

    ``visible`` is the party's current field of view: a monster standing in it
    sees the party too. ``step`` is the running step count on this floor and
    ``player_spd`` the leader's effective speed; both drive the slow-monster rule.
    """
    chasers = [m for m in monsters if m.cooldown == 0 and (m.pos in visible or m.chasing)]
    field: Dict[Pos, int] = {}
    if chasers:
        field = distance_field(fmap, player, MONSTER_MEMORY + 14)
    occupied = {m.pos for m in monsters}
    caught: Optional[Monster] = None
    for m in monsters:
        if m.cooldown > 0:
            m.cooldown -= 1
            continue
        if m.pos in visible:
            m.state = "chase"
            m.memory = MONSTER_MEMORY
        elif m.chasing:
            m.memory -= 1
            if m.memory <= 0:
                m.state = "wander"
        occupied.discard(m.pos)
        if m.chasing:
            slow = m.spd < player_spd and step % 2 == 1
            if not slow:
                here = field.get(m.pos)
                if here is not None:
                    options = [
                        (m.pos[0] + dx, m.pos[1] + dy) for dx, dy in NEIGHBOURS
                    ]
                    options = [
                        p for p in options
                        if p in field and field[p] < here and p not in occupied
                    ]
                    if options:
                        m.pos = options[rng.randrange(len(options))]
        elif rng.random() >= WANDER_PAUSE:
            options = [
                (m.pos[0] + dx, m.pos[1] + dy) for dx, dy in NEIGHBOURS
            ]
            options = [
                p for p in options
                if fmap.is_walkable(*p) and p not in occupied and p != player
                and p != fmap.stairs
            ]
            if options:
                m.pos = options[rng.randrange(len(options))]
        occupied.add(m.pos)
        if m.pos == player and caught is None:
            caught = m
    return caught


def remove_monster(monsters: List[Monster], monster: Monster) -> None:
    monsters[:] = [m for m in monsters if m.id != monster.id]


def daze(monster: Monster) -> None:
    """The party fled: the monster loses the scent for a few steps."""
    monster.state = "wander"
    monster.memory = 0
    monster.cooldown = FLEE_COOLDOWN


__all__ = [
    "MONSTER_MEMORY",
    "WANDER_PAUSE",
    "SPAWN_MIN_DIST",
    "FLEE_COOLDOWN",
    "Monster",
    "monster_rng",
    "monster_count",
    "distance_field",
    "spawn_monsters",
    "maybe_respawn",
    "monster_at",
    "step_monsters",
    "remove_monster",
    "daze",
]
