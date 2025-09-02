import pytest

from amor_mortuorum.game.interactables import Door
from amor_mortuorum.game.items import KEY_ITEM_ID
from amor_mortuorum.game.inventory import SimpleInventory, ActorWithInventory


class TestLockedDoors:
    def test_attempt_without_key_blocks(self):
        inv = SimpleInventory()
        actor = ActorWithInventory(name="Hero", inventory=inv)
        door = Door(position=(3, 7))

        result = door.attempt_pass(actor)

        assert result.allowed is False
        assert result.consumed_key is False
        assert result.was_open is False
        assert "locked" in result.message.lower()
        assert inv.get_item_count(KEY_ITEM_ID) == 0
        assert door.is_passable() is False

    def test_attempt_with_key_consumes_and_opens(self):
        inv = SimpleInventory({KEY_ITEM_ID: 1})
        actor = ActorWithInventory(name="Hero", inventory=inv)
        door = Door(position=(1, 2))

        result = door.attempt_pass(actor)

        assert result.allowed is True
        assert result.consumed_key is True
        assert result.was_open is False
        assert inv.get_item_count(KEY_ITEM_ID) == 0
        assert door.is_passable() is True

    def test_open_door_allows_pass_without_consumption(self):
        inv = SimpleInventory({KEY_ITEM_ID: 1})
        actor = ActorWithInventory(name="Hero", inventory=inv)
        door = Door(position=(0, 0))

        # First pass consumes a key and opens the door
        first = door.attempt_pass(actor)
        assert first.allowed is True
        assert first.consumed_key is True
        assert inv.get_item_count(KEY_ITEM_ID) == 0
        assert door.is_passable() is True

        # Second pass should not require a key
        second = door.attempt_pass(actor)
        assert second.allowed is True
        assert second.consumed_key is False
        assert second.was_open is True
        assert inv.get_item_count(KEY_ITEM_ID) == 0

    def test_multiple_keys_only_one_consumed_on_open(self):
        inv = SimpleInventory({KEY_ITEM_ID: 5})
        actor = ActorWithInventory(name="Hero", inventory=inv)
        door = Door(position=(9, 9))

        result = door.attempt_pass(actor)
        assert result.allowed is True
        assert result.consumed_key is True
        assert inv.get_item_count(KEY_ITEM_ID) == 4

    def test_actor_direct_inventory_protocol_supported(self):
        class DirectInventoryActor(SimpleInventory):
            pass

        actor = DirectInventoryActor({KEY_ITEM_ID: 1})
        door = Door(position=(10, 10))

        res = door.attempt_pass(actor)
        assert res.allowed is True
        assert res.consumed_key is True
        assert actor.get_item_count(KEY_ITEM_ID) == 0

    def test_consume_race_condition_guard(self):
        class FlakyInventory(SimpleInventory):
            def consume_item(self, item_id: str, qty: int = 1) -> None:
                # simulate a rare race condition / bug elsewhere
                raise ValueError("Simulated failure")

        inv = FlakyInventory({KEY_ITEM_ID: 1})
        actor = ActorWithInventory(name="Hero", inventory=inv)
        door = Door(position=(5, 4))

        result = door.attempt_pass(actor)
        assert result.allowed is False
        assert result.consumed_key is False
        assert door.is_passable() is False
        # Count unchanged due to failure
        assert inv.get_item_count(KEY_ITEM_ID) == 1
