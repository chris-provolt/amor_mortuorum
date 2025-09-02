from typing import Optional, Dict, Any
from .entities import Actor
from ..core.events import EventBus
from ..core.audio import AudioManager


class DamageService:
    """Applies damage to actors and emits events and SFX hooks."""

    def __init__(self, bus: EventBus, audio: AudioManager) -> None:
        self.bus = bus
        self.audio = audio

    def apply_damage(self, target: Actor, amount: int, source: str, sfx_key: Optional[str] = None) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Damage amount must be positive")
        pre_hp = target.hp
        target.hp = max(0, target.hp - amount)
        post_hp = target.hp
        self.bus.publish(
            "damage",
            {
                "target_id": target.eid,
                "target_name": target.name,
                "amount": amount,
                "source": source,
                "hp_before": pre_hp,
                "hp_after": post_hp,
            },
        )
        # Player-facing notification
        self.bus.publish(
            "notification",
            {"message": f"{target.name} takes {amount} damage from {source}."},
        )
        if sfx_key:
            self.audio.play_sfx(sfx_key)
        died = post_hp == 0
        if died:
            self.bus.publish(
                "actor_dead", {"target_id": target.eid, "target_name": target.name, "source": source}
            )
        return {"died": died, "hp_before": pre_hp, "hp_after": post_hp}
