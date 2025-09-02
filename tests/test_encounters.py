import pytest

from amor.config import GameConfig
from amor.state.run_state import RunState
from amor.scenes.manager import SceneManager
from amor.scenes.overworld import OverworldScene
from amor.scenes.combat import CombatScene


class SceneHost:
    """Helper host that attaches a SceneManager to a scene instance.

    The EncounterSystem expects the scene to expose 'scene_manager'.
    """

    def __init__(self, scene, manager):
        self.scene = scene
        self.scene.scene_manager = manager


def make_overworld(floor: int, seed: int, is_hub: bool = False, config: GameConfig | None = None):
    cfg = config or GameConfig()
    run = RunState.with_seed(floor=floor, seed=seed)
    sm = SceneManager()
    ow = OverworldScene(run_state=run, config=cfg, is_hub=is_hub)
    # Attach scene manager for encounter system to work
    SceneHost(ow, sm)
    sm.transition_to(ow)
    return ow, sm, run, cfg


def test_encounter_triggers_when_rate_is_one():
    # Set tier 1 rate to guaranteed encounter
    cfg = GameConfig(encounter_rates={1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0})
    ow, sm, run, _ = make_overworld(floor=10, seed=123, config=cfg)

    # Move one tile; must enter combat
    ow.move_player(1, 0)
    assert isinstance(sm.active_scene, CombatScene)
    # Combat scene should know the run state floor
    assert sm.active_scene.context.floor == 10


def test_no_encounter_in_hub_even_with_rate_one():
    # Encounters disabled in hub by default; rate would otherwise guarantee encounter
    cfg = GameConfig(encounter_rates={1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0}, encounters_in_hub=False)
    ow, sm, run, _ = make_overworld(floor=0, seed=42, is_hub=True, config=cfg)

    # Move; should NOT transition to combat because hub encounters disabled
    ow.move_player(0, 1)
    assert sm.active_scene is ow


def test_tier_configurable_rates_affect_outcome():
    # Controlled RNG roll: Using seed ensures roll sequence.
    # We'll set rates so that on the same roll, floor 5 won't trigger but floor 25 will.
    # For seed=7, the first random() ~ 0.323832... (implementation detail, but stable for this test)
    seed = 7
    rates = {1: 0.3, 2: 0.4, 3: 0.0, 4: 0.0, 5: 0.0}
    cfg = GameConfig(encounter_rates=rates)

    # Floor 5 -> tier 1 -> rate=0.3 (< roll), so no encounter
    ow1, sm1, run1, _ = make_overworld(floor=5, seed=seed, config=cfg)
    ow1.move_player(1, 0)
    assert sm1.active_scene is ow1

    # Floor 25 -> tier 2 -> rate=0.4 (> same first roll), so encounter triggers
    ow2, sm2, run2, _ = make_overworld(floor=25, seed=seed, config=cfg)
    ow2.move_player(1, 0)
    assert isinstance(sm2.active_scene, CombatScene)


def test_transition_to_combat_scene_preserves_context():
    cfg = GameConfig(encounter_rates={1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0})
    ow, sm, run, _ = make_overworld(floor=60, seed=999, config=cfg)
    ow.move_player(-1, 2)
    combat = sm.active_scene
    assert isinstance(combat, CombatScene)
    # Start position stored in combat context should match the arrival tile from overworld
    assert combat.context.start_position == ow.player.position


def test_deterministic_randomness_with_seed():
    cfg = GameConfig(encounter_rates={1: 0.5, 2: 0.5, 3: 0.5, 4: 0.5, 5: 0.5})
    # Using same seed and same movement pattern should produce the same scene outcome
    ow_a, sm_a, run_a, _ = make_overworld(floor=10, seed=555, config=cfg)
    ow_b, sm_b, run_b, _ = make_overworld(floor=10, seed=555, config=cfg)

    # First move should be identical outcome
    ow_a.move_player(1, 0)
    ow_b.move_player(1, 0)
    assert (isinstance(sm_a.active_scene, CombatScene)) == (isinstance(sm_b.active_scene, CombatScene))

    # Reset fresh pair with a different seed to get a likely different outcome
    ow_c, sm_c, run_c, _ = make_overworld(floor=10, seed=556, config=cfg)
    ow_c.move_player(1, 0)
    # Not asserting difference strictly; just ensure it produces a valid scene
    assert sm_c.active_scene is not None
