# PRISM-benchmarks — global report (2 scene(s))

## Global aggregate — mean per method (over all scenes × rates × variants)
*N = runs averaged. Scale err averaged over metric-capable runs only.*

| Method | N | Eff.FPS↑ | Scale err %↓ | ATE cm↓ | Masked F↑ | Full-360 F↑ | Map MB↓ | Noise %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laser | 2 | 4.68 | N/A | 13.4 | 0.756 | 0.543 | 3.3 | 15.2 | 26.2 |
| mapanything | 2 | 2.72 | 6.6 | 55.5 | 0.419 | 0.304 | 30.3 | 43.6 | 10.4 |
| panovggt | 2 | 2.64 | N/A | 23.8 | 0.793 | 0.681 | 91.0 | 12.8 | 31.1 |
| pi3 | 2 | 4.77 | 9.8 | 7.4 | 0.889 | 0.653 | 22.6 | 3.3 | 32.1 |
| prism | 2 | 3.02 | 1.2 | 15.0 | 0.677 | 0.527 | 16.1 | 12.1 | 29.9 |
| vggtslam | 2 | 3.87 | N/A | 119.0 | 0.388 | 0.293 | 85.5 | 41.8 | 14.9 |


---

# PRISM-benchmarks — all runs (every scene / rate / variant)

*Preliminary results; full evaluation is future work. Hardware: RTX PRO 6000.*

## Table A — Performance & resources

| Method | Run | Eff.FPS↑ | Latency s↓ | VRAM peak GB↓ | GPU % |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.30 | 3.7 | 8.41 | 13 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 5.06 | 5.2 | 8.45 | 5 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.47 | 6.4 | 20.52 | 31 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 2.81 | 11.2 | 23.34 | 45 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3.15 | 14.3 | 9.02 | 6 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 4.60 | 13.7 | 9.02 | 5 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 4.45 | 2.5 | 35.42 | 26 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 5.09 | 3.8 | 39.87 | 28 |
| prism | office_4/synthetic_2.0hz/pano | 2.84 | 5.9 | 13.94 | 22 |
| prism | apartment_0/synthetic_2.0hz/pano | 3.20 | 10.6 | 13.94 | 31 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 2.48 | 5.6 | 35.36 | 8 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 2.96 | 8.0 | 45.91 | 9 |


## Table B — Metric accuracy (absolute scale vs. rendered GT)

| Method | Run | Scale est. | Scale err %↓ | Extent err %↓ |
| --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| panovggt | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| vggtslam | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| pi3 | office_4/synthetic_2.0hz | 0.863 | 13.7 | 61.5 |
| pi3 | apartment_0/synthetic_2.0hz | 0.941 | 5.9 | 18.5 |
| prism | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.6 |
| prism | apartment_0/synthetic_2.0hz | 0.977 | 2.3 | 2.4 |
| mapanything | office_4/synthetic_2.0hz | 0.978 | 2.2 | 5.4 |
| mapanything | apartment_0/synthetic_2.0hz | 0.891 | 10.9 | 14.8 |


## Table C — Reconstruction, co-visibility masked (fair)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.0 | 2.8 | 6.8 | 0.871 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 9.6 | 6.3 | 15.8 | 0.641 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.5 | 0.9 | 3.4 | 0.967 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 7.6 | 2.7 | 10.3 | 0.619 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3.3 | 7.3 | 10.6 | 0.727 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 35.8 | 156.8 | 192.6 | 0.050 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.5 | 1.5 | 4.0 | 0.960 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 4.7 | 2.2 | 6.9 | 0.819 |
| prism | office_4/synthetic_2.0hz/pano | 2.3 | 7.2 | 9.5 | 0.830 |
| prism | apartment_0/synthetic_2.0hz/pano | 9.8 | 10.2 | 20.0 | 0.525 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.5 | 11.9 | 23.5 | 0.441 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 13.5 | 13.3 | 26.8 | 0.397 |


## Table C2 — Reconstruction, full-360 (no mask; pano methods)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.4 | 7.8 | 12.2 | 0.728 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 11.0 | 70.5 | 81.5 | 0.358 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.7 | 1.7 | 4.4 | 0.922 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 9.3 | 61.9 | 71.2 | 0.441 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 5.8 | 10.4 | 16.3 | 0.553 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 31.3 | 186.4 | 217.8 | 0.033 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.7 | 6.8 | 9.5 | 0.844 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 4.9 | 71.7 | 76.6 | 0.463 |
| prism | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.0 | 0.710 |
| prism | apartment_0/synthetic_2.0hz/pano | 9.2 | 71.0 | 80.3 | 0.344 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.1 | 19.2 | 30.3 | 0.389 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 14.7 | 75.6 | 90.3 | 0.219 |


## Table D — Cloud cleanliness & size

*noise% = pred points far from any GT surface; precision@2cm = within 2 cm (sharpness).*

| Method | Run | Points | Size MB↓ | Noise %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 122538 | 1.8 | 6.1 | 40.0 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 319033 | 4.8 | 24.2 | 12.4 |
| panovggt | office_4/synthetic_2.0hz/pano | 4664513 | 70.0 | 1.4 | 52.6 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 7467450 | 112.0 | 24.1 | 9.5 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3177384 | 85.8 | 1.0 | 28.1 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 3155185 | 85.2 | 82.5 | 1.6 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 1077863 | 16.2 | 0.5 | 47.6 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 1937315 | 29.1 | 6.0 | 16.5 |
| prism | office_4/synthetic_2.0hz/pano | 648230 | 9.7 | 0.4 | 49.8 |
| prism | apartment_0/synthetic_2.0hz/pano | 1497190 | 22.5 | 23.8 | 9.9 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 1220267 | 18.3 | 42.8 | 14.5 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 2815222 | 42.2 | 44.4 | 6.4 |


## Trajectory (ATE/RPE, Sim(3)-aligned)

| Method | Run | ATE RMSE cm↓ | RPE RMSE cm↓ |
| --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.2 | 2.9 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 22.6 | 5.2 |
| panovggt | office_4/synthetic_2.0hz/pano | 0.9 | 0.6 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 46.7 | 65.6 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 30.7 | 32.0 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 207.3 | 150.3 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 5.2 | 4.4 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 9.6 | 9.4 |
| prism | office_4/synthetic_2.0hz/pano | 1.7 | 0.7 |
| prism | apartment_0/synthetic_2.0hz/pano | 28.3 | 35.8 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 26.1 | 18.0 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 85.0 | 78.2 |