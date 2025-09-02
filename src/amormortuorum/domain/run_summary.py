from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)


class RunOutcome(Enum):
    """High-level outcome of the run.

    - DEATH: Player died during the run.
    - EXIT: Player exited the dungeon via a portal or intentional retreat.
    - VICTORY: Player defeated the final boss and finished the run.
    """

    DEATH = "death"
    EXIT = "exit"
    VICTORY = "victory"


@dataclass(frozen=True)
class LootItem:
    name: str
    qty: int = 1
    rarity: Optional[str] = None

    def display(self) -> str:
        base = f"{self.name}"
        if self.qty > 1:
            base += f" x{self.qty}"
        if self.rarity:
            base += f" [{self.rarity}]"
        return base


@dataclass(frozen=True)
class Relic:
    id: str
    name: str

    def display(self) -> str:
        return self.name


@dataclass
class RunSummary:
    """Aggregated summary for a completed run.

    This object is UI-agnostic and safe to unit test.
    """

    outcome: RunOutcome
    depth_reached: int
    floors_cleared: int
    enemies_defeated: int
    loot: List[LootItem] = field(default_factory=list)
    relics: List[Relic] = field(default_factory=list)
    gold_collected: int = 0
    duration_seconds: Optional[int] = None
    seed: Optional[int] = None

    @staticmethod
    def from_run_stats(
        *,
        outcome: RunOutcome,
        depth_reached: int,
        enemies_defeated: int,
        loot: Optional[Iterable[LootItem]] = None,
        relics: Optional[Iterable[Relic]] = None,
        gold_collected: int = 0,
        duration_seconds: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> "RunSummary":
        """Create a RunSummary from raw stats.

        Floors cleared is derived from depth reached where possible. Example:
        - If you die on floor N, floors_cleared = N - 1.
        - If you exit on floor N (via portal) and return, floors_cleared = N - 1
          unless you exited before fully clearing. This function assumes N - 1
          as a neutral default. Callers may override floors_cleared later.
        """
        if depth_reached < 1:
            raise ValueError("depth_reached must be >= 1")
        if enemies_defeated < 0:
            raise ValueError("enemies_defeated must be >= 0")
        floors_cleared = max(0, depth_reached - 1)
        loot_list = list(loot) if loot else []
        relic_list = list(relics) if relics else []
        logger.debug(
            "Constructing RunSummary: outcome=%s, depth=%d, floors=%d, enemies=%d, loot=%d, relics=%d, gold=%d",
            outcome, depth_reached, floors_cleared, enemies_defeated, len(loot_list), len(relic_list), gold_collected,
        )
        return RunSummary(
            outcome=outcome,
            depth_reached=depth_reached,
            floors_cleared=floors_cleared,
            enemies_defeated=enemies_defeated,
            loot=loot_list,
            relics=relic_list,
            gold_collected=gold_collected,
            duration_seconds=duration_seconds,
            seed=seed,
        )

    def title(self) -> str:
        if self.outcome is RunOutcome.DEATH:
            return "You Died"
        if self.outcome is RunOutcome.EXIT:
            return "Run Concluded"
        return "Victory!"

    def subtitle(self) -> str:
        if self.outcome is RunOutcome.DEATH:
            return f"Fell on Floor {self.depth_reached}"
        if self.outcome is RunOutcome.EXIT:
            return f"Exited on Floor {self.depth_reached}"
        return f"Conquered Floor {self.depth_reached}"

    def _format_duration(self) -> Optional[str]:
        if self.duration_seconds is None:
            return None
        secs = int(self.duration_seconds)
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        if h > 0:
            return f"{h}h {m}m {s}s"
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    def format_lines(self, width: int = 80) -> List[str]:
        """Format the summary into fixed-width text lines for any UI.

        This provides a consistent rendering across terminal, logs, or Arcade.
        """
        lines: List[str] = []
        title = self.title()
        subtitle = self.subtitle()
        lines.append(title.center(width))
        lines.append(subtitle.center(width))
        lines.append("".center(width, "-"))

        # Core metrics
        lines.append(f"Floors cleared: {self.floors_cleared}")
        lines.append(f"Enemies defeated: {self.enemies_defeated}")
        if self.gold_collected:
            lines.append(f"Gold collected: {self.gold_collected}")
        duration_str = self._format_duration()
        if duration_str:
            lines.append(f"Time: {duration_str}")
        if self.seed is not None:
            lines.append(f"Run Seed: {self.seed}")

        # Loot
        lines.append("")
        lines.append(f"Loot acquired ({len(self.loot)}):")
        if self.loot:
            for item in self.loot:
                lines.append(f"  - {item.display()}")
        else:
            lines.append("  - None")

        # Relics
        lines.append("")
        lines.append(f"Relics found ({len(self.relics)}):")
        if self.relics:
            for relic in self.relics:
                lines.append(f"  - {relic.display()}")
        else:
            lines.append("  - None")

        # Footer instructions
        lines.append("")
        lines.append("Press Enter/Space to return to Graveyard, or M for Main Menu")
        return lines

    def to_dict(self) -> dict:
        """Serialize summary for saving/telemetry."""
        return {
            "outcome": self.outcome.value,
            "depth_reached": self.depth_reached,
            "floors_cleared": self.floors_cleared,
            "enemies_defeated": self.enemies_defeated,
            "loot": [
                {"name": li.name, "qty": li.qty, "rarity": li.rarity}
                for li in self.loot
            ],
            "relics": [
                {"id": r.id, "name": r.name}
                for r in self.relics
            ],
            "gold_collected": self.gold_collected,
            "duration_seconds": self.duration_seconds,
            "seed": self.seed,
        }
