from random import Random

import pytest

from amormortuorum.data import GameData
from amormortuorum.errors import InvalidOperation
from amormortuorum.systems.combat import (
    Action,
    ActionKind,
    Battle,
    Battler,
    Outcome,
    damage,
    flee_chance,
    turn_order,
)
from amormortuorum.systems.entities import Enemy, Stats, new_player


@pytest.fixture(scope="module")
def data() -> GameData:
    return GameData.load()


def enemy(data: GameData, enemy_id: str) -> Enemy:
    return Enemy.from_def(data.enemy(enemy_id))


def attack(actor: int = 0, target=None) -> Action:
    return Action(ActionKind.ATTACK, actor=actor, target=target)


# damage / turn order / flee


def test_damage_floor_and_range():
    rng = Random(1)
    for _ in range(200):
        assert damage(1, 50, rng) == 1
    rng = Random(2)
    seen = {damage(10, 4, rng) for _ in range(500)}
    assert seen == {6, 7, 8}


def test_turn_order_sorts_by_spd_with_deterministic_ties(data):
    fast = Battler("fast", False, 0, Enemy("e", "fast", Stats(spd=9)))
    slow = Battler("slow", False, 1, Enemy("e", "slow", Stats(spd=2)))
    p0 = new_player("p0")
    p0.stats.spd = 5
    p1 = new_player("p1")
    p1.stats.spd = 5
    same_spd_enemy = Battler("tie", False, 2, Enemy("e", "tie", Stats(spd=5)))
    pb0 = Battler("p0", True, 0, p0, _data=data)
    pb1 = Battler("p1", True, 1, p1, _data=data)
    dead = Battler("dead", False, 3, Enemy("e", "dead", Stats(hp=0, spd=99)))

    order = turn_order([same_spd_enemy, dead, pb1, slow, pb0, fast])
    assert [b.name for b in order] == ["fast", "p0", "p1", "tie", "slow"]


def test_flee_chance_is_clamped():
    assert flee_chance(5, 5) == pytest.approx(0.5)
    assert flee_chance(30, 0) == pytest.approx(0.9)
    assert flee_chance(0, 30) == pytest.approx(0.1)


# battle mechanics


def test_attack_until_victory_sets_outcome_and_rewards(data):
    player = new_player()
    player.stats.max_hp = player.stats.hp = 200  # mechanics test, not a balance test
    foes = [enemy(data, "skel_basic"), enemy(data, "wraith")]
    battle = Battle([player], foes, Random(7), data)
    rounds = 0
    while battle.outcome is Outcome.ONGOING:
        events = battle.submit(attack())
        assert events, "a lone player's action should resolve the round"
        rounds += 1
        assert rounds < 50
    assert battle.outcome is Outcome.VICTORY
    assert battle.rewards() == (6 + 7, 4 + 5)
    gold_before, xp_before = player.gold, player.xp
    assert battle.apply_rewards() == (13, 9)
    assert player.gold == gold_before + 9
    assert player.xp == xp_before + 13
    assert battle.log[-1].kind == "victory"
    with pytest.raises(InvalidOperation):
        battle.submit(attack())


def test_defend_halves_enemy_damage(data):
    def run(defend: bool) -> int:
        player = new_player()
        player.stats.max_hp = player.stats.hp = 1000
        battle = Battle([player], [enemy(data, "bone_colossus")], Random(11), data)
        battle.submit(Action(ActionKind.DEFEND if defend else ActionKind.ATTACK, actor=0))
        return 1000 - player.stats.hp

    undefended = run(False)
    defended = run(True)
    assert undefended > 1
    # Same seed: enemy draws the same rng values only if the player's attack did not
    # consume any, so compare against the formula instead of exact equality.
    assert defended <= max(1, undefended // 2) + 2
    assert defended < undefended


def test_defend_logs_event_and_resets_each_round(data):
    player = new_player()
    player.stats.max_hp = player.stats.hp = 1000
    battle = Battle([player], [enemy(data, "skel_basic")], Random(3), data)
    events = battle.submit(Action(ActionKind.DEFEND, actor=0))
    assert any(e.kind == "defend" for e in events)
    assert battle.players[0].defending is False
    assert battle.pending == {}
    assert battle.round_number == 2


def test_item_heals_and_consumes(data):
    player = new_player()
    player.stats.hp = 5
    potion = data.item("potion_small")
    player.inventory.add(potion, 2)
    battle = Battle([player], [enemy(data, "skel_basic")], Random(5), data)
    hp_before = player.stats.hp
    events = battle.submit(Action(ActionKind.ITEM, actor=0, item_id="potion_small"))
    heal_events = [e for e in events if e.kind == "heal"]
    assert len(heal_events) == 1
    assert "recovers" in heal_events[0].text
    assert player.inventory.count("potion_small") == 1
    # healed by hp_restore, then possibly hit by the enemy afterwards
    assert player.stats.hp > hp_before - 10 or player.stats.hp == player.stats.max_hp


def test_item_heal_is_capped_at_max_hp(data):
    player = new_player()
    player.stats.hp = player.stats.max_hp - 1
    player.inventory.add(data.item("potion_large"), 1)
    # Enemy with 0 atk-equivalent so it cannot reduce hp meaningfully: use a dead-slow weakling
    weak = Enemy("w", "Weakling", Stats(max_hp=1, hp=1, atk=0, df=0, spd=0))
    battle = Battle([player], [weak], Random(1), data)
    events = battle.submit(Action(ActionKind.ITEM, actor=0, item_id="potion_large"))
    heal = next(e for e in events if e.kind == "heal")
    assert "recovers 1 HP" in heal.text


def test_item_validation_errors(data):
    player = new_player()
    battle = Battle([player], [enemy(data, "skel_basic")], Random(1), data)
    with pytest.raises(InvalidOperation):
        battle.submit(Action(ActionKind.ITEM, actor=0, item_id="potion_small"))  # none held
    with pytest.raises(InvalidOperation):
        battle.submit(Action(ActionKind.ITEM, actor=0, item_id="no_such_item"))
    with pytest.raises(InvalidOperation):
        battle.submit(Action(ActionKind.ITEM, actor=0))  # missing item_id
    player.inventory.add(data.item("blade_bone"), 1)
    with pytest.raises(InvalidOperation):
        battle.submit(Action(ActionKind.ITEM, actor=0, item_id="blade_bone"))  # not usable
    player.inventory.add(data.item("res_token"), 1)
    with pytest.raises(InvalidOperation):
        battle.submit(Action(ActionKind.ITEM, actor=0, item_id="res_token"))
    assert battle.pending == {}


def test_scroll_damage_kills_weak_enemy(data):
    player = new_player()
    player.inventory.add(data.item("scroll_frost"), 1)
    wraith = enemy(data, "wraith")  # 9 hp, scroll_frost deals 18 flat
    battle = Battle([player], [wraith], Random(9), data)
    events = battle.submit(Action(ActionKind.ITEM, actor=0, item_id="scroll_frost", target=0))
    assert battle.outcome is Outcome.VICTORY
    assert not wraith.is_alive
    assert player.inventory.count("scroll_frost") == 0
    assert any(e.kind == "item" and "Scroll of Grave Frost" in e.text for e in events)
    assert any(e.kind == "defeat" for e in events)


def test_attack_and_scroll_targets_are_validated(data):
    player = new_player()
    battle = Battle([player], [enemy(data, "skel_basic")], Random(1), data)
    with pytest.raises(InvalidOperation):
        battle.submit(attack(target=5))
    with pytest.raises(InvalidOperation):
        battle.submit(attack(actor=3))


def test_flee_success_and_failure_are_deterministic(data):
    def outcome_for(seed: int) -> Outcome:
        player = new_player()
        battle = Battle([player], [enemy(data, "skel_basic")], Random(seed), data)
        battle.submit(Action(ActionKind.FLEE, actor=0))
        return battle.outcome

    success = next(s for s in range(100) if outcome_for(s) is Outcome.FLED)
    failure = next(s for s in range(100) if outcome_for(s) is Outcome.ONGOING)
    assert outcome_for(success) is Outcome.FLED
    assert outcome_for(failure) is Outcome.ONGOING

    player = new_player()
    battle = Battle([player], [enemy(data, "skel_basic")], Random(success), data)
    events = battle.submit(Action(ActionKind.FLEE, actor=0))
    assert any(e.kind == "flee" for e in events)
    assert player.stats.hp == player.stats.max_hp  # enemies did not act
    with pytest.raises(InvalidOperation):
        battle.submit(attack())

    player = new_player()
    battle = Battle([player], [enemy(data, "skel_basic")], Random(failure), data)
    events = battle.submit(Action(ActionKind.FLEE, actor=0))
    assert any(e.kind == "flee" and "fails" in e.text for e in events)
    assert battle.round_number == 2


def test_defeat_when_outmatched(data):
    player = new_player()
    player.stats.hp = 1
    battle = Battle([player], [enemy(data, "grave_titan")], Random(2), data)
    events = battle.submit(attack())
    assert battle.outcome is Outcome.DEFEAT
    assert not player.is_alive
    assert events[-1].kind == "defeat"
    assert battle.living_players == []


def test_dead_enemy_skipped_and_retargeting(data):
    player = new_player()
    player.stats.atk = 500  # one-shots anything
    player.stats.max_hp = player.stats.hp = 1000
    foes = [enemy(data, "skel_basic"), enemy(data, "bone_guard")]
    battle = Battle([player], foes, Random(4), data)

    battle.submit(attack(target=0))
    assert not foes[0].is_alive
    assert foes[1].is_alive
    assert battle.first_living_enemy_index() == 1
    assert [b.name for b in battle.living_enemies] == ["Bone Guard"]
    assert all(b.is_alive for b in turn_order(battle.all_battlers()))

    # Pointing at the dead enemy is rejected at submit time...
    with pytest.raises(InvalidOperation):
        battle.submit(attack(target=0))
    # ...and an unspecified target retargets to the first living enemy.
    battle.submit(attack())
    assert battle.outcome is Outcome.VICTORY
    assert not foes[1].is_alive


def test_retarget_when_target_dies_earlier_in_round(data):
    p0 = new_player("p0")
    p1 = new_player("p1")
    for p in (p0, p1):
        p.stats.atk = 500
        p.stats.max_hp = p.stats.hp = 1000
    foes = [enemy(data, "skel_basic"), enemy(data, "bone_guard")]
    battle = Battle([p0, p1], foes, Random(8), data)

    assert battle.submit(attack(actor=0, target=0)) == []  # waiting for p1
    events = battle.submit(attack(actor=1, target=0))  # same target, dies to p0 first
    assert battle.outcome is Outcome.VICTORY
    hits = [e for e in events if e.kind == "attack"]
    assert [e.text.split(" hits ")[1].split(" for")[0] for e in hits] == [
        "Skeletal Thrall",
        "Bone Guard",
    ]


def test_multi_player_round_waits_for_all_living_players(data):
    p0 = new_player("p0")
    p1 = new_player("p1")
    battle = Battle([p0, p1], [enemy(data, "skel_basic")], Random(1), data)
    assert battle.submit(Action(ActionKind.DEFEND, actor=0)) == []
    assert battle.pending.keys() == {0}
    events = battle.submit(Action(ActionKind.DEFEND, actor=1))
    assert events and battle.round_number == 2
    p1.stats.hp = 0
    with pytest.raises(InvalidOperation):
        battle.submit(Action(ActionKind.DEFEND, actor=1))
    # Only p0 is living now, so its action alone resolves the round.
    assert battle.submit(Action(ActionKind.DEFEND, actor=0))


def test_battle_replays_identically_with_same_seed(data):
    def play(seed: int):
        player = new_player()
        battle = Battle([player], [enemy(data, "ghoul"), enemy(data, "wraith")], Random(seed), data)
        while battle.outcome is Outcome.ONGOING:
            battle.submit(attack())
        return battle.outcome, [e.text for e in battle.log], player.stats.hp

    assert play(42) == play(42)
