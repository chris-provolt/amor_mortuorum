Relic Passives (Light Bonuses)

Summary
- Each Relic of the Veil has an optional, small passive bonus.
- If the player owns a relic, they can toggle its passive ON/OFF.
- Enabled passives apply globally across the game: exploration, rewards, and combat systems.
- The aggregate effect is broadcast via an event so all subsystems can react.

Design
- A Relic is defined with a GlobalModifiers payload capturing stat multipliers and gameplay deltas.
- RelicPassiveManager tracks ownership and toggle state, builds the aggregate GlobalModifiers, and publishes:
  - relic.toggle.changed when a single relic state changes
  - relic.passives.changed when the aggregate modifiers change
- Systems (e.g., combat stat calc, loot rolls, portal spawn, FOV) subscribe to relic.passives.changed and/or query get_global_modifiers().

Light Bonuses Examples
- Veil Fragment: +2% HP, +2% DEF
- Ferryman's Coin: +5% gold
- Lantern Wisp: +1 vision radius
- Whispering Compass: +3% portal chance
- Seer's Eye: +5% trap detection
- Dawn Sigil: +2% to all core stats

Persistence
- RelicPassiveManager exposes to_dict/load_dict to read/write save data.
- On load, the manager re-emits events so subscribers can update their views/state.

Integration Points
- Combat: use StatsCalculator.apply_modifiers with the manager's aggregate GlobalModifiers.
- Loot/Rewards: multiply gold and item drop chances by gold_find_multiplier and item_find_multiplier.
- World: add portal_chance_delta to base portal chance; increase FOV radius by light_radius_delta.
- Traps: add trap_detect_chance_delta to detection rolls (clamp 0..1 in the caller).

Notes
- Multiplicative stacking for stat/item/gold multipliers; additive for deltas.
- Relic passives are intentionally conservative to avoid trivializing the run.
