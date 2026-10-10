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
