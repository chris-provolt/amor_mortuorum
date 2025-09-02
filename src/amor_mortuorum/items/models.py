from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .schema import validate_item_dict

logger = logging.getLogger(__name__)


class ItemType(str, Enum):
    EQUIPMENT = 'equipment'
    CONSUMABLE = 'consumable'
    KEY = 'key'


class EquipmentSlot(str, Enum):
    WEAPON = 'weapon'
    ARMOR = 'armor'
    ACCESSORY = 'accessory'


# Supported stat keys for equipment deltas
SUPPORTED_STATS = {
    'max_hp', 'max_mp', 'atk', 'defense', 'magic', 'resistance', 'speed', 'luck'
}


@dataclass
class Item:
    """Domain model for a game item.

    This model is intentionally light-weight and validates against the JSON schema
    when constructed from raw dictionaries.
    """

    id: str
    name: str
    type: ItemType
    # Equipment-specific
    slot: Optional[EquipmentSlot] = None
    stat_deltas: Dict[str, int] = field(default_factory=dict)
    # Consumable-specific
    effects: List[Dict[str, Any]] = field(default_factory=list)
    # Tags / metadata
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        """Create an Item from a dict, validating with the JSON schema."""
        validate_item_dict(data)
        item_type = ItemType(data['type'])
        slot = None
        stat_deltas: Dict[str, int] = {}
        effects: List[Dict[str, Any]] = []
        if item_type == ItemType.EQUIPMENT:
            slot = EquipmentSlot(data['slot'])
            stat_deltas = {k: int(v) for k, v in data.get('stat_deltas', {}).items()}
        elif item_type == ItemType.CONSUMABLE:
            effects = list(data.get('effects', []))
        return cls(
            id=data['id'],
            name=data['name'],
            type=item_type,
            slot=slot,
            stat_deltas=stat_deltas,
            effects=effects,
            tags=list(data.get('tags', [])),
        )

    def is_equipment(self) -> bool:
        return self.type == ItemType.EQUIPMENT

    def is_consumable(self) -> bool:
        return self.type == ItemType.CONSUMABLE


# Effects processing for consumables

def _compute_amount(spec: Any, max_value: int, current_value: int) -> int:
    """
    Compute an integer amount from a spec that can be:
    - int/float: direct amount
    - dict: {'flat': int, 'percent_max': float, 'percent_missing': float}
    Values are summed, with percent components multiplied accordingly.
    """
    if spec is None:
        return 0
    if isinstance(spec, (int, float)):
        return int(round(spec))
    if isinstance(spec, dict):
        flat = spec.get('flat', 0)
        pct_max = spec.get('percent_max', 0.0)
        pct_missing = spec.get('percent_missing', 0.0)
        missing = max(0, max_value - current_value)
        amount = float(flat) + float(pct_max) * max_value + float(pct_missing) * missing
        return int(round(amount))
    raise ValueError(f'Unsupported amount spec: {spec!r}')


def apply_consumable_effects(stats: 'Stats', effects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply a list of consumable effects to the provided stats object.

    Currently supported effects:
    - {'type': 'heal_hp', 'amount': int|dict}
    - {'type': 'heal_mp', 'amount': int|dict}

    Returns a summary dict with keys per effect type, values representing net change applied.
    """
    summary: Dict[str, Any] = {}
    for eff in effects:
        eff_type = eff.get('type')
        if eff_type == 'heal_hp':
            amount = _compute_amount(eff.get('amount', 0), stats.max_hp, stats.hp)
            before = stats.hp
            stats.hp = min(stats.max_hp, max(0, stats.hp + amount))
            delta = stats.hp - before
            summary['heal_hp'] = summary.get('heal_hp', 0) + delta
            logger.debug('Applied heal_hp %s => +%d (HP %d -> %d)', eff.get('amount'), delta, before, stats.hp)
        elif eff_type == 'heal_mp':
            amount = _compute_amount(eff.get('amount', 0), stats.max_mp, stats.mp)
            before = stats.mp
            stats.mp = min(stats.max_mp, max(0, stats.mp + amount))
            delta = stats.mp - before
            summary['heal_mp'] = summary.get('heal_mp', 0) + delta
            logger.debug('Applied heal_mp %s => +%d (MP %d -> %d)', eff.get('amount'), delta, before, stats.mp)
        else:
            logger.warning('Unsupported consumable effect type: %s', eff_type)
    return summary


# Avoid circular imports in type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..characters.stats import Stats

__all__ = [
    'Item',
    'ItemType',
    'EquipmentSlot',
    'apply_consumable_effects',
]
