# Metrics & fairness

Every metric is computed in the orchestrator env from the common results layout; no
method is imported.

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

## Performance & resources (`bench/perf.py` → `collect_perf.py`)
Uniform across every method (the sampler wraps each subprocess):
effective FPS, per-window + end-to-end latency, **average & peak VRAM**, GPU util %,
GPU power, CPU RAM peak, checkpoint size, and (ours) TSDF block count. For PRISM the
runner also surfaces the engine's `VRAMProfiler` numbers via `perf_runner.json`.

## Absolute metric-scale accuracy (`metric_accuracy.py`)
Our differentiator. Using the rendered GT (exact scale), recover the similarity scale
`s` that aligns each method's trajectory to GT: metric-capable PRISM should give s≈1,
reported as **metric-scale error |s−1|** plus room-extent (bbox-diagonal) error.
Scale-free baselines (Pi3, VGGT-SLAM, MapAnything, LASER) are reported **N/A** — they
recover geometry only up to scale.

## Fairness — co-visibility masking (`visibility_mask.py`)
Pano sees 360°, pinhole baselines see a frustum. Build the **union of bounded pinhole
view frustums** (far = `max_depth`) over the trajectory and keep only points inside it;
apply the identical mask to our recon, each baseline's recon, and the GT.

- `containment` — point-in-frustum-union.
- `rigorous` — + per-frame GT-depth occlusion test (observed only if it projects into a
  frame **and** range ≤ GT depth + tol). Preferred; we have GT depth.

The full-360 no-mask table is kept separately so the report is transparent about what
each number measures.
