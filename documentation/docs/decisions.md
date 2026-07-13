# Design decisions

Confirmed with Rafael on 2026-07-13. Ground truth for scope is
`uofa-2026-report/resources/context/05_benchmark_plan.md` (05 wins on conflict).

## D1 — Orchestrator repo
Separate repo `PRISM-benchmarks`, Makefile-driven. Methods as submodules with
per-submodule isolated envs. Eval layer imports no method.

## D2 — Streaming only; drop the PanoVGGT-no-SLAM ablation
We test **streaming** performance. Running PRISM full-batch (no streaming) would only
benchmark the underlying PanoVGGT net, not the engine — so it is **excluded**. Only
methods run in the streaming harness (native streamers stream; feed-forward methods
are windowed + chained via Sim(3), the same fairness PRISM gets).

## D3 — Methods & pins
Core: **PRISM-VGGT** (ours, pano), **Pi3** (pinhole), **VGGT-SLAM** (pinhole).
Optional: **MapAnything** (pinhole), **LASER** (pano; can ingest the pano renders
directly). Pins in `bench.env`:

| Method | Repo | Commit |
|---|---|---|
| Pi3 | yyfz/Pi3 | `9fa3ddb3f8d53041f8b2738df404f62223bbaa7b` |
| VGGT-SLAM | MIT-SPARK/VGGT-SLAM | `35327ac28b7d193df9ccc39ba6346052bb6f1207` |
| MapAnything | facebookresearch/map-anything | `c845b8f4f6cde0c20aecd87573656c3f69f5b2b0` |
| LASER | neu-vi/LASER | `7adbb7d5c1558f0446398310f31ee92fb4bc2de1` |
| PRISM-VGGT | zRafaF/PRISM-VGGT | pinned via `bench.env PRISM_REF` |

## D4 — VGGT-SLAM install (the heavy one)
GTSAM + custom SL(4) bindings + DINOv2-SALAD. `envs/setup_vggtslam.sh` delegates to
the repo's own installer in an isolated venv. Prefer the repo's pinned GTSAM wheel;
build from source only if it fails on the 6000. We run it **non-looping** (max_loops=0)
to match PRISM's shipped mode.

## D5 — Datasets: go straight to ScanNet++
Start on **ScanNet++** (higher-fidelity meshes/textures) rather than plain ScanNet.
Then KITTI-360 (fisheye→equirect, stretch), and the panorama-native
**Matterport3D** + **Stanford2D3D** (equirectangular RGB-D with GT). Other SoTA
panoramic sets can be added later. Synthetic-trajectory free-space sampling currently
uses mesh-distance rejection (`trajectories.free_space_waypoints`) — open for a proper
occupancy/ESDF sampler if points land in walls.

## D6 — Hardware
Benchmark on the **RTX PRO 6000 only** (`HW_ID` in `bench.env`). No second HW point.

## D7 — Pinhole intrinsics: render BOTH, benchmark separately
No single "fairest" choice, so we render two pinhole variants and report both:
`synthetic_fov` (a fixed common FOV, fairest cross-dataset) and `real_intrinsics`
(the dataset's own K, when available). Kept as separate result variants.

## D8 — Performance: avg AND peak VRAM
`bench/perf.py` samples VRAM continuously and reports **average and peak**, plus GPU
util %/power, effective FPS, per-window + end-to-end latency, CPU RAM peak, and (ours)
TSDF block count. Uniform across every method (wraps the subprocess).

## D9 — Metric accuracy: keep it, but from rendered GT (drop the tape measure)
The lab-capture / tape-measure path is dropped. Instead we benchmark **absolute
metric-scale accuracy** against the rendered GT (which has exact scale). Only PRISM is
metric-capable (RANSAC floor + known camera height); the scale-free baselines are
reported **N/A**. Metric = Umeyama scale-to-GT (|s−1|) + room-extent error.

## D10 — No own captures
We do **not** use the Theta-X lab captures. Rendered ScanNet++ (+ KITTI-360,
Matterport3D, Stanford2D3D) only.

## Conflict note (brief vs. 05)
05 marked the ScanNet-render pipeline "build deferred" and prioritised perf + lab
tape-measure first. Rafael's 2026-07-13 direction supersedes: build the render
orchestrator now, streaming-only, drop tape-measure, keep rendered-GT metric accuracy.
