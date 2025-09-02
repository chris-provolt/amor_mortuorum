from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..stats.modifiers import GlobalModifiers


@dataclass(frozen=True)
class Relic:
    """Data for a single Relic of the Veil.

    Attributes:
        id: Unique relic id (string key)
        name: Display name
        description: Flavor and mechanical description
        effect: GlobalModifiers representing the relic's passive when enabled
    """

    id: str
    name: str
    description: str
    effect: GlobalModifiers


# Light bonus definitions for Relic passives (balanced, non-game-breaking)
# Note: Values are intentionally small; they are meant to be persistent, optional bonuses.
RELICS: Dict[str, Relic] = {
    # Base relic set (9)
    "veil_fragment": Relic(
        id="veil_fragment",
        name="Veil Fragment",
        description="A sliver of the ancient veil. +2% HP and +2% DEF when empowered.",
        effect=GlobalModifiers(stat_multipliers={"HP": 1.02, "ATK": 1.0, "DEF": 1.02, "SPD": 1.0}),
    ),
    "ferryman_coin": Relic(
        id="ferryman_coin",
        name="Ferryman's Coin",
        description="A coin for safe passage. +5% gold from all sources when empowered.",
        effect=GlobalModifiers(gold_find_multiplier=1.05),
    ),
    "lantern_wisp": Relic(
        id="lantern_wisp",
        name="Lantern Wisp",
        description="A pale flame that never fades. +1 vision radius when empowered.",
        effect=GlobalModifiers(light_radius_delta=1),
    ),
    "fortune_fetish": Relic(
        id="fortune_fetish",
        name="Fortune Fetish",
        description="A charm against scarcity. +5% item drop chances when empowered.",
        effect=GlobalModifiers(item_find_multiplier=1.05),
    ),
    "whispering_compass": Relic(
        id="whispering_compass",
        name="Whispering Compass",
        description="It hums near seams in the veil. +3% portal chance when empowered.",
        effect=GlobalModifiers(portal_chance_delta=0.03),
    ),
    "ghoststep_anklet": Relic(
        id="ghoststep_anklet",
        name="Ghoststep Anklet",
        description="You move with unearthly grace. +2% SPD when empowered.",
        effect=GlobalModifiers(stat_multipliers={"HP": 1.0, "ATK": 1.0, "DEF": 1.0, "SPD": 1.02}),
    ),
    "grave_tuned_charm": Relic(
        id="grave_tuned_charm",
        name="Grave‑Tuned Charm",
        description="It resonates with conflict. +2% ATK when empowered.",
        effect=GlobalModifiers(stat_multipliers={"HP": 1.0, "ATK": 1.02, "DEF": 1.0, "SPD": 1.0}),
    ),
    "seers_eye": Relic(
        id="seers_eye",
        name="Seer's Eye",
        description="Sees the cracks and snares. +5% trap detection when empowered.",
        effect=GlobalModifiers(trap_detect_chance_delta=0.05),
    ),
    "bone_bindings": Relic(
        id="bone_bindings",
        name="Bone Bindings",
        description="A stiffened resolve. +2% DEF when empowered.",
        effect=GlobalModifiers(stat_multipliers={"HP": 1.0, "ATK": 1.0, "DEF": 1.02, "SPD": 1.0}),
    ),
    # Final relic (boss)
    "dawn_sigil": Relic(
        id="dawn_sigil",
        name="Dawn Sigil",
        description="A promise of return. +2% to all stats when empowered.",
        effect=GlobalModifiers(stat_multipliers={"HP": 1.02, "ATK": 1.02, "DEF": 1.02, "SPD": 1.02}),
    ),
}
