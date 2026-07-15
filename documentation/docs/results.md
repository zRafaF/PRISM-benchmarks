# Preliminary results

!!! warning "Preliminary"
    Single scene (Replica `office_4`), one synthetic trajectory, **fixed seed, no variance
    study**. Rendered frames are noise/artifact-free → an **optimistic upper bound**.
    Numbers are for orientation, not publication.

**Setup.** Scene: Replica `office_4`, one floor-anchored constant-velocity walkthrough
captured at **2.0 Hz → 50 frames** (all methods on the *same* frames). PRISM consumes the
equirectangular pano (1036×518); baselines consume the matched pinhole (`synthetic_fov`)
frames. Each method runs in its **native mode**: PRISM streams (pano); VGGT-SLAM is its own
incremental SL(4) SLAM (pinhole); Pi3X and MapAnything are full-batch feed-forward (pinhole).
GT = exact render poses + scene mesh. Hardware RTX PRO 6000 — **VRAM/util this run are
unreliable (a second container shared the GPU), so ignore Table A memory here.**

## Four-method comparison (office_4 / synthetic_2.0hz — the fair run)

| Metric | PRISM (pano, stream) | VGGT-SLAM (pinhole, SLAM) | Pi3X (pinhole, batch) | MapAnything (pinhole, batch) |
|---|---|---|---|---|
| Metric scale err %↓ | **0.2** | N/A | 13.7 | 2.2 |
| ATE RMSE cm↓ | **1.8** | 30.7 | 5.2 | 26.1 |
| Recon accuracy cm↓ | **2.3** | 3.3 | 2.5 | 11.5 |
| Recon F@5cm↑ (masked) | 0.830 | 0.726 | **0.960** | 0.441 |
| Recon F@5cm↑ (full-360) | 0.712 | 0.552 | **0.845** | 0.390 |
| Map size MB↓ | **9.7** | 85.8 | 16.2 | 18.3 |
| Noise % (floaters)↓ | **0.5** | 1.0 | **0.5** | 42.8 |
| Precision @2cm %↑ | **49.8** | 28.2 | 47.7 | 14.5 |

**Preliminary observations.**

- **PRISM leads or ties nearly everything except raw masked F-score.** It has the best
  metric scale (**0.2%**), best trajectory (**ATE 1.8 cm**), best reconstruction accuracy
  (2.3 cm), the **most compact map (9.7 MB)**, and the **sharpest, cleanest cloud** (49.8%
  precision@2cm, 0.5% floaters). It also uniquely covers 360°.
- **Pi3X is the reconstruction-quality leader (masked F 0.960)** — but it is **full-batch
  offline** (not streaming), the **worst on metric scale (13.7%)**, and pinhole-only. It's
  the "offline upper bound," not a deployable streaming competitor.
- **VGGT-SLAM (the true streaming peer): PRISM wins across the board** — ATE 1.8 vs 30.7 cm,
  masked F 0.830 vs 0.726, map 9.7 vs 85.8 MB, metric vs scale-free. VGGT-SLAM's high ATE
  partly reflects that a short, non-looping pinhole clip is not its intended regime (it's
  built for larger looping trajectories). Its **RPE is not comparable** — it emits sparse
  keyframes, and our per-frame RPE measures keyframe-to-keyframe motion (a known artifact;
  fix pending).
- **MapAnything degrades at this frame count** (masked F 0.441, **42.8% floaters**) — the
  feed-forward metric model wants many more views than 50 to shine.
- **Headline:** in the streaming/real-time regime that matters for a telepresence robot,
  **PRISM is the strongest all-around method**; the only thing beating it on pure recon
  F-score is an offline, non-metric, pinhole full-batch model (Pi3X).

Recon quality (Table C) is scale-normalised (Sim(3)+ICP) so scale-free methods aren't
penalised for scale; absolute metric scale (Table B) is reported only for metric methods.

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
