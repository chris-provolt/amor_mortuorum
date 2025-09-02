from amor_mortuorum.economy.events import EventBus
from amor_mortuorum.economy.wallet import GoldWallet
from amor_mortuorum.economy.rewards import CombatRewardCalculator, ChestRewardCalculator, Enemy
from amor_mortuorum.economy.config import EconomyConfig


def test_combat_reward_adds_gold_depth_scaling():
    bus = EventBus()
    wallet = GoldWallet(event_bus=bus)

    cfg = EconomyConfig(depth_gold_scale_base=1.0, depth_gold_scale_per_floor=0.02)
    calc = CombatRewardCalculator(config=cfg)

    enemies = [Enemy(gold_value=5, name="Slime"), Enemy(gold_value=7, name="Bat")]
    # base_sum = 12; depth=10 => scale=1 + 0.2 = 1.2; gold=14 (rounded)
    gold = calc.award_combat_gold(wallet, enemies, depth=10)

    assert gold == 14
    assert wallet.amount == 14


def test_chest_reward_adds_gold_by_quality_and_depth():
    bus = EventBus()
    wallet = GoldWallet(event_bus=bus)

    cfg = EconomyConfig(base_chest_gold=10, chest_gold_per_floor=2)
    chest_calc = ChestRewardCalculator(config=cfg)

    # depth=5 => base 10 + 10 = 20; rich multiplier 1.75 => 35
    gold = chest_calc.award_chest_gold(wallet, quality="rich", depth=5)
    assert gold == 35
    assert wallet.amount == 35

    # poor at depth 0 => base 10 * 0.5 = 5
    gold2 = chest_calc.award_chest_gold(wallet, quality="poor", depth=0)
    assert gold2 == 5
    assert wallet.amount == 40
