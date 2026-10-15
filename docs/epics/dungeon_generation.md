# EPIC: Dungeon Generation & Navigation

Scope: the procedural map generation and movement/rendering stack.

- BSP room-and-corridor floors as the default generator (`systems/procgen.py`).
- Optional cellular-automata caverns as a second generator.
- Stairs placement far from the start room; mini-boss floors lock the stairs.
- Chests, traps, locked doors, and the depth-scaled portal spawn.
- Tile rendering at 32px with a camera that follows the player.
- Grid pathfinding for enemies and auto-explore.
- Determinism: every floor is a pure function of `(seed, floor)`.
