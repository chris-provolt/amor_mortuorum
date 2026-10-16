#!/usr/bin/env python3
"""Headless run simulator for balance work.

Plays whole runs with a plain auto-policy (attack the weakest foe, cast when it
pays off, drink when low, run from a fight it cannot win, rest and shop when a
portal shows up and the party is hurt) and reports how deep parties get. Pure
systems code, no arcade.

Each floor is walked tile by tile along the shortest route (key, chests, stairs)
with the real wandering-monster rules, so fights happen where the game would
start them: ambushes from the dark, monsters the walker bumps into, and chasers
that catch up.

    python tools/balance/simulate.py --runs 200 --party 1
    python tools/balance/simulate.py --runs 100 --party 2 --seed 7 --verbose
"""
from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from amormortuorum.data import MAX_FLOOR, GameData  # noqa: E402
from amormortuorum.persistence import MetaState  # noqa: E402
from amormortuorum.systems.combat import Action, ActionKind, Battle, Outcome  # noqa: E402
from amormortuorum.systems.encounters import (  # noqa: E402
    boss_formation,
    combat_rng,
    encounter_rng,
    roll_formation,
    step_encounter,
)
from amormortuorum.systems.entities import Enemy, Player  # noqa: E402
from amormortuorum.systems.fov import compute_fov  # noqa: E402
from amormortuorum.systems.loot import roll_chest, roll_chest_gold  # noqa: E402
from amormortuorum.systems.monsters import (  # noqa: E402
    Monster,
    daze,
    make_noise,
    maybe_respawn,
    monster_at,
    monster_rng,
    remove_monster,
    spawn_monsters,
    step_monsters,
)
from amormortuorum.systems.party import recruit  # noqa: E402
from amormortuorum.systems.procgen import FloorMap, Pos, Tile, generate_floor  # noqa: E402
from amormortuorum.systems.progression import sync_level  # noqa: E402
from amormortuorum.systems.rng import chest_rng  # noqa: E402
from amormortuorum.systems.run import Run, new_run  # noqa: E402
from amormortuorum.systems.shop import Shop  # noqa: E402

POTIONS = ("potion_grand", "potion_large", "potion_medium", "potion_small")
LOW_HP = 0.35
FLEE_MARGIN = 1.5  # flee when the foes would kill us this many times faster than we kill them
REST_BELOW = 0.5
MAX_POTIONS = 8


@dataclass
class RunResult:
    seed: int
    floor: int
    level: int
    cause: str
    victory: bool
    battles: int
    boss_kills: List[int] = field(default_factory=list)
    revived: bool = False
    fled: int = 0


def _shortest_path(fmap: FloorMap, a: Pos, b: Pos) -> List[Pos]:
    """Tiles after ``a`` up to and including ``b``; locked doors count as passable
    (the walker fetches the key first, so it can open them)."""

    def passable(x: int, y: int) -> bool:
        return fmap.is_walkable(x, y) or fmap.tile(x, y) == Tile.DOOR

    prev: Dict[Pos, Optional[Pos]] = {a: None}
    queue = deque([a])
    while queue:
        cur = queue.popleft()
        if cur == b:
            break
        x, y = cur
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt not in prev and passable(*nxt):
                prev[nxt] = cur
                queue.append(nxt)
    if b not in prev:
        return []
    path: List[Pos] = []
    cur: Optional[Pos] = b
    while cur is not None and cur != a:
        path.append(cur)
        cur = prev[cur]
    return path[::-1]


def _route(fmap: FloorMap) -> List[Pos]:
    """Key first (if any), then chests nearest-first, then the stairs."""
    goals: List[Pos] = sorted(fmap.keys) + sorted(fmap.chests)
    route: List[Pos] = []
    cur = fmap.start
    # Keys first, then greedy nearest chest
    keys = [g for g in goals if g in fmap.keys]
    chests = [g for g in goals if g in fmap.chests]
    for key in keys:
        leg = _shortest_path(fmap, cur, key)
        route.extend(leg)
        cur = key if leg else cur
    while chests:
        legs = [(len(_shortest_path(fmap, cur, c)) or 10 ** 6, c) for c in chests]
        _, nxt = min(legs)
        chests.remove(nxt)
        leg = _shortest_path(fmap, cur, nxt)
        if not leg:
            continue
        route.extend(leg)
        cur = nxt
    route.extend(_shortest_path(fmap, cur, fmap.stairs))
    return route


class AutoPolicy:
    """Chooses one action per living member each round."""

    def __init__(self, data: GameData, run: Run):
        self.data = data
        self.run = run

    def _potion(self, bag) -> Optional[str]:
        for pid in POTIONS:
            if bag.has(pid):
                return pid
        return None

    def _weakest(self, battle: Battle) -> Optional[int]:
        living = battle.living_enemies
        if not living:
            return None
        return min(living, key=lambda b: (b.stats.hp, b.index)).index

    def doomed(self, battle: Battle) -> bool:
        """Would the enemies win a slugging match by a wide margin? (Never flee bosses.)"""
        foes = battle.living_enemies
        players = battle.living_players
        if not foes or not players or any(getattr(f.ref, "boss", False) for f in foes):
            return False
        our_df = min(p.ref.effective_df(self.data) for p in players)
        their_hit = sum(max(1, f.stats.atk - our_df + 1) for f in foes)
        our_hit = sum(
            max(1, p.ref.effective_atk(self.data) - min(f.stats.df for f in foes) + 1)
            for p in players
        )
        rounds_to_die = sum(max(0, p.stats.hp) for p in players) / their_hit
        rounds_to_win = sum(max(0, f.stats.hp) for f in foes) / our_hit
        return rounds_to_win > rounds_to_die * FLEE_MARGIN

    def choose(self, battle: Battle, actor_idx: int) -> Action:
        actor: Player = battle.party[actor_idx]
        bag = battle.bag
        if self._potion(bag) is None and self.doomed(battle):
            return Action(ActionKind.FLEE, actor_idx)
        # Emergency drink
        if actor.hp <= actor.max_hp * LOW_HP:
            pid = self._potion(bag)
            if pid:
                return Action(ActionKind.ITEM, actor_idx, target=actor_idx, item_id=pid)
        skills = actor.known_skills(self.data)
        # Heal a badly hurt ally with a healing skill
        heals = [s for s in skills if s.heal and actor.stats.mp >= s.mp]
        if heals:
            hurt = [
                (i, p) for i, p in enumerate(battle.party) if p.is_alive and p.hp <= p.max_hp * 0.4
            ]
            if hurt:
                i, _ = min(hurt, key=lambda ip: ip[1].hp / ip[1].max_hp)
                best = max(heals, key=lambda s: s.heal)
                return Action(ActionKind.SKILL, actor_idx, target=i, skill_id=best.id)
        # Offence: multi-target when it pays, single-target on tough foes
        living = battle.living_enemies
        target = self._weakest(battle)
        offensive = [s for s in skills if s.damage and actor.stats.mp >= s.mp]
        if offensive and target is not None:
            if len(living) >= 2:
                aoe = [s for s in offensive if s.target == "all_enemies"]
                if aoe:
                    best_aoe = max(aoe, key=lambda s: s.damage)
                    return Action(ActionKind.SKILL, actor_idx, skill_id=best_aoe.id)
            foe = battle.foes[target]
            plain = max(1, actor.effective_atk(self.data) - foe.df + 1)
            strong = max(offensive, key=lambda s: s.damage)
            if strong.damage + actor.level >= plain * 2 or getattr(foe.ref, "boss", False):
                return Action(ActionKind.SKILL, actor_idx, target=target, skill_id=strong.id)
        return Action(ActionKind.ATTACK, actor_idx, target=target)


def _auto_equip(player: Player, item, data: GameData) -> None:
    if item.slot is None:
        return
    current = player.equipment.slots.get(item.slot)
    score_new = item.atk * 2 + item.df * 2 + item.spd
    score_old = 0
    if current is not None:
        cur = data.item(current)
        score_old = cur.atk * 2 + cur.df * 2 + cur.spd
    if score_new > score_old:
        player.equip_from_inventory(item, data)


def _shop(run: Run, data: GameData, meta: MetaState) -> None:
    meta.hub_cycle += 1
    shop = Shop(data)
    shop.restock(seed=meta.meta_seed, cycle=meta.hub_cycle)
    leader = run.leader
    bag = leader.inventory
    for pid in ("potion_large", "potion_medium", "potion_small", "tonic_mind"):
        stock = shop.stock().get(pid)
        if not stock:
            continue
        while (
            stock.quantity > 0
            and leader.gold >= stock.price
            and sum(bag.count(p) for p in POTIONS) < MAX_POTIONS
        ):
            shop.buy(leader, pid, 1)
            stock = shop.stock().get(pid)
            if not stock:
                break


def _fight(run: Run, enemies: List[Enemy], rng, data: GameData, policy: AutoPolicy) -> Battle:
    battle = Battle(run.party, enemies, rng, data)
    rounds = 0
    while battle.outcome is Outcome.ONGOING and rounds < 200:
        for b in battle.living_players:
            if battle.outcome is not Outcome.ONGOING:
                break
            if b.index in battle.pending:
                continue
            try:
                battle.submit(policy.choose(battle, b.index))
            except Exception:
                battle.submit(Action(ActionKind.ATTACK, b.index))
        rounds += 1
    if battle.outcome is Outcome.VICTORY:
        battle.apply_rewards()
        for m in run.party:
            sync_level(m, data)
    return battle


def simulate_run(
    seed: int, data: GameData, party_size: int = 1, verbose: bool = False
) -> RunResult:
    meta = MetaState(meta_seed=seed)
    run = new_run(data, seed=seed, meta=meta)
    policy = AutoPolicy(data, run)
    battles = 0
    fled = 0
    boss_kills: List[int] = []
    revived = False
    companions = ["ossian", "sister_vel", "pale_cassia", "brother_moss"]

    def rest_and_shop():
        for m in run.party:
            m.heal_full()
        _shop(run, data, meta)
        while len(run.party) < party_size and companions:
            cid = companions[0]
            if run.leader.gold >= data.companion(cid).cost:
                recruit(run, cid, data)
                companions.pop(0)
            else:
                break

    rest_and_shop()
    floor = 1
    while floor <= MAX_FLOOR:
        run.floor = floor
        fmap = generate_floor(seed, floor)
        enc = encounter_rng(seed, floor)
        crng = chest_rng(seed, floor)
        mrng = monster_rng(seed, floor)
        monsters = spawn_monsters(fmap, floor, data, mrng)
        died_here = False

        def open_chest(pos: Pos) -> None:
            if not fmap.remove_chest(pos):
                return
            gold = roll_chest_gold(crng, floor)
            if gold is not None:
                run.leader.add_gold(gold)
                return
            item = roll_chest(crng, floor, data)
            try:
                run.leader.inventory.add(item, 1)
                _auto_equip(run.leader, item, data)
            except Exception:
                pass

        def fight(enemies: List[Enemy], monster: Optional[Monster]) -> bool:
            """Run one battle; return True if the party fell."""
            nonlocal battles, fled
            battle = _fight(run, enemies, combat_rng(seed, floor, run.encounters), data, policy)
            run.encounters += 1
            run.steps_since_encounter = 0
            battles += 1
            fled += battle.outcome is Outcome.FLED
            if monster is not None:
                if battle.outcome is Outcome.VICTORY:
                    run.leader.add_gold(monster.bounty)
                    remove_monster(monsters, monster)
                else:
                    daze(monster)
            if battle.outcome is not Outcome.DEFEAT:
                make_noise(monsters, fmap, pos)
            return battle.outcome is Outcome.DEFEAT

        def enemies_of(m: Monster) -> List[Enemy]:
            return [Enemy.from_def(data.enemy(eid), floor, data.balance) for eid in m.enemies]

        pos: Pos = fmap.start
        floor_steps = 0
        for nxt in _route(fmap):
            # Walking into a monster engages it; keep attacking until the tile is free.
            guard = 0
            while monster_at(monsters, nxt) is not None and guard < 5:
                guard += 1
                if fight(enemies_of(monster_at(monsters, nxt)), monster_at(monsters, nxt)):
                    died_here = True
                    break
            if died_here:
                break
            pos = nxt
            floor_steps += 1
            run.steps_since_encounter += 1
            open_chest(pos)
            if step_encounter(enc, floor, run.steps_since_encounter, data):
                if fight(roll_formation(enc, floor, data), None):
                    died_here = True
                    break
            visible = compute_fov(fmap, pos)
            caught = step_monsters(
                monsters, fmap, pos, visible, mrng,
                step=floor_steps, player_spd=run.leader.effective_spd(data),
            )
            maybe_respawn(monsters, fmap, floor, pos, data, mrng, visible=visible)
            if caught is not None and fight(enemies_of(caught), caught):
                died_here = True
                break
        if not died_here:
            boss = data.boss_for_floor(floor)
            if boss is not None:
                enemies = boss_formation(floor, data)
                battle = _fight(run, enemies, combat_rng(seed, floor, 1000), data, policy)
                battles += 1
                if battle.outcome is Outcome.DEFEAT:
                    died_here = True
                else:
                    boss_kills.append(floor)
                    if boss.final:
                        return RunResult(seed, floor, run.leader.level, "victory", True, battles,
                                         boss_kills, revived, fled)
        if died_here:
            if run.has_token() and not revived:
                result = run.on_death(meta, data)
                revived = result.revived
                rest_and_shop()
                if verbose:
                    print(f"  seed {seed}: fell on B{floor}, token revived")
                continue  # retry the same floor
            return RunResult(seed, floor, run.leader.level, "died", False, battles, boss_kills,
                             revived, fled)
        # Portal home when hurt
        hurt = min(m.hp / m.max_hp for m in run.party if m.is_alive)
        if fmap.portal is not None and hurt < REST_BELOW:
            rest_and_shop()
        if verbose:
            hp = "/".join(f"{m.hp}" for m in run.party)
            print(
                f"  seed {seed}: cleared B{floor} lv{run.leader.level} "
                f"hp {hp} gold {run.leader.gold}"
            )
        run.descend()
        floor += 1
    return RunResult(
        seed, MAX_FLOOR, run.leader.level, "victory", True, battles, boss_kills, revived, fled
    )


def summarize(results: List[RunResult]) -> Dict[str, object]:
    floors = sorted(r.floor for r in results)
    q = statistics.quantiles(floors, n=4) if len(floors) >= 4 else floors
    bosses = Counter(f for r in results for f in r.boss_kills)
    return {
        "runs": len(results),
        "median_floor": statistics.median(floors),
        "p25_floor": q[0] if len(q) >= 3 else floors[0],
        "p75_floor": q[2] if len(q) >= 3 else floors[-1],
        "min_floor": floors[0],
        "max_floor": floors[-1],
        "victories": sum(1 for r in results if r.victory),
        "revived": sum(1 for r in results if r.revived),
        "boss_kills": {f: bosses.get(f, 0) for f in (20, 40, 60, 80, 99)},
        "mean_level": round(statistics.mean(r.level for r in results), 1),
        "mean_battles": round(statistics.mean(r.battles for r in results), 1),
        "mean_fled": round(statistics.mean(r.fled for r in results), 1),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate runs for balance tuning")
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1, help="first seed (runs use seed..seed+N-1)")
    parser.add_argument(
        "--party", type=int, default=1, help="target party size (recruits as gold allows)"
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    data = GameData.load()
    seeds = range(args.seed, args.seed + args.runs)
    results = [simulate_run(s, data, args.party, args.verbose) for s in seeds]
    summary = summarize(results)
    print(f"runs={summary['runs']} party={args.party}")
    print(
        f"floor reached: median {summary['median_floor']}  p25 {summary['p25_floor']}  "
        f"p75 {summary['p75_floor']}  min {summary['min_floor']}  max {summary['max_floor']}"
    )
    print(f"victories {summary['victories']}  token revives {summary['revived']}")
    print(f"boss kills: {summary['boss_kills']}")
    print(
        f"mean level at end {summary['mean_level']}  mean battles {summary['mean_battles']}"
        f"  mean escapes {summary['mean_fled']}"
    )
    hist = Counter((r.floor - 1) // 10 for r in results)
    for bucket in range(10):
        label = f"B{bucket * 10 + 1:>2}-{bucket * 10 + 10:<3}"
        print(f"  {label} {'#' * hist.get(bucket, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
