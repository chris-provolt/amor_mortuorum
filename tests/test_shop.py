from amor_mortuorum.economy.events import EventBus, PurchaseCompletedEvent, PurchaseFailedEvent
from amor_mortuorum.economy.wallet import GoldWallet
from amor_mortuorum.economy.config import EconomyConfig
from amor_mortuorum.shop.shop import ShopService
from amor_mortuorum.shop.models import ShopItem


def test_shop_purchase_spends_gold_and_emits_events():
    bus = EventBus()
    wallet = GoldWallet(event_bus=bus)
    wallet.set(50)

    shop = ShopService(wallet=wallet, event_bus=bus, config=EconomyConfig(shop_price_modifier=1.0))
    shop.set_inventory({
        "potion": ShopItem(item_id="potion", name="Minor Potion", base_cost=30),
        "scroll": ShopItem(item_id="scroll", name="Fire Scroll", base_cost=60),
    })

    completed = []
    failed = []
    bus.subscribe(PurchaseCompletedEvent, lambda e: completed.append(e))
    bus.subscribe(PurchaseFailedEvent, lambda e: failed.append(e))

    receipt = shop.purchase("potion")
    assert receipt.success is True
    assert wallet.amount == 20
    assert len(completed) == 1
    assert completed[0].item_id == "potion" and completed[0].cost == 30 and completed[0].remaining_gold == 20
    assert len(failed) == 0

    # Now attempt purchase too expensive
    receipt2 = shop.purchase("scroll")
    assert receipt2.success is False
    assert wallet.amount == 20
    assert len(failed) == 1
    assert failed[0].item_id == "scroll" and failed[0].reason == "insufficient_gold"

    # Unknown item
    receipt3 = shop.purchase("unknown")
    assert receipt3.success is False
    assert len(failed) == 2
    assert failed[1].reason == "not_found"
