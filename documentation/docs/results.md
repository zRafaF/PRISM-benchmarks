# Preliminary results

!!! warning "Preliminary"
    Single scene (Replica `office_4`), one synthetic trajectory, 200 pano frames,
    fixed seed, **no variance study**. Rendered frames are noise/artifact-free → an
    **optimistic upper bound**. Numbers are for orientation, not publication.

**Setup.** Method: PRISM-VGGT (ours). Input: equirectangular pano (1036×518) rendered
from the Replica `office_4` mesh along a floor-anchored, nearest-neighbour synthetic
walkthrough. GT: exact render poses + scene mesh. Hardware: **RTX PRO 6000 (95 GB)**.
Engine: `window=16, overlap=4, voxel=0.02 m, max_depth=4.5 m, face_size=768, parallel`.

## The numbers (PRISM-VGGT, office_4 / synthetic_spline)

| Family | Metric | Value |
|---|---|---|
| Performance | Effective FPS | **5.38** |
| | End-to-end latency | 23.8 s (200 frames) |
| | VRAM avg / peak | 8.0 / 13.9 GB (of 95 GB) |
| | GPU util / power | 52% / 318 W |
| | Checkpoint | 3.94 GB |
| Metric scale | Scale estimate (1.0 = perfect) | **0.977** |
| | Scale error | **2.3%** |
| | Room-extent error | 7.9% |
| Trajectory | ATE RMSE | **5.7 cm** |
| | RPE RMSE (per frame) | 0.4 cm |
| Reconstruction (masked) | Accuracy / Completeness | 3.7 / 14.1 cm |
| | Chamfer / F-score@5cm | 17.8 cm / **0.617** |
| Reconstruction (full-360) | Accuracy / Completeness | 7.7 / 5.9 cm |
| | Chamfer / F-score@5cm | 13.6 cm / 0.517 |

**One-line read.** PRISM runs at streaming rate on a fraction of the GPU, recovers
real-world scale to ~2%, tracks with sub-centimetre per-step error and ~6 cm global
drift, and reconstructs the room to a few centimetres of accuracy.

## What each metric means (in depth)

### Performance & resources
- **Effective FPS** — frames processed per second end-to-end (perception + alignment +
  TSDF fusion + coloring), not just network inference. `n_frames / wall_time`. Higher is
  better; 5.4 FPS supports the "real-time on commodity GPU" claim.
- **End-to-end latency** — wall time to process the whole sequence. (Per-window latency
  is also captured for streaming responsiveness.)
- **VRAM avg / peak** — GPU memory sampled continuously during the run by the
  orchestrator (`pynvml`), so it is comparable across methods, not self-reported. Peak
  is the worst-case footprint; avg reflects steady state. Reported against the card's
  total so it's unambiguous.
- **GPU util / power** — how hard the card works. Low util (52%) means headroom.
- **Checkpoint size** — model footprint on disk (deployment cost).

### Metric scale (absolute size) — our differentiator
Most baselines are **scale-free** (monocular): they recover geometry only up to an
unknown similarity scale, so their absolute size is undefined. PRISM grounds scale from
a **RANSAC floor fit under the camera** against the known camera height, so it should
reconstruct at true metric size.
- **Scale estimate** — the similarity scale `s` that best maps PRISM's trajectory onto
  GT. A perfectly metric map gives **s = 1.0**; 0.977 means the map is 2.3% too small.
- **Scale error = |s − 1|** — the headline metric-accuracy number. 2.3% is strong for
  vision-only metric grounding (the known accuracy limit vs. LiDAR).
- **Extent error** — difference in reconstructed room size (bounding-box diagonal) vs.
  GT. A coarser, outlier-sensitive cross-check on scale.

Reported **only for metric-capable methods** (PRISM, MapAnything). Scale-free methods
(Pi3, VGGT-SLAM, LASER) are **N/A** here — scoring absolute size against them is unfair.

### Trajectory / localization (needs GT poses)
Both computed after a **Sim(3) Umeyama alignment** of the estimated path to GT
(monocular convention), via `evo`.
- **ATE (Absolute Trajectory Error), RMSE** — global position error over the whole path.
  The headline localization number. 5.7 cm over a 6.5 m room.
- **RPE (Relative Pose Error), RMSE** — frame-to-frame error. Small RPE with a larger
  ATE is the signature of **slow drift**: each step is accurate, errors accumulate. PRISM
  ships **without loop closure**, so bounded-length ATE is the fair thing to report and
  long-loop drift is named as future work.

### Reconstruction quality (needs GT geometry)
The predicted cloud is first **registered to GT** — a scale-corrected **Sim(3)** from the
trajectory, then **ICP** refinement — because the cloud is produced in the method's own
frame. Because scale is corrected in this step, recon quality is **scale-normalised**, so
scale-free methods compete fairly on geometry alone. Then, via Open3D:
- **Accuracy** — mean distance from each predicted point to the nearest GT surface. "Did
  we hallucinate geometry?" Lower is better.
- **Completeness** — mean distance from each GT point to the nearest predicted point.
  "Did we miss parts of the room?" Lower is better.
- **Chamfer** — accuracy + completeness combined.
- **F-score@5cm** — harmonic mean of precision (pred within 5 cm of GT) and recall (GT
  within 5 cm of pred). The single **headline quality** number (as in Tanks & Temples /
  ScanNet). Higher is better; 0.617 masked is a solid preliminary reconstruction.

**Masked vs. full-360.**
- **Masked** restricts both clouds to the **co-visibility volume** (union of the pinhole
  baselines' view frustums) — the fair comparison when pano is measured against pinhole
  methods.
- **Full-360** uses the whole room with no mask — this legitimately **credits PRISM's
  360° coverage** and is fair among panorama-capable methods.

## Caveats to carry into the report
- Rendered = clean; pair with real-sensor behaviour before over-claiming.
- One scene, one trajectory, one seed — no variance/error bars yet.
- No loop closure → report ATE on bounded sequences; long-loop drift is future work.
- Metric scale is vision-only (floor + camera height) — mitigated, not eliminated.
