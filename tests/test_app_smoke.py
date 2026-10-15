"""Opens a real window for a few frames. Skipped unless AMOR_GL_TESTS=1.

Run with:  AMOR_GL_TESTS=1 pytest -m gl
"""
import os

import pytest

pytestmark = pytest.mark.gl


@pytest.mark.skipif(os.environ.get("AMOR_GL_TESTS") != "1", reason="needs a display / GL context")
def test_app_boots_and_exits_after_smoke_frames(tmp_path, monkeypatch):
    monkeypatch.setenv("AMOR_MUTE", "1")
    from amormortuorum.app import GameApp
    from amormortuorum.core.settings import Settings
    from amormortuorum.persistence import SaveManager

    settings = Settings.load()
    settings.video.width, settings.video.height = 640, 360
    app = GameApp(
        settings,
        save_manager=SaveManager(root_dir=tmp_path, profile_id="gl-test"),
        seed=1,
        smoke_frames=5,
    )
    app.run()
