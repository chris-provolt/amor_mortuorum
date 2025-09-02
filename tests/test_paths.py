from __future__ import annotations

import os
from pathlib import Path

import pytest

from amormortuorum.io.paths import AppPaths, initialize_app_paths


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    # Force platform directories to use our temp dirs via overrides
    config = tmp_path / "user_config"
    data = tmp_path / "user_data"
    logs = tmp_path / "user_logs"
    cache = tmp_path / "user_cache"
    monkeypatch.setenv("AMOR_CONFIG_DIR", str(config))
    monkeypatch.setenv("AMOR_SAVE_DIR", str(data / "saves"))
    monkeypatch.setenv("AMOR_LOG_DIR", str(logs))
    monkeypatch.setenv("AMOR_CACHE_DIR", str(cache))
    return {
        "config": config,
        "data": data,
        "logs": logs,
        "cache": cache,
    }


def test_environment_overrides_are_used(tmp_env):
    paths = AppPaths()
    paths.ensure_dirs()

    assert paths.config_dir == tmp_env["config"].resolve()
    assert paths.save_dir == (tmp_env["data"] / "saves").resolve()
    assert paths.log_dir == tmp_env["logs"].resolve()
    assert paths.cache_dir == tmp_env["cache"].resolve()

    # Ensure directories exist
    assert paths.config_dir.exists()
    assert paths.save_dir.exists()
    assert paths.log_dir.exists()
    assert paths.cache_dir.exists()


def test_migrate_from_scaffold_config_and_saves(tmp_path, tmp_env):
    # Create a scaffold layout
    scaffold = tmp_path / "project"
    configs = scaffold / "configs"
    saves = scaffold / "data" / "saves"
    configs.mkdir(parents=True)
    saves.mkdir(parents=True)

    # Create sample files
    (configs / "settings.yaml").write_text("foo: 1\n", encoding="utf-8")
    (saves / "slot1.sav").write_text("SAVE_DATA", encoding="utf-8")

    paths = initialize_app_paths(scaffold)

    # Files should be migrated
    assert (paths.config_dir / "settings.yaml").exists()
    assert (paths.save_dir / "slot1.sav").exists()

    # Source should be pruned if empty
    assert not configs.exists() or not any(configs.iterdir())
    # Saves parent may still exist, but saves directory should be pruned or empty
    assert not saves.exists() or not any(saves.iterdir())


def test_migration_is_conservative_on_conflicts(tmp_path, tmp_env):
    scaffold = tmp_path / "project"
    (scaffold / "configs").mkdir(parents=True)

    # Destination already has a settings.yaml with new content
    paths = AppPaths()
    paths.ensure_dirs()

    dest_settings = paths.config_dir / "settings.yaml"
    dest_settings.write_text("foo: NEW\n", encoding="utf-8")

    # Source has conflicting file
    src_settings = scaffold / "configs" / "settings.yaml"
    src_settings.write_text("foo: OLD\n", encoding="utf-8")

    result = paths.migrate_from_scaffold(scaffold)

    # Destination file should be preserved
    assert dest_settings.read_text(encoding="utf-8") == "foo: NEW\n"
    # A migrated copy should exist with suffix
    migrated_candidates = list(paths.config_dir.glob("settings.yaml.migrated.*"))
    assert len(migrated_candidates) == 1

    # Migration result should report activity
    assert result.migrated is True


def test_identical_files_result_in_skip(tmp_path, tmp_env):
    # Setup identical file in dest and src
    scaffold = tmp_path / "project"
    (scaffold / "configs").mkdir(parents=True)

    paths = AppPaths()
    paths.ensure_dirs()

    src = scaffold / "configs" / "keybinds.json"
    dst = paths.config_dir / "keybinds.json"

    content = '{"a":"b"}\n'
    src.write_text(content, encoding="utf-8")
    dst.write_text(content, encoding="utf-8")

    result = paths.migrate_from_scaffold(scaffold)

    # No migrated copy should be created, destination preserved, source removed
    assert dst.exists()
    assert not src.exists()
    # Verify at least one action had a skipped file
    assert any(a.skipped_files for a in result.actions)


def test_saves_migration_from_top_level_saves_dir(tmp_path, tmp_env):
    scaffold = tmp_path / "project"
    (scaffold / "saves").mkdir(parents=True)
    (scaffold / "saves" / "slot2.sav").write_text("DATA", encoding="utf-8")

    paths = AppPaths()
    paths.ensure_dirs()

    paths.migrate_from_scaffold(scaffold)

    assert (paths.save_dir / "slot2.sav").exists()
