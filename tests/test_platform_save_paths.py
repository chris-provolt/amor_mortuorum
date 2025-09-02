import os
import sys
from pathlib import Path

import importlib
import types

import pytest


MODULE = "amor_mortuorum.platform.save_paths"


def reload_module():
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    return importlib.import_module(MODULE)


def test_non_portable_linux_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("AMOR_PORTABLE", "0")
    # Simulate non-frozen
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    # Simulate Linux
    import platform as _platform

    monkeypatch.setattr(_platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", "")

    m = reload_module()

    root = m.get_user_data_root()
    # Should be ~/.local/share/amor-mortuorum
    expected = Path.home() / ".local" / "share" / m.APP_SLUG
    assert root == expected
    assert root.exists()

    # Child dirs
    assert m.get_save_dir().is_dir()
    assert m.get_config_dir().is_dir()
    assert m.get_cache_dir().is_dir()
    assert m.get_logs_dir().is_dir()


def test_non_portable_linux_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("AMOR_PORTABLE", "0")
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    import platform as _platform

    monkeypatch.setattr(_platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    m = reload_module()

    root = m.get_user_data_root()
    assert root == tmp_path / "xdg" / m.APP_SLUG
    assert root.exists()


def test_windows_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("AMOR_PORTABLE", "0")
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    import platform as _platform

    monkeypatch.setattr(_platform, "system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))

    m = reload_module()

    root = m.get_user_data_root()
    assert root == tmp_path / "Roaming" / m.APP_NAME
    assert root.exists()


def test_macos_support_dir(monkeypatch):
    monkeypatch.setenv("AMOR_PORTABLE", "0")
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    import platform as _platform

    monkeypatch.setattr(_platform, "system", lambda: "Darwin")

    m = reload_module()

    root = m.get_user_data_root()
    assert str(root).endswith("Library/Application Support/Amor Mortuorum")


def test_portable_mode_via_env(monkeypatch, tmp_path):
    # Simulate a frozen app in tmp_path
    fake_exe = tmp_path / "AmorMortuorum.exe"
    fake_exe.write_text("bin")

    monkeypatch.setenv("AMOR_PORTABLE", "1")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    m = reload_module()

    assert m.portable_mode_enabled() is True

    root = m.get_user_data_root()
    assert root == tmp_path / "userdata"
    assert root.exists()

    # Verify subdirectories are inside portable root
    assert m.get_save_dir().is_relative_to(root)
    assert m.get_config_dir().is_relative_to(root)


def test_portable_mode_via_flag(monkeypatch, tmp_path):
    # Non-frozen with flag in CWD
    flag = tmp_path / "portable_mode.flag"
    flag.write_text("on")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AMOR_PORTABLE", "0")
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    m = reload_module()

    assert m.portable_mode_enabled() is True
    assert m.get_user_data_root() == tmp_path / "userdata"


@pytest.mark.parametrize("val", ["true", "True", "YES", "on"])
def test_portable_truthy_values(monkeypatch, tmp_path, val):
    fake_exe = tmp_path / "AmorMortuorum"
    fake_exe.write_text("bin")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    monkeypatch.setenv("AMOR_PORTABLE", val)
    m = reload_module()
    assert m.portable_mode_enabled() is True
