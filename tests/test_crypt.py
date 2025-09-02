from pathlib import Path

from amormortuorum.progression.crypt import Crypt


def test_crypt_capacity_and_deposit_withdraw(tmp_path: Path):
    crypt = Crypt(capacity=3, save_dir=tmp_path)

    crypt.deposit("Potion")
    crypt.deposit({"name": "Hi-Potion", "rarity": 2})
    crypt.deposit({"id": "X001", "power": 99})

    assert crypt.is_full()
    assert crypt.space_left() == 0
    assert len(crypt.items) == 3

    # Attempt to overfill
    try:
        crypt.deposit("Elixir")
    except ValueError as e:
        assert "full" in str(e)
    else:
        assert False, "Expected ValueError when depositing into a full crypt"

    # Withdraw by index
    item0 = crypt.withdraw(0)
    assert item0["name"] == "Potion"
    assert len(crypt.items) == 2

    # Withdraw by name (the item created from id has name derived from id)
    item_named = crypt.withdraw("X001")
    assert item_named["name"] == "X001"
    assert len(crypt.items) == 1

    # Persistence check: new instance should see the same remaining items
    crypt2 = Crypt(capacity=3, save_dir=tmp_path)
    assert len(crypt2.items) == 1
    assert crypt2.items[0]["name"] == "Hi-Potion"

    # Clear and confirm
    crypt2.clear()
    crypt3 = Crypt(capacity=3, save_dir=tmp_path)
    assert len(crypt3.items) == 0


def test_invalid_inputs(tmp_path: Path):
    crypt = Crypt(capacity=2, save_dir=tmp_path)

    try:
        crypt.deposit({"power": 10})
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError for item without name or id"

    # Withdraw with bad selectors
    crypt.deposit("A")
    try:
        crypt.withdraw(5)
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError for invalid index"

    try:
        crypt.withdraw("unknown")
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError for unknown name"
