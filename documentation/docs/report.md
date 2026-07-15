# PRISM-benchmarks — global report (2 scene(s))

## Global aggregate — mean per method (over all scenes × rates × variants)
*N = runs averaged. Scale err averaged over metric-capable runs only.*

| Method | N | Eff.FPS↑ | Scale err %↓ | ATE cm↓ | Masked F↑ | Full-360 F↑ | Map MB↓ | Outlier %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laser | 6 | 4.35 | N/A | 17.6 | 0.739 | 0.529 | 3.6 | 3.2 | 26.4 |
| mapanything | 6 | 2.46 | 7.3 | 53.5 | 0.370 | 0.275 | 29.9 | 3.8 | 9.6 |
| panovggt | 6 | 2.12 | N/A | 26.0 | 0.754 | 0.678 | 73.0 | 3.0 | 34.3 |
| pi3 | 6 | 5.29 | 8.7 | 13.3 | 0.851 | 0.586 | 22.3 | 2.8 | 27.6 |
| prism | 6 | 2.70 | 3.2 | 25.6 | 0.602 | 0.488 | 16.4 | 2.3 | 28.1 |
| vggtslam | 6 | 4.30 | N/A | 97.7 | 0.429 | 0.341 | 89.7 | 3.8 | 18.3 |


---

# PRISM-benchmarks — all runs (every scene / rate / variant)

*Preliminary results; full evaluation is future work. Hardware: RTX PRO 6000.*

**Inter-frame baseline = speed/rate is the quality-driving quantity (not FPS):** at 0.5 m/s, 0.5 Hz→100 cm, 2 Hz→25 cm, 5 Hz→10 cm between frames.

## Table A — Performance & resources

| Method | Run | Baseline cm | Eff.FPS↑ | Latency s↓ | VRAM peak GB↓ | GPU % |
| --- | --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 25 | 3.96 | 3.9 | 70.29 | 7 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 100 | 1.49 | 1.5 | 69.98 | 6 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 10 | 6.53 | 8.4 | 70.38 | 20 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 5.09 | 5.2 | 70.36 | 12 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 1.92 | 2.2 | 70.23 | 8 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 7.11 | 11.8 | 70.49 | 18 |
| panovggt | office_4/synthetic_2.0hz/pano | 25 | 2.66 | 6.4 | 82.39 | 34 |
| panovggt | office_4/synthetic_0.5hz/pano | 100 | 1.17 | 1.1 | 74.28 | 10 |
| panovggt | office_4/synthetic_5.0hz/pano | 10 | 2.49 | 31.4 | 96.01 | 62 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 25 | 2.59 | 11.6 | 85.39 | 44 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 100 | 1.34 | 1.6 | 75.57 | 15 |
| panovggt | apartment_0/synthetic_5.0hz/pano | 10 | 2.47 | 0.0 | 101.68 | 83 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 25 | 3.17 | 14.3 | 9.02 | 2 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 100 | 0.92 | 12.8 | 8.31 | 4 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 10 | 7.94 | 14.2 | 9.02 | 3 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 4.27 | 14.9 | 9.02 | 2 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 1.24 | 13.2 | 8.75 | 2 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 8.23 | 19.1 | 101.40 | 6 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 25 | 4.43 | 2.5 | 97.29 | 25 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 100 | 1.59 | 0.8 | 78.03 | 7 |
| pi3 | office_4/synthetic_5.0hz/synthetic_fov | 10 | 12.60 | 0.0 | 102.14 | 18 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 4.95 | 3.8 | 82.57 | 28 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 2.15 | 1.0 | 77.68 | 11 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 6.05 | 15.1 | 69.69 | 55 |
| prism | office_4/synthetic_2.0hz/pano | 25 | 2.05 | 6.0 | 75.81 | 17 |
| prism | office_4/synthetic_0.5hz/pano | 100 | 0.88 | 3.0 | 77.44 | 10 |
| prism | office_4/synthetic_5.0hz/pano | 10 | 4.51 | 15.4 | 75.74 | 39 |
| prism | apartment_0/synthetic_2.0hz/pano | 25 | 3.10 | 10.9 | 75.81 | 33 |
| prism | apartment_0/synthetic_0.5hz/pano | 100 | 1.10 | 5.2 | 81.56 | 17 |
| prism | apartment_0/synthetic_5.0hz/pano | 10 | 4.53 | 25.6 | 76.39 | 48 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 25 | 1.94 | 6.3 | 91.19 | 7 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 100 | 0.81 | 1.5 | 93.22 | 3 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 10 | 3.88 | 15.2 | 94.41 | 15 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 2.91 | 8.0 | 92.13 | 10 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 1.11 | 2.1 | 76.19 | 4 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 4.14 | 22.2 | 96.28 | 19 |


## Table B — Metric accuracy (absolute scale vs. rendered GT)

| Method | Run | Scale est. | Scale err %↓ | Extent err %↓ |
| --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| laser | office_4/synthetic_0.5hz | N/A (scale-free) | — | — |
| laser | office_4/synthetic_5.0hz | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_0.5hz | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_5.0hz | N/A (scale-free) | — | — |
| panovggt | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| panovggt | office_4/synthetic_0.5hz | N/A (scale-free) | — | — |
| panovggt | office_4/synthetic_5.0hz | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_0.5hz | N/A (scale-free) | — | — |
| vggtslam | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| vggtslam | office_4/synthetic_0.5hz | N/A (scale-free) | — | — |
| vggtslam | office_4/synthetic_5.0hz | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_0.5hz | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_5.0hz | N/A (scale-free) | — | — |
| pi3 | office_4/synthetic_2.0hz | 0.863 | 13.7 | 61.5 |
| pi3 | office_4/synthetic_0.5hz | 0.871 | 12.9 | 58.2 |
| pi3 | apartment_0/synthetic_2.0hz | 0.941 | 5.9 | 18.5 |
| pi3 | apartment_0/synthetic_0.5hz | 0.953 | 4.7 | 16.3 |
| pi3 | apartment_0/synthetic_5.0hz | 0.938 | 6.2 | 19.4 |
| prism | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.6 |
| prism | office_4/synthetic_0.5hz | 1.002 | 0.2 | 4.0 |
| prism | office_4/synthetic_5.0hz | 0.982 | 1.8 | 11.4 |
| prism | apartment_0/synthetic_2.0hz | 0.977 | 2.3 | 2.4 |
| prism | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.1 |
| prism | apartment_0/synthetic_5.0hz | 1.034 | 3.4 | 0.6 |
| mapanything | office_4/synthetic_2.0hz | 0.978 | 2.2 | 5.4 |
| mapanything | office_4/synthetic_0.5hz | 0.973 | 2.7 | 0.9 |
| mapanything | office_4/synthetic_5.0hz | 0.981 | 1.9 | 6.8 |
| mapanything | apartment_0/synthetic_2.0hz | 0.891 | 10.9 | 14.8 |
| mapanything | apartment_0/synthetic_0.5hz | 0.837 | 16.3 | 14.7 |
| mapanything | apartment_0/synthetic_5.0hz | 0.901 | 9.9 | 21.6 |


## Table C — Reconstruction, co-visibility masked (fair)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.0 | 2.8 | 6.8 | 0.870 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 2.6 | 2.5 | 5.0 | 0.957 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 5.6 | 3.0 | 8.6 | 0.791 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 9.6 | 6.3 | 15.9 | 0.641 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 7.4 | 4.0 | 11.4 | 0.693 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 11.9 | 6.4 | 18.3 | 0.484 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.5 | 0.9 | 3.4 | 0.966 |
| panovggt | office_4/synthetic_0.5hz/pano | 2.2 | 1.1 | 3.2 | 0.977 |
| panovggt | office_4/synthetic_5.0hz/pano | 2.9 | 0.8 | 3.7 | 0.949 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 7.6 | 2.7 | 10.3 | 0.620 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 17.6 | 13.7 | 31.3 | 0.259 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3.3 | 7.3 | 10.6 | 0.726 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 3.2 | 8.1 | 11.3 | 0.802 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3.8 | 5.9 | 9.7 | 0.755 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 35.5 | 157.1 | 192.6 | 0.050 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 30.6 | 37.3 | 67.9 | 0.170 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 25.5 | 153.4 | 178.9 | 0.072 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.5 | 1.5 | 4.0 | 0.960 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 2.4 | 2.1 | 4.5 | 0.965 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 4.7 | 2.2 | 6.9 | 0.819 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 5.1 | 4.8 | 9.9 | 0.730 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 5.7 | 2.0 | 7.6 | 0.780 |
| prism | office_4/synthetic_2.0hz/pano | 2.3 | 7.7 | 10.0 | 0.831 |
| prism | office_4/synthetic_0.5hz/pano | 1.8 | 2.2 | 4.0 | 0.958 |
| prism | office_4/synthetic_5.0hz/pano | 3.1 | 13.5 | 16.6 | 0.715 |
| prism | apartment_0/synthetic_2.0hz/pano | 9.8 | 10.2 | 20.0 | 0.526 |
| prism | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.223 |
| prism | apartment_0/synthetic_5.0hz/pano | 12.7 | 18.8 | 31.5 | 0.359 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.5 | 11.9 | 23.5 | 0.441 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 13.5 | 15.9 | 29.4 | 0.397 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 12.1 | 10.6 | 22.7 | 0.419 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 13.5 | 13.4 | 26.9 | 0.397 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 27.0 | 27.6 | 54.6 | 0.213 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 13.3 | 9.5 | 22.8 | 0.353 |


## Table C2 — Reconstruction, full-360 (no mask; pano methods)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.4 | 7.8 | 12.2 | 0.728 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 2.7 | 21.6 | 24.2 | 0.749 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 7.8 | 7.7 | 15.5 | 0.691 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 11.0 | 70.6 | 81.6 | 0.357 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 7.7 | 75.5 | 83.2 | 0.349 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 12.2 | 71.6 | 83.8 | 0.297 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.7 | 1.7 | 4.4 | 0.922 |
| panovggt | office_4/synthetic_0.5hz/pano | 2.3 | 2.1 | 4.4 | 0.925 |
| panovggt | office_4/synthetic_5.0hz/pano | 3.1 | 1.5 | 4.6 | 0.905 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 9.3 | 61.9 | 71.2 | 0.441 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 16.4 | 70.6 | 87.0 | 0.194 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 5.8 | 10.4 | 16.2 | 0.553 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 3.6 | 22.5 | 26.1 | 0.625 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3.9 | 10.7 | 14.5 | 0.672 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 31.1 | 186.4 | 217.5 | 0.033 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 24.2 | 93.8 | 118.0 | 0.105 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 23.2 | 161.3 | 184.5 | 0.056 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.7 | 6.9 | 9.5 | 0.844 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 2.5 | 19.8 | 22.2 | 0.783 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 4.9 | 71.6 | 76.5 | 0.464 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 5.4 | 73.6 | 79.0 | 0.379 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 5.9 | 71.4 | 77.3 | 0.461 |
| prism | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.0 | 0.711 |
| prism | office_4/synthetic_0.5hz/pano | 1.9 | 3.8 | 5.8 | 0.890 |
| prism | office_4/synthetic_5.0hz/pano | 6.2 | 6.2 | 12.4 | 0.636 |
| prism | apartment_0/synthetic_2.0hz/pano | 9.3 | 71.0 | 80.3 | 0.345 |
| prism | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.8 | 101.1 | 0.137 |
| prism | apartment_0/synthetic_5.0hz/pano | 21.4 | 71.8 | 93.2 | 0.210 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.1 | 19.2 | 30.3 | 0.390 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 12.6 | 33.9 | 46.5 | 0.328 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 11.8 | 16.5 | 28.3 | 0.374 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 14.7 | 75.6 | 90.4 | 0.219 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 23.1 | 87.6 | 110.7 | 0.124 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 16.4 | 69.8 | 86.3 | 0.215 |


## Table D — Cloud cleanliness & size

*Outlier% = kNN statistical outliers (density-independent fluffiness — the fair noise measure across sparse vs dense clouds); Acc-p95 = 95th-pct pred→GT distance (worst floaters); noise% = points >10 cm from GT; prec@2cm = within 2 cm.*

| Method | Run | Points | Size MB↓ | Outlier %↓ | Acc-p95 cm↓ | Noise %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 122538 | 1.8 | 2.7 | 11.9 | 6.1 | 40.0 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 66040 | 1.0 | 2.4 | 6.5 | 3.3 | 63.7 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 148265 | 2.2 | 3.3 | 15.6 | 10.4 | 23.3 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 319033 | 4.8 | 3.5 | 39.9 | 24.2 | 12.5 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 124669 | 1.9 | 3.9 | 26.0 | 17.9 | 12.8 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 642544 | 9.6 | 3.5 | 40.3 | 36.1 | 6.1 |
| panovggt | office_4/synthetic_2.0hz/pano | 4664513 | 70.0 | 2.4 | 5.2 | 1.4 | 52.6 |
| panovggt | office_4/synthetic_0.5hz/pano | 2694678 | 40.4 | 2.2 | 4.4 | 0.6 | 58.1 |
| panovggt | office_4/synthetic_5.0hz/pano | 6147230 | 92.2 | 2.6 | 6.4 | 2.6 | 47.9 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 7467450 | 112.0 | 4.3 | 20.6 | 24.2 | 9.6 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 3357864 | 50.4 | 3.6 | 49.7 | 58.3 | 3.5 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3177384 | 85.8 | 4.3 | 6.4 | 1.0 | 28.2 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 1589087 | 42.9 | 3.7 | 10.9 | 6.1 | 39.5 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3797683 | 102.5 | 4.6 | 10.8 | 5.7 | 33.6 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 3155185 | 85.2 | 2.9 | 78.6 | 82.1 | 1.7 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 2127018 | 57.4 | 4.0 | 73.1 | 70.3 | 3.3 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 6077135 | 164.1 | 3.5 | 67.8 | 64.8 | 3.4 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 1077863 | 16.2 | 2.3 | 5.2 | 0.5 | 47.6 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 680452 | 10.2 | 1.7 | 4.5 | 0.3 | 45.3 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 1937315 | 29.1 | 3.4 | 11.0 | 6.0 | 16.6 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 1023680 | 15.4 | 3.1 | 12.4 | 8.0 | 14.6 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 2697310 | 40.5 | 3.4 | 14.8 | 9.9 | 13.9 |
| prism | office_4/synthetic_2.0hz/pano | 647577 | 9.7 | 2.3 | 4.7 | 0.4 | 49.7 |
| prism | office_4/synthetic_0.5hz/pano | 547120 | 8.2 | 2.1 | 3.9 | 0.2 | 66.5 |
| prism | office_4/synthetic_5.0hz/pano | 657041 | 9.9 | 2.2 | 6.3 | 1.7 | 32.0 |
| prism | apartment_0/synthetic_2.0hz/pano | 1493304 | 22.4 | 2.4 | 37.2 | 23.7 | 9.9 |
| prism | apartment_0/synthetic_0.5hz/pano | 1389184 | 20.8 | 2.1 | 52.2 | 57.4 | 3.8 |
| prism | apartment_0/synthetic_5.0hz/pano | 1845611 | 27.7 | 2.4 | 42.8 | 34.8 | 6.6 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 1220150 | 18.3 | 4.5 | 33.9 | 42.8 | 14.5 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 574014 | 8.6 | 3.4 | 35.2 | 48.7 | 14.8 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 1628324 | 24.4 | 4.2 | 34.2 | 46.2 | 13.2 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 2814956 | 42.2 | 3.7 | 43.0 | 44.5 | 6.4 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 1045511 | 15.7 | 3.7 | 69.2 | 69.5 | 4.1 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 4682508 | 70.2 | 3.6 | 38.5 | 47.1 | 4.3 |


## Trajectory (ATE/RPE, Sim(3)-aligned)

| Method | Run | ATE RMSE cm↓ | RPE RMSE cm↓ |
| --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.2 | 2.9 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 4.0 | 4.7 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 6.0 | 4.4 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 22.6 | 5.2 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 47.3 | 50.9 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 21.3 | 3.5 |
| panovggt | office_4/synthetic_2.0hz/pano | 0.9 | 0.6 |
| panovggt | office_4/synthetic_0.5hz/pano | 0.7 | 0.8 |
| panovggt | office_4/synthetic_5.0hz/pano | 0.8 | 0.4 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 46.7 | 65.6 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 81.1 | 119.7 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 30.7 | 32.0 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 39.3 | 46.7 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 27.1 | 33.2 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 207.3 | 150.3 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 88.2 | 102.2 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 193.8 | 58.1 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 5.2 | 4.4 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 6.1 | 7.4 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 9.6 | 9.4 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 37.5 | 41.1 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 8.2 | 5.8 |
| prism | office_4/synthetic_2.0hz/pano | 1.7 | 0.7 |
| prism | office_4/synthetic_0.5hz/pano | 0.7 | 0.8 |
| prism | office_4/synthetic_5.0hz/pano | 5.9 | 0.5 |
| prism | apartment_0/synthetic_2.0hz/pano | 28.3 | 35.8 |
| prism | apartment_0/synthetic_0.5hz/pano | 66.5 | 105.5 |
| prism | apartment_0/synthetic_5.0hz/pano | 50.3 | 18.2 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 26.1 | 18.0 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 28.2 | 30.8 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 25.3 | 11.5 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 85.0 | 78.2 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 83.7 | 94.9 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 72.6 | 51.4 |