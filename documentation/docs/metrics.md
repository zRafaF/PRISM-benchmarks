# Metrics & fairness

Every metric is computed in the orchestrator env from the common results layout; no
method is imported.

## Cloud cleanliness & size (Table D)
Complements F-score, which rewards coverage but ignores stray floaters:

- **Point count** and **map size (MB)** — compactness / deployment cost.
- **Noise fraction** — % of predicted points farther than `cleanliness.noise_threshold_m`
  (10 cm) from any GT surface. Directly measures the "fluffy dots"; PRISM's edge-masked
  TSDF surface scores low, per-pixel feed-forward pointmaps higher.
- **Precision@2cm** — % of predicted points within 2 cm of GT (sharpness).

## Temporal sampling — capture-rate sweep
Frames are sampled at **constant velocity** (`speed_mps`) along the path at spacing
`speed / rate`, so each trajectory simulates a real capture at `rate` Hz. We render one
trajectory per rate in `trajectories.rates_hz` (`synthetic_<rate>hz`) to sweep 0.5–2.5 Hz.
All methods consume the same frames (fair); frame count is capped at `n_frames`. Low rate =
sparse wide-baseline; high rate = dense overlap and higher full-batch memory.

## Trajectory (`eval_traj.py`)
ATE (RMSE) + RPE with **Sim(3) Umeyama alignment** (`--correct_scale`), via `evo`.
Method `poses.tum` vs. shared GT `poses_gt.tum`. Report ATE on bounded-length
sequences (no loop closure in PRISM's shipped pipeline → drift on long loops is
future work).

## Reconstruction (`eval_recon.py`)
Accuracy (pred→GT), completeness (GT→pred), Chamfer, F-score@5cm via Open3D, in two
variants:

- **masked** — both pred and GT restricted to the co-visibility support (fair vs. pinhole).
- **full_360** — no mask; credits pano coverage (pano-capable methods).

**Registration first (critical).** A method's cloud is in its OWN world frame, so it
must be aligned to GT before any distance is meaningful. `eval_recon`:

1. computes a **Sim(3)** (scale, rotation, translation) from the method's trajectory to
   GT (Umeyama over matched poses) and applies it to the cloud, then
2. **refines with ICP** (point-to-point, `eval.icp`) to remove residual misalignment.

Because the Sim(3) is **scale-corrected**, recon quality is **scale-normalised** — a
scale-free method (Pi3, VGGT-SLAM, LASER) is judged purely on geometry, not on whether
it recovered absolute size. This is the fair cross-method quality comparison. F-score@τ
is the SOTA headline metric (as in Tanks & Temples / ScanNet).

## Performance & resources (`bench/perf.py` → `collect_perf.py`)
Uniform across every method (the sampler wraps each subprocess):
effective FPS, per-window + end-to-end latency, **average & peak VRAM**, GPU util %,
GPU power, CPU RAM peak, checkpoint size, and (ours) TSDF block count. For PRISM the
runner also surfaces the engine's `VRAMProfiler` numbers via `perf_runner.json`.

## Absolute metric-scale accuracy (`metric_accuracy.py`)
Separate from quality: does the method reconstruct at TRUE real-world size? Using the
rendered GT (exact scale), recover the similarity scale `s` aligning the method's
trajectory to GT: a metric method gives s≈1, reported as **metric-scale error |s−1|**
plus room-extent (bbox-diagonal) error. Reported only for **metric-capable** methods
(PRISM via floor+camera-height; MapAnything). Scale-free methods (Pi3, VGGT-SLAM,
LASER) are **N/A** — they recover geometry only up to scale, so absolute size is
undefined and must not be scored against them.

**Floor anchor (PRISM).** PRISM's scale comes from a RANSAC floor fit under the camera
against a known camera height. The renderer therefore (a) only places trajectory
waypoints **over bare floor** (a downward ray must hit the floor, not furniture) and
(b) measures the true camera-to-floor height by that downward ray and feeds it to
PRISM (`measured_camera_height.json`). Starting over a sofa was the cause of an early
~27% scale error.

## Fairness — co-visibility masking (`visibility_mask.py`)
Pano sees 360°, pinhole baselines see a frustum. Build the **union of bounded pinhole
view frustums** (far = `max_depth`) over the trajectory and keep only points inside it;
apply the identical mask to our recon, each baseline's recon, and the GT.

- `containment` — point-in-frustum-union.
- `rigorous` — + per-frame GT-depth occlusion test (observed only if it projects into a
  frame **and** range ≤ GT depth + tol). Preferred; we have GT depth.

The full-360 no-mask table is kept separately so the report is transparent about what
each number measures.
