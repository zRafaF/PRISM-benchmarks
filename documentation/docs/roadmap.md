# Roadmap

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
