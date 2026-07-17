# PRISM-benchmarks — global report (2 scene(s))

## Global aggregate — mean per method (over all scenes × rates × variants)
*N = runs averaged. Scale err averaged over metric-capable runs only.*

| Method | N | Eff.FPS↑ | Scale err %↓ | ATE cm↓ | Masked F↑ | Full-360 F↑ | Map MB↓ | Outlier %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laser | 6 | 4.35 | N/A | 17.6 | 0.739 | 0.529 | 3.6 | 3.2 | 26.4 |
| mapanything | 6 | 2.46 | 7.3 | 53.5 | 0.370 | 0.275 | 29.9 | 3.8 | 9.5 |
| panovggt | 6 | 2.12 | N/A | 26.0 | 0.755 | 0.678 | 73.0 | 3.0 | 34.3 |
| pi3 | 6 | 5.29 | 8.7 | 13.3 | 0.851 | 0.586 | 22.3 | 2.8 | 27.6 |
| prism | 6 | 2.70 | 3.2 | 25.6 | 0.602 | 0.488 | 16.4 | 2.3 | 28.0 |
| prism_noguards | 6 | 2.83 | 3.9 | 29.1 | 0.606 | 0.500 | 16.0 | 2.3 | 28.4 |
| prism_nolock | 6 | 2.77 | 3.9 | 29.1 | 0.607 | 0.501 | 16.3 | 2.2 | 28.4 |
| prism_nostill | 6 | 2.78 | 3.2 | 25.6 | 0.602 | 0.488 | 16.5 | 2.3 | 28.2 |
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

| prism_nostill | office_4/synthetic_2.0hz/pano | 25 | 2.87 | 5.9 | 13.94 | 29 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 100 | 0.90 | 3.1 | 15.57 | 9 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 10 | 4.49 | 15.6 | 13.77 | 43 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 25 | 3.23 | 10.8 | 13.94 | 33 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 100 | 1.09 | 5.2 | 19.69 | 14 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 10 | 4.08 | 29.2 | 14.53 | 45 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 25 | 2.78 | 6.1 | 13.74 | 19 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 100 | 0.88 | 3.0 | 15.57 | 15 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 10 | 4.66 | 15.9 | 13.87 | 44 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 25 | 3.12 | 11.2 | 14.06 | 34 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 100 | 1.10 | 5.2 | 19.69 | 20 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 10 | 4.08 | 29.4 | 15.62 | 46 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 25 | 1.94 | 6.3 | 91.19 | 7 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 100 | 0.81 | 1.5 | 93.22 | 3 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 10 | 3.88 | 15.2 | 94.41 | 15 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 2.91 | 8.0 | 92.13 | 10 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 1.11 | 2.1 | 76.19 | 4 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 4.14 | 22.2 | 96.28 | 19 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 25 | 3.07 | 6.0 | 13.87 | 23 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 100 | 0.93 | 3.1 | 15.57 | 14 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 10 | 4.46 | 15.2 | 13.94 | 45 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 25 | 3.08 | 11.0 | 14.06 | 34 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 100 | 1.12 | 5.2 | 19.69 | 15 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 10 | 4.34 | 28.1 | 14.79 | 47 |


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
| prism_nostill | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.6 |
| prism_nostill | office_4/synthetic_0.5hz | 1.001 | 0.1 | 4.3 |
| prism_nostill | office_4/synthetic_5.0hz | 0.982 | 1.8 | 12.1 |
| prism_nostill | apartment_0/synthetic_2.0hz | 0.977 | 2.3 | 2.5 |
| prism_nostill | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.1 |
| prism_nostill | apartment_0/synthetic_5.0hz | 1.034 | 3.4 | 0.6 |
| prism_nolock | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.7 |
| prism_nolock | office_4/synthetic_0.5hz | 1.002 | 0.2 | 4.1 |
| prism_nolock | office_4/synthetic_5.0hz | 0.991 | 0.9 | 9.8 |
| prism_nolock | apartment_0/synthetic_2.0hz | 0.967 | 3.3 | 2.5 |
| prism_nolock | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.0 |
| prism_nolock | apartment_0/synthetic_5.0hz | 0.927 | 7.3 | 3.5 |
| mapanything | office_4/synthetic_2.0hz | 0.978 | 2.2 | 5.4 |
| mapanything | office_4/synthetic_0.5hz | 0.973 | 2.7 | 0.9 |
| mapanything | office_4/synthetic_5.0hz | 0.981 | 1.9 | 6.8 |
| mapanything | apartment_0/synthetic_2.0hz | 0.891 | 10.9 | 14.8 |
| mapanything | apartment_0/synthetic_0.5hz | 0.837 | 16.3 | 14.7 |
| mapanything | apartment_0/synthetic_5.0hz | 0.901 | 9.9 | 21.6 |
| prism_noguards | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.6 |
| prism_noguards | office_4/synthetic_0.5hz | 1.002 | 0.2 | 4.3 |
| prism_noguards | office_4/synthetic_5.0hz | 0.990 | 1.0 | 9.8 |
| prism_noguards | apartment_0/synthetic_2.0hz | 0.967 | 3.3 | 2.5 |
| prism_noguards | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.1 |
| prism_noguards | apartment_0/synthetic_5.0hz | 0.926 | 7.4 | 3.4 |


## Table C — Reconstruction, co-visibility masked (fair)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.0 | 2.8 | 6.8 | 0.870 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 2.6 | 2.5 | 5.0 | 0.957 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 5.6 | 3.0 | 8.6 | 0.792 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 9.6 | 6.3 | 15.9 | 0.640 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 7.4 | 4.0 | 11.4 | 0.693 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 11.9 | 6.4 | 18.3 | 0.483 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.5 | 0.9 | 3.4 | 0.967 |
| panovggt | office_4/synthetic_0.5hz/pano | 2.2 | 1.1 | 3.2 | 0.977 |
| panovggt | office_4/synthetic_5.0hz/pano | 2.9 | 0.8 | 3.7 | 0.950 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 7.6 | 2.7 | 10.3 | 0.620 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 17.6 | 13.7 | 31.2 | 0.260 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3.3 | 7.3 | 10.6 | 0.726 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 3.2 | 8.1 | 11.3 | 0.801 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3.8 | 5.9 | 9.7 | 0.754 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 35.7 | 157.4 | 193.2 | 0.049 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 30.6 | 37.3 | 67.9 | 0.170 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 25.2 | 153.2 | 178.4 | 0.073 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.5 | 1.5 | 4.0 | 0.960 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 2.4 | 2.1 | 4.5 | 0.965 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 4.7 | 2.2 | 6.9 | 0.819 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 5.1 | 4.7 | 9.8 | 0.733 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 5.7 | 1.9 | 7.6 | 0.780 |
| prism | office_4/synthetic_2.0hz/pano | 2.3 | 7.4 | 9.7 | 0.830 |
| prism | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism | office_4/synthetic_5.0hz/pano | 3.1 | 13.6 | 16.6 | 0.714 |
| prism | apartment_0/synthetic_2.0hz/pano | 9.8 | 10.1 | 19.9 | 0.527 |
| prism | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.223 |
| prism | apartment_0/synthetic_5.0hz/pano | 12.7 | 18.8 | 31.5 | 0.360 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 2.3 | 7.5 | 9.8 | 0.831 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 3.1 | 13.5 | 16.5 | 0.717 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 9.8 | 10.1 | 19.9 | 0.526 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.221 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 12.7 | 19.0 | 31.7 | 0.361 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 2.3 | 7.5 | 9.8 | 0.829 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 2.8 | 4.9 | 7.7 | 0.855 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 5.7 | 7.8 | 13.4 | 0.563 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.221 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 19.3 | 24.8 | 44.2 | 0.215 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.5 | 12.0 | 23.5 | 0.441 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 13.5 | 15.9 | 29.3 | 0.398 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 12.1 | 10.6 | 22.7 | 0.420 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 13.5 | 13.4 | 26.9 | 0.396 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 27.0 | 27.8 | 54.9 | 0.212 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 13.3 | 9.5 | 22.8 | 0.353 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 2.3 | 7.0 | 9.3 | 0.835 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 2.7 | 4.8 | 7.5 | 0.866 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 5.6 | 7.7 | 13.3 | 0.565 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.6 | 36.6 | 0.225 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 20.0 | 25.4 | 45.3 | 0.186 |


## Table C2 — Reconstruction, full-360 (no mask; pano methods)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.4 | 7.8 | 12.2 | 0.728 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 2.7 | 21.6 | 24.3 | 0.748 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 7.8 | 7.7 | 15.4 | 0.692 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 11.0 | 70.8 | 81.8 | 0.356 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 7.7 | 75.2 | 82.9 | 0.351 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 12.2 | 71.8 | 84.0 | 0.297 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.7 | 1.7 | 4.4 | 0.922 |
| panovggt | office_4/synthetic_0.5hz/pano | 2.3 | 2.1 | 4.4 | 0.925 |
| panovggt | office_4/synthetic_5.0hz/pano | 3.1 | 1.5 | 4.6 | 0.906 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 9.3 | 61.9 | 71.2 | 0.442 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 16.3 | 70.6 | 86.9 | 0.195 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 5.8 | 10.4 | 16.2 | 0.553 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 3.6 | 22.5 | 26.1 | 0.625 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3.9 | 10.6 | 14.5 | 0.672 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 31.2 | 186.3 | 217.5 | 0.033 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 24.2 | 93.7 | 118.0 | 0.105 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 23.1 | 161.3 | 184.4 | 0.057 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.7 | 6.8 | 9.5 | 0.844 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 2.5 | 19.8 | 22.2 | 0.783 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 4.9 | 71.5 | 76.3 | 0.464 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 5.4 | 73.6 | 79.0 | 0.380 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 5.9 | 71.4 | 77.3 | 0.460 |
| prism | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.0 | 0.711 |
| prism | office_4/synthetic_0.5hz/pano | 1.9 | 3.9 | 5.8 | 0.889 |
| prism | office_4/synthetic_5.0hz/pano | 6.3 | 6.2 | 12.4 | 0.636 |
| prism | apartment_0/synthetic_2.0hz/pano | 9.3 | 71.4 | 80.6 | 0.345 |
| prism | apartment_0/synthetic_0.5hz/pano | 16.3 | 85.0 | 101.3 | 0.137 |
| prism | apartment_0/synthetic_5.0hz/pano | 21.4 | 72.1 | 93.5 | 0.210 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 5.7 | 5.4 | 11.1 | 0.710 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 1.9 | 3.9 | 5.8 | 0.889 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 6.3 | 6.2 | 12.4 | 0.637 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 9.2 | 71.0 | 80.3 | 0.346 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.9 | 101.1 | 0.136 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 21.2 | 72.0 | 93.2 | 0.211 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.0 | 0.707 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 1.9 | 3.9 | 5.8 | 0.890 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 3.7 | 4.7 | 8.4 | 0.775 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 6.4 | 69.7 | 76.1 | 0.371 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.6 | 100.9 | 0.137 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 23.8 | 84.9 | 108.6 | 0.127 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.1 | 19.2 | 30.3 | 0.390 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 12.6 | 34.0 | 46.6 | 0.328 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 11.8 | 16.5 | 28.2 | 0.376 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 14.7 | 75.8 | 90.5 | 0.218 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 23.1 | 87.3 | 110.4 | 0.124 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 16.4 | 69.9 | 86.3 | 0.215 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.0 | 0.709 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 1.9 | 3.8 | 5.8 | 0.890 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 3.7 | 4.7 | 8.4 | 0.775 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 6.4 | 69.6 | 76.0 | 0.370 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.6 | 100.9 | 0.139 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 24.7 | 85.5 | 110.2 | 0.118 |


## Table D — Cloud cleanliness & size

*Outlier% = kNN statistical outliers (density-independent fluffiness — the fair noise measure across sparse vs dense clouds); Acc-p95 = 95th-pct pred→GT distance (worst floaters); noise% = points >10 cm from GT; prec@2cm = within 2 cm.*

| Method | Run | Points | Size MB↓ | Outlier %↓ | Acc-p95 cm↓ | Noise %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 122538 | 1.8 | 2.7 | 11.8 | 6.1 | 39.9 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 66040 | 1.0 | 2.4 | 6.4 | 3.3 | 63.6 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 148265 | 2.2 | 3.3 | 15.7 | 10.4 | 23.3 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 319033 | 4.8 | 3.5 | 39.8 | 24.3 | 12.5 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 124669 | 1.9 | 3.9 | 26.2 | 17.9 | 12.8 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 642544 | 9.6 | 3.5 | 40.2 | 36.1 | 6.1 |
| panovggt | office_4/synthetic_2.0hz/pano | 4664513 | 70.0 | 2.4 | 5.2 | 1.4 | 52.7 |
| panovggt | office_4/synthetic_0.5hz/pano | 2694678 | 40.4 | 2.2 | 4.4 | 0.6 | 58.0 |
| panovggt | office_4/synthetic_5.0hz/pano | 6147230 | 92.2 | 2.6 | 6.4 | 2.6 | 47.9 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 7467450 | 112.0 | 4.3 | 20.6 | 24.2 | 9.5 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 3357864 | 50.4 | 3.6 | 49.7 | 58.3 | 3.6 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3177384 | 85.8 | 4.3 | 6.4 | 1.0 | 28.1 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 1589087 | 42.9 | 3.7 | 10.9 | 6.1 | 39.7 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3797683 | 102.5 | 4.6 | 10.8 | 5.7 | 33.7 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 3155185 | 85.2 | 2.9 | 78.6 | 82.3 | 1.6 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 2127018 | 57.4 | 4.0 | 72.9 | 70.3 | 3.3 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 6077135 | 164.1 | 3.5 | 67.5 | 63.7 | 3.5 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 1077863 | 16.2 | 2.3 | 5.2 | 0.5 | 47.6 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 680452 | 10.2 | 1.7 | 4.5 | 0.3 | 45.4 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 1937315 | 29.1 | 3.4 | 11.0 | 6.0 | 16.6 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 1023680 | 15.4 | 3.1 | 12.4 | 8.0 | 14.6 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 2697310 | 40.5 | 3.4 | 14.8 | 9.9 | 14.0 |
| prism | office_4/synthetic_2.0hz/pano | 647577 | 9.7 | 2.3 | 4.7 | 0.4 | 49.4 |
| prism | office_4/synthetic_0.5hz/pano | 547120 | 8.2 | 2.1 | 3.9 | 0.2 | 66.4 |
| prism | office_4/synthetic_5.0hz/pano | 657041 | 9.9 | 2.2 | 6.3 | 1.7 | 32.1 |
| prism | apartment_0/synthetic_2.0hz/pano | 1493304 | 22.4 | 2.4 | 37.3 | 23.7 | 10.0 |
| prism | apartment_0/synthetic_0.5hz/pano | 1389184 | 20.8 | 2.1 | 52.2 | 57.5 | 3.9 |
| prism | apartment_0/synthetic_5.0hz/pano | 1845611 | 27.7 | 2.4 | 42.7 | 34.8 | 6.5 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 648498 | 9.7 | 2.3 | 4.7 | 0.4 | 50.0 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 547419 | 8.2 | 2.2 | 3.9 | 0.2 | 66.3 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 656400 | 9.8 | 2.2 | 6.3 | 1.8 | 32.5 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 1493421 | 22.4 | 2.4 | 37.0 | 23.7 | 10.0 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 1386487 | 20.8 | 2.4 | 52.2 | 57.6 | 3.7 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 1849178 | 27.7 | 2.5 | 42.9 | 34.7 | 6.5 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 649959 | 9.8 | 2.3 | 4.7 | 0.5 | 49.7 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 547936 | 8.2 | 2.3 | 3.9 | 0.2 | 66.4 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 601999 | 9.0 | 2.1 | 5.7 | 0.4 | 37.0 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 1475587 | 22.1 | 2.3 | 14.0 | 13.9 | 10.4 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 1384292 | 20.8 | 2.0 | 52.4 | 57.5 | 3.7 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 1856064 | 27.8 | 2.4 | 63.6 | 54.2 | 3.3 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 1220150 | 18.3 | 4.5 | 33.9 | 42.8 | 14.5 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 574014 | 8.6 | 3.4 | 35.2 | 48.7 | 14.9 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 1628324 | 24.4 | 4.2 | 34.2 | 46.2 | 13.2 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 2814956 | 42.2 | 3.7 | 43.1 | 44.4 | 6.4 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 1045511 | 15.7 | 3.7 | 69.2 | 69.6 | 4.0 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 4682508 | 70.2 | 3.6 | 38.5 | 47.1 | 4.3 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 655566 | 9.8 | 2.2 | 4.7 | 0.5 | 49.5 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 546736 | 8.2 | 2.2 | 3.9 | 0.2 | 66.2 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 604559 | 9.1 | 2.2 | 5.7 | 0.4 | 37.1 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 1486957 | 22.3 | 2.3 | 14.0 | 13.7 | 10.6 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 1384402 | 20.8 | 2.2 | 52.3 | 57.5 | 4.0 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 1731263 | 26.0 | 2.4 | 63.8 | 56.4 | 3.2 |


## Trajectory (ATE + drift/m, Sim(3)-aligned)

*Drift/m = relative pose error per metre of GT motion — fair across dense vs keyframe-sparse methods (replaces the frame-delta RPE, which penalised keyframes).*

| Method | Run | ATE RMSE cm↓ | Drift %/m↓ |
| --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.2 | 9.7 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 4.0 | 4.3 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 6.0 | 13.9 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 22.6 | 9.3 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 47.3 | 29.4 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 21.3 | 10.7 |
| panovggt | office_4/synthetic_2.0hz/pano | 0.9 | 2.5 |
| panovggt | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| panovggt | office_4/synthetic_5.0hz/pano | 0.8 | 3.2 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 46.7 | 49.8 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 81.1 | 49.9 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 30.7 | 62.7 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 39.3 | 28.5 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 27.1 | 105.7 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 207.3 | 250.4 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 88.2 | 57.3 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 193.8 | 266.6 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 5.2 | 16.3 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 6.1 | 5.9 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 9.6 | 16.8 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 37.5 | 25.6 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 8.2 | 23.0 |
| prism | office_4/synthetic_2.0hz/pano | 1.7 | 2.8 |
| prism | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism | office_4/synthetic_5.0hz/pano | 5.9 | 4.4 |
| prism | apartment_0/synthetic_2.0hz/pano | 28.3 | 30.5 |
| prism | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism | apartment_0/synthetic_5.0hz/pano | 50.3 | 37.8 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 1.8 | 2.8 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 5.9 | 4.3 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 28.3 | 30.5 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 50.4 | 37.8 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 1.7 | 2.8 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 3.2 | 3.1 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 30.0 | 33.8 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 72.5 | 49.9 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 26.1 | 61.6 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 28.2 | 34.1 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 25.3 | 74.7 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 85.0 | 120.3 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 83.7 | 62.1 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 72.6 | 166.1 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 1.7 | 2.7 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 3.2 | 3.1 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 30.0 | 33.8 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 72.5 | 49.5 |