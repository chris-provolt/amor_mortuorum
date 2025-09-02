Miniboss Templates - Design Notes

Overview
This implementation adds four miniboss templates, each with a unique mechanic and a distinct telegraph message for UI/UX integration.

Implemented Minibosses
- ShieldedMiniboss
  - Mechanic: Starts combat with a Shield that absorbs incoming damage until depleted.
  - Telegraph: "An Aegis shimmers into being!"
- SummonerMiniboss
  - Mechanic: Every 3 turns it telegraphs a chant and then summons 2 adds next turn.
  - Telegraph: "Chanting to summon allies..."
- EnragedMiniboss
  - Mechanic: When HP falls to 50% or below for the first time, the boss Enrages, increasing attack damage.
  - Telegraph: "Blood fury courses through veins!"
- ReflectMiniboss
  - Mechanic: Periodically applies Mirror Veil which reflects a portion of received damage for 2 turns.
  - Telegraph: "The Mirror Veil shimmers into place..."

Architecture
- Core combat primitives live under src/amor_mortuorum/combat:
  - core.py: Stats, Entity, Actions, Status effects (Shield, Reflect, Enrage), DamageEvent, and a minimal Controller interface.
  - engine.py: A deterministic turn engine to simulate turns and process actions. Suitable for unit tests and as a foundation for the full system.
- Boss logic lives under src/amor_mortuorum/bosses:
  - miniboss_base.py: BaseMiniboss helpers (telegraph, opening shield helper, factory build helper).
  - minibosses.py: Concrete miniboss controllers and factory functions to create battle-ready boss entities.

Integration Points
- Each miniboss is a Controller assigned to an Entity (the boss). The BattleEngine calls controller hooks at battle start, turn start/end, and to choose actions.
- Telegraphs are emitted to CombatLog.telegraphs, making it easy for UI layers to display them distinctly from normal combat messages.
- Status effects encapsulate mechanics cleanly:
  - ShieldStatus absorbs damage before HP is reduced.
  - ReflectStatus reflects a percentage of damage after HP loss is applied.
  - EnrageStatus multiplies effective attack for outgoing damage.

Testing
- tests/test_minibosses.py covers each mechanic and verifies telegraphs:
  - Shield absorbs damage and telegraphs on battle start.
  - Summoner chants (telegraph) and then summons adds on a cadence.
  - Enraged telegraphs upon threshold and increases damage beyond base.
  - Reflect telegraphs when cast and reflects damage back to the attacker.

Notes
- The engine and core components are intentionally minimal to keep the scope focused on miniboss mechanics. They are designed for extension to the full game.
- Damage calculations are simple (ATK - DEF, minimum 1) with Enrage as a multiplicative modifier.
- Turn ordering is by SPD in descending order with stable ordering.
