# Roadmap

## Findings & paper framing (after the preliminary 2-scene run)

**What this project is.** A *systems / robotics* contribution: a training-free engine
that turns a frozen feed-forward panoramic backbone (PanoVGGT) into an **online, metric,
bounded-memory 360° reconstruction system** — the first metric streaming reconstruction
in the VGGT family. It is NOT a new-alignment-math paper and NOT a best-reconstruction
paper (offline full-batch Pi3/PanoVGGT beat us on raw F; that is the streaming tax).

**Conclusive results so far (2 scenes, preliminary — need the big run to claim them):**

- **PRISM ≫ VGGT-SLAM (its direct streaming-SLAM competitor):** ATE 25.6 vs 97.7 cm
  (~4×), masked F 0.60 vs 0.43, map 16 vs 90 MB (~6×), and metric (3.2%) vs scale-free.
- **The win is the engine, not the SLAM math.** `prism_sl4` runs VGGT-SLAM's *own* SL(4)
  alignment group inside PRISM and still gets ATE 26 / F 0.66 / 15 MB — so PRISM's
  advantage comes from panoramic input + metric grounding + TSDF fusion, not the pose
  graph. This is the answer to "aren't we just VGGT-SLAM?": no.
- **Only metric method that works:** scale err 3.2% vs Pi3 8.7% / MapAnything 7.3%;
  LASER/PanoVGGT/VGGT-SLAM cannot produce metric scale at all.
- **Cheapest, cleanest, most compact map** among the dense methods (outlier 2.3%, 16 MB).
- **Streaming costs ~nothing in trajectory:** PRISM ATE 25.6 ≈ offline PanoVGGT 26.0,
  while adding metric scale and 4.5× compression.
- **Alignment-group ablation (2 easy scenes):** SL(4) ≥ Sim(3) > SE(3), all small
  margins; on the hard scene all three are identical (F 0.369). The smooth spline cannot
  stress the projective DoF — hence the loop/stop-and-go trajectories in the big run.
  Clean sub-result: the scale DoF helps (Sim(3) > SE(3)).

**Design decision:** default alignment group set to **SL(4)** (best on the preliminary
data; floor grounding keeps it metric). Sim(3)/SE(3) stay as measured ablation arms
(`prism_sim3`, `prism_se3`). Revisit after the loop/dwell trajectories — those are
designed to expose SL(4)'s projective drift, which may reverse this.

**Honest gaps to close in the big run:** (1) only 2 scenes / no seeds → nothing is
significant yet; (2) everyone fails on the large apartment (a *backbone* limit, must be
stated); (3) the bounded-memory figure is contaminated by GPU co-tenancy (~77 GB vs the
real ~14 GB) — needs a dedicated-GPU pass; (4) own the recon-F gap as the streaming tax.

## Big benchmark (the run that drops "preliminary")

Matrix: **6 Replica scenes × 2 seeds × trajectories × all methods + ablations**, on a
dedicated GPU (clean VRAM). Trajectories (`config.trajectories`):

- **smooth** (`synthetic_<rate>hz`) — full rate sweep 0.5/2/5 Hz (the easy reference).
- **stop-and-go** (`stopgo_2.0hz`) — walk / dwell / walk; accumulates noise, exercises
  the still-guard (the "parked robot" failure).
- **loop** (`loop_2.0hz`) — returns to and re-observes the start; the drift / loop-closure
  test where SL(4) projective drift should finally diverge from Sim(3).

Driver: `scripts/run_overnight.sh` (`make bench-overnight`) — detached (tmux), resumable
(skips completed runs), priority-ordered (headline smooth-2 Hz first), with eval+report
CHECKPOINTS after each phase so a partial overnight still yields a current report.

## Now — first small run
- [x] Orchestrator scaffold: Makefile, config, envs, dataset, adapters, eval, docs.
- [ ] `make init` + `make setup-all` on the 6000 box (clone + isolated envs).
- [ ] ScanNet++ ToU + one room; `make render` (synthetic_spline first — no dataset poses needed).
- [ ] `run-prism` end-to-end; confirm PRISM outputs → perf/recon/metric tables.
- [ ] Confirm the baseline runner API seams (marked `<-- API line N`) against the
      pinned commits for Pi3, VGGT-SLAM; then `run-pi3`, `run-vggtslam`.

## Next
- [ ] `dataset_path` pose importer per dataset (variant A) + `real_intrinsics` K loader.
- [ ] MapAnything + LASER runners wired and validated.
- [ ] Matterport3D + Stanford2D3D (panorama-native) importers.
- [ ] KITTI-360 fisheye→equirect stitcher (stretch, one sequence).

## Later (for publication, not preliminary)
- [ ] More scenes; seeds + variance study (drop the "preliminary" label).
- [ ] Proper occupancy/ESDF free-space sampler for synthetic trajectories.
- [ ] Loop-closure comparison once PRISM grows a working panoramic loop closure.

## Runner API status
- **PRISM** — verified public API. ✅
- **Pi3 / Pi3X** — verified against the pinned commit. Run **full-batch** (all frames one
  pass); it is permutation-equivariant, NOT a streamer. ✅
- **MapAnything** — verified (`MapAnything.from_pretrained("facebook/map-anything")`,
  `model.infer(views)`, outputs `pts3d`/`camera_poses`). Feed-forward metric, **full-batch**. ✅
- **VGGT-SLAM 2.0** — verified against the pinned commit. Drives the repo's `main.py`
  (`--log_results` → TUM keyed by true frame_id; `_points.pcd` → cloud). Streaming SLAM
  with SL(4) submaps + GTSAM + DINO-SALAD loop closure. ✅
- **LASER** — verified against the pinned commit. Training-free streamer wrapping Pi3
  (`StreamingWindowEngine`; `parse_inference_cache_summary` → extrinsic/intrinsic/depth →
  we unproject to a cloud). Pinhole. ✅
- **PanoVGGT (raw backbone)** — full-batch 360° reference; reuses the PRISM env, runs
  `PanoVGGTBackend.process_sequence` over all pano frames (no engine). ✅

## Method roster (current)
Streaming: **PRISM** (ours, pano), **VGGT-SLAM** (pinhole SLAM), **LASER** (pinhole).
Full-batch feed-forward: **PanoVGGT** (pano, raw backbone ref), **Pi3X**, **MapAnything**
(pinhole). PanoVGGT vs PRISM isolates the engine's contribution; PanoVGGT vs Pi3X/MapAnything
is pano-vs-pinhole at equal (batch) footing.

## Paper plan (agreed)
- **Phase 1 (now): PRISM ablations + fair RPE.** ✅ built:
  - `make ablations` runs PRISM with engine guards toggled via env (`config.ablations`):
    `prism_nolock` (free Sim(3) scale), `prism_nostill` (no still-guard), `prism_noguards`
    (all off). Shows what the drift-control guards contribute. They appear as their own
    methods in the report.
  - **Fair drift metric**: report now shows **Drift %/m** (relative pose error per metre of
    GT motion) instead of frame-delta RPE, so keyframe-sparse methods (VGGT-SLAM/LASER)
    aren't penalised for keyframe spacing.
  - **Memory-scaling figure**: `vram_vs_frames.png` (peak VRAM vs #frames per method) — the
    deployability plot (needs an isolated GPU run to be clean).
  - **Alignment-group study (DONE — required a PRISM-repo change).** `PRISM_ALIGN`
    now switches the submap registration group in the engine: `sim3` (default 7-DoF,
    = the plain `prism` run), `se3` (6-DoF rigid at the locked metric scale, via the
    existing `register_camera_poses_kabsch`), and `sl4` (15-DoF projective homography
    fit from the DENSE overlap point maps — VGGT-SLAM's group). nvblox is rigid, so
    SL(4) places poses through the exact homography and integrates at its local
    similarity; the discarded shear/perspective is logged per submap as the
    non-similarity distortion (`sl4_nonsimilarity_report`). Benchmark: `make ablations`
    (or `make ablations-align`) runs `prism_se3` + `prism_sl4`; the report adds an
    **Alignment-group study** table comparing all three on compute cost AND fidelity.
  - **Still TODO:** no-metric-grounding ablation (disable floor-RANSAC scale anchoring)
    — another small PRISM-repo toggle; and a guard-stressing / looping trajectory so
    the alignment differences (and the guards) actually get exercised.
- **Phase 2:** wire **StreamVGGT** then **CUT3R**; scale to ~6–10 Replica scenes with seeds
  for mean±std error bars (drops "preliminary").
- **Phase 3:** ScanNet++ + real Theta-X captures; a looping trajectory variant (fair loop
  closure for VGGT-SLAM/LASER); KITTI-360 (outdoor).

## Future streaming/SLAM baselines to add (from the SoTA)
Preferably online/streaming for a fair table (see each paper's own comparisons):
- **StreamVGGT** (Streaming 4D Visual Geometry Transformer) — causal VGGT; closest to our
  backbone family, isolates engine value best.
- **CUT3R** — online recurrent pointmap with persistent state.
- **Spann3R** — online incremental DUSt3R with spatial memory.
- **MASt3R-SLAM** — real-time SLAM (source of VGGT-SLAM's eval datasets); non-VGGT SLAM ref.

## Method modes
Streaming (incremental): PRISM (ours), LASER, VGGT-SLAM. Full-batch feed-forward: Pi3/Pi3X,
MapAnything. Windowing a feed-forward net misaligns it (overlapping submaps) — don't.

## First comparison
PRISM (pano) vs. Pi3 (pinhole) on Replica `office_4`. See **Preliminary results** for
PRISM's numbers; run `make run-pi3` then re-eval to populate the baseline row. Recon is
compared in the **masked** (co-visibility) table for fairness; PRISM additionally gets
the full-360 credit.
