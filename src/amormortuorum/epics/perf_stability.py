from typing import List, Tuple

from amormortuorum.tools.github_issues import ensure_epic_with_children


EPIC_TITLE = "EPIC: Performance & Stability"
EPIC_LABELS = ["epic", "performance", "stability", "tracking"]
TARGET_WINDOW = "2025-08-26 → (Ongoing)"


EPIC_BODY = f"""
## Summary
Sprite batching, collision bounds, culling.

Goal: Track and group related child issues under this Epic.
Target Window: {TARGET_WINDOW}

## Acceptance
- Child issues exist and are linked in comments.
- Labels applied: `epic`.
- Progress can be tracked via linked issues checklist.

## Child Issues
Below checklist is auto-generated between markers. Do not edit manually.
""".strip()


def child_issue_specs() -> List[Tuple[str, str, List[str]]]:
    specs: List[Tuple[str, str, List[str]]] = []

    specs.append(
        (
            "Perf: Sprite batching & draw call reduction",
            (
                "## Summary\n"
                "Batch static and dynamic sprites to minimize draw calls and state changes. Implement per-layer batching and in-viewport filtering.\n\n"
                "## Acceptance\n"
                "- Draw calls reduced by >=50% on test scene vs baseline.\n"
                "- Supports per-layer batching (terrain, props, entities, FX).\n"
                "- No visual regressions (golden image snapshot).\n\n"
                "## Notes\n"
                "- Use texture atlases to avoid texture binds.\n"
                "- Separate dynamic (moving) from static batches.\n"
                "- Integrate with camera culling.\n"
            ),
            ["performance", "graphics", "batching"],
        )
    )

    specs.append(
        (
            "Perf: Texture atlas pipeline (tooling + runtime)",
            (
                "## Summary\n"
                "Introduce an atlas build step and runtime region management to reduce binds and enable batching.\n\n"
                "## Acceptance\n"
                "- Atlas builder produces deterministic packs with manifest.\n"
                "- Runtime loads atlas + regions and updates sprites accordingly.\n"
                "- Zero per-frame texture swaps on test scene.\n\n"
                "## Notes\n"
                "- Provide CLI tool to pack assets.\n"
                "- Cache manifests for CI.\n"
            ),
            ["performance", "graphics", "tooling"],
        )
    )

    specs.append(
        (
            "Perf: View frustum culling + spatial index (quadtree/grid)",
            (
                "## Summary\n"
                "Cull off-screen sprites and collisions using camera frustum and a spatial index (uniform grid or quadtree).\n\n"
                "## Acceptance\n"
                "- Only in-viewport sprites are submitted to the renderer.\n"
                "- Collision queries reduced to relevant cells/nodes.\n"
                "- 60 FPS maintained in stress scene at 1080p (reference PC).\n\n"
                "## Notes\n"
                "- Benchmark grid vs quadtree; choose simpler if perf is similar.\n"
                "- Integrate with minimap/fog of war updates.\n"
            ),
            ["performance", "culling", "spatial-index"],
        )
    )

    specs.append(
        (
            "Perf: Collision bounds simplification & AABB usage",
            (
                "## Summary\n"
                "Replace complex polygonal or per-pixel collisions with simplified AABBs/OBBs where possible.\n\n"
                "## Acceptance\n"
                "- Broadphase uses AABBs exclusively.\n"
                "- Narrow-phase only for special cases (e.g., boss attacks).\n"
                "- Hitbox coverage within 5% of legacy behavior (test fixtures).\n\n"
                "## Notes\n"
                "- Provide data-driven hitbox definitions.\n"
                "- Visual debug overlay toggle.\n"
            ),
            ["performance", "collisions"],
        )
    )

    specs.append(
        (
            "Perf: Particle system pooling & batched rendering",
            (
                "## Summary\n"
                "Object-pool particle emitters and batch their rendering to avoid per-frame allocations and excessive draws.\n\n"
                "## Acceptance\n"
                "- No GC spikes during high FX scenes (GC time < 2ms/frame).\n"
                "- Constant-time emitter reuse under load.\n"
                "- 2x throughput vs baseline in benchmark.\n"
            ),
            ["performance", "fx", "pooling"],
        )
    )

    specs.append(
        (
            "Perf: Map chunking & fog-of-war culling",
            (
                "## Summary\n"
                "Chunk tilemaps and compute fog updates only for changed/visible chunks.\n\n"
                "## Acceptance\n"
                "- CPU time for fog updates reduced by >=60% on 100x100 map.\n"
                "- No visible seams between chunks.\n"
            ),
            ["performance", "map", "culling"],
        )
    )

    specs.append(
        (
            "Perf/Stability: Profiling & performance benchmarks harness",
            (
                "## Summary\n"
                "Add reproducible profiling scenes and a benchmark CLI, export JSON for CI trend graphs.\n\n"
                "## Acceptance\n"
                "- Deterministic seeds for scenes.\n"
                "- CLI reports FPS, CPU time, draw calls, memory usage.\n"
                "- CI job uploads artifact and compares to baseline with thresholds.\n"
            ),
            ["performance", "ci", "benchmark"],
        )
    )

    specs.append(
        (
            "Stability: Determinism & replay capture",
            (
                "## Summary\n"
                "Deterministic simulation ticks with input replay capture to reproduce bugs.\n\n"
                "## Acceptance\n"
                "- Replay file reproduces run within 1 frame over 5 minutes.\n"
                "- Hash of state per tick for verification.\n"
            ),
            ["stability", "testing", "determinism"],
        )
    )

    specs.append(
        (
            "Stability: Crash telemetry & structured error reporting",
            (
                "## Summary\n"
                "Capture exceptions with breadcrumb trail, environment info, and optional user consent; export locally and support remote provider plug-in.\n\n"
                "## Acceptance\n"
                "- Uncaught exceptions produce a structured report (JSON+logs).\n"
                "- User can opt-in to send reports.\n"
                "- Redact PII and access tokens.\n"
            ),
            ["stability", "telemetry"],
        )
    )

    specs.append(
        (
            "Stability: Memory budgets, leak detection, and GC tuning",
            (
                "## Summary\n"
                "Define memory budgets for assets and add leak detection tooling; tune Python GC thresholds for game loop.\n\n"
                "## Acceptance\n"
                "- No unbounded growth in long-run soak test (30 min).\n"
                "- Asset loader enforces budgets and logs violations.\n"
                "- GC pauses under 2ms per minute on reference machine.\n"
            ),
            ["stability", "memory", "tooling"],
        )
    )

    specs.append(
        (
            "CI: Performance regression guardrails",
            (
                "## Summary\n"
                "Integrate benchmarks with CI and fail PRs exceeding regression thresholds.\n\n"
                "## Acceptance\n"
                "- CI job computes delta vs baseline.\n"
                "- Thresholds configurable per-metric.\n"
                "- PR comment with summary table.\n"
            ),
            ["ci", "performance", "regression"],
        )
    )

    return specs


def create_or_update_epic(gh_client) -> None:
    ensure_epic_with_children(
        gh_client,
        EPIC_TITLE,
        EPIC_BODY,
        EPIC_LABELS,
        child_issue_specs(),
    )
