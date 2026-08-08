# PRISM-benchmarks — clean seeded-only results

*Source: `archive:bigrun_2026-07`. 434 input run-records → 368 seeded (66 excluded) → **325 complete runs aggregated** (43 produced no evaluable output).*

Scenes: apartment_0, apartment_1, frl_apartment_0, hotel_0 · Seeds: s0, s1 · Trajectories: 10 ids

## Exclusions applied

- unseeded traj id — stale 2-scene experiment (co-tenancy-inflated VRAM 70-100 GB)

> **Incomplete runs are excluded from every aggregate, including perf.** `eff_fps` is computed from the *input* frame count, so a run that died early reports a spuriously high fps; averaging those in inflates throughput. See the completion table for the failure breakdown.

## Completion / failure rate

| Method | N total | N complete | N incomplete | Incomplete % | By scene | By motion |
| --- | --- | --- | --- | --- | --- | --- |
| laser | 40 | 40 | 0 | 0.0 | — | — |
| mapanything | 40 | 40 | 0 | 0.0 | — | — |
| panovggt | 40 | 40 | 0 | 0.0 | — | — |
| pi3 | 40 | 40 | 0 | 0.0 | — | — |
| prism | 40 | 31 | 9 | 22.5 | apartment_1:4, hotel_0:5 | loop:2, smooth:4, stop-and-go:3 |
| prism_noguards | 16 | 11 | 5 | 31.2 | apartment_1:2, hotel_0:3 | loop:2, stop-and-go:3 |
| prism_nolock | 16 | 11 | 5 | 31.2 | apartment_1:2, hotel_0:3 | loop:2, stop-and-go:3 |
| prism_nostill | 16 | 11 | 5 | 31.2 | apartment_1:2, hotel_0:3 | loop:2, stop-and-go:3 |
| prism_se3 | 40 | 31 | 9 | 22.5 | apartment_1:4, hotel_0:5 | loop:2, smooth:4, stop-and-go:3 |
| prism_sim3 | 40 | 30 | 10 | 25.0 | apartment_0:1, apartment_1:4, hotel_0:5 | loop:2, smooth:5, stop-and-go:3 |
| vggtslam | 40 | 40 | 0 | 0.0 | — | — |


## Per-method aggregate (clean, seeded, complete runs only)

| Method | N | ATE cm↓ | drift %/m↓ | Masked F↑ | Full-360 F↑ | Map MB↓ | Outlier %↓ | Prec@2cm %↑ | Scale err %↓ | VRAM peak GB↓ | per-win lat s↓ | Eff.FPS↑ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laser | 40 | 86.8 | 56.7 | 0.348 | 0.221 | 6.1 | 3.35 | 9.7 | N/A | 8.43 | — | 4.83 |
| mapanything | 40 | 95.7 | 95.4 | 0.256 | 0.177 | 28.9 | 3.51 | 7.4 | 22.0 | 44.93 | 9.20 | 2.85 |
| panovggt | 40 | 66.6 | 49.0 | 0.580 | 0.453 | 103.0 | 3.93 | 16.9 | N/A | 24.94 | 17.44 | 2.35 |
| pi3 | 40 | 62.5 | 61.3 | 0.494 | 0.348 | 23.4 | 2.73 | 14.4 | 8.7 | 36.25 | 5.17 | 4.72 |
| prism | 31 | 65.3 | 52.2 | 0.417 | 0.309 | 22.1 | 2.44 | 16.3 | 14.6 | 15.95 | 1.60 | 2.88 |
| prism_noguards | 11 | 81.2 | 58.8 | 0.336 | 0.256 | 29.6 | 2.53 | 11.1 | 23.0 | 16.93 | 1.51 | 3.33 |
| prism_nolock | 11 | 83.9 | 63.7 | 0.334 | 0.255 | 28.6 | 2.56 | 11.3 | 22.6 | 16.41 | 1.51 | 3.37 |
| prism_nostill | 11 | 83.9 | 63.6 | 0.335 | 0.255 | 28.7 | 2.58 | 11.3 | 22.6 | 16.79 | 1.51 | 3.38 |
| prism_se3 | 31 | 67.1 | 48.6 | 0.393 | 0.279 | 21.0 | 2.46 | 15.1 | 13.4 | 16.01 | 1.52 | 2.93 |
| prism_sim3 | 30 | 68.9 | 49.1 | 0.396 | 0.283 | 20.9 | 2.48 | 15.5 | 14.0 | 15.89 | 1.53 | 2.84 |
| vggtslam | 40 | 131.9 | 159.4 | 0.221 | 0.156 | 102.2 | 3.71 | 8.9 | N/A | 8.90 | — | 4.61 |


## Streaming comparison (native streaming mode; throughput included)

| Method | N | ATE cm↓ | Masked F↑ | 360 F↑ | Outlier %↓ | Map MB↓ | VRAM GB↓ | per-win s↓ | Eff.FPS↑ | Scale %↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prism | 31 | 65.3 | 0.417 | 0.309 | 2.44 | 22.1 | 15.95 | 1.60 | 2.88 | 14.6 |
| prism_sim3 | 30 | 68.9 | 0.396 | 0.283 | 2.48 | 20.9 | 15.89 | 1.53 | 2.84 | 14.0 |
| prism_se3 | 31 | 67.1 | 0.393 | 0.279 | 2.46 | 21.0 | 16.01 | 1.52 | 2.93 | 13.4 |
| laser | 40 | 86.8 | 0.348 | 0.221 | 3.35 | 6.1 | 8.43 | — | 4.83 | N/A |
| vggtslam | 40 | 131.9 | 0.221 | 0.156 | 3.71 | 102.2 | 8.90 | — | 4.61 | N/A |


## Full-batch offline upper bound (ingest all views at once)

| Method | N | ATE cm↓ | Masked F↑ | 360 F↑ | Outlier %↓ | Map MB↓ | VRAM GB↓ | per-win s↓ | Eff.FPS↑ | Scale %↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| panovggt | 40 | 66.6 | 0.580 | 0.453 | 3.93 | 103.0 | 24.94 | 17.44 | 2.35 | N/A |
| pi3 | 40 | 62.5 | 0.494 | 0.348 | 2.73 | 23.4 | 36.25 | 5.17 | 4.72 | 8.7 |
| mapanything | 40 | 95.7 | 0.256 | 0.177 | 3.51 | 28.9 | 44.93 | 9.20 | 2.85 | 22.0 |


## Alignment-group study — Sim(3) vs SL(4) vs SE(3)

*Same backbone / fusion / trajectory; only the submap registration group varies.*

| Group (arm) | DoF | N | Eff.FPS↑ | per-win s↓ | VRAM GB↓ | Scale err %↓ | ATE cm↓ | Drift %/m↓ | Masked F↑ | Outlier %↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sim(3) (prism_sim3) | 7 | 30 | 2.84 | 1.53 | 15.89 | 14.0 | 68.9 | 49.1 | 0.396 | 2.48 |
| SL(4) (prism) | 15 | 31 | 2.88 | 1.60 | 15.95 | 14.6 | 65.3 | 52.2 | 0.417 | 2.44 |
| SE(3) (prism_se3) | 6 | 31 | 2.93 | 1.52 | 16.01 | 13.4 | 67.1 | 48.6 | 0.393 | 2.46 |


## Alignment group stratified by motion (2 Hz)

| Trajectory (2 Hz) | Sim(3) ATE / F / scale% | SL(4) ATE / F / scale% | SE(3) ATE / F / scale% |
| --- | --- | --- | --- |
| smooth | 46.2 / 0.41 / 10.0 (N=7) | 44.0 / 0.46 / 10.3 (N=7) | 46.6 / 0.41 / 10.1 (N=7) |
| stop-and-go | 72.3 / 0.38 / 16.0 (N=5) | 51.9 / 0.43 / 12.1 (N=5) | 67.4 / 0.37 / 15.0 (N=5) |
| loop | 101.9 / 0.34 / 20.3 (N=6) | 110.5 / 0.26 / 31.4 (N=6) | 101.2 / 0.33 / 20.1 (N=6) |


## ATE by motion family, all methods (2 Hz)

| Method | ATE cm — smooth | ATE cm — stop-and-go | ATE cm — loop |
| --- | --- | --- | --- |
| laser | 88.8 | 87.5 | 118.6 |
| mapanything | 97.5 | 92.7 | 103.1 |
| panovggt | 72.3 | 56.0 | 76.1 |
| pi3 | 62.4 | 57.5 | 62.5 |
| prism | 44.0 | 51.9 | 110.5 |
| prism_noguards | — | 49.1 | 108.0 |
| prism_nolock | — | 52.0 | 110.5 |
| prism_nostill | — | 51.9 | 110.5 |
| prism_se3 | 46.6 | 67.4 | 101.2 |
| prism_sim3 | 46.2 | 72.3 | 101.9 |
| vggtslam | 136.4 | 144.7 | 132.5 |


## Headline metrics with error bars

*Pooled mean ± **within-cell seed std** — the replicate cell is (scene, trajectory family, rate) and the 2 seeds inside it are the repeats, so the ± isolates seed noise rather than scene/motion heterogeneity (the central value is identical to the aggregate table above). With only 2 seeds per cell each variance estimate has 1 d.o.f.; pooling across cells is what makes it usable, but this is still indicative dispersion, not a converged interval — add seeds to tighten it. Between-cell heterogeneity is reported separately in `variance.csv`.*

| Method | Paired cells | ATE cm | Masked F | VRAM peak GB | Eff.FPS |
| --- | --- | --- | --- | --- | --- |
| laser | 20 | 86.8 ± 46.5 | 0.348 ± 0.136 | 8.4 ± 0.1 | 4.8 ± 0.5 |
| mapanything | 20 | 95.7 ± 30.0 | 0.256 ± 0.059 | 44.9 ± 5.4 | 2.8 ± 0.3 |
| panovggt | 20 | 66.6 ± 32.9 | 0.580 ± 0.183 | 24.9 ± 3.3 | 2.4 ± 0.2 |
| pi3 | 20 | 62.5 ± 15.6 | 0.494 ± 0.147 | 36.2 ± 8.4 | 4.7 ± 0.3 |
| prism | 13 | 65.3 ± 35.5 | 0.417 ± 0.219 | 15.9 ± 0.9 | 2.9 ± 0.2 |
| prism_noguards | 4 | 81.2 ± 55.9 | 0.336 ± 0.166 | 16.9 ± 0.9 | 3.3 ± 0.2 |
| prism_nolock | 4 | 83.9 ± 55.3 | 0.334 ± 0.166 | 16.4 ± 0.9 | 3.4 ± 0.2 |
| prism_nostill | 4 | 83.9 ± 55.3 | 0.335 ± 0.167 | 16.8 ± 1.0 | 3.4 ± 0.2 |
| prism_se3 | 13 | 67.1 ± 38.7 | 0.393 ± 0.223 | 16.0 ± 1.6 | 2.9 ± 0.2 |
| prism_sim3 | 12 | 68.9 ± 41.5 | 0.396 ± 0.230 | 15.9 ± 1.2 | 2.8 ± 0.2 |
| vggtslam | 20 | 131.9 ± 58.8 | 0.221 ± 0.208 | 8.9 ± 0.2 | 4.6 ± 0.8 |


## Paired head-to-head vs `prism_sim3`

*Every method saw the same rendered trajectories, so runs are matched on (scene, traj) and differenced run-by-run — cancelling the scene/motion spread that dominates the marginal means. `mean_delta` is reference − comparator (so **negative is better for the reference** on ↓ metrics). `ci_excludes_zero` and the exact sign test are the two independent separability checks; the sign test assumes no distribution, which matters because ATE is heavy-tailed.*

| reference | comparator | metric | n_matched | mean_delta_ref_minus_cmp | ci95_halfwidth | ref_wins | sign_test_p | ci_excludes_zero |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prism_sim3 | laser | ate_cm | 30 | -10.850 | 14.298 | 20/30 | 0.0987 | no |
| prism_sim3 | laser | masked_f | 30 | -0.008 | 0.063 | 10/30 | 0.0987 | no |
| prism_sim3 | laser | map_mb | 30 | 14.510 | 2.519 | 0/30 | 0.0000 | yes |
| prism_sim3 | laser | outlier_pct | 30 | -0.950 | 0.161 | 28/28 | 0.0000 | yes |
| prism_sim3 | laser | eff_fps | 30 | -1.787 | 0.311 | 0/30 | 0.0000 | yes |
| prism_sim3 | laser | vram_peak_gb | 30 | 7.468 | 0.867 | 0/30 | 0.0000 | yes |
| prism_sim3 | mapanything | ate_cm | 30 | -21.697 | 13.552 | 23/30 | 0.0052 | yes |
| prism_sim3 | mapanything | masked_f | 30 | 0.143 | 0.083 | 22/30 | 0.0161 | yes |
| prism_sim3 | mapanything | map_mb | 30 | -10.617 | 5.358 | 21/29 | 0.0241 | yes |
| prism_sim3 | mapanything | outlier_pct | 30 | -1.380 | 0.245 | 29/30 | 0.0000 | yes |
| prism_sim3 | mapanything | eff_fps | 30 | 0.120 | 0.107 | 21/30 | 0.0428 | yes |
| prism_sim3 | mapanything | vram_peak_gb | 30 | -27.271 | 7.655 | 23/30 | 0.0052 | yes |
| prism_sim3 | panovggt | ate_cm | 30 | 6.243 | 11.346 | 9/26 | 0.1686 | no |
| prism_sim3 | panovggt | masked_f | 30 | -0.204 | 0.069 | 4/30 | 0.0001 | yes |
| prism_sim3 | panovggt | map_mb | 30 | -82.337 | 13.735 | 30/30 | 0.0000 | yes |
| prism_sim3 | panovggt | outlier_pct | 30 | -1.360 | 0.318 | 29/29 | 0.0000 | yes |
| prism_sim3 | panovggt | eff_fps | 30 | 0.575 | 0.308 | 22/30 | 0.0161 | yes |
| prism_sim3 | panovggt | vram_peak_gb | 30 | -8.425 | 3.675 | 22/30 | 0.0161 | yes |
| prism_sim3 | pi3 | ate_cm | 30 | 17.020 | 13.353 | 11/30 | 0.2005 | yes |
| prism_sim3 | pi3 | masked_f | 30 | -0.134 | 0.087 | 9/30 | 0.0428 | yes |
| prism_sim3 | pi3 | map_mb | 30 | -5.213 | 4.299 | 17/30 | 0.5847 | yes |
| prism_sim3 | pi3 | outlier_pct | 30 | -0.390 | 0.206 | 20/25 | 0.0041 | yes |
| prism_sim3 | pi3 | eff_fps | 30 | -1.674 | 0.243 | 0/30 | 0.0000 | yes |
| prism_sim3 | pi3 | vram_peak_gb | 30 | -18.767 | 6.055 | 27/30 | 0.0000 | yes |
| prism_sim3 | prism | ate_cm | 30 | 2.727 | 8.894 | 8/22 | 0.2863 | no |
| prism_sim3 | prism | masked_f | 30 | -0.014 | 0.059 | 15/28 | 0.8506 | no |
| prism_sim3 | prism | map_mb | 30 | -1.303 | 2.827 | 12/25 | 1.0000 | no |
| prism_sim3 | prism | outlier_pct | 30 | 0.050 | 0.103 | 11/26 | 0.5572 | no |
| prism_sim3 | prism | eff_fps | 30 | 0.039 | 0.107 | 18/30 | 0.3616 | no |
| prism_sim3 | prism | vram_peak_gb | 30 | -0.139 | 1.274 | 8/19 | 0.6476 | no |
| prism_sim3 | prism_noguards | ate_cm | 11 | 7.182 | 25.417 | 3/11 | 0.2266 | no |
| prism_sim3 | prism_noguards | masked_f | 11 | 0.021 | 0.120 | 5/11 | 1.0000 | no |
| prism_sim3 | prism_noguards | map_mb | 11 | -5.264 | 8.599 | 5/10 | 1.0000 | no |
| prism_sim3 | prism_noguards | outlier_pct | 11 | 0.000 | 0.183 | 4/10 | 0.7539 | no |
| prism_sim3 | prism_noguards | eff_fps | 11 | 0.173 | 0.250 | 6/11 | 1.0000 | no |
| prism_sim3 | prism_noguards | vram_peak_gb | 11 | -1.815 | 4.236 | 4/9 | 1.0000 | no |
| prism_sim3 | prism_nolock | ate_cm | 11 | 4.545 | 24.564 | 3/11 | 0.2266 | no |
| prism_sim3 | prism_nolock | masked_f | 11 | 0.023 | 0.118 | 5/11 | 1.0000 | no |
| prism_sim3 | prism_nolock | map_mb | 11 | -4.327 | 6.273 | 6/11 | 1.0000 | no |
| prism_sim3 | prism_nolock | outlier_pct | 11 | -0.036 | 0.195 | 4/8 | 1.0000 | no |
| prism_sim3 | prism_nolock | eff_fps | 11 | 0.130 | 0.189 | 6/11 | 1.0000 | no |
| prism_sim3 | prism_nolock | vram_peak_gb | 11 | -1.300 | 3.137 | 4/10 | 0.7539 | no |
| prism_sim3 | prism_nostill | ate_cm | 11 | 4.564 | 24.568 | 3/11 | 0.2266 | no |
| prism_sim3 | prism_nostill | masked_f | 11 | 0.023 | 0.120 | 5/11 | 1.0000 | no |
| prism_sim3 | prism_nostill | map_mb | 11 | -4.409 | 6.236 | 7/11 | 0.5488 | no |
| prism_sim3 | prism_nostill | outlier_pct | 11 | -0.055 | 0.197 | 4/9 | 1.0000 | no |
| prism_sim3 | prism_nostill | eff_fps | 11 | 0.121 | 0.195 | 5/11 | 1.0000 | no |
| prism_sim3 | prism_nostill | vram_peak_gb | 11 | -1.685 | 3.109 | 5/10 | 1.0000 | no |
| prism_sim3 | prism_se3 | ate_cm | 30 | 0.867 | 1.400 | 6/12 | 1.0000 | no |
| prism_sim3 | prism_se3 | masked_f | 30 | 0.004 | 0.010 | 14/23 | 0.4049 | no |
| prism_sim3 | prism_se3 | map_mb | 30 | 0.017 | 0.563 | 7/17 | 0.6291 | no |
| prism_sim3 | prism_se3 | outlier_pct | 30 | 0.023 | 0.057 | 10/20 | 1.0000 | no |
| prism_sim3 | prism_se3 | eff_fps | 30 | -0.014 | 0.031 | 13/30 | 0.5847 | no |
| prism_sim3 | prism_se3 | vram_peak_gb | 30 | -0.098 | 0.210 | 5/15 | 0.3018 | no |
| prism_sim3 | vggtslam | ate_cm | 30 | -59.500 | 19.007 | 29/30 | 0.0000 | yes |
| prism_sim3 | vggtslam | masked_f | 30 | 0.128 | 0.056 | 25/30 | 0.0003 | yes |
| prism_sim3 | vggtslam | map_mb | 30 | -76.660 | 13.674 | 30/30 | 0.0000 | yes |
| prism_sim3 | vggtslam | outlier_pct | 30 | -1.167 | 0.210 | 30/30 | 0.0000 | yes |
| prism_sim3 | vggtslam | eff_fps | 30 | -1.594 | 0.636 | 1/30 | 0.0000 | yes |
| prism_sim3 | vggtslam | vram_peak_gb | 30 | 7.026 | 0.889 | 0/30 | 0.0000 | yes |


## Standing caveats

- Rendered frames are noise-free → an **optimistic upper bound** vs real Theta-X captures.
- Metric scale degrades on loops (Sim(3) ~20%, SL(4) ~31%).
- Shipped PRISM has **no loop closure**; the full-batch nets implicitly close loops.
- All seeded scenes are large/hard unless a small room has been added to the matrix — check the scene list above.
