from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .base import BaseBoss, BossPhase, PhaseDefinition
from ..combat.actions import DamageAction, DrainAction, HealSelfPercent, MultiAction, Action
from ..combat.actors import Party
from ..core.events import EventBus
from ..core.save import SaveService


@dataclass
class OHConfig:
    max_hp: int
    thresholds: Dict[str, float]
    music: Dict[str, str]
    sfx: Dict[str, str]
    numbers: Dict[str, int]

    @staticmethod
    def from_json(path: str | Path) -> "OHConfig":
        data = json.loads(Path(path).read_text())
        return OHConfig(
            max_hp=int(data["max_hp"]),
            thresholds={k: float(v) for k, v in data["thresholds"].items()},
            music=data["music"],
            sfx=data["sfx"],
            numbers={k: int(v) for k, v in data["numbers"].items()},
        )


def build_oblivion_heart(config: OHConfig, bus: EventBus, save: SaveService) -> BaseBoss:
    name = "Oblivion Heart"

    def p1_ai(self: BaseBoss, party: Party) -> Action:
        # Phase 1: Primarily single-target; opportunistic AoE on cooldown
        if self.cooldowns.get("p1_aoe", 0) == 0:
            self.cooldowns["p1_aoe"] = 3
            bus.publish("sfx.play", {"key": config.sfx["abyssal_maelstrom"], "boss": name})
            return DamageAction("Abyssal Maelstrom", damage=config.numbers["p1_aoe"], target="all")
        # Default single-target pulse
        bus.publish("sfx.play", {"key": config.sfx["shadow_pulse"], "boss": name})
        return DamageAction("Shadow Pulse", damage=config.numbers["p1_st"], target="single")

    def p2_ai(self: BaseBoss, party: Party) -> Action:
        # Phase 2: Mix of AoE and self-heal check below 40% HP
        hp_frac = self.hp / self.max_hp
        if hp_frac <= 0.4 and self.cooldowns.get("self_heal", 0) == 0:
            self.cooldowns["self_heal"] = 4
            bus.publish("sfx.play", {"key": config.sfx["reconstitution"], "boss": name})
            return HealSelfPercent("Oblivion Reconstitution", percent=0.2)
        if self.cooldowns.get("p2_aoe", 0) == 0:
            self.cooldowns["p2_aoe"] = 2
            bus.publish("sfx.play", {"key": config.sfx["abyssal_maelstrom"], "boss": name})
            return DamageAction("Abyssal Maelstrom", damage=config.numbers["p2_aoe"], target="all")
        # Opportunistic drain to self-heal slightly
        if self.cooldowns.get("drain", 0) == 0:
            self.cooldowns["drain"] = 2
            bus.publish("sfx.play", {"key": config.sfx["heartseeker_drain"], "boss": name})
            return DrainAction("Heartseeker Drain", damage=config.numbers["p2_drain"], heal_ratio=0.5)
        bus.publish("sfx.play", {"key": config.sfx["shadow_pulse"], "boss": name})
        return DamageAction("Shadow Pulse", damage=config.numbers["p2_st"], target="single")

    def p3_enter(self: BaseBoss) -> None:
        # Enrage status, immediate roar SFX handled by phase enter SFX.
        self.status["enraged"] = True
        # Make Cataclysm available immediately
        self.cooldowns["cataclysm"] = 0

    def p3_ai(self: BaseBoss, party: Party) -> Action:
        # Phase 3: Enraged. Cataclysmic Beat on cooldown, otherwise drain + hit combo.
        if self.cooldowns.get("cataclysm", 0) == 0:
            self.cooldowns["cataclysm"] = 2
            bus.publish("sfx.play", {"key": config.sfx["cataclysmic_beat"], "boss": name})
            return DamageAction("Cataclysmic Beat", damage=config.numbers["p3_cataclysm"], target="all")
        # Emergency self-heal if extremely low
        hp_frac = self.hp / self.max_hp
        if hp_frac <= 0.25 and self.cooldowns.get("self_heal", 0) == 0:
            self.cooldowns["self_heal"] = 4
            bus.publish("sfx.play", {"key": config.sfx["reconstitution"], "boss": name})
            return HealSelfPercent("Oblivion Reconstitution", percent=0.2)
        # Combo: Drain + single pulse
        bus.publish("sfx.play", {"key": config.sfx["combo"], "boss": name})
        return MultiAction(
            name="Ravenous Combo",
            actions=[
                DrainAction("Heartseeker Drain", damage=config.numbers["p3_drain"], heal_ratio=0.5),
                DamageAction("Shadow Pulse", damage=config.numbers["p3_st"], target="single"),
            ],
        )

    phases = [
        BossPhase(
            definition=PhaseDefinition(
                id="phase1",
                threshold_pct=config.thresholds["phase1"],
                music_track=config.music["phase1"],
                enter_sfx=config.sfx["enter_p1"],
            ),
            on_choose_action=p1_ai,
        ),
        BossPhase(
            definition=PhaseDefinition(
                id="phase2",
                threshold_pct=config.thresholds["phase2"],
                music_track=config.music["phase2"],
                enter_sfx=config.sfx["enter_p2"],
            ),
            on_choose_action=p2_ai,
        ),
        BossPhase(
            definition=PhaseDefinition(
                id="phase3",
                threshold_pct=config.thresholds["phase3"],
                music_track=config.music["phase3"],
                enter_sfx=config.sfx["enter_p3"],
            ),
            on_choose_action=p3_ai,
            on_enter=p3_enter,
        ),
    ]

    boss = BaseBoss(
        name=name,
        max_hp=config.max_hp,
        bus=bus,
        save=save,
        phases=phases,
        death_sfx=config.sfx["death"],
        relic_id="relic.final.oblivion_heart",
        clear_flag="boss.b99.cleared",
    )
    return boss
