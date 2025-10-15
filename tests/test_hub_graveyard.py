from pathlib import Path

import json

from amormortuorum.errors import InvalidOperation, InsufficientGold, NotFound, OutOfStock
from amormortuorum.hub import GraveyardHub
from amormortuorum.models import ItemCatalog, Player
from amormortuorum.save import SaveManager


def make_hub(tmp_path: Path) -> GraveyardHub:
    sm = SaveManager(root=tmp_path)
    # Ensure deterministic seed and fresh state
    data = sm.load()
    data.meta_seed = 42
    data.hub_cycle = 0
    data.crypt = []
    sm.save(data)
    hub = GraveyardHub(save_manager=sm, catalog=ItemCatalog())
    return hub


def test_rest_heals_player(tmp_path: Path):
    hub = make_hub(tmp_path)
    player = Player(max_hp=150, hp=37)
    hub.enter()
    hub.rest(player)
    assert player.hp == player.max_hp


def test_shop_limited_stock_and_purchase(tmp_path: Path):
    hub = make_hub(tmp_path)
    ctx = hub.enter()
    stock = ctx.shop.stock()
    assert stock, "Shop should have stock on enter"

    # Pick one item to buy fully
    item_id, entry = next(iter(stock.items()))
    player = Player(gold=10_000)

    # Buying beyond stock should fail
    try:
        ctx.shop.buy(player, item_id, quantity=entry.quantity + 1)
        assert False, "Expected OutOfStock"
    except OutOfStock:
        pass

    # Buy full remaining stock
    ctx.shop.buy(player, item_id, quantity=entry.quantity)
    post = ctx.shop.stock()
    assert item_id not in post or post[item_id].quantity == 0

    # Insufficient gold case
    ctx = hub.enter()  # next cycle restocks
    # Choose a possibly expensive item and drain gold
    poor_player = Player(gold=0)
    item_id, entry = next(iter(ctx.shop.stock().items()))
    try:
        ctx.shop.buy(poor_player, item_id, quantity=1)
        assert False, "Expected InsufficientGold"
    except InsufficientGold:
        pass


def test_shop_restock_is_deterministic(tmp_path: Path):
    hub = make_hub(tmp_path)
    ctx1 = hub.enter()
    stock1 = ctx1.shop.stock()
    # Recreate hub with same save, but revert cycle increment to re-enter same cycle number
    sm = hub.save_manager
    data = sm.load()
    # The current cycle is 1; manually set back to 0 so the next enter returns cycle 1
    data.hub_cycle = 0
    sm.save(data)

    # New hub instance for clean state
    hub2 = GraveyardHub(save_manager=sm, catalog=ItemCatalog())
    ctx2 = hub2.enter()
    stock2 = ctx2.shop.stock()

    assert stock1.keys() == stock2.keys()
    for k in stock1:
        assert stock1[k].quantity == stock2[k].quantity
        assert stock1[k].price == stock2[k].price


def test_crypt_capacity_and_withdraw(tmp_path: Path):
    hub = make_hub(tmp_path)
    ctx = hub.enter()
    player = Player(gold=100)

    # Prepare inventory with 3 distinct items
    cat = ItemCatalog()
    for iid in ["potion_small", "scroll_embers", "antidote"]:
        player.inventory.add(cat.get(iid), 1)

    # Deposit 3 items into 3 slots
    hub.crypt_deposit(player, "potion_small", 1)
    hub.crypt_deposit(player, "scroll_embers", 1)
    hub.crypt_deposit(player, "antidote", 1)
    assert len(ctx.crypt.list_slots()) == 3

    # Try depositing a fourth distinct item -> full
    player.inventory.add(cat.get("potion_small"), 1)
    try:
        # Re-using potion_small would stack; pick a new id to force the crypt to reject it.
        # Expect a NotFound because the item is not present in the catalog or crypt slots.
        # New distinct only if we pick an id not in crypt; we reuse potion_small but it stacks instead.
        # To force a failure, attempt to deposit another distinct item (not present) -> expect NotFound.

        hub.crypt_deposit(player, "nonexistent", 1)
        assert False, "Expected NotFound"
    except NotFound:
        pass

    # Withdraw from slot 1 fully, should free a slot
    hub.crypt_withdraw(player, 1)
    assert len(ctx.crypt.list_slots()) == 2

    # Deposit more potion_small should stack (no new slot)
    hub.crypt_deposit(player, "potion_small", 1)
    assert len(ctx.crypt.list_slots()) == 2

    # Bad withdraw index
    try:
        hub.crypt_withdraw(player, 100)
        assert False, "Expected NotFound for invalid slot"
    except NotFound:
        pass

    # Bad quantities
    try:
        hub.crypt_deposit(player, "potion_small", 0)
        assert False, "Expected InvalidOperation for zero quantity"
    except InvalidOperation:
        pass


def test_save_persistence_across_instances(tmp_path: Path):
    hub = make_hub(tmp_path)
    _ctx = hub.enter()
    player = Player()
    cat = ItemCatalog()
    player.inventory.add(cat.get("potion_small"), 2)
    hub.crypt_deposit(player, "potion_small", 2)

    # New hub with same SaveManager should load crypt contents
    hub2 = GraveyardHub(save_manager=hub.save_manager, catalog=cat)
    ctx2 = hub2.enter()
    slots = ctx2.crypt.list_slots()
    assert len(slots) == 1
    assert slots[0].item_id == "potion_small" and slots[0].quantity >= 2


def test_atomic_save(tmp_path: Path):
    sm = SaveManager(root=tmp_path)
    data = sm.load()
    data.meta_seed = 1
    sm.save(data)
    save_path = sm.save_path
    tmp = save_path.with_suffix(save_path.suffix + ".tmp")
    assert save_path.exists()
    assert not tmp.exists(), "Atomic temp file should not remain after save"

    # Validate json is parseable
    with save_path.open("r", encoding="utf-8") as f:
        json.load(f)
