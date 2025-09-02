Audio System Overview

This module provides a small, testable audio layering system focused on dynamic overlays for miniboss and final boss encounters. It aims to avoid clicks/pops by using linear volume ramps and by never abruptly starting/stopping audio at non-zero gain.

Key components:
- engine.py
  - TrackPlayer protocol to abstract the backing audio library
  - FakeAudioEngine/FakeTrackPlayer for tests and headless execution
  - ArcadeAudioEngine/ArcadeTrackPlayer for production (optional dependency)
- mixer.py
  - AudioMixer manages named tracks and fade tasks
  - FadeTask executes linear ramps and can stop tracks when reaching zero
- boss_layers.py
  - BossLayerController encapsulates boss-specific overlay behavior (miniboss/final)

Usage snippet (production):

- Load your audio assets via ArcadeAudioEngine
- Register overlay tracks with the mixer
- Create BossLayerController and call enter/exit methods in response to combat state changes
- Ensure you call mixer.tick(dt) once per frame from your main loop

Why this design?
- Separation of concerns: Engine vs. Mixer vs. Gameplay controller
- Determinism and testability: A Fake engine enables unit tests without audio drivers
- Robust against pops/clicks: All changes are ramped; tracks only stop at zero volume

Configuration
- See configs/audio/boss_layers.json as a reference for default levels and asset paths.
