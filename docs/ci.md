# CI / CD and release pipeline

## Lint and test (every push to `main` and every pull request)

- Runs on Ubuntu with Python 3.11 and 3.13.
- Installs the project with `pip install -e ".[dev]"` (arcade, pytest, flake8, flake8-bugbear).
- `flake8 .` then `pytest`. Unit tests never open a window; everything under
  `systems/`, `data/` and `persistence/` is pure Python, and the scene stack is
  tested with a dummy window object.
- A separate advisory step runs `python -m amormortuorum --smoke 60 --seed 1`
  with `ARCADE_HEADLESS=True` on the 3.13 job. Arcade's headless mode needs EGL,
  which only exists on Linux, so the step installs Mesa and is marked
  `continue-on-error` until it has proven stable on the runner.

## Build (tags matching `v*`)

- Matrix across ubuntu-latest, windows-latest, macos-latest.
- Installs the project with the `build` extra (PyInstaller) and runs
  `tools/ci/build_binary.py --name AmorMortuorum --out dist/release`.
- Entry point detection, in order: a hand-written `pyinstaller/*.spec` file (only
  that directory; the spec PyInstaller generates itself goes to `build/` and is
  never reused), then
  `src/amormortuorum/__main__.py` (preferred because it uses absolute imports),
  then the first `[project.scripts]` module.
- The one-file build adds `--paths src`, bundles `amormortuorum/config`,
  `amormortuorum/data` and `amormortuorum/resources` with `--add-data`, collects
  pyglet's resource files (arcade ships its own PyInstaller hook; do not add
  `--collect-data arcade`, it duplicates arcade's VERSION entry and the frozen
  app fails to extract), and uses `--windowed` on Windows and macOS.
- The frozen app prints one harmless `Unable to load version number via
  ...arcade\VERSION: Permission denied` line at startup: arcade's hook bundles
  its VERSION file as a directory, and arcade falls back to a default string.
- A windowed build has no console, so the game logs to `amor.log` in the save
  root (`%APPDATA%\AmorMortuorum` on Windows) and writes any fatal traceback
  there instead of dying silently.
- The binary is zipped with the README and LICENSE (when present) as
  `AmorMortuorum-<version>-<platform>.zip`, uploaded as a workflow artifact and
  attached to the GitHub Release for the tag.

## Local equivalents

```powershell
python -m pip install -e ".[dev]"
flake8 .
pytest
python -m amormortuorum --smoke 120 --seed 1   # opens a real window briefly
python -m pip install ".[build]"; python tools/ci/build_binary.py
```

Codesigning and macOS notarization are out of scope for the default pipeline.
