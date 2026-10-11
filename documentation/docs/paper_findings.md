# Findings for the paper (rerun-v3)

Short, citable results gathered while building the benchmark. Each points to the
decision entry (`decisions.md`) with the full reasoning and the numbers' provenance.
Paper sentences are drafts.

## 1. Benchmark trajectories must be checked against the geometry (D19)
- The rerun-v2 camera paths went through walls in the multi-room scenes: 42
  (apartment_0) and 22 (apartment_1) wall crossings over 3 seeds, found by ray casting
  every pose against the mesh (`scripts/traj_audit.py`). Every method lost track at
  exactly those frames.
- Fix: plan on the walkable free space (>= 0.30 m camera clearance, >= 0.20 m body
  clearance, doorways included) and re-check every pose; 0 crossings in all new
  sequences.
- Replica room_2 is tilted 8.7 deg in the release; meshes are levelled before
  rendering (D20).
- *Draft:* "Camera paths are planned on the walkable free space of each mesh and
  verified collision-free by ray casting; meshes are levelled (room_2 is tilted 8.7 deg
  in the release)."

## 2. PRISM never gets lost; the baselines tear or drift (D25, pilot)
Pilot: room_0, office_0, apartment_1; one 30 m walk at 10 / 5 / 2 Hz (seed 0).

| | ATE (cm) | tracked % | loss events | survives full walk |
|---|---|---|---|---|
| PRISM | 1.1–4.1 | 100 | 0 | 9 / 9 |
| LASER | 11–62 | 89 | 16 | 0 / 9 (fails after 6.5–18 m) |
| VGGT-SLAM | 22–164 | 35 | 45 | 0 / 9 (fails after 2.6–10 m) |

- Metrics (`scripts/lost_metrics.py`, poses + GT only): tracked % = 2 m windows of the
  walk, each aligned on its own, within 5 cm / 5 deg; loss events = runs of untracked
  windows; distance to failure = distance until > 0.30 m off after aligning on the first
  2 m (survival curve). Ranking unchanged at 3 / 5 / 10 cm thresholds
  (PRISM 100/100/100, LASER 79/89/96, VGGT-SLAM 21/35/53).
- They separate failure modes: LASER on apartment_1 is 100% tracked locally but drifts
  out after ~7 m (smooth drift); VGGT-SLAM tears (office_0: 2–7% tracked).
- *Draft:* "PRISM tracked 100% of every walk with no loss events, while the pinhole
  baselines lost track within 3–18 m."

## 3. Denser input does not rescue the pinhole baselines (D22)
- Same walk, rendered once at 10 Hz, 5 and 2 Hz cut from it: VGGT-SLAM 22–49 cm at
  10 Hz vs 23–164 cm at 2 Hz; LASER gets worse in room_0 (24 -> 48 -> 62 cm at
  2 / 5 / 10 Hz). Their published settings do not help (VGGT-SLAM 50 px keyframing:
  27–105 cm; LASER 20/5 window: same as 16/4).
- PRISM is 1.1–4.1 cm at every rate with its default window (16/4); larger windows help
  at 10 Hz (mean 3.0 -> 1.5 cm at 64/16). It processes ~4.5 frames/s: real time at the
  deployed 2 Hz.
- *Draft:* "Increasing the capture rate to 10 Hz did not close the gap: the pinhole
  baselines remained at 22–62 cm."

## 4. The VGGT-SLAM integration reproduces its own benchmark (D29)
- TUM RGB-D fr1 (9 sequences), published settings: the authors' evaluation script on our
  build 4.1 cm mean ATE; the same sequences through our harness 4.1 cm, identical per
  sequence within 0.1 cm (at or below the 1.0 paper's ~5.3 cm, as expected for 2.0 code).
- So its Replica errors are the method in this setting, not the benchmark. Its own
  setting is easier: 30 fps textured handheld video, of which its keyframing keeps
  7–14%.
- *Draft:* "We verified our VGGT-SLAM integration on TUM RGB-D fr1: 4.1 cm mean ATE
  through our harness, identical to the authors' evaluation script on the same build."

## 5. 360 deg data vs engine (D26, D28) — results pending
- Claim structure: the 360 deg view keeps PRISM from getting lost (it still sees
  structure behind it when facing a blank wall); the engine makes 360 deg streamable,
  metric and bounded in memory.
- Controls: the pinhole baselines on the same 360 deg captures as 4 cube faces per
  timestep, plain (90 deg) and with 20 deg overlap (110 deg) (D28); the engine ablation
  (prism_se3 / prism_sl4: PanoVGGT windows chained with a weaker alignment; 2–6x worse
  than full PRISM on the rooms in rerun-v2).
- Report accuracy, loss metrics, rig consistency and frames/s per 360 deg capture.

## 6. Protocol facts to state
- 6 Replica scenes, walks planned per scene: rooms (< 20 m2 walkable) 30 m / 121 frames,
  apartments 74.75 m / 300 frames, 0.5 m/s, 2 Hz (deployed Theta-X rate), yaw <= 45 deg/s,
  3 seeds (D21–D24).
- Offline feed-forward methods (Pi3, MapAnything, PanoVGGT) need 50–93 GB: OOM on the
  32 GB RTX 5090; report as such or run on a 96 GB card.

## 7. rerun-v3 Replica results (18 sequences, 2 Hz; scored 2026-10-11)
Medians over runs. Survive = whole walk tracked (2 m-anchored, 30 cm threshold).

| Method | ATE | Masked F@5cm | Tracked % | Survives whole walk |
|---|---|---|---|---|
| PRISM | 2.5 cm | 0.94 | 100 | 18/18 |
| LASER pinhole | 22.5 cm | 0.59 | 95 | 2/18 (0/6 apartments) |
| LASER cube 90 / 110 deg | 6.2 / 6.7 cm | 0.74 / 0.69 | 100 (rooms) | 6/8 rooms; apartment_0 OOM-killed on the first pass |
| VGGT-SLAM pinhole | 30 cm | 0.42 | 32 | 0/15 |
| VGGT-SLAM cube 90 / 110 deg | 22 / 25 cm | 0.52 / 0.55 | 33–53 | 0/12 |

(VGGT-SLAM seed-2 apartment_0/1/office_0 and laser_cube apartment_0 were rerun after a
GitHub outage / host-RAM fix; refresh this table from `results/report_clean/` after
the incremental eval.)

- **Getting lost.** VGGT-SLAM loses track (submap junctions tear); LASER keeps
  tracking but drifts (fails the 30 cm test after ~12 m); PRISM completes every walk.
- **The field of view itself helps.** The same panorama as 4 cube faces cuts LASER's
  ATE 22 -> 6 cm on the rooms and it then survives most walks: the 360 deg view
  prevents getting lost even for a pinhole method. PRISM is still 2–3x better, and
  LASER on cube faces cannot hold the apartments (1,200 images; host-memory kill) —
  where PRISM's bounded memory matters. VGGT-SLAM barely gains from cube faces.
- **Alignment study (engine).** Sim(3) 2.8 cm / F 0.92 / 1.9 %/m drift; SL(4) 3.2 cm /
  0.91 / 2.1 %/m; SE(3) 7.6 cm / 0.73 / 4.1 %/m, survives ~23 m of 73 on the
  apartments. Scale correction between windows is what matters; SL(4)'s extra 8 DoF
  buy nothing (VGGT-SLAM's argument does not hold here). Note Sim(3) has 18 runs, the
  other two 6: compare on the same 6 sequences in the paper table.
- **Figures (candidates):** `results/_deepdive/traj_all.png` (all 18 aligned
  trajectories — answers "cherry-picked paths"), `traj_cube.png`,
  `cloud_slices.png` (slice at camera height, coloured by distance to GT).

## 8. Fairness and correctness audit of the baselines (2026-10-11)
Done after the baseline clouds "looked wrong" in a viewer. Nothing in the harness
disadvantages them; one scoring bug (a failed run scored) was found and fixed.

- **Pose format.** For every run, a joint fit of world rotation and camera-axis
  convention on orientations alone: all methods are camera-to-world in the GT axis
  convention (identity), median residual 0.4 deg PRISM, 1 deg LASER, 2.5 deg VGGT-SLAM.
  All poses present, matched to the right GT timestamps.
- **Trajectory alignment.** Rotation from the position-only Sim(3) agrees with the
  orientation-only fit within 0.2–3 deg; tilt < 1 deg (the walks are planar, so this
  had to be checked).
- **Cloud alignment.** Re-aligned every cloud with a far more generous search
  (wide-radius Sim(3) ICP, then the tight one): baseline F improves only by a few
  points (LASER 0.32 -> 0.36, VGGT-SLAM 0.24 -> 0.27 on subsampled clouds, PRISM 0.78).
  The gap is the clouds: thick, noisy walls even where tracking is good, doubled
  walls where it drifts — one rigid transform cannot undo drift.
- **Why the raw clouds look wrong in a viewer.** `cloud.ply` is in each method's own
  frame and scale; the eval aligns in memory. PRISM's looks right because it is metric
  and gravity-aligned. `SAVE_ALIGNED=1 eval_recon` now writes `cloud_aligned.ply`.
- **Scoring bug fixed.** A killed `laser_cube` run (apartment_0) left 1,200 per-face
  poses (not collapsed to 300 timesteps) and was scored against the wrong GT frames
  (3.2 m). eval_traj / eval_recon / lost_metrics now refuse runs whose perf.json says
  they did not complete, or with more poses than GT frames; they count as failures.
- **VGGT-SLAM implementation.** On TUM fr1 our runner reproduces the authors' own
  eval script: 4.1 vs 4.1 cm (D29). Settings are the published ones: submap 32, loop
  closure on, retrieval 0.95, confidence 25 %. Its machinery engages (room_0 s0: 6
  submaps, 2 loop closures).
- **VGGT-SLAM keyframing.** Keeping every frame beats its 30 fps-video gate
  (min_disparity 50 px): 22 vs 27 cm (room_0, 10 Hz pilot) — we use its better setting.
- **Frame rate is not what hurts it.** Pilot at 2 / 5 / 10 Hz: 23 / 29 / 22 cm on room_0,
  28 / 26 / 23 cm on office_0. VGGT-SLAM is designed for dense video; at 2 Hz frames are
  25 cm apart and the submap junctions misalign (zig-zag trajectories), but denser
  input does not fix it, so the regime is not the explanation.
- **LASER window.** Its own eval window (20/5) vs ours (16/4): 62 vs 62 cm (room_0,
  10 Hz), 30 vs 31 cm (office_0) — no better.
- **Camera motion.** Yaw capped at 45 deg/s, so consecutive 90 deg pinhole frames always
  overlap (D23).
- **Why older runs looked better (do not cite them).** The rerun-v2 / August walks were
  short (rooms ~20 frames, apartments 20–80) and VGGT-SLAM's 50 px keyframe gate
  dropped most frames: room_0 had 1 submap, 0 loop closures
  (`degenerate_single_submap: true`) — a single VGGT pass, not SLAM (14 cm). LASER was
  likewise on 30–80 frames (~3 cm). The apartments were already bad then (VGGT-SLAM
  1.7–2.8 m, LASER 2.2 m). rerun-v3 walks are 121–300 frames with every frame kept: the
  methods' real streaming regime.
- **State in the paper.** Baselines are scored on their native raw clouds; PRISM's
  TSDF caps depth at 4.5 m and carves floaters. Same Sim(3)+ICP alignment for all.
