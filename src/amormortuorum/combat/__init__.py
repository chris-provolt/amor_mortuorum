"""
Combat package for Amor Mortuorum.

Implements core, testable combat logic with actions (Attack, Defend, Flee),
party and actor models, and a thin engine facade.

Key concepts:
- Actor: A combatant with HP and SPD (and other stats as needed)
- Party: A collection of actors (player party or enemy group)
- Actions:
  - Defend: Applies a temporary damage multiplier to the next incoming hit
  - Flee: Attempts to escape based on relative party vs enemy SPD
  - Attack: Simple damage application (used for tests and basic flows)
"""
