from pathlib import Path

import pytest

from amormortuorum.data import GameData
from amormortuorum.errors import CryptFull, InsufficientGold, InvalidOperation, NotFound, OutOfStock
from amormortuorum.persistence import SaveManager
from amormortuorum.systems.entities import new_player
from amormortuorum.systems.hub import GraveyardHub
from amormortuorum.systems.run import new_run


@pytest.fixture(scope="module")
def data():
    return GameData.load()


def make_hub(tmp_path: Path, data: GameData) -> GraveyardHub:
    sm = SaveManager(root_dir=tmp_path, profile_id="test")
    hub = GraveyardHub(sm, data)
    hub.meta.meta_seed = 42
    hub.meta.hub_cycle = 0
    return hub


def test_rest_heals_player(tmp_path, data):
    hub = make_hub(tmp_path, data)
    player = new_player()
    player.take_damage(20)
    hub.enter()
    hub.rest(player)
    assert player.hp == player.max_hp


def test_shop_limited_stock_and_purchase(tmp_path, data):
    hub = make_hub(tmp_path, data)
    ctx = hub.enter()
    stock = ctx.shop.stock()
    assert stock, "Shop should have stock on enter"

    item_id, entry = next(iter(stock.items()))
    player = new_player()
    player.gold = 10_000

    with pytest.raises(OutOfStock):
        ctx.shop.buy(player, item_id, quantity=entry.quantity + 1)

    spent = ctx.shop.buy(player, item_id, quantity=entry.quantity)
    assert spent == entry.price * entry.quantity
    assert player.gold == 10_000 - spent
    assert player.inventory.count(item_id) == entry.quantity
    assert item_id not in ctx.shop.stock()

    ctx = hub.enter()  # next cycle restocks
    poor = new_player()
    poor.gold = 0
    item_id, entry = next(iter(ctx.shop.stock().items()))
    with pytest.raises(InsufficientGold):
        ctx.shop.buy(poor, item_id, quantity=1)


def test_shop_restock_is_deterministic(tmp_path, data):
    hub = make_hub(tmp_path, data)
    stock1 = hub.enter().shop.stock()

    # Re-enter the same cycle number with a fresh hub on the same save
    hub.meta.hub_cycle = 0
    hub.save_manager.save_meta(hub.meta)
    hub2 = GraveyardHub(hub.save_manager, data)
    stock2 = hub2.enter().shop.stock()

    assert stock1.keys() == stock2.keys()
    for k in stock1:
        assert (stock1[k].quantity, stock1[k].price) == (stock2[k].quantity, stock2[k].price)


def test_crypt_capacity_and_withdraw(tmp_path, data):
    hub = make_hub(tmp_path, data)
    ctx = hub.enter()
    player = new_player()
    for iid in ("potion_small", "scroll_embers", "antidote", "potion_medium"):
        player.inventory.add(data.item(iid), 1)

    hub.crypt_deposit(player, "potion_small", 1)
    hub.crypt_deposit(player, "scroll_embers", 1)
    hub.crypt_deposit(player, "antidote", 1)
    assert len(ctx.crypt.list_slots()) == 3
    assert ctx.crypt.is_full()

    with pytest.raises(CryptFull):
        hub.crypt_deposit(player, "potion_medium", 1)
    with pytest.raises(NotFound):
        hub.crypt_deposit(player, "nonexistent", 1)

    # Stacking into an existing slot still works when full
    player.inventory.add(data.item("potion_small"), 2)
    hub.crypt_deposit(player, "potion_small", 2)
    assert ctx.crypt.list_slots()[0].qty == 3

    hub.crypt_withdraw(player, 1)  # scroll_embers, full stack
    assert len(ctx.crypt.list_slots()) == 2
    assert player.inventory.count("scroll_embers") == 1

    with pytest.raises(NotFound):
        hub.crypt_withdraw(player, 100)
    with pytest.raises(InvalidOperation):
        hub.crypt_deposit(player, "potion_small", 0)


def test_crypt_persists_across_hub_instances(tmp_path, data):
    hub = make_hub(tmp_path, data)
    hub.enter()
    player = new_player()
    player.inventory.add(data.item("potion_small"), 2)
    hub.crypt_deposit(player, "potion_small", 2)

    hub2 = GraveyardHub(hub.save_manager, data)
    slots = hub2.enter().crypt.list_slots()
    assert len(slots) == 1
    assert slots[0].id == "potion_small" and slots[0].qty == 2
    assert hub2.meta.hub_cycle == 2


def test_save_and_load_run_only_from_graveyard(tmp_path, data):
    hub = make_hub(tmp_path, data)
    hub.enter()
    run = new_run(data, seed=77)
    run.floor = 4
    run.leader.take_damage(3)
    hub.save_run(run)

    hub2 = GraveyardHub(hub.save_manager, data)
    loaded = hub2.load_run()
    assert loaded is not None
    assert loaded.floor == 4 and loaded.seed == 77
    assert loaded.leader.hp == run.leader.hp

    hub2.end_run(loaded)
    assert hub2.load_run() is None
    assert hub2.meta.runs_completed == 1 and hub2.meta.deepest_floor == 4
    assert GraveyardHub(hub.save_manager, data).meta.runs_completed == 1
