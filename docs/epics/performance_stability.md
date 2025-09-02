# EPIC: Performance & Stability

This Epic tracks work to improve runtime performance and stability across the engine. Key themes include sprite batching, texture atlases, collision bounds simplification, culling via spatial partitioning, and robust testing and telemetry.

Target Window: 2025-08-26 → (Ongoing)

How to use this Epic:
- Run the CLI to create/update the Epic and child issues in GitHub:
  - python -m src.cli.create_epic --repo owner/repo
- The CLI is idempotent: re-running will update the Epic checklist and child issues without duplication.
- Child issues are linked in Epic comments and a checklist is auto-maintained between markers in the body.

Child issues created by the CLI include:
- Perf: Sprite batching & draw call reduction
- Perf: Texture atlas pipeline (tooling + runtime)
- Perf: View frustum culling + spatial index (quadtree/grid)
- Perf: Collision bounds simplification & AABB usage
- Perf: Particle system pooling & batched rendering
- Perf: Map chunking & fog-of-war culling
- Perf/Stability: Profiling & performance benchmarks harness
- Stability: Determinism & replay capture
- Stability: Crash telemetry & structured error reporting
- Stability: Memory budgets, leak detection, and GC tuning
- CI: Performance regression guardrails

Acceptance criteria for this Epic are encoded in the issue body and implemented by the automation. Progress is tracked via the auto-generated checklist in the Epic body.
