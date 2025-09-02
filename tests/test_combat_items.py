import os
import sys

# Ensure the 'src' directory is on the PYTHONPATH for test execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest

from amor_mortuorum.combat.actions import UseItemAction
from amor_mortuorum.combat.context import CombatContext, Combatant
from amor_mortuorum.exceptions import ItemUseError


@pytest.fixture()
def setup_battle():
    hero = Combatant(name="Hero", hp=50, hp_max=100, mp=10, mp_max=50)
    slime = Combatant(name="Slime", hp=80, hp_max=80, mp=0, mp_max=0)
    ctx = CombatContext(team_a=[hero], team_b=[slime])

    # Provide starting items
    hero.inventory.add("potion_hp_small", 2)
    hero.inventory.add("potion_mp_small", 1)
    hero.inventory.add("scroll_fire", 1)
    hero.inventory.add("scroll_heal", 1)

    return ctx, hero, slime


def test_use_healing_potion_on_self(setup_battle):
    ctx, hero, _ = setup_battle
    # Hero uses healing potion on self; should heal up to +50 but max at 100
    action = UseItemAction(actor=hero, item_id="potion_hp_small")
    action.execute(ctx)

    assert hero.hp == 100  # 50 + 50 -> 100 (max)
    assert hero.inventory.quantity("potion_hp_small") == 1
    assert any("uses Minor Healing Potion" in line for line in ctx.log)
    assert any("recovers" in line and "HP" in line for line in ctx.log)


def test_use_mp_potion_on_self(setup_battle):
    ctx, hero, _ = setup_battle
    # Spend some MP then restore
    hero.mp = 15
    action = UseItemAction(actor=hero, item_id="potion_mp_small")
    action.execute(ctx)

    assert hero.mp == 45  # 15 + 30 -> 45
    assert hero.inventory.quantity("potion_mp_small") == 0
    assert any("recovers" in line and "MP" in line for line in ctx.log)


def test_use_scroll_fire_on_enemy(setup_battle):
    ctx, hero, slime = setup_battle
    action = UseItemAction(actor=hero, item_id="scroll_fire", target=slime)
    action.execute(ctx)

    assert slime.hp == 40  # 80 - 40
    assert hero.inventory.quantity("scroll_fire") == 0
    # Ensure log mentions fire damage
    assert any("fire" in line.lower() and "takes" in line.lower() for line in ctx.log)


def test_use_scroll_heal_on_ally(setup_battle):
    ctx, hero, slime = setup_battle
    # Add an ally with missing HP
    ally = Combatant(name="Cleric", hp=20, hp_max=100, mp=30, mp_max=50)
    ctx.team_a.append(ally)

    action = UseItemAction(actor=hero, item_id="scroll_heal", target=ally)
    action.execute(ctx)

    assert ally.hp == 60
    assert hero.inventory.quantity("scroll_heal") == 0


def test_cannot_use_item_not_in_inventory(setup_battle):
    ctx, hero, slime = setup_battle
    # Deplete the only MP potion
    hero.inventory.consume("potion_mp_small")

    with pytest.raises(ItemUseError):
        UseItemAction(actor=hero, item_id="potion_mp_small").execute(ctx)


def test_invalid_target_type_raises(setup_battle):
    ctx, hero, slime = setup_battle
    # Healing scroll can't target enemy
    with pytest.raises(ItemUseError):
        UseItemAction(actor=hero, item_id="scroll_heal", target=slime).execute(ctx)


def test_cannot_target_dead_unit(setup_battle):
    ctx, hero, slime = setup_battle
    # Kill slime, then attempt to target it with fire scroll again
    slime.hp = 0
    with pytest.raises(ItemUseError):
        UseItemAction(actor=hero, item_id="scroll_fire", target=slime).execute(ctx)
