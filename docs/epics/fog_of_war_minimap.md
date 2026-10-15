# EPIC: Fog of War & Minimap

Scope: visibility (field of view), explored-tile memory, and the minimap overlay.

- FOV grid computed per step (shadowcasting) with a configurable radius.
- Explored tiles are remembered for the current floor and drawn dimmed.
- Minimap overlay with a toggle hotkey (default `M`) and icons for stairs, chests, portals, and bosses.
- Colourblind-friendly icon shapes in addition to colour.
- Explored state is part of run state so a graveyard save can restore it.
- Performance target: no per-frame recomputation; update on movement only.
