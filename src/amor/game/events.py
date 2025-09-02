from dataclasses import dataclass


@dataclass(frozen=True)
class BossDefeatedEvent:
    """Event emitted when a boss is defeated.

    Attributes:
      floor: Dungeon floor number where the boss was defeated.
      boss_id: Unique identifier for the boss.
      is_final: True if this boss represents the final boss of B99.
      run_id: Identifier for the current run (for analytics/persistence hooks).
    """
    floor: int
    boss_id: str
    is_final: bool
    run_id: str
