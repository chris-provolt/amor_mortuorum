"""Wandering monsters: visible enemy groups that roam a floor and hunt the party.

Pure Python. The dungeon is turn-based, so monsters take one move each time
the player takes a step. Every group has a *kind* that decides how it behaves
on the map; the kind comes from the formation data (``behaviour``) or, by
default, from the lead enemy's combat ``behavior``:

* ``hunter`` (lead ``chase``): wanders until the party's field of view reaches
  it, then chases by walking down a BFS distance field centred on the player,
  and keeps hunting for ``MONSTER_MEMORY`` steps after losing sight.
* ``guard`` (lead ``tank``): stands at a post next to a chest, key or the
  stairs and never roams. It gives chase only when the party is in sight within
  ``GUARD_RANGE`` steps, follows for at most ``GUARD_LEASH`` steps from its
  post, then walks back and resumes its watch.
* ``skittish`` (lead ``ranged``): keeps its distance. When the party is in
  sight it moves *up* the distance field, away from them, and only stands its
  ground when cornered. Catching one pays a gold ``bounty`` on top of the
  battle's normal rewards.

Monsters also react to each other. A guard that rouses bellows and every idle
hunter within ``CALL_RADIUS`` steps joins the chase; a hunter that first spots
the party howls and its kin within ``HOWL_RADIUS`` steps follow. Battles and
sprung traps make noise (``make_noise``): sleepers within earshot wake and
idle hunters come to investigate.

Walking into a monster, or being caught by one, starts a battle with the
monster's formation. Slow monsters (lower SPD than the party leader) only move
every other step while chasing or fleeing, so a quick party can outrun hunters
and run down skittish groups. Some hunters and skittish groups start asleep:
they never move until the party comes within ``WAKE_DIST`` tiles in plain
sight, so a careful party can slip past them or strike first.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from random import Random
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ..data import FORMATION_BEHAVIOURS, Balance, Formation, GameData
from .entities import Enemy
from .procgen import FloorMap, Pos, bfs_reachable
from .rng import stream_rng

MONSTER_MEMORY = 6        # steps a chasing/fleeing monster keeps it up after losing sight
WANDER_PAUSE = 0.4        # chance a wandering monster stands still on a given step
SPAWN_MIN_DIST = 10       # BFS distance from the party's start for initial spawns
RESPAWN_MIN_DIST = 12     # BFS distance from the party for later spawns
FLEE_COOLDOWN = 5         # steps a monster stands dazed after the party flees it
SLEEP_CHANCE = 0.3        # share of spawned hunters/skittish groups that start asleep
WAKE_DIST = 2             # Manhattan distance at which a visible sleeper wakes
GUARD_RANGE = 4           # BFS steps within which a visible party rouses a guard
GUARD_LEASH = 6           # BFS steps from its post a guard will chase before turning back
GUARD_POST_DIST = 2       # guards spawn within this many steps of a chest, key or the stairs
CALL_RADIUS = 8           # BFS steps a roused guard's bellow carries to idle hunters
HOWL_RADIUS = 5           # BFS steps a hunter's howl carries when it first spots the party
NOISE_RADIUS = 7          # BFS steps the din of a battle carries
TRAP_NOISE_RADIUS = 4     # BFS steps a sprung trap's clatter carries
CHASE_LIMIT = MONSTER_MEMORY + 14  # radius of the distance field chasers walk down
NEIGHBOURS: Tuple[Pos, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))

KINDS: Tuple[str, ...] = FORMATION_BEHAVIOURS
KIND_FOR_BEHAVIOR = {"chase": "hunter", "tank": "guard", "ranged": "skittish"}


@dataclass
class Monster:
    """One roaming group, drawn as a single marker on the floor."""

    id: int
    pos: Pos
    enemies: Tuple[str, ...]
    name: str
    spd: int
    kind: str = "hunter"      # "hunter" | "guard" | "skittish"
    state: str = "wander"     # "sleep" | "wander" | "chase" | "flee" | "return"
    memory: int = 0
    cooldown: int = 0
    post: Optional[Pos] = None  # where a guard stands watch
    bounty: int = 0           # extra gold for catching a skittish group
    lead: str = ""            # def id of the group's biggest enemy (drawn on the map)
    noticed: bool = False     # the HUD has announced this monster

    @property
    def chasing(self) -> bool:
        return self.state == "chase"

    @property
    def fleeing(self) -> bool:
        return self.state == "flee"

    @property
    def asleep(self) -> bool:
        return self.state == "sleep"

    @property
    def alert(self) -> bool:
        """The monster knows where the party is (hunting or running from them)."""
        return self.state in ("chase", "flee")


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


def kind_for(formation: Formation, scaled: List[Enemy], data: GameData) -> str:
    """The map behaviour of a formation: explicit ``behaviour`` or the lead enemy's style."""
    if formation.behaviour:
        return formation.behaviour
    lead = max(scaled, key=lambda e: e.stats.max_hp)
    return KIND_FOR_BEHAVIOR.get(data.enemy(lead.def_id).behavior, "hunter")


def _pick_formation(floor: int, data: GameData, rng: Random):
    tier = data.tier_for_floor(floor)
    formations = data.encounters[tier.name].formations
    weights = [max(0, f.weight) for f in formations]
    chosen = rng.choices(formations, weights=weights, k=1)[0]
    scaled = [Enemy.from_def(data.enemy(eid), floor, data.balance) for eid in chosen.enemies]
    return chosen, scaled


def _make_monster(
    mid: int,
    pos: Pos,
    chosen: Formation,
    scaled: List[Enemy],
    data: GameData,
    rng: Random,
    *,
    may_sleep: bool = True,
) -> Monster:
    kind = kind_for(chosen, scaled, data)
    lead = max(scaled, key=lambda e: e.stats.max_hp)
    name = lead.name if len(scaled) == 1 else f"{lead.name} pack"
    sleeps = kind != "guard" and may_sleep and rng.random() < SLEEP_CHANCE
    return Monster(
        id=mid,
        pos=pos,
        enemies=tuple(chosen.enemies),
        name=name,
        spd=max(e.stats.spd for e in scaled),
        kind=kind,
        state="sleep" if sleeps else "wander",
        post=pos if kind == "guard" else None,
        bounty=sum(e.gold for e in scaled) if kind == "skittish" else 0,
        lead=lead.def_id,
    )


def _spawn_cells(fmap: FloorMap, origin: Pos, min_dist: int, taken: Set[Pos]) -> List[Pos]:
    reserved = {fmap.start, fmap.stairs} | fmap.chests | fmap.keys | taken
    if fmap.portal is not None:
        reserved.add(fmap.portal)
    reachable = bfs_reachable(fmap, fmap.start)
    near = distance_field(fmap, origin, min_dist - 1)
    return sorted(c for c in reachable if c not in reserved and c not in near)


def guard_posts(fmap: FloorMap, cells: Iterable[Pos]) -> List[Pos]:
    """The subset of ``cells`` close enough to a chest, key or the stairs to stand guard at."""
    allowed = set(cells)
    posts: Set[Pos] = set()
    for feature in list(fmap.chests) + list(fmap.keys) + [fmap.stairs]:
        posts.update(p for p in distance_field(fmap, feature, GUARD_POST_DIST) if p in allowed)
    return sorted(posts)


def _place(
    cells: List[Pos], kind: str, fmap: FloorMap, rng: Random
) -> Pos:
    """Pick a spawn tile from ``cells`` (guards prefer a post by something worth guarding)."""
    if kind == "guard":
        posts = guard_posts(fmap, cells)
        if posts:
            return rng.choice(posts)
    return rng.choice(cells)


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
        chosen, scaled = _pick_formation(floor, data, rng)
        pos = _place(cells, kind_for(chosen, scaled, data), fmap, rng)
        cells.remove(pos)
        taken.add(pos)
        monsters.append(_make_monster(i, pos, chosen, scaled, data, rng))
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
    chosen, scaled = _pick_formation(floor, data, rng)
    pos = _place(cells, kind_for(chosen, scaled, data), fmap, rng)
    monster = _make_monster(next_id, pos, chosen, scaled, data, rng, may_sleep=False)
    monsters.append(monster)
    return monster


def monster_at(monsters: Iterable[Monster], pos: Pos) -> Optional[Monster]:
    for m in monsters:
        if m.pos == pos:
            return m
    return None


def _neighbours(pos: Pos) -> List[Pos]:
    return [(pos[0] + dx, pos[1] + dy) for dx, dy in NEIGHBOURS]


def rally(
    monsters: Iterable[Monster], fmap: FloorMap, caller: Monster, radius: int
) -> List[Monster]:
    """Idle, awake hunters within ``radius`` steps of ``caller`` join the chase."""
    field = distance_field(fmap, caller.pos, radius)
    joined: List[Monster] = []
    for m in monsters:
        if m is caller or m.kind != "hunter" or m.state != "wander" or m.cooldown > 0:
            continue
        if m.pos in field:
            m.state, m.memory = "chase", MONSTER_MEMORY
            joined.append(m)
    return joined


def make_noise(
    monsters: Iterable[Monster], fmap: FloorMap, origin: Pos, radius: int = NOISE_RADIUS
) -> List[Monster]:
    """Something loud happened at ``origin``: wake sleepers and draw idle hunters.

    Sleeping hunters wake straight into the chase, sleeping skittish groups wake
    and start roaming, idle hunters come to investigate. Guards keep their posts
    and dazed monsters stay dazed. Returns every monster whose state changed.
    """
    field = distance_field(fmap, origin, radius)
    stirred: List[Monster] = []
    for m in monsters:
        if m.pos not in field or m.cooldown > 0 or m.kind == "guard":
            continue
        if m.asleep:
            if m.kind == "hunter":
                m.state, m.memory = "chase", MONSTER_MEMORY
            else:
                m.state = "wander"
            stirred.append(m)
        elif m.kind == "hunter" and m.state == "wander":
            m.state, m.memory = "chase", MONSTER_MEMORY
            stirred.append(m)
    return stirred


def step_monsters(
    monsters: List[Monster],
    fmap: FloorMap,
    player: Pos,
    visible: Set[Pos],
    rng: Random,
    *,
    step: int = 0,
    player_spd: int = 0,
    log: Optional[List[Tuple[str, Monster, List[Monster]]]] = None,
) -> Optional[Monster]:
    """Advance every monster one turn. Returns the monster that caught the party, if any.

    ``visible`` is the party's current field of view: a monster standing in it
    sees the party too. ``step`` is the running step count on this floor and
    ``player_spd`` the leader's effective speed; both drive the slow-monster rule.
    When ``log`` is given, every rally is appended to it as
    ``("bellow" | "howl", caller, joiners)`` so the HUD can report it.
    """
    field: Dict[Pos, int] = {}
    post_fields: Dict[Pos, Dict[Pos, int]] = {}

    def player_field() -> Dict[Pos, int]:
        nonlocal field
        if not field:
            field = distance_field(fmap, player, CHASE_LIMIT)
        return field

    def post_field(post: Pos) -> Dict[Pos, int]:
        if post not in post_fields:
            post_fields[post] = distance_field(fmap, post, GUARD_LEASH + CHASE_LIMIT)
        return post_fields[post]

    occupied = {m.pos for m in monsters}
    caught: Optional[Monster] = None
    for m in monsters:
        if m.cooldown > 0:
            m.cooldown -= 1
            continue
        sees = m.pos in visible
        if m.asleep:
            near = abs(m.pos[0] - player[0]) + abs(m.pos[1] - player[1]) <= WAKE_DIST
            if not (near and sees):
                continue
            m.state = "flee" if m.kind == "skittish" else "chase"
            m.memory = MONSTER_MEMORY
        # Notice or forget the party
        was_chasing = m.chasing
        if m.kind == "guard":
            if sees and player_field().get(m.pos, CHASE_LIMIT + 1) <= GUARD_RANGE:
                m.state, m.memory = "chase", MONSTER_MEMORY
                if not was_chasing:
                    joined = rally(monsters, fmap, m, CALL_RADIUS)
                    if joined and log is not None:
                        log.append(("bellow", m, joined))
            elif m.chasing:
                m.memory -= 1
                if m.memory <= 0:
                    m.state = "return"
        elif m.kind == "skittish":
            if sees:
                m.state, m.memory = "flee", MONSTER_MEMORY
            elif m.fleeing:
                m.memory -= 1
                if m.memory <= 0:
                    m.state = "wander"
        else:
            if sees:
                m.state, m.memory = "chase", MONSTER_MEMORY
                if not was_chasing:
                    joined = rally(monsters, fmap, m, HOWL_RADIUS)
                    if joined and log is not None:
                        log.append(("howl", m, joined))
            elif m.chasing:
                m.memory -= 1
                if m.memory <= 0:
                    m.state = "wander"
        # Move
        occupied.discard(m.pos)
        slow = m.spd < player_spd and step % 2 == 1
        if m.chasing:
            if not slow:
                pf = player_field()
                here = pf.get(m.pos)
                if here is not None:
                    options = [
                        p for p in _neighbours(m.pos)
                        if p in pf and pf[p] < here and p not in occupied
                    ]
                    if options:
                        m.pos = options[rng.randrange(len(options))]
            if m.post is not None and post_field(m.post).get(m.pos, GUARD_LEASH + 1) > GUARD_LEASH:
                m.state = "return"
        elif m.fleeing:
            if not slow:
                pf = player_field()
                here = pf.get(m.pos)
                if here is not None:
                    options = [
                        p for p in _neighbours(m.pos)
                        if p in pf and pf[p] > here and p not in occupied and p != fmap.stairs
                    ]
                    if options:
                        best = max(pf[p] for p in options)
                        options = [p for p in options if pf[p] == best]
                        m.pos = options[rng.randrange(len(options))]
                else:
                    _wander(m, fmap, player, occupied, rng)
        elif m.state == "return":
            if m.post is None or m.pos == m.post:
                m.state = "wander"
            else:
                rf = post_field(m.post)
                here = rf.get(m.pos)
                options = [
                    p for p in _neighbours(m.pos)
                    if here is not None and p in rf and rf[p] < here
                    and p not in occupied and p != player
                ]
                if options:
                    m.pos = options[rng.randrange(len(options))]
                if m.pos == m.post:
                    m.state = "wander"
        elif m.kind != "guard" and rng.random() >= WANDER_PAUSE:
            _wander(m, fmap, player, occupied, rng)
        occupied.add(m.pos)
        if m.pos == player and caught is None:
            caught = m
    return caught


def _wander(m: Monster, fmap: FloorMap, player: Pos, occupied: Set[Pos], rng: Random) -> None:
    options = [
        p for p in _neighbours(m.pos)
        if fmap.is_walkable(*p) and p not in occupied and p != player and p != fmap.stairs
    ]
    if options:
        m.pos = options[rng.randrange(len(options))]


def remove_monster(monsters: List[Monster], monster: Monster) -> None:
    monsters[:] = [m for m in monsters if m.id != monster.id]


def daze(monster: Monster) -> None:
    """The party fled: the monster loses the scent for a few steps."""
    monster.state = "return" if monster.kind == "guard" else "wander"
    monster.memory = 0
    monster.cooldown = FLEE_COOLDOWN


__all__ = [
    "MONSTER_MEMORY",
    "WANDER_PAUSE",
    "SPAWN_MIN_DIST",
    "FLEE_COOLDOWN",
    "SLEEP_CHANCE",
    "WAKE_DIST",
    "GUARD_RANGE",
    "GUARD_LEASH",
    "GUARD_POST_DIST",
    "CALL_RADIUS",
    "HOWL_RADIUS",
    "NOISE_RADIUS",
    "TRAP_NOISE_RADIUS",
    "KINDS",
    "KIND_FOR_BEHAVIOR",
    "Monster",
    "monster_rng",
    "monster_count",
    "distance_field",
    "kind_for",
    "guard_posts",
    "spawn_monsters",
    "maybe_respawn",
    "monster_at",
    "step_monsters",
    "rally",
    "make_noise",
    "remove_monster",
    "daze",
]
