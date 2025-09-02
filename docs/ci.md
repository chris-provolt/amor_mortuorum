CI / CD and Release Pipeline

Overview
- Linting: flake8 enforces style and static checks.
- Tests: pytest runs the unit test suite headlessly.
- Build: On tags (v*), PyInstaller builds standalone binaries for Linux, Windows, and macOS. Artifacts are uploaded to the GitHub Release and stored as workflow artifacts.

How it works
1. Triggers
   - push to main and pull requests: run lint and tests
   - push tags matching v*: run lint/tests first, then build and upload artifacts for three platforms

2. Lint & Test
   - Uses Python 3.11 on Ubuntu
   - Installs the project and dev tools (flake8, pytest)
   - Headless-friendly environment variables are set for graphics libs

3. Build
   - Matrix across ubuntu-latest, windows-latest, macos-latest
   - Installs PyInstaller and the project
   - Auto-detection for the entry point:
     - If a PyInstaller spec exists in pyinstaller/*.spec, it is used
     - Otherwise, [project.scripts] from pyproject.toml is parsed, and the corresponding module is used
     - Otherwise, src/**/__main__.py is used
   - Produces a single-file binary and zips it with README and LICENSE
   - Artifact name: AmorMortuorum-<version>-<platform>.zip

4. Release Upload
   - Tag pushes (refs/tags/v*) upload all artifacts to the corresponding GitHub Release
   - Artifacts are also uploaded as workflow artifacts for later inspection

Customization
- Change the application/binary name by editing the --name argument in the build step or invoking tools/ci/build_binary.py directly.
- Provide a custom PyInstaller spec in pyinstaller/*.spec to fully control packaging.

Notes
- If your project requires platform-specific build dependencies (SDL, OpenGL, etc.), install them before running PyInstaller by adding steps to the build job.
- Codesigning and notarization (macOS) are out of scope for the default pipeline but can be added as follow-up work.
