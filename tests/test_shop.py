from pathlib import Path

import pytest

from amormortuorum.economy.shop import Shop
from amormortuorum.economy.wallet import Wallet
from amormortuorum.runtime.exceptions import InsufficientFundsError, OutOfStockError, UnknownItemError, ValidationError
from amormortuorum.runtime.run_state import RunState


FIXTURE_INVENTORY = Path("configs/shop/inventory.json")


def make_shop_with_gold(gold: int) -> Shop:
    run_state = RunState()
    wallet = Wallet(initial_gold=gold)
    shop = Shop(FIXTURE_INVENTORY, run_state, wallet)
    return shop


def test_purchase_deducts_gold_and_decrements_stock(tmp_path):
    shop = make_shop_with_gold(200)

    # Ensure stock before purchase
    stock_before = {x["id"]: x for x in shop.get_stock()}
    assert stock_before["potion_small"]["remaining"] == 5

    receipt = shop.purchase("potion_small", qty=2)

    assert receipt.item_id == "potion_small"
    assert receipt.quantity == 2
    assert receipt.unit_price == 25
    assert receipt.total_spent == 50

    # Gold deducted
    assert shop.wallet.gold == 150

    # Stock decremented
    stock_after = {x["id"]: x for x in shop.get_stock()}
    assert stock_after["potion_small"]["remaining"] == 3


def test_purchase_insufficient_gold_message():
    shop = make_shop_with_gold(10)

    with pytest.raises(InsufficientFundsError) as exc:
        shop.purchase("potion_small", qty=1)

    assert "need" in str(exc.value).lower()
    assert "gold" in str(exc.value).lower()


def test_purchase_out_of_stock_message():
    shop = make_shop_with_gold(1000)

    # Try buying more than available
    with pytest.raises(OutOfStockError) as exc:
        shop.purchase("scroll_fire", qty=5)  # only 2 in stock

    assert "remain in stock" in str(exc.value)


def test_stock_resets_only_on_new_run():
    run_state = RunState()
    wallet = Wallet(initial_gold=1000)
    shop = Shop(FIXTURE_INVENTORY, run_state, wallet)

    # Buy all antidotes (3)
    shop.purchase("antidote", qty=3)

    # Ensure no more in this run
    with pytest.raises(OutOfStockError):
        shop.purchase("antidote", qty=1)

    # Not restocked yet
    remaining_before = {x["id"]: x for x in shop.get_stock()}["antidote"]["remaining"]
    assert remaining_before == 0

    # Start a new run -> should restock
    run_state.start_new_run()

    remaining_after = {x["id"]: x for x in shop.get_stock()}["antidote"]["remaining"]
    assert remaining_after == 3


def test_unknown_item_and_validation_errors():
    shop = make_shop_with_gold(100)

    with pytest.raises(UnknownItemError):
        shop.purchase("nonexistent", qty=1)

    with pytest.raises(ValidationError):
        shop.purchase("potion_small", qty=0)

    with pytest.raises(ValidationError):
        shop.purchase("potion_small", qty=-5)
