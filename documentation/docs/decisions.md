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

## D15 — Alignment-group ablation + SL(4) as the default  *(SUPERSEDED by D17)*
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

## D17 — Default alignment group reverted to Sim(3)  *(supersedes D15)*
D15 set the default to SL(4) on preliminary 2-easy-scene data and explicitly said
"revisit the default after the loop/dwell trajectories". The big run ran them, and they
reversed the call: the choice is **motion-dependent**, not uniformly in SL(4)'s favour.

| Trajectory (2 Hz) | SL(4) ATE / F / scale% | Sim(3) ATE / F / scale% |
|---|---|---|
| smooth | **44.0** / **0.46** / 10.3 | 46.2 / 0.41 / **10.0** |
| stop-and-go | **51.9** / **0.43** / **12.1** | 72.3 / 0.38 / 16.0 |
| loop | 110.5 / 0.26 / 31.4 | **101.9** / **0.34** / **20.3** |

SL(4)'s projective freedom accumulates non-rigid drift once the path closes — exactly
the failure Sim(3)/SE(3) forbid by construction, and the loop trajectory made it visible.
Since real deployments loop, **the default is Sim(3)**, set explicitly in `config.yaml`
(`run_env: {PRISM_ALIGN: "sim3"}`) rather than inherited from the engine, so the arm's
identity cannot drift if the PRISM repo changes its own default. SL(4) moves to the
`prism_sl4` ablation arm.

Two caveats attached to this decision. First, **pooled across all motion the three groups
are not statistically separable** (paired test, p = 0.29-1.00); the trade-off is real only
*within* motion families, and the stratified table is the result — not the marginal means.
Second, **arm naming changed meaning**: in the 2026-07 archive `prism` was SL(4); from
this decision forward `prism` is Sim(3). `eval/aggregate_clean.py` carries an era map
(`ALIGN_ERAS`) so historical results stay correctly labelled.

## D18 — Publication aggregation is separate from `make report`
`make report` aggregates every run present in `results/`, which is how the 2026-07
"Global aggregate" ended up mixing the seeded matrix with stale 2-scene runs carrying
co-tenancy-inflated VRAM. Rather than change its behaviour (per-scene browsing still
wants everything), publication-facing aggregation lives in `make report-clean`
(`eval/aggregate_clean.py`): seeded-only, named exclusions, and **complete runs only**.

The last filter matters more than it looks: 43 of 368 seeded runs produced no evaluable
output, all of them PRISM arms, and their `eff_fps` was computed from the *input* frame
count — so including them inflated PRISM's throughput. `make verify-clean` is the
regression guard and fails non-zero if any contaminated run reaches a clean table. See
`RESULTS_CHANGELOG.md`.

## D19 — Collision-free trajectories (grid planner) *(decided, rerun-v3)*
The rerun-v2 spline planner checked only its waypoints; the Catmull-Rom curve between
them cut through walls. Ray-casting audit (`scripts/traj_audit.py`) of the rendered GT:
42 (apartment_0) and 22 (apartment_1) wall crossings over 3 seeds, the camera inside
geometry exactly where PRISM, VGGT-SLAM and LASER all failed at once
(apartment_1 s0 frames 73-74, 141-144, 195-196, 264-267); room_0 passed 0.11 m from
furniture and over the coffee table. Rooms were otherwise clean.
Now (`planner: grid`): walkable-space raster at camera height (floor below, >= 0.30 m
camera clearance, >= 0.20 m body clearance), Dijkstra legs biased to corridor centres,
line-of-sight shortcut, clearance-safe corner rounding, exact mesh re-check that
rejects any crossing; `check_scenes` gates rendering on it. Each lap draws a fresh
waypoint set (2-opt order). Audit of the 36 new sequences: 0 crossings, min clearance
>= 0.30 m. All rerun-v2 numbers on apartments are void; room numbers are superseded.
*Paper:* "Camera paths are planned on the walkable free space of each mesh (>= 0.3 m
from any surface, doorways included) and verified collision-free by ray casting."

## D20 — Scene meshes are levelled *(decided, rerun-v3)*
Replica room_2 is tilted 8.7 deg relative to its mesh Z (the others 0.1-1.5 deg): a
level camera saw a sloping floor and its height above the floor varied by ~0.6 m along
the walk, while PRISM anchors metric scale on that height. The renderer now fits the
floor plane and rotates it horizontal (`level_floor`, threshold 0.2 deg) before
rendering; GT mesh and poses are in the levelled frame.
*Paper:* "Meshes are rotated so that the floor is horizontal (room_2 is tilted 8.7 deg
in the release)."

## D21 — Motion families: `loop` was a duplicate *(DECIDED 2026-10-10: dropped)*
In rerun-v2 `loop_*` and `synthetic_*` were the same poses to within 5 mm (laps put the
appended return waypoints past the truncation point) — half the matrix was duplicated.
Now `loop` ends at its start and draws its own waypoints. Proposal: drop the family.
Every 75 m walk already revisits 40-85% of its frames (>= 20 s apart, < 0.5 m), so
loop closure is exercised in every sequence; dropping it halves the matrix (D24).

## D22 — Capture rate and window sizes chosen by a pilot *(DONE — see D22 outcome)*
At 0.5 m/s and 2 Hz (0.25 m between frames) the furnished rooms force 12-22 deg of
heading change per frame (office_0 sits at the 45 deg/s yaw cap); a 90 deg pinhole
keeps 75-87% overlap per frame, a panorama 100%. Published pinhole baselines run on
~30 fps video (VGGT-SLAM's 50 px keyframing, LASER's 20/5 window assume dense input).
Pilot (`config.pilot.yaml`, `scripts/pilot.sh`): room_0, office_0, apartment_1, one
30 m walk rendered at 10 Hz; 5 and 2 Hz are every 2nd/5th frame of the same render
(`derive_rates_hz`), so rate is the only variable. Arms: defaults at 10/5/2 Hz; PRISM
window/overlap 16/4, 24/8, 32/8, 32/16, 48/16, 64/16; VGGT-SLAM min_disparity 0 vs 50;
LASER 16/4 vs 20/5 (its own eval setting). The report compares rates on the shared
2 Hz frames (`ATE@2Hz`). Record the chosen rate and windows here once it has run.
Current settings: PRISM 16/4, LASER 16/4, VGGT-SLAM w=32, min_disparity 0, loop on.

## D23 — Scenes: keep all six; size the walk to the scene *(DECIDED 2026-10-10)*
Walkable area (0.2 m body clearance): office_0 4.6 m2, room_1 7.4, room_2 10.8,
room_0 14.4, apartment_0 44.9, apartment_1 43.2. Keep the scenes: room_0/office_0 are
the NICE-SLAM / iMAP standard and comparable to the literature, the apartments are the
multi-room case where bounded memory and drift matter. The mismatch is the path, not
the scene: a fixed 74.75 m walk is 16 m per m2 of floor in office_0 and 1.7 in the
apartments, i.e. ~5 laps of a 4.6 m2 office. Proposal: one length per size class —
rooms ~30 m (2-3 covers), apartments ~60-75 m — reported per scene, never averaged
across classes.
Applied: `small_scene_area_m2: 20`, `small_scene_path_m: 30` — the four rooms walk 30 m
(121 frames at 2 Hz), the apartments keep 74.75 m (300 frames).

## D24 — Benchmark cost *(DECIDED 2026-10-10, overhead cut deferred)*
Measured per run on the RTX 5090 (300 frames): PRISM 105 s wall / 65 s processing,
VGGT-SLAM 175 / 53, LASER 117 / 41 — 40-70% of every run is fixed overhead (model
load, point-cloud write; VGGT-SLAM's raw dump is ~45 M points). Model
`wall = overhead + per-frame x frames`, fitted to these: current matrix 156 runs ~5.6 h;
drop `loop` (D21) 78 runs ~2.8 h; also drop `prism_sim3lock` (within 0.1 cm of
`prism_se3` on every scene) 72 runs ~2.6 h; also cut overhead (one model load per method
per scene, decimated cloud dump) ~1.9 h. With D22 at 5 Hz on 30 m walks ~2.0 h; at
10 Hz ~3.1 h.
Applied: 2 Hz main matrix (the deployed rate; the pilot is reported as the rate study,
D22), `loop` dropped, `prism_sim3lock` dropped, walk length by size class (D23); seeds
stay at 3. Per-run overhead cut deferred (code work, only pays off over several reruns).
Projection with the cube-face arms (D28): 54 main + 18 ablation + 12 cube runs
~2.9 h; render ~43% of the rerun-v2 pixel count.

## D25 — "Got lost" metrics: tracking continuity, not only ATE *(decided, rerun-v3)*
ATE cannot tell smooth drift (locally right, globally off) from a tracking loss (the map
tears and the scene is duplicated). `scripts/lost_metrics.py` (poses + GT only, every
method): **tracked %** (2 m GT-path windows, each Sim(3)-aligned on its own, tracked if
RMSE < 5 cm and rotation error < 5 deg), **loss events** (runs of untracked windows) and
first loss distance, **re-anchoring segments** (greedy, 10 cm), and **distance to
failure** (aligned on the first 2 m, distance until error > 0.30 m; survival curve).
Pilot (3 scenes x 3 rates, 30 m): PRISM 100% tracked, 0 losses, survives the full walk
in 9/9 runs; LASER 89% tracked, 16 losses, fails after 6.5-18 m (apartment_1: 100%
tracked locally but drifts out after 6.5-8 m: smooth drift); VGGT-SLAM 35% tracked,
45 losses, fails after 2.6-10 m (office_0 1.8-7% tracked). Ranking unchanged at
3 / 5 / 10 cm local thresholds (PRISM 100/100/100, LASER 79/89/96, VGGT-SLAM 21/35/53):
report the threshold sweep. PRISM also logs a per-window alignment residual
(`alignment.json`: dense_rmse, inliers) — a candidate self-reported confidence to
check against these GT-based losses.

## D22 outcome — capture rate and windows *(pilot done 2026-10-10)*
- Density does NOT rescue the pinhole baselines: VGGT-SLAM 22-49 cm at 10 Hz vs 23-164
  at 2 Hz; LASER gets worse in room_0 (24 -> 48 -> 62 cm at 2 / 5 / 10 Hz). Their
  published settings do not help either (VGGT-SLAM 50 px keyframing: 27-105 cm; LASER
  20/5: same as 16/4). The H2 "input regime" explanation is refuted for these scenes.
- PRISM is 1.1-4.1 cm at every rate with the default 16/4. Larger windows help at 10 Hz
  (mean 3.0 -> 1.5 cm at 64/16, +50% time, 23.6 GB) and at 5 Hz (2.4 -> 1.4 cm at 32/8).
- PRISM processes 4.4-4.7 frames/s (w16) — real time at the deployed 2 Hz.
- Decided: main matrix at 2 Hz (deployed rate, PRISM w16/o4); the pilot (10/5/2 Hz, window
  sweep, baselines' published settings) is reported as a separate rate study.

## D26 — Paper focus: continuity / "never gets lost" *(PROPOSED)*
The pilot's sharpest separation is not ATE but continuity: PRISM never loses track,
the baselines tear (VGGT-SLAM) or drift out (LASER) within 3-18 m. Proposal: lead with
robust long-horizon mapping (survival curve, loss events, tracked %), keep the Sim(3)
alignment as the mechanism and its ablation as support. Framing (Rafael, 2026-10-10): the
360 deg view is what keeps PRISM from getting lost (it still sees structure behind it
when facing a blank wall); the engine is what makes 360 deg streamable, metric and
bounded. Required controls: (a) FOV control — the baselines on the same 360 deg data
as cube faces (D28, mandatory), and the engine ablation (prism_se3 / prism_sl4 /
prism_sim3cam = PanoVGGT windows chained with a weaker alignment; no ICP chaining
needed); (b) a VGGT-SLAM sanity run on its own data, so a reviewer cannot read
its numbers as a harness problem; (c) multiple seeds and the full scene set.

## D27 — DUSt3R / MASt3R-SLAM: not added for now *(DECIDED 2026-10-10)*
DUSt3R is pairwise with an offline global alignment over a pair graph; it does not
stream and does not scale to 300-600-frame sequences on 32 GB, and the feed-forward
reference slot is already covered by Pi3 / MapAnything (VGGT-family). If one more
baseline is wanted, MASt3R-SLAM (CVPR 2025; real-time monocular SLAM on MASt3R, loop
closure) is the DUSt3R-family streaming SLAM a reviewer would ask for; expect a CUDA
extension + lietorch build (VGGT-SLAM-level effort); it pins PyTorch 2.5.1, which has
no RTX 5090 (sm_120) kernels, so it needs a rebuild on a newer PyTorch. Revisit if a
reviewer asks.

## D28 — Baselines on the 360 deg data as cube faces *(DECIDED 2026-10-10, mandatory)*
The control that separates the 360 deg input from the engine: the same captures given to
the pinhole baselines as 4 square pinhole faces per timestep (front, right, back, left —
the horizontal ring of a cubemap; PanoVGGT also uses cubemaps with Pi3), 512x512,
interleaved in one folder (image 4t+k = face k of timestep t; `faces.json` stores face
rotations and width). Seed 0. Two variants, both run by every `camera: cube` arm:
- `cube4` — `face_overlap_deg: 0`: plain 90 deg cubemap. The faces of one timestep touch
  only at the seams, so they can be linked only through neighbouring timesteps.
- `cube4_o20` — `face_overlap_deg: 20`: 110 deg faces, neighbours share 20 deg, so the
  faces of a timestep can be matched directly — the fairest chance for a pinhole method.
  Comparing the two shows whether the seams are what limits them.
Arms `vggtslam_cube` (submap 64 images = 16 timesteps) and `laser_cube` (window 32 /
overlap 8 images = 8 / 2 timesteps; boundaries on timestep boundaries). Each face is a
frame to the method; per-face poses are collapsed to one pose per timestep (front face),
and the runners record rig consistency (how much the faces' implied body orientations /
centres disagree — a diagnostic of how well a pinhole method exploits the rig).
`n_frames` counts timesteps, so fps compares with PRISM per 360 deg capture (4x the
images per timestep: the timing comparison).
Caveats to state: the methods do not know the faces share an optical centre (no rig
constraint); VGGT-SLAM's 1-frame submap overlap can split a timestep's faces; the window
sizes are image budgets chosen to fit 32 GB, not tuned.
Run order: the first rerun-v3 pod run has `cube4` (90 deg) only — the inputs were
rendered before the overlap variant existed. `cube4_o20` is added afterwards: the
renderer resumes per camera, so only that variant is rendered (seed 0), then the cube
arms run on it.
*Paper:* "To separate the panoramic input from the engine, the pinhole baselines are also
given the same 360 deg captures as four pinhole views per timestep, both as a plain
cubemap (90 deg faces) and with 20 deg overlap between neighbouring views (110 deg)."

## D29 — VGGT-SLAM sanity check on TUM *(DECIDED 2026-10-10)*
`scripts/sanity_tum.sh` (`make sanity-tum`): VGGT-SLAM on the 9 TUM fr1 sequences of
its own evaluation, published settings (w=32, min_disparity 50, loop closure on), twice:
(A) its own `evals/eval_tum.sh` + evo — checks the pinned install reproduces the paper;
(B) the same sequences through our runner (`scripts/tum_to_export.py`) — checks the
harness. Run it first on the pod; if A does not match the paper or B does not match A,
fix that before the matrix.
**Result (2026-10-10, RTX 5090 pod):** PASSED. Mean ATE over the 9 fr1 sequences:
A (their script) 4.1 cm, B (our runner) 4.1 cm; per sequence identical within 0.1 cm
(360 5.0, desk 2.7, desk2 2.9, floor 10.0/9.9, plant 2.5, room 6.4, rpy 2.6, teddy
3.5/3.6, xyz 1.4). That is at or below the 1.0 paper's ~5.3 cm (SL(4), w=32), as
expected for the pinned 2.0 code. The install and our harness reproduce VGGT-SLAM on
its own data, so its errors on the Replica renders (22-164 cm, D22) are the method in
that setting, not the benchmark. Note for the paper: on TUM (30 fps) its 50 px
keyframing keeps 7-14% of frames (54/613 desk ... 186/1362 room) — dense, slow,
textured handheld video; our sequences are a robot walk at 0.5 m/s through
low-texture rooms, where the pilot showed denser input does not help it.
*Paper:* "We verified our VGGT-SLAM integration on TUM RGB-D fr1: 4.1 cm mean ATE through
our harness, identical to the authors' evaluation script on the same build."
Published for traceability on the HF dataset under `sanity/tum_vggtslam/` (summary,
both pipelines' poses and logs, provenance; `make sanity-tum-push`).

## D30 — Public, gated Hugging Face dataset for traceability *(DECIDED 2026-10-10)*
Inputs and results (`DoninhaD/prism-bench-inputs`) are made public so every paper
number traces back to its frames, poses and logs. Replica's terms
(https://github.com/facebookresearch/Replica-Dataset/blob/main/LICENSE) allow using,
modifying and publishing the data for non-commercial research or education, but sharing
only with people who first agree to be bound by the terms — and the results packs
contain copies of the Replica meshes. So the repo is public **and gated**: visitors
accept the Replica terms before downloading. Card: `documentation/hf/README.md`;
`scripts/hf_publish.py` uploads it, enables gating, then flips the repo public.
(Not legal advice; the PanoVGGT weights bucket is a separate repo.)

## D31 — A small real 360 deg dataset for the harness *(DECIDED 2026-10-10: 360Loc)*
Need: real equirectangular sequences with GT poses, indoor, small enough to add quickly
(not KITTI-360). Candidates checked:
- **360Loc** (CVPR 2024; https://huajianup.github.io/research/360Loc/, data via
  https://github.com/HuajianUP/360Loc) — **recommended.** 4 campus scenes (atrium,
  concourse, hall: indoor; piatrium: indoor + outdoor piazza), 360 deg equirectangular
  6144x3072, 18 sequences (reference 491-632 images per scene; day and night queries up
  to ~1,200), GT from lidar SLAM + lidar bundle adjustment (cm level), reference point
  cloud + TSDF mesh + depth for the reference images (so reconstruction can be scored
  too), poses in COLMAP convention (`name x y z qw qx qy qz`). Its own tools generate
  pinhole and fisheye views from the 360 images — the same "same data, other camera"
  control as our cube faces. To check when adding: whether images are a continuous,
  ordered stream and their spacing; camera height above the floor (needed for PRISM's
  metric scale — measurable from GT poses + mesh); no licence is stated, so link to the
  source instead of re-hosting.
- Hilti-Trimble-Oxford 2026 (https://hilti-trimble-challenge.com/dataset-2026) — 30
  sequences x ~180 s, Insta360 ONE RS 1-inch at 30 Hz, lidar-inertial GT, construction
  site (robot-like). Raw dual-fisheye (stitching needed) and much larger: a second step.
- ORBIT / ORBIT++ (360 deg video SfM) — rejected: pseudo-GT from SfM, perspective crops.
Implemented: `dataset/import_360loc.py` + `config.real360.yaml` + `scripts/real360.sh`
(`make real-*`), tag `real360-v1`, dataset id `loc360`. The panorama is resized to
1036x518 (360Loc's equirect and camera axes are the same as ours, checked against its
process.py); the 90 deg pinhole and both cube variants are resampled from the same
full-resolution panorama, so every method sees the same capture. GT = 360Loc's lidar
poses (frame-index timestamps); the longest continuous segment is used (split at jumps
> max(1 m, 8x median step)). Camera height for PRISM: estimated from the scene point
cloud under the GT poses (or set in the config); a 25 deg cone around nadir is masked
in the panorama (handheld rig/operator). No depth/GT mesh: trajectory and continuity
metrics only (`scripts/real360_report.py`: ATE, metric scale, tracked %, loss events,
survival, fps per 360 capture). Quick check: hall, reference sequence, 5 arms.
Isolation from the Replica matrix: own overlay, tag and dataset dir; no change to the
render settings or trajectory/render code (rerun-v3 inputs stay valid); results.sh
packs/uploads only `loc360` runs (`RESULTS_DATASET`).
Validated before the real download (the cloud sandbox cannot reach the 360Loc host): a
fake 360Loc scene rendered from Replica office_0 — importer camera height 1.466 m vs
1.45 m true; resampled pinhole vs direct render mean abs. diff 2.6/255 (pano rendered at
1024 px only).
Download: the SharePoint links in the 360Loc repo now return an HTML page; the scripts
use the authors' file server https://hkustvgd.com/statics/360loc/<scene>.zip (hall
7.1 GB). Only the PC downloads raw 360Loc; pods fetch the imported, resized inputs from
HF (`inputs/real360-v1/`, a few hundred MB per sequence) like the Replica inputs.
360Loc states no licence: its imported frames can go to a separate HF repo
(`REAL_HF_REPO=<user>/<repo>`, e.g. private) until the authors confirm re-hosting is fine;
the public paper artefacts then link to 360Loc instead of re-hosting.
Alternatives re-checked 2026-10-10 (licence was the question):
- **Hilti-Trimble-Oxford 2026** — **CC BY-NC-SA 3.0** (re-hosting derived frames under the
  same terms is allowed), per-sequence ROS 2 bags on HF
  (`Hilti-Research/hilti-trimble-slam-challenge-2026`, 30 sequences, 162 GB total ->
  ~5 GB each), Insta360 ONE RS 1-inch dual fisheye 1472x1440 at 30 Hz + 1 kHz IMU, GT
  (lidar-inertial, `cam0 -> map`, TUM) public for ALL sequences since 2026-06-16 (first ~5
  s not covered), Kalibr EUCM calibration, and a reference dual-fisheye -> equirect
  stitcher in their repo (`challenge_tools_ros/bag_helper/image_stitching.py`; not exact,
  the lenses have different centres). Construction site across 7 floors — robot-like,
  long, textureless. No point cloud/mesh released (raw lidar withheld), so PRISM's camera
  height must come from the rig spec and reconstruction cannot be scored. Best licensed
  option; ~1 day to add (bag reader + stitching + 30 -> 2 Hz).
- **ODGS-SLAM** (CVPR 2026, UIBK) — CC BY-NC-SA 4.0, real indoor room with Insta360
  Pro / X4 on a mobile robot and motion-capture GT; but the real-world part is one
  126.9 GB zip, format not documented. Too heavy for a quick add.
- PALVIO — panoramic annular lens (360 x 40-120 deg, grayscale), Vicon GT; not an
  equirect 360 camera.
- IM360 / Matterport3D / Stanford2D3D — single panoramas, no sequences.
Decision: run the quick check on 360Loc now (downloaded, importer ready; frames go to
our HF repo provisionally while the authors are asked about the licence); add
Hilti-Trimble-Oxford 2026 as the licensed real dataset for the paper.
First look at the real data (hall, 2026-10-10):
- Layout: `mapping/daytime_360_0/{image,depth,camera_pose.json}`, 540 images, 275 m,
  0.51 m median step (one continuous sequence); `pose/360_mapping_gt.txt` matches.
  No point cloud in the zip; 16-bit 360 depth maps per image.
- Depth unit = centimetres: unprojecting frames 5 and 10 with the GT poses, the clouds
  agree to a 1.6 cm median at scale 0.01 vs 3.4-6.5 cm at 0.0075/0.0125/0.002. This also
  confirms that 360Loc's equirect and camera axes match ours. Straight-down depth ~1.9 m
  = camera height (rig held above the operator's head).
- **hall is outdoor** (a courtyard between dormitory buildings). It stays as the pipeline
  check; the indoor scenes for the paper are atrium and concourse.
- **The operator is in every panorama**, and the image centre is not the walking
  direction (the person sits at azimuth ~29 deg in frame 5, ~125 deg in frame 200 —
  i.e. right behind the direction of travel: 29 / 114 deg predicted from the GT motion).
  Fix in the importer: rotate each panorama about the vertical (exact column shift) so
  its centre looks along the world-smoothed direction of travel, apply the same rotation
  to the GT; the operator is then always at the back and a fixed region is blacked out
  (back +-55 deg below -8 deg, +-85 deg below -35 deg, everything below -65 deg; ~26% of
  the panorama, almost all below the horizon) before any view is resampled, and set
  invalid in every mask. The forward pinhole never sees the operator; the cube faces see
  the same blacked-out pixels as PRISM. Validated on a synthetic stand-in with random
  per-frame grip rotations: a pinhole rendered directly at the written GT pose matches
  the imported pinhole to 2.5-3.1/255 mean abs. difference.
Scene choice and scoring (Rafael, 2026-10-10): **atrium only** — indoor and essentially
static, so PRISM's indoor settings (max_depth 4.5 m, floor-based scale) apply and every
run is scored against one fixed map. Dropped: hall (outdoor), concourse (crowded: moving
people, no single static map), piatrium (half outdoor).
How the comparison works without a released map: (1) trajectories vs the lidar GT poses
(ATE, loss metrics, PRISM's metric scale) need no map; (2) for reconstruction, the
importer rebuilds the GT map by fusing the reference sequence's 360 depth maps (rendered
by the authors from their lidar map) with the GT poses — every 4th pixel, <= 10 m,
2 cm voxels — into `_gt_map.ply` / `gt_cloud.ply`, and resamples the depth into the
pinhole view for the co-visibility mask. `eval_recon.py` then scores every method's
cloud against that map exactly as on Replica (Sim(3)/ICP alignment, F@5 cm in the mask).
Stand-in check: fused map 10 mm median from the true surface (1024 px fake panoramas,
cm-quantised depth), pinhole depth within 5 mm of a direct render, a perfect prediction
scores F = 1.000.
First real run (atrium ref, 581 frames, RTX 5090, 2026-10-11): PRISM ran out of GPU
memory at 2 cm voxels — nvblox TSDF 1.04 M blocks at submap 33, and the GPU hash table's
doubling 2 M -> 4 M blocks failed (34.1 of 34.2 GB; PyTorch 8.8 GB, nvblox 15.3 GB before
the resize). The network side is bounded; the global TSDF map grows with the area seen
(275 m through a large building vs a few m^2 of Replica room) and real depth noise fills
more blocks than rendered depth. Real-data PRISM now uses 4 cm voxels
(`PRISM_VOXEL_SIZE`, config.real360.yaml); the reconstruction is still scored at 5 cm.
For the paper: "bounded memory" applies to the streaming inference; the map itself grows
with the explored area unless pruned (`tsdf_prune_radius`, the deployed local-map mode).
VGGT-SLAM 11.5 GB / LASER 9.0 GB on the pinhole input; VGGT-SLAM on cube faces 26.7 GB.
Unverified until the real data is downloaded: the folder layout of `mapping/` (use
`make real-list`), frame spacing, and the presence/format of the point cloud.

## Conflict note (brief vs. 05)
05 marked the ScanNet-render pipeline "build deferred" and prioritised perf + lab
tape-measure first. Rafael's 2026-07-13 direction supersedes: build the render
orchestrator now, streaming-only, drop tape-measure, keep rendered-GT metric accuracy.

## D32 — Failed runs are failures, not datapoints *(DECIDED 2026-10-11)*
A run whose `perf.json` says it did not complete, or whose `poses.tum` has more poses
than GT frames, is not scored by eval_traj / eval_recon / lost_metrics (stale scores are
deleted) and counts in the completion table. Trigger: a killed laser_cube run left
uncollapsed per-face poses that were scored against the wrong frames. eval_recon is now
incremental (skips runs whose recon.json matches the current cloud; `EVAL_FORCE=1`,
`EVAL_GLOB=...`), and `SAVE_ALIGNED=1` writes the scored cloud in the GT frame.

## D33 — Offline methods are rerun on the rerun-v3 walks, not reused *(DECIDED 2026-10-11)*
The 2026-08 PanoVGGT / Pi3 / MapAnything runs used the old spline walks (different
paths, lengths and renders, some through walls); their numbers are not comparable with
rerun-v3 and are not cited. PanoVGGT's peak VRAM grows ~0.18 GB/frame (23 GB at 63
frames, 40 GB at 156): 121-frame rooms need ~33 GB (just over the 5090), 300-frame
apartments ~65 GB — an 80 GB A100/H100 is enough; no RTX PRO 6000 needed.

## D34 — Offline references: PanoVGGT + Pi3, Replica seed 0 + real atrium *(DECIDED 2026-10-11)*
Two full-batch references, run once per map: PanoVGGT (PRISM's own backbone, 360 deg —
"what the streaming engine adds") and Pi3 (pinhole feed-forward, LASER's backbone).
Sequences: the 6 rerun-v3 Replica walks (seed 0) and the 360Loc atrium — 14 runs, on a
96 GB RTX PRO 6000. Every frame is tried first (121 / 300 / 581 — the frames PRISM
sees). A sequence that does not fit (OOM or host-RAM kill) is recorded
(`logs/offline_oom/`, `arm_config.json`: `full_length_oom`, `frames_used`) and rerun
uniformly subsampled to 200 frames (OFFLINE_FALLBACK_FRAMES) — the capacity limit and
the subsampling are both reported. Expected from 2026-08 peaks (PanoVGGT 50 GB, Pi3
93 GB at 200 frames): PanoVGGT full length on rooms/apartments, Pi3 full only on rooms;
both subsampled on the atrium. MapAnything dropped. Run: `make offline-pod`
(installs only the PRISM-VGGT and Pi3 envs; results tag offline-v3); PC:
`make offline-fetch`. The 2026-08 offline runs (old walks) are not reused (D33).

**D34 addendum (2026-10-11): offline-v3 is incomplete — rerun.** Two bugs: (1) runners
read `config.yaml` directly, so the offline overlay's `max_frames: null` never reached
them and the 200-frame cap applied (apartments 300 -> 200, atrium 581 -> 200; the pod
labelled them "full length" because no OOM fallback fired); (2) offline.sh read the
Replica scene list before the inputs (with the frozen split in config.local.yaml)
arrived, so the Replica pass ran nothing. Fixed: `adapters/base.py` hands every runner
the resolved config (`config_resolved.yaml` in the run dir); offline.sh reads scenes
after the fetch and refuses an empty list. The streaming results are unaffected: none of
their overlays set runner-side keys (PRISM's 4 cm voxels on 360Loc come from an env var).


## D35 — Map-centric scores and a second real campaign (real360-v2) *(DECIDED 2026-10-12)*

**Why.** The reconstruction score of eval_recon places each cloud with the Sim(3) of its
*trajectory* (+15 cm ICP). A map whose trajectory is poor is then judged partly by its
trajectory, and a map whose trajectory is fine but whose windows disagree (duplicated
walls) is not singled out. On the atrium, LASER's ATE is lower than PRISM's while its
map is several times worse; the protocol must be able to show that.

**Map scores (`eval/map_metrics.py`, `map.json` per run).** (1) Best-fit map placement:
starting from the trajectory Sim(3), a trimmed Sim(3) ICP of the cloud against the GT,
radii halving (Replica 0.5 -> 0.05 m, real 2 -> 0.25 m). (2) Accuracy (median map->GT),
completeness, precision / recall / F at 2/5/10 cm (Replica) and 10/20/50 cm (real),
under both placements. (3) Local accuracy: the placed map cut into square tiles (2 m
Replica, 5 m real), each re-aligned rigidly on its own; median of tile medians and the
share of points beyond tau ("ghost share"). Region: map points within the eval range of
the GT cameras (4.5 m; hall 10 m); on real data also within 3 m of the reference map
(it exists only where the mapping walk's depth maps saw; the kept share is reported).
Replica has no surface crop: a first version cropped there too, and a lost VGGT-SLAM
map then scored 3 cm on the fragment that was left (`--rescore` reapplies the rule to a
stored placement without redoing the ICP). Completeness has no
occlusion test (coverage-dependent; accuracy and local scores are not). numpy/scipy
only. `make map-metrics`.

**real360-v2 (`config.real360.yaml`).** All 360 sequences of atrium (indoor) and hall
(outdoor courtyard): mapping + 2 day + 2 night query walks each; queries scored against
the scene's GT map from the mapping walk and given its camera height (importer). One run
per method and sequence, streaming only: prism, laser, vggtslam; prism_h090 / prism_h110
(camera height x0.9 / x1.1, mapping walks only, `only_trajs`); `laser_tsdf` = LASER's
per-frame depth fused with its own poses by a TSDF at PRISM's voxel size and cap
(`LASER_SAVE_DEPTH`, `eval/fuse_tsdf.py`, numpy TSDF: Open3D 0.20's ScalableTSDFVolume
returned empty clouds), the same-back-end control. Hall: PRISM 10 m cap, 8 cm voxels
(`scene_env`), co-visibility range 10 m (`frustum_far_m_by_scene`). Dropped from v1:
cube-face arms on real data (no better than pinhole on the atrium) and offline methods
(best case = Replica + v1 atrium). Importer fix: path-keyed GT pose lookup (query pose
files list several sequences with the same image names).

## D36 — atrium-v3: longer PRISM range + LASER through the same TSDF *(DECIDED 2026-10-12)*
The real360-v2 campaign (D35) was not run (time). Instead, two runs on the atrium mapping
walk (inputs real360-v1): `prism_r8` (PRISM, Sim(3), free scale, TSDF range 8 m instead of
4.5 m so the map reaches the atrium's walls, 6 cm voxels for GPU memory) and `laser` with
its per-frame depth saved, fused by `eval/fuse_tsdf.py` at prism_r8's voxel and range
(`laser_tsdf`). Map scores of every atrium run are recomputed with a 10 m evaluation range
(`config.atrium_v3.yaml`). `make atrium3-pod` / `atrium3-watch` / `atrium3-fetch`.

## D37 — Fixes from the independent review *(DECIDED 2026-10-12)*
(1) `lost_metrics.seg_err`: the rotation part of "tracked" removed the median of unsigned
error ANGLES; it now removes the stretch's mean ROTATION (chordal mean) and takes the
largest geodesic residual. PRISM's tracked share drops from 100 % to 97-99 %; the
ranking is unchanged. (2) `metric_accuracy`: scale was fitted on rows paired by
position in the file; subsampled runs (Pi3X 200-frame) were matched to the wrong GT
frames. Now paired by timestamp. Affects only Pi3X's subsampled scale errors.
(3) Naming: the `pi3` arm runs Pi3X (`yyfz233/Pi3X`); LASER runs original Pi3. VGGT-SLAM
is 2.0 (min_disparity 0 = every frame kept, our adaptation).
