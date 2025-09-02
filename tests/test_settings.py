from pathlib import Path

import yaml

from amormortuorum.core.settings import Settings


def test_default_settings_load():
    s = Settings.load()
    assert s.video.width == 1280
    assert s.video.height == 720
    assert s.audio.music_volume == 0.6
    # Has default mapping for confirm
    assert "confirm" in s.input.mapping


def test_user_override_merge(tmp_path: Path):
    user = tmp_path / "settings.yaml"
    user.write_text(
        yaml.safe_dump(
            {
                "video": {"width": 1024, "fullscreen": True},
                "audio": {"music_volume": 0.25},
                "input": {"mapping": {"confirm": ["ENTER"]}},
            }
        ),
        encoding="utf-8",
    )
    s = Settings.load(user_path=user)
    assert s.video.width == 1024
    assert s.video.fullscreen is True
    assert s.audio.music_volume == 0.25
    # Confirm mapping overridden to single key
    assert s.input.mapping["confirm"] == ["ENTER"]
