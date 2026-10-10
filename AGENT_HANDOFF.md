# Handoff: PRISM benchmark rerun (rerun-v2) — context for the next agent

You are picking up an in-progress benchmark effort. Read this, then verify things
yourself before acting — treat everything labelled *hypothesis* as unproven.

## Who / what

- User: Rafael (rafael@neosenti.com), runs the benchmark for a paper (repo
  `uofa-2026-report`). Prefers short, direct answers and exact copy-paste commands.
  Compute is limited and paid per hour: be selective about GPU runs.
- **Do not commit or push without the user's OK.** He reviews changes first. He pushes.
- Workspace on his Windows PC: `C:\Dev\ualberta\` with four repos:
  - `PRISM-benchmarks` (this repo, branch `rerun-v2`) — the harness.
  - `PRISM-VGGT` (branch `prism-v2`) — our method (PanoVGGT windows + submap alignment + nvblox TSDF).
  - `uofa-2026-report` — the paper.
  - `vat-monorepo` — robot system using PRISM-VGGT as a submodule (server docs in `docs/setup/server.md`).
- File quirks: PRISM-VGGT files are CRLF; most PRISM-benchmarks files are LF
  (README.md is CRLF). Preserve line endings.
- Hugging Face (private): https://huggingface.co/datasets/DoninhaD/prism-bench-inputs
  - `inputs/rerun-v2/` rendered frames (tar per scene) + MANIFEST
  - `results/rerun-v2/live/` checkpoints from the pod; `results/rerun-v2/*.tar` final packs
  - PanoVGGT weights: https://huggingface.co/buckets/DoninhaD/PanoVGGT-bucket
  - A HF token was pasted in an earlier chat; it should be revoked after the run. Ask the user for a token if you need one.

## Pipeline (see README.md for commands)

1. PC (WSL) renders Replica once: `make inputs` -> `make inputs-push`.
   `make replica` streams the archive and keeps only the 6 scene meshes.
2. One GPU pod: `make pod` = prep -> env check -> data -> precheck -> bench -> pack -> Studio.
   Sequential runs, HF checkpoint every 15 min, resumable (`make pod` again).
   `make watch` = progress. Pod used: RTX 5090 32 GB, 100 GB disk.
3. PC scores: `make results-fetch && make results-merge && make eval-all publication`.
- `make diag SCENE=.. TRAJ=..` / `make diag-all`: per-sequence trajectory diagnosis
  (ATE all vs first 30 frames, heading drift, frame-to-frame rotation jumps with the
  worst frames, camera-convention flip test) + top-down plot in `results/diag/`.

Matrix (config.yaml): 6 Replica scenes (apartment_0, apartment_1, office_0, room_0,
room_1, room_2), paths `synthetic` and `loop` at 2 Hz x 3 seeds, 300 frames each.
Methods: prism (Sim3), vggtslam (published config: submap 32, loop closure on), laser;
ablations prism_sl4 / prism_se3 / prism_sim3lock / vggtslam_noloop on seed 0.
Offline methods (panovggt, pi3, mapanything) off on 32 GB (`BENCH_OFFLINE=0`).

## What was changed in this effort (all on rerun-v2 / prism-v2)

- PRISM-VGGT `prism-v2`: alignment rework (all groups fit from the same dense overlap
  correspondences; robust Sim3; trimmed SL4 DLT), scale lock rework, levelling with a
  gravity prior + deferred refinement, guard fixes (flip pivot, upside-down skip).
  See `PRISM-VGGT/docs/PRISM_V2_CHANGES.md`.
- VGGT-SLAM harness: previously double-subsampled frames and ended up as a single
  submap (no pose graph). Now every frame kept (min_disparity 0), submap 32, loop
  closure on; poses deduped; timing fixed. Pinned gtsam 4.3.0 and upstream commits.
- Trajectories: yaw-rate limited to 45 deg/s (was up to ~180 deg/frame).
- Replica mesh loading: Open3D silently dropped ~50% of the quad faces; now parsed with
  plyfile (inputs were re-rendered after this fix; panoramas 98-100% valid).
- Harness: render-on-PC inputs + fingerprint check, precheck gate, progress monitor,
  HF checkpoints + resume, retry of crashed runs, per-method multi-pod split, diag tool.
- Earlier result sets (2026-07/08) are not comparable: alignment-study numbers void,
  renders had holes (see RESULTS_CHANGELOG.md §14).

## Current state (2026-10-10)

The full run on the pod was **stopped** after ~13-20 runs because the user inspected
point clouds and found them badly misaligned on the apartments ("3 copies of the scene
around one pivot, Y-shaped") and still misaligned on some rooms.

`make diag-all` output (seed 0, synthetic path; ATE = Sim3-aligned RMSE):

| scene | prism | prism_sl4 | prism_se3 / sim3lock | laser | vggtslam | vggtslam_noloop |
|---|---|---|---|---|---|---|
| room_0 | 2.9 cm | 4.3 | 22.0 / 22.1 | 36.8 | 67.7 | 206.3 |
| room_1 | 3.7 | 3.5 | 18.4 / 18.4 | 34.5 | 68.7 | — |
| room_2 | 2.6 | 3.2 | 7.1 / 7.1 | 41.2 | 32.9 | — |
| office_0 | 4.2 | 6.1 | 11.3 / 11.3 | 70.0 | 47.5 | — |
| apartment_0 | 436 | 430 | 433 / 433 | 432 | 284 | 412 |
| apartment_1 | 361 | 362 | 357 / 357 | 360 | 240 | 366 |

Other diag facts:
- Camera-convention flip test: "ok" for every method/scene.
- Rooms: PRISM has 0 frame-to-frame jumps >5 deg; VGGT-SLAM has 33-110 per sequence
  (RPE median 1.3-3.8 deg); LASER drifts in heading (up to -45 deg on office_0).
- Apartments: **all methods fail at the same frames** — apartment_1: 73-74, 143-144,
  196, 265-266; apartment_0: 105-106, 133-135, 158, 243-244, 266-273 (90-178 deg errors).
- Rendered depth at those apartment_1 frames: frame 143 median depth 4 cm, 90% of
  pixels < 30 cm; frames 73, 196, 265-266 have 36-46% of pixels < 30 cm; neighbours
  are normal (median ~1 m).
- GT paths: 300 frames x 0.25 m (0.5 m/s @ 2 Hz), ~74 m, lapped around a circuit
  ("lengthened: N laps", up to 11 in rooms). Median heading change per frame:
  room_0 5.5 deg, room_1 15.4, office_0 and room_2 22.5 (= the yaw-rate cap), apartments ~4.
- `synthetic_*` and `loop_*` GT files differ but had identical span/step statistics in a
  quick check — whether the two families are actually distinct is unverified.
- Timing per run on the 5090: PRISM ~105 s wall (~65 s processing), VGGT-SLAM
  ~170-180 s wall (~53 s SLAM), LASER ~117 s (~41 s). Fixed per-run overhead is large
  (model load, point-cloud write; VGGT-SLAM raw dump ~45 M points). Full matrix
  projected ~5.7 h.

Hypotheses from the previous agent (verify, don't assume):
- H1: in multi-room scenes the path generator (`dataset/trajectories.py`, waypoint tour)
  routes the camera through walls/doorframes; that would explain the shared failure frames.
- H2: the baselines' poor room numbers (vs published VGGT-SLAM ~5-7 cm on TUM/7-Scenes,
  30 fps) come largely from the input regime: 2 Hz, 0.25 m between frames, constant
  turning up to 22.5 deg/frame, narrow-ish pinhole FOV (`synthetic_fov`). Not yet tested
  (e.g. by running VGGT-SLAM on TUM, or on a gentler/denser render).
- H3: per-window scale (prism Sim3 free) matters: se3/sim3lock are 2-6x worse on rooms.

## Open questions / decisions for the user

- How should trajectories be generated so they are collision-free and fair to pinhole
  methods (turn rate, frame rate, lapping vs. a single tour, path length)? Any change to
  `config.yaml` render sections, `dataset/trajectories.py` or `dataset/render_scene.py`
  requires re-rendering on the PC (`make inputs`, a few hours) and re-pushing inputs.
- Is the 2 Hz protocol defensible against the baselines, or should a denser rate be added?
- Stop-and-go trajectories are in the paper draft but disabled in config.
- Paper text: alignment-study numbers and the "globally consistent" claim are void;
  offline methods must be reported as OOM on 32 GB or run on a 96 GB card.
- Later: per-run overhead reduction; a VGGT-SLAM sanity check on its own dataset.

## Working conventions that saved time

- Iterate on 1-2 sequences, not the matrix: on the pod
  `PRISM_FORCE=1 uv run python adapters/run.py --method <m> --config config.yaml --scenes <scene> --traj <traj>`
  then `make diag SCENE=<scene> TRAJ=<traj>`.
- Precheck (`make precheck`) gates the long run; `PRECHECK_MAX_ATE_M` default 0.5 m was
  raised to 3 for the last run because VGGT-SLAM exceeded it.
- Never run two GPU jobs at once on the pod (timings). `make watch` is read-only.
- Don't `git pull` on the pod while `pod.sh`/`run_overnight.sh` is executing (bash reads
  scripts incrementally); Python files are safe.
- `make -n` executes recipe lines containing `$(MAKE)` — it once started a 34 GB download.
