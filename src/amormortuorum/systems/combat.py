"""FF1-style turn-based combat resolution.

Pure Python. A ``Battle`` collects one ``Action`` per living player, then
resolves a round: flee attempts first, then every living battler acts in SPD
order (players before enemies on ties). All randomness comes from the ``Random``
instance handed in, so a seeded run replays identically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from random import Random
from typing import Dict, List, Optional, Tuple, Union

from ..data import GameData
from ..errors import InvalidOperation
from .entities import Enemy, Player, Stats


class ActionKind(Enum):
    ATTACK = auto()
    ITEM = auto()
    DEFEND = auto()
    FLEE = auto()


class Outcome(Enum):
    ONGOING = auto()
    VICTORY = auto()
    DEFEAT = auto()
    FLED = auto()


@dataclass
class Action:
    """A player's chosen action for the round.

    ``actor`` indexes ``Battle.party``. ``target`` indexes ``Battle.enemies`` for
    ATTACK or a damaging ITEM, and ``Battle.party`` for a healing ITEM (defaults
    to the actor).
    """

    kind: ActionKind
    actor: int
    target: Optional[int] = None
    item_id: Optional[str] = None


@dataclass
class LogEvent:
    """One line of the combat log.

    ``kind`` is one of: attack, heal, item, defend, flee, defeat, victory, info.
    """

    text: str
    kind: str = "info"


@dataclass
class Battler:
    """Wraps a Player or Enemy with per-round combat state."""

    name: str
    is_player: bool
    index: int
    ref: Union[Player, Enemy]
    defending: bool = False
    _data: Optional[GameData] = field(default=None, repr=False, compare=False)

    @property
    def stats(self) -> Stats:
        return self.ref.stats

    @property
    def is_alive(self) -> bool:
        return self.ref.is_alive

    @property
    def atk(self) -> int:
        if self.is_player and self._data is not None:
            return self.ref.effective_atk(self._data)  # type: ignore[union-attr]
        bonus = self.ref.enrage if getattr(self.ref, "is_enraged", False) else 0
        return self.stats.atk + bonus

    @property
    def df(self) -> int:
        if self.is_player and self._data is not None:
            return self.ref.effective_df(self._data)  # type: ignore[union-attr]
        return self.stats.df

    @property
    def spd(self) -> int:
        if self.is_player and self._data is not None:
            return self.ref.effective_spd(self._data)  # type: ignore[union-attr]
        return self.stats.spd


def damage(atk: int, df: int, rng: Random) -> int:
    """Design formula: ``max(1, atk - df + small_rng)`` with ``small_rng`` in 0..2."""
    return max(1, atk - df + rng.randint(0, 2))


def turn_order(battlers: List[Battler]) -> List[Battler]:
    """Living battlers sorted by SPD descending; players win ties, then lower index."""
    living = [b for b in battlers if b.is_alive]
    return sorted(living, key=lambda b: (-b.spd, 0 if b.is_player else 1, b.index))


def flee_chance(party_spd: int, max_enemy_spd: int) -> float:
    chance = 0.5 + 0.05 * (party_spd - max_enemy_spd)
    return max(0.1, min(0.9, chance))


def _halved(amount: int) -> int:
    return max(1, amount // 2)


class Battle:
    """One encounter between ``party`` and ``enemies``."""

    def __init__(
        self,
        party: List[Player],
        enemies: List[Enemy],
        rng: Random,
        data: GameData,
    ) -> None:
        if not party:
            raise InvalidOperation("A battle needs at least one party member")
        if not enemies:
            raise InvalidOperation("A battle needs at least one enemy")
        self.party = party
        self.enemies = enemies
        self.rng = rng
        self.data = data
        self.players: List[Battler] = [
            Battler(name=p.name, is_player=True, index=i, ref=p, _data=data)
            for i, p in enumerate(party)
        ]
        self.foes: List[Battler] = [
            Battler(name=e.name, is_player=False, index=i, ref=e, _data=data)
            for i, e in enumerate(enemies)
        ]
        self.outcome: Outcome = Outcome.ONGOING
        self.log: List[LogEvent] = []
        self.round_number: int = 1
        self.pending: Dict[int, Action] = {}
        self._update_outcome()

    # Queries

    @property
    def living_players(self) -> List[Battler]:
        return [b for b in self.players if b.is_alive]

    @property
    def living_enemies(self) -> List[Battler]:
        return [b for b in self.foes if b.is_alive]

    def first_living_enemy_index(self) -> Optional[int]:
        for b in self.foes:
            if b.is_alive:
                return b.index
        return None

    def all_battlers(self) -> List[Battler]:
        return self.players + self.foes

    def rewards(self) -> Tuple[int, int]:
        """Total (xp, gold) carried by every enemy in the battle."""
        xp = sum(e.xp for e in self.enemies)
        gold = sum(e.gold for e in self.enemies)
        return xp, gold

    def apply_rewards(self) -> Tuple[int, int]:
        """Grant rewards to the first living player (or the first player).

        Relic passives ``xp_pct`` / ``gold_pct`` on the recipient scale the amounts.
        """
        xp, gold = self.rewards()
        living = self.living_players
        recipient = living[0].ref if living else self.party[0]
        bonus = getattr(recipient, "bonus", lambda _k: 0)
        xp = xp * (100 + bonus("xp_pct")) // 100
        gold = gold * (100 + bonus("gold_pct")) // 100
        recipient.xp += xp  # type: ignore[union-attr]
        recipient.add_gold(gold)  # type: ignore[union-attr]
        return xp, gold

    # Action intake

    def submit(self, action: Action) -> List[LogEvent]:
        """Record a player's action; resolve the round once every living player has one.

        Returns the events of the round that was resolved, or ``[]`` if the round
        is still waiting on other players.
        """
        if self.outcome is not Outcome.ONGOING:
            raise InvalidOperation("Battle is already over")
        self._validate(action)
        self.pending[action.actor] = action
        if all(b.index in self.pending for b in self.living_players):
            return self.resolve_round()
        return []

    def _validate(self, action: Action) -> None:
        if not isinstance(action.kind, ActionKind):
            raise InvalidOperation(f"Unknown action kind: {action.kind!r}")
        if not 0 <= action.actor < len(self.players):
            raise InvalidOperation(f"Invalid actor index: {action.actor}")
        actor = self.players[action.actor]
        if not actor.is_alive:
            raise InvalidOperation(f"{actor.name} cannot act while defeated")

        if action.kind is ActionKind.ATTACK:
            self._validate_enemy_target(action)
        elif action.kind is ActionKind.ITEM:
            if not action.item_id:
                raise InvalidOperation("ITEM action requires an item_id")
            if not self.data.has_item(action.item_id):
                raise InvalidOperation(f"Unknown item id: {action.item_id}")
            item = self.data.item(action.item_id)
            if not item.usable_in_combat:
                raise InvalidOperation(f"{item.name} cannot be used in combat")
            player: Player = actor.ref  # type: ignore[assignment]
            if not player.inventory.has(item.id):
                raise InvalidOperation(f"{player.name} has no {item.name}")
            if item.damage > 0:
                self._validate_enemy_target(action)
            else:
                target = action.actor if action.target is None else action.target
                if not 0 <= target < len(self.players):
                    raise InvalidOperation(f"Invalid party target index: {target}")
                if not self.players[target].is_alive:
                    raise InvalidOperation(f"{self.players[target].name} is defeated")
                action.target = target

    def _validate_enemy_target(self, action: Action) -> None:
        if action.target is None:
            action.target = self.first_living_enemy_index()
            if action.target is None:
                raise InvalidOperation("No living enemy to target")
        if not 0 <= action.target < len(self.foes):
            raise InvalidOperation(f"Invalid enemy target index: {action.target}")
        if not self.foes[action.target].is_alive:
            raise InvalidOperation(f"{self.foes[action.target].name} is already defeated")

    # Resolution

    def resolve_round(self) -> List[LogEvent]:
        """Resolve the round with whatever actions are pending and return its events."""
        if self.outcome is not Outcome.ONGOING:
            raise InvalidOperation("Battle is already over")
        events: List[LogEvent] = [LogEvent(f"Round {self.round_number}", "info")]

        if self._resolve_flee(events):
            self._end_round(events)
            return events

        for battler in turn_order(self.all_battlers()):
            if not battler.is_alive:
                continue  # died earlier this round
            if self.outcome is not Outcome.ONGOING:
                break
            if battler.is_player:
                self._player_turn(battler, events)
            else:
                self._enemy_turn(battler, events)
            self._update_outcome()

        self._end_round(events)
        return events

    def _resolve_flee(self, events: List[LogEvent]) -> bool:
        fleeing = [a for a in self.pending.values() if a.kind is ActionKind.FLEE]
        if not fleeing:
            return False
        party_spd = max(b.spd for b in self.living_players)
        enemy_spd = max(b.spd for b in self.living_enemies)
        chance = flee_chance(party_spd, enemy_spd)
        if self.rng.random() < chance:
            events.append(LogEvent("The party slips away into the dark.", "flee"))
            self.outcome = Outcome.FLED
            return True
        events.append(LogEvent("The party fails to escape!", "flee"))
        return False

    def _player_turn(self, battler: Battler, events: List[LogEvent]) -> None:
        action = self.pending.get(battler.index)
        if action is None or action.kind is ActionKind.FLEE:
            return
        if action.kind is ActionKind.DEFEND:
            battler.defending = True
            events.append(LogEvent(f"{battler.name} braces for the blow.", "defend"))
            return
        if action.kind is ActionKind.ATTACK:
            target = self._live_enemy_target(action.target)
            if target is None:
                events.append(LogEvent(f"{battler.name} finds no foe to strike.", "info"))
                return
            amount = damage(battler.atk, target.df, self.rng)
            if target.defending:
                amount = _halved(amount)
            self._hit(battler, target, amount, events, kind="attack")
            return
        if action.kind is ActionKind.ITEM:
            self._use_item(battler, action, events)

    def _use_item(self, battler: Battler, action: Action, events: List[LogEvent]) -> None:
        player: Player = battler.ref  # type: ignore[assignment]
        item = self.data.item(action.item_id or "")
        if not player.inventory.has(item.id):
            events.append(LogEvent(f"{battler.name} fumbles for a missing {item.name}.", "info"))
            return
        if item.damage > 0:
            target = self._live_enemy_target(action.target)
            if target is None:
                events.append(LogEvent(f"{battler.name} finds no foe for {item.name}.", "info"))
                return
            player.inventory.remove(item, 1)
            self._hit(battler, target, item.damage, events, kind="item", source=item.name)
            return
        target_idx = battler.index if action.target is None else action.target
        target = self.players[target_idx]
        if not target.is_alive:
            events.append(LogEvent(f"{target.name} is beyond the reach of {item.name}.", "info"))
            return
        player.inventory.remove(item, 1)
        healed = target.ref.heal(item.hp_restore)  # type: ignore[union-attr]
        text = f"{battler.name} uses {item.name}: {target.name} recovers {healed} HP."
        events.append(LogEvent(text, "heal"))

    def _enemy_turn(self, battler: Battler, events: List[LogEvent]) -> None:
        living = self.living_players
        if not living:
            return
        target = self.rng.choice(living)
        amount = damage(battler.atk, target.df, self.rng)
        if target.defending:
            amount = _halved(amount)
        self._hit(battler, target, amount, events, kind="attack")

    def _hit(
        self,
        attacker: Battler,
        target: Battler,
        amount: int,
        events: List[LogEvent],
        *,
        kind: str,
        source: Optional[str] = None,
    ) -> None:
        was_enraged = bool(getattr(target.ref, "is_enraged", False))
        dealt = target.ref.take_damage(amount)
        verb = f"uses {source} on" if source else "hits"
        events.append(LogEvent(f"{attacker.name} {verb} {target.name} for {dealt}.", kind))
        if not target.is_alive:
            events.append(LogEvent(f"{target.name} is defeated.", "defeat"))
        elif not was_enraged and getattr(target.ref, "is_enraged", False):
            events.append(LogEvent(f"{target.name} shudders and rages!", "info"))

    def _live_enemy_target(self, index: Optional[int]) -> Optional[Battler]:
        if index is not None and 0 <= index < len(self.foes) and self.foes[index].is_alive:
            return self.foes[index]
        retarget = self.first_living_enemy_index()
        return self.foes[retarget] if retarget is not None else None

    def _update_outcome(self) -> None:
        if self.outcome is not Outcome.ONGOING:
            return
        if not self.living_enemies:
            self.outcome = Outcome.VICTORY
        elif not self.living_players:
            self.outcome = Outcome.DEFEAT

    def _end_round(self, events: List[LogEvent]) -> None:
        for b in self.all_battlers():
            b.defending = False
        self.pending.clear()
        self.round_number += 1
        self._update_outcome()
        if self.outcome is Outcome.VICTORY:
            events.append(LogEvent("Victory! The dead lie still once more.", "victory"))
        elif self.outcome is Outcome.DEFEAT:
            events.append(LogEvent("The party has fallen.", "defeat"))
        self.log.extend(events)


__all__ = [
    "ActionKind",
    "Action",
    "Battler",
    "LogEvent",
    "Outcome",
    "Battle",
    "damage",
    "turn_order",
    "flee_chance",
]
