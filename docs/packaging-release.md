# Packaging & Release

This document describes how Amor Mortuorum is packaged into cross-platform binaries and released.

Contents:
- Save directories & portable mode
- PyInstaller configuration
- CI build & release pipeline
- Creating and managing the Epic with child tasks

## Save directories & portable mode

Code: src/amor_mortuorum/platform/save_paths.py

- Default locations (non-portable):
  - Windows: %APPDATA%/Amor Mortuorum
  - macOS: ~/Library/Application Support/Amor Mortuorum
  - Linux: ~/.local/share/amor-mortuorum or $XDG_DATA_HOME/amor-mortuorum
- Portable mode: enabled if either
  - Environment AMOR_PORTABLE in {1, true, yes, on}
  - A file named portable_mode.flag is present next to the executable

When portable mode is active, user data is saved in ./userdata alongside the app binary.

## PyInstaller

Spec file: tools/pyinstaller/amormortuorum.spec

- Entry script defaults to src/amor_mortuorum/__main__.py
- Override entry by setting AMOR_ENTRY to a valid path
- Hooks path includes tools/pyinstaller/hooks; hook-amor_mortuorum.py collects package data
- Output collected under dist/AmorMortuorum

Build locally:

```
pip install pyinstaller
AMOR_ENTRY=src/amor_mortuorum/__main__.py pyinstaller tools/pyinstaller/amormortuorum.spec
```

## CI build & release

Workflow: .github/workflows/build-release.yml

- Triggers on tags matching v*
- Builds on Windows, macOS, and Linux with Python 3.11
- Runs tests via pytest
- Bundles with PyInstaller and uploads artifacts
- Creates a GitHub Release attaching artifacts

Manual build/test via workflow_dispatch is supported; you can override the entry path via the input.

## Epic and child issues

Issue template: .github/ISSUE_TEMPLATE/epic.yml

- Includes a Children section with a checklist. The workflow
  .github/workflows/epic-children.yml reads unchecked items, creates issues,
  and links them back into the checklist and as a comment on the epic.

Usage:
1. Open a new issue using the Epic template.
2. Add/adjust checklist items under the "### Children" section.
3. Upon submission or edit, the workflow will:
   - Create issues for any unchecked, non-linked tasks
   - Replace them inline with `- [ ] #<number> <title>` to enable progress tracking
   - Comment on the epic with links to newly created issues

Notes:
- You can add label hints per task with "(labels: a,b,c)"; the workflow will apply them.
- The parent epic must have the `epic` label for the workflow to trigger.

## Icons and metadata

Add platform icons to tools/pyinstaller/:
- AmorMortuorum.ico (Windows)
- AmorMortuorum.icns (macOS)

If not present, the spec will build without custom icons.

## Troubleshooting

- If the build fails to find the entry script, set AMOR_ENTRY to your game's entry point.
- Arcade/pyglet may require additional system libraries at runtime; building does not run the app.
- For missing assets in the bundled app, ensure they live under src/amor_mortuorum/assets or add additional collect rules in the spec or hook.
