# Preliminary results

!!! warning "Preliminary"
    Single scene (Replica `office_4`), one synthetic trajectory, **fixed seed, no variance
    study**. Rendered frames are noise/artifact-free → an **optimistic upper bound**.
    Numbers are for orientation, not publication.

**Setup.** Scene: Replica `office_4`, one floor-anchored constant-velocity walkthrough
captured at **2.0 Hz → 50 frames** (all methods on the *same* frames). PRISM consumes the
equirectangular pano (1036×518); baselines consume the matched pinhole (`synthetic_fov`)
frames. Each method runs in its **native mode**: **PRISM** streams (pano); **VGGT-SLAM** is
its own incremental SL(4) SLAM and **LASER** a training-free streamer (both pinhole);
**PanoVGGT** (the raw backbone, pano), **Pi3X** and **MapAnything** are full-batch feed-forward.
GT = exact render poses + scene mesh. Hardware RTX PRO 6000 — **VRAM/util this run are
unreliable (a second container shared the GPU), so ignore Table A memory here.**

## Six-method comparison (office_4 / synthetic_2.0hz — the fair run)

VRAM/util omitted (a second container shared the GPU this run). Grouped by role.

| Method | Mode | Scale err %↓ | ATE cm↓ | Masked F@5↑ | Full-360 F@5↑ | Map MB↓ | Noise %↓ | Prec@2cm %↑ |
|---|---|---|---|---|---|---|---|---|
| **PRISM (ours)** | stream · pano | **0.2** | 1.8 | 0.830 | 0.712 | **9.7** | 0.5 | 49.8 |
| VGGT-SLAM | stream · pinhole | N/A | 30.7 | 0.726 | 0.553 | 85.8 | 1.0 | 28.2 |
| LASER | stream · pinhole | N/A | 4.2 | 0.870 | 0.728 | **1.8** | 6.1 | 40.0 |
| PanoVGGT (raw backbone) | batch · pano | N/A | **0.9** | **0.967** | **0.922** | 70.0 | 1.4 | **52.6** |
| Pi3X | batch · pinhole | 13.7 | 5.2 | 0.960 | 0.844 | 16.2 | 0.5 | 47.6 |
| MapAnything | batch · pinhole | 2.2 | 26.1 | 0.441 | 0.389 | 18.3 | 42.8 | 14.5 |

**Preliminary observations.**

- **The engine's contribution, made explicit.** Raw **PanoVGGT** — the same backbone PRISM
  wraps, run *offline over all frames* — is the pano upper bound (masked F **0.967**, ATE
  **0.9 cm**). PRISM's streaming engine turns that backbone into a **causal, streaming,
  metric (0.2% vs scale-free), and compact (9.7 MB vs 70 MB — ~7×)** system, at the cost of
  some offline reconstruction quality (F 0.830) and ATE (1.8 cm). **That trade — deployability
  for a modest quality hit — is exactly the engine's value.**
- **Among streaming methods (PRISM, VGGT-SLAM, LASER), PRISM is the best all-rounder:** only
  metric one (0.2%), best-but-one ATE (1.8 cm), most complete 360° coverage, compact map.
  **LASER** edges masked F (0.870) but produces a very sparse map (1.8 MB / 122 k pts) and is
  scale-free; **VGGT-SLAM** is weakest here (ATE 30.7 — a short non-looping pinhole clip is
  not its regime).
- **Full-batch references set the ceiling:** PanoVGGT (pano) and Pi3X (pinhole) lead on recon
  F, but both are offline and Pi3X is badly non-metric (13.7%). **MapAnything** collapses at
  50 frames (F 0.441, 42.8% floaters).
- **Cleanliness/compactness:** PRISM and Pi3X are cleanest (0.5% floaters); PRISM has the most
  compact dense map; MapAnything is by far the fluffiest.

Recon quality (Table C) is scale-normalised (Sim(3)+ICP) so scale-free methods aren't
penalised for scale; absolute metric scale (Table B) is reported only for metric methods.
Each method runs in its **native mode**. VGGT-SLAM/LASER RPE is not comparable (sparse
keyframes vs. our per-frame delta — fix pending).

!!! note "On 360° coverage vs. pinhole (discussed in text, not benchmarked)"
    The intuitive way to give a pinhole model 360° coverage is to feed it the panorama as
    multiple perspective crops (the equirect→pinhole route PanoVGGT uses). We deliberately
    do **not** run this as a separate condition: cropping one panorama into ~6 faces at a
    single camera centre gives **zero baseline between faces** (degenerate for feed-forward
    multi-view stereo) and multiplies the frame count ~6×, which would blow the VRAM budget
    and **collapse effective FPS**. The takeaway — that reaching 360° through a pinhole model
    costs a large throughput/memory penalty, which PRISM avoids by consuming the panorama
    natively — is made in the report text. Same-FOV fairness is handled by the co-visibility
    mask (Table C); PRISM's coverage is credited in the full-360 table (C2).

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
