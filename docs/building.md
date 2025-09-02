Amor Mortuorum - Packaging and Building

Overview
- We provide PyInstaller specs and a convenience build script to produce standalone executables for Windows, macOS, and Linux.
- The MVP includes a minimal game loop and a basic Arcade window when available.

Prerequisites
- Python 3.9–3.12 recommended
- Install dependencies:
  - Runtime: arcade (for GUI) + its transitive deps
  - Build: pyinstaller

  pip install -U "arcade>=3,<4" pyinstaller

Running the MVP
- GUI (preferred, if arcade installed):
  python -m amor_mortuorum --gui

- Headless:
  python -m amor_mortuorum --headless --max-steps 120

- Auto-detect (GUI if available else headless):
  python -m amor_mortuorum

Environment Overrides
- AMOR_HEADLESS=1 forces headless mode.
- AMOR_GUI=1 forces GUI mode (if arcade importable).

Building Executables
- Using spec files directly:
  - GUI build (windowed):
    pyinstaller -y pyinstaller/amor_mortuorum_gui.spec --onefile

  - CLI build (console):
    pyinstaller -y pyinstaller/amor_mortuorum_cli.spec --onefile

- Using the helper script (adds platform suffix to name):
  python tools/packaging/build.py --mode gui --onefile --clean

Artifacts
- Executables are produced under the dist/ directory. Names include a platform suffix when using the build helper.

Notes
- The spec collects arcade resources and hidden imports for robustness across platforms.
- Cross-compilation is not supported by PyInstaller; build on each target OS.
- For macOS, you may need to notarize/sign for distribution outside Gatekeeper in production.
- For Windows, SmartScreen may flag unsigned binaries; consider code signing for release builds.

CI/CD Integration
- On each platform runner (Windows/macOS/Linux), install deps, then run the build helper.
- Archive dist/ artifacts for release.
