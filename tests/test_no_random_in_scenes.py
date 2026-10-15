"""Determinism guard: scenes must get randomness from ``systems`` rng streams only."""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "amormortuorum"
PATTERN = re.compile(r"^\s*(import random|from random import)", re.MULTILINE)
ARCADE_PATTERN = re.compile(r"^\s*(import arcade|from arcade)", re.MULTILINE)


def test_scenes_and_ui_do_not_import_random():
    offenders = []
    for folder in ("scenes", "ui", "core"):
        for path in (SRC / folder).rglob("*.py"):
            if PATTERN.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(SRC)))
    assert offenders == []


def test_systems_and_data_do_not_import_arcade():
    offenders = []
    for folder in ("systems", "data", "persistence"):
        for path in (SRC / folder).rglob("*.py"):
            if ARCADE_PATTERN.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(SRC)))
    assert offenders == []
