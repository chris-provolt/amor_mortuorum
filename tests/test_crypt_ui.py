from __future__ import annotations

import pytest

from src.amormortuorum.configs.defaults import CRYPT_CAPACITY
from src.amormortuorum.core.models import Item, Inventory
from src.amormortuorum.persistence.save_manager import InMemorySaveManager
from src.amormortuorum.services.crypt_service import CryptService
from src.amormortuorum.ui.crypt_ui import CryptUI


@pytest.fixture()
def sample_inventory() -> Inventory:
    # Inventory with 4 items for capacity tests
    return Inventory(
        items=[
            Item(id="a", name="Apple"),
            Item(id="b", name="Bread"),
            Item(id="c", name="Cheese"),
            Item(id="d", name="Doughnut"),
        ]
    )


@pytest.fixture()
def crypt_ui(sample_inventory: Inventory) -> CryptUI:
    save = InMemorySaveManager()
    service = CryptService(inventory=sample_inventory, save_manager=save, capacity=CRYPT_CAPACITY)
    return CryptUI(service=service)


def test_initial_state_empty_crypt(crypt_ui: CryptUI) -> None:
    state = crypt_ui.get_state()
    assert state["crypt"] == []
    assert len(state["inventory"]) == 4


def test_store_with_capacity_limit(crypt_ui: CryptUI) -> None:
    # Store three items successfully
    assert crypt_ui.store(0).startswith("Stored ")
    assert crypt_ui.store(0).startswith("Stored ")  # indices shift as we pop from inventory
    assert crypt_ui.store(0).startswith("Stored ")

    # Attempt to store a fourth item should hit capacity and show exact message
    msg = crypt_ui.store(0)
    assert msg == "Crypt full"

    state = crypt_ui.get_state()
    assert len(state["crypt"]) == 3
    # One item should remain in inventory because the last store failed
    assert len(state["inventory"]) == 1


def test_withdraw_adds_to_inventory_and_removes_from_crypt(crypt_ui: CryptUI) -> None:
    # Preload crypt by storing two items
    crypt_ui.store(0)
    crypt_ui.store(0)
    state = crypt_ui.get_state()
    assert len(state["crypt"]) == 2
    inv_count_before = len(state["inventory"])  # 4 -> store 2 -> now 2

    # Withdraw the second item
    msg = crypt_ui.withdraw(1)
    assert msg.startswith("Withdrew ")

    state = crypt_ui.get_state()
    assert len(state["crypt"]) == 1
    assert len(state["inventory"]) == inv_count_before + 1


def test_invalid_indices_are_handled_gracefully(crypt_ui: CryptUI) -> None:
    # Invalid inventory index
    msg = crypt_ui.store(99)
    assert msg == "Invalid selection"

    # Invalid crypt index
    msg = crypt_ui.withdraw(0)
    assert msg == "Invalid selection"


def test_persistence_roundtrip_inmemory(sample_inventory: Inventory) -> None:
    # Use the same in-memory save manager to simulate persistence within session
    save = InMemorySaveManager()

    service1 = CryptService(inventory=sample_inventory, save_manager=save)
    ui1 = CryptUI(service1)
    ui1.store(0)
    ui1.store(0)
    state1 = ui1.get_state()
    assert len(state1["crypt"]) == 2

    # New service instance reading from the same save manager should see the same crypt
    new_inventory = Inventory(items=[Item(id="x", name="X")])
    service2 = CryptService(inventory=new_inventory, save_manager=save)
    ui2 = CryptUI(service2)
    state2 = ui2.get_state()
    assert state2["crypt"] == state1["crypt"]
