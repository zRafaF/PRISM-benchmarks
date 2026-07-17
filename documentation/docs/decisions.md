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
| Pi3 | yyfz/Pi3 | `9fa3ddb…` (latest; includes **Pi3X**) |
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

## D11 — Scale: quality is scale-normalised; metric accuracy is separate
Two distinct axes, never conflated:

- **Reconstruction quality** (acc/compl/Chamfer/F-score) is measured after aligning each
  cloud to GT with a **scale-corrected Sim(3) + ICP**. Scale is normalised out, so
  scale-free baselines (Pi3, VGGT-SLAM, LASER) are judged purely on geometry — the fair
  cross-method comparison.
- **Absolute metric-scale accuracy** (Table B) is a *separate* metric reported only for
  **metric-capable** methods (PRISM, MapAnything). Scale-free methods are N/A there.

So we do "disregard scaling" for the quality comparison, while still crediting metric
methods for getting real-world size right.

## D12 — Trajectory waypoints over bare floor + measured camera height
PRISM's metric scale is anchored by a RANSAC floor fit under the camera. The renderer
only samples waypoints where a downward ray hits the floor (not furniture) and feeds
PRISM the down-ray-measured camera height. Fixed the "first frame over a sofa -> 27%
scale error" issue.

## D13 — Physical capture-rate sweep (constant velocity)
Trajectory frames are sampled by **arc length** at spacing `speed / rate` (constant
velocity), simulating a real capture at `rate` Hz. We sweep **rates_hz = [0.5, 2, 5]** and
report by the inter-frame **baseline** = speed/rate (1.0 / 0.25 / 0.10 m at 0.5 m/s) — the
quantity that actually drives quality. Each rate is its own traj id
`synthetic_<rate>hz`, so the report shows every method across the spectrum. Frame count is
capped at `n_frames` (200) because full-batch baselines are near the VRAM ceiling there.
The same frames feed every method, so the sweep is inherently fair; low rate = sparse
wide-baseline (favours feed-forward), high rate = dense overlap (favours streaming, and
pushes full-batch toward the memory wall).

## D14 — Cloud cleanliness & size metrics
F-score@5cm rewards coverage but ignores stray floaters, so we add: **point count** and
**map size (MB)** (compactness), **noise fraction** (% of pred points > 10 cm from any GT
surface — the "fluffy dots"), and **precision@2cm** (sharpness). Computed on the saved
cloud (identical voxel dedup for all). These quantify the visible sharpness advantage of
PRISM's TSDF surface over per-pixel feed-forward pointmaps.

## D15 — Alignment-group ablation + SL(4) as the default
Added `PRISM_ALIGN` to the PRISM engine to switch the submap registration group:
**sim3** (7-DoF similarity), **se3** (6-DoF rigid at locked scale), **sl4** (15-DoF
projective homography fit from the DENSE overlap point maps — VGGT-SLAM's group,
integrated at its local similarity since nvblox is rigid; the discarded shear/perspective
is logged as the non-similarity distortion). Preliminary result: SL(4) ≥ Sim(3) > SE(3)
(small margins; scale DoF clearly helps). **Default set to SL(4)** (best on preliminary
data; floor grounding keeps it metric); Sim(3)/SE(3) remain measured arms
(`prism_sim3`, `prism_se3`). Key finding: `prism_sl4` (VGGT-SLAM's group inside PRISM)
still beats VGGT-SLAM ~4× on ATE → the advantage is the panoramic metric engine, not the
alignment math. Revisit the default after the loop/dwell trajectories.

## D16 — Big benchmark: motion-stress trajectories + variance
Beyond the smooth spline we add two trajectory families that stress streaming drift:
**stop-and-go** (walk / dwell / walk — noise accumulation, still-guard) and **loop**
(return to & re-observe the start — drift / loop-closure, where SL(4) projective drift
should diverge from Sim(3)). Big run = 6 scenes × 2 seeds × {smooth rate-sweep, stopgo,
loop} on a dedicated GPU, via `scripts/run_overnight.sh` (resumable, priority-ordered,
report checkpoints). This is the run that drops the "preliminary" label.

## Conflict note (brief vs. 05)
05 marked the ScanNet-render pipeline "build deferred" and prioritised perf + lab
tape-measure first. Rafael's 2026-07-13 direction supersedes: build the render
orchestrator now, streaming-only, drop tape-measure, keep rendered-GT metric accuracy.
