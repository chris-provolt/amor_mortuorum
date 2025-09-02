from __future__ import annotations

import json
from pathlib import Path
from typing import List
from unittest import mock

import pytest

from amormortuorum.core.scenes import Scene
from amormortuorum.save.manager import SaveManager
from amormortuorum.save.model import SaveMeta
from amormortuorum.save.storage import SaveStorage
from amormortuorum.ui.toast import ToastManager


@pytest.fixture()
def storage(tmp_path: Path) -> SaveStorage:
    return SaveStorage(root=tmp_path)


@pytest.fixture()
def toasts() -> ToastManager:
    return ToastManager()


@pytest.fixture()
def manager(storage: SaveStorage, toasts: ToastManager) -> SaveManager:
    return SaveManager(storage=storage, ui_toasts=toasts)


def make_meta(**overrides) -> SaveMeta:
    defaults = dict(gold=123, relics=["veil_shard"], crypt_items=["potion"], player_level=4, depth=0)
    defaults.update(overrides)
    return SaveMeta(**defaults)


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_save_in_dungeon_shows_notice_and_does_not_write_file(manager: SaveManager, storage: SaveStorage, toasts: ToastManager):
    meta = make_meta(depth=12)

    result = manager.request_save(scene=Scene.DUNGEON, meta=meta)

    assert result.success is False
    assert result.wrote_meta is False
    assert result.code == "NOT_IN_GRAVEYARD"
    # Non-blocking notice posted
    assert toasts.last_message is not None
    assert toasts.last_message.text == manager.NOTICE_NOT_IN_GRAVEYARD
    assert toasts.last_message.level == "warning"
    # No file created
    assert not storage.meta_path.exists()


def test_save_in_graveyard_writes_meta_and_posts_success(manager: SaveManager, storage: SaveStorage, toasts: ToastManager):
    meta = make_meta(depth=0)

    result = manager.request_save(scene=Scene.GRAVEYARD, meta=meta)

    assert result.success is True
    assert result.wrote_meta is True
    assert result.code == "OK"
    # Success toast posted
    assert toasts.last_message is not None
    assert toasts.last_message.text == manager.NOTICE_SAVE_SUCCESS
    assert toasts.last_message.level == "success"
    # File written with expected keys
    assert storage.meta_path.exists()
    data = read_json(storage.meta_path)
    for key in ["gold", "relics", "crypt_items", "player_level", "depth", "version", "timestamp"]:
        assert key in data


def test_save_io_error_is_handled_with_error_toast(manager: SaveManager, storage: SaveStorage, toasts: ToastManager):
    meta = make_meta(depth=0)

    with mock.patch.object(storage, "write_meta", side_effect=OSError("disk full")):
        result = manager.request_save(scene=Scene.GRAVEYARD, meta=meta)

    assert result.success is False
    assert result.wrote_meta is False
    assert result.code == "IO_ERROR"
    assert toasts.last_message is not None
    assert toasts.last_message.text == manager.NOTICE_SAVE_ERROR
    assert toasts.last_message.level == "error"
