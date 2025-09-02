from __future__ import annotations

import logging

from .logging_config import configure_logging
from .save_system import SaveManager
from .settings import SettingsManager

try:
    import arcade  # type: ignore
except Exception:  # pragma: no cover
    arcade = None  # type: ignore


log = logging.getLogger(__name__)


def run() -> None:  # pragma: no cover - entry point, not unit-tested
    configure_logging()

    if arcade is None:
        raise RuntimeError("Arcade is required to run the game. Please install 'arcade'.")

    settings_mgr = SettingsManager()
    save_mgr = SaveManager()

    window = arcade.Window(1280, 720, "Amor Mortuorum")
    settings_mgr.adapter.bind_window(window)
    settings_mgr.apply()

    from .ui.views.main_menu import MainMenuView

    view = MainMenuView(settings_mgr, save_mgr)
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":  # pragma: no cover
    run()
