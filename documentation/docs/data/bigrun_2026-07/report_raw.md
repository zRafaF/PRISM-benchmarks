# PRISM-benchmarks — global report (5 scene(s))

## Global aggregate — mean per method (over all scenes × rates × variants)
*N = runs averaged. Scale err averaged over metric-capable runs only.*

| Method | N | Eff.FPS↑ | Scale err %↓ | ATE cm↓ | Masked F↑ | Full-360 F↑ | Map MB↓ | Outlier %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laser | 46 | 4.77 | N/A | 77.8 | 0.399 | 0.261 | 5.8 | 3.3 | 11.9 |
| mapanything | 46 | 2.80 | 20.1 | 90.2 | 0.270 | 0.190 | 29.0 | 3.5 | 7.7 |
| panovggt | 46 | 2.32 | N/A | 62.1 | 0.599 | 0.478 | 99.6 | 3.8 | 18.9 |
| pi3 | 46 | 4.79 | 8.7 | 57.0 | 0.534 | 0.375 | 23.3 | 2.7 | 15.8 |
| prism | 46 | 3.18 | 12.8 | 58.9 | 0.447 | 0.338 | 21.2 | 2.4 | 18.2 |
| prism_noguards | 22 | 3.31 | 16.3 | 62.8 | 0.431 | 0.342 | 24.8 | 2.4 | 17.2 |
| prism_nolock | 22 | 3.34 | 16.0 | 64.5 | 0.430 | 0.342 | 24.3 | 2.5 | 17.3 |
| prism_nostill | 22 | 3.34 | 15.8 | 63.3 | 0.429 | 0.337 | 24.4 | 2.5 | 17.3 |
| prism_se3 | 46 | 3.22 | 12.1 | 62.0 | 0.412 | 0.297 | 20.6 | 2.4 | 15.8 |
| prism_sim3 | 40 | 3.43 | 14.0 | 68.9 | 0.396 | 0.283 | 20.9 | 2.5 | 15.5 |
| prism_sl4 | 6 | 2.83 | N/A | 26.3 | 0.661 | 0.557 | 15.1 | 2.2 | 36.4 |
| vggtslam | 46 | 4.57 | N/A | 127.5 | 0.249 | 0.180 | 100.6 | 3.7 | 10.1 |


## Alignment-group study — Sim(3) vs SE(3) vs SL(4) (core ablation)
*Same backbone / fusion / trajectory; only the submap registration group changes. Left block = **computing impact** (throughput, latency, peak VRAM — SL(4)'s dense 15-DoF projective solve costs more per submap); right block = metric fidelity. Expectation: more DoF fit overlaps better but inflate scale/extent/floaters, while Sim(3) stays metric. SL(4) also logs its mean non-similarity distortion to the run log (the shear/perspective Sim(3) forbids).*

| Group (arm) | DoF | N | Eff.FPS↑ | Latency s↓ | VRAM GB↓ | Scale err %↓ | Extent err %↓ | ATE cm↓ | Drift %/m↓ | Masked F↑ | Outlier %↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SL(4) (prism) | 15 | 46 | 3.18 | 9.9 | 23.54 | 12.8 | 22.6 | 58.9 | 47.0 | 0.447 | 2.4 |
| Sim(3) (prism_sim3) | 7 | 40 | 3.43 | 8.9 | 15.40 | 14.0 | 18.8 | 68.9 | 49.1 | 0.396 | 2.5 |
| SE(3) (prism_se3) | 6 | 46 | 3.22 | 9.7 | 23.80 | 12.1 | 17.5 | 62.0 | 45.2 | 0.412 | 2.4 |


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
| laser | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 25 | 6.29 | 6.9 | 8.48 | 11 |
| laser | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 5.21 | 5.7 | 8.42 | 8 |
| laser | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 4.47 | 4.4 | 8.40 | 9 |
| laser | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 6.09 | 6.7 | 8.52 | 7 |
| laser | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 2.26 | 2.2 | 8.36 | 9 |
| laser | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.74 | 1.6 | 8.19 | 6 |
| laser | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 6.92 | 9.3 | 8.62 | 17 |
| laser | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 5.47 | 5.8 | 8.49 | 9 |
| laser | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 7.85 | 12.6 | 8.62 | 20 |
| laser | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 25 | 5.33 | 5.2 | 8.46 | 15 |
| laser | apartment_1/loop_2.0hz_s0/synthetic_fov | 25 | 5.80 | 5.5 | 8.49 | 14 |
| laser | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 25 | 5.70 | 6.2 | 8.48 | 10 |
| laser | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 25 | 5.14 | 4.8 | 8.48 | 13 |
| laser | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 25 | 4.92 | 4.8 | 8.42 | 12 |
| laser | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.47 | 1.4 | 8.12 | 6 |
| laser | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.96 | 2.1 | 8.36 | 6 |
| laser | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 10 | 7.69 | 10.8 | 8.69 | 16 |
| laser | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 25 | 4.05 | 3.6 | 8.42 | 14 |
| laser | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 10 | 6.49 | 7.7 | 8.48 | 16 |
| laser | apartment_1/loop_2.0hz_s1/synthetic_fov | 25 | 6.07 | 6.3 | 8.45 | 11 |
| laser | hotel_0/loop_2.0hz_s0/synthetic_fov | 25 | 3.85 | 3.5 | 8.40 | 11 |
| laser | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 4.81 | 4.0 | 8.36 | 13 |
| laser | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 3.67 | 3.0 | 8.40 | 3 |
| laser | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 4.63 | 4.1 | 8.40 | 14 |
| laser | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.32 | 1.2 | 8.04 | 4 |
| laser | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.29 | 1.2 | 8.04 | 2 |
| laser | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 6.18 | 6.3 | 8.56 | 10 |
| laser | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 3.55 | 2.9 | 8.40 | 11 |
| laser | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 5.77 | 6.3 | 8.42 | 14 |
| laser | hotel_0/loop_2.0hz_s1/synthetic_fov | 25 | 4.82 | 4.2 | 8.39 | 14 |
| laser | apartment_0/loop_2.0hz_s0/synthetic_fov | 25 | 5.79 | 6.2 | 8.46 | 13 |
| laser | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 6.04 | 6.8 | 8.52 | 11 |
| laser | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 5.31 | 5.8 | 8.48 | 12 |
| laser | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 5.83 | 6.4 | 8.48 | 12 |
| laser | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.87 | 2.1 | 8.36 | 6 |
| laser | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 2.18 | 2.2 | 8.33 | 8 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 5.09 | 5.2 | 70.36 | 12 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 1.92 | 2.2 | 70.23 | 8 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 7.11 | 11.8 | 70.49 | 18 |
| laser | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 7.83 | 12.4 | 8.62 | 19 |
| laser | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 4.40 | 5.1 | 8.42 | 13 |
| laser | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 7.37 | 11.6 | 8.59 | 10 |
| laser | apartment_0/loop_2.0hz_s1/synthetic_fov | 25 | 5.83 | 6.3 | 8.52 | 11 |
| panovggt | office_4/synthetic_2.0hz/pano | 25 | 2.66 | 6.4 | 82.39 | 34 |
| panovggt | office_4/synthetic_0.5hz/pano | 100 | 1.17 | 1.1 | 74.28 | 10 |
| panovggt | office_4/synthetic_5.0hz/pano | 10 | 2.49 | 31.4 | 96.01 | 62 |
| panovggt | frl_apartment_0/loop_2.0hz_s0/pano | 25 | 2.60 | 23.4 | 32.79 | 57 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s1/pano | 25 | 2.78 | 13.6 | 24.71 | 50 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s1/pano | 25 | 2.74 | 8.0 | 20.78 | 40 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s0/pano | 25 | 2.66 | 21.3 | 29.23 | 57 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s0/pano | 100 | 1.69 | 1.7 | 13.50 | 16 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s1/pano | 100 | 1.31 | 1.2 | 12.86 | 11 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s1/pano | 10 | 2.40 | 40.6 | 37.29 | 69 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s0/pano | 25 | 2.74 | 14.0 | 25.30 | 47 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s0/pano | 10 | 1.97 | 76.4 | 48.50 | 75 |
| panovggt | frl_apartment_0/loop_2.0hz_s1/pano | 25 | 2.79 | 12.5 | 24.12 | 49 |
| panovggt | apartment_1/loop_2.0hz_s0/pano | 25 | 2.77 | 15.3 | 26.09 | 50 |
| panovggt | apartment_1/stopgo_2.0hz_s1/pano | 25 | 2.80 | 17.7 | 27.27 | 55 |
| panovggt | apartment_1/synthetic_2.0hz_s1/pano | 25 | 2.88 | 11.2 | 23.34 | 45 |
| panovggt | apartment_1/stopgo_2.0hz_s0/pano | 25 | 2.77 | 10.6 | 24.24 | 45 |
| panovggt | apartment_1/synthetic_0.5hz_s0/pano | 100 | 1.11 | 0.9 | 12.20 | 8 |
| panovggt | apartment_1/synthetic_0.5hz_s1/pano | 100 | 1.49 | 1.5 | 13.51 | 14 |
| panovggt | apartment_1/synthetic_5.0hz_s1/pano | 10 | 2.15 | 60.8 | 43.99 | 75 |
| panovggt | apartment_1/synthetic_2.0hz_s0/pano | 25 | 2.51 | 5.8 | 19.87 | 31 |
| panovggt | apartment_1/synthetic_5.0hz_s0/pano | 10 | 2.56 | 28.0 | 32.38 | 61 |
| panovggt | apartment_1/loop_2.0hz_s1/pano | 25 | 2.78 | 19.7 | 28.44 | 57 |
| panovggt | hotel_0/loop_2.0hz_s0/pano | 25 | 2.53 | 5.3 | 19.21 | 30 |
| panovggt | hotel_0/stopgo_2.0hz_s1/pano | 25 | 2.76 | 8.6 | 21.18 | 41 |
| panovggt | hotel_0/synthetic_2.0hz_s1/pano | 25 | 2.44 | 4.4 | 18.11 | 26 |
| panovggt | hotel_0/stopgo_2.0hz_s0/pano | 25 | 2.69 | 8.1 | 20.78 | 38 |
| panovggt | hotel_0/synthetic_0.5hz_s0/pano | 100 | 0.93 | 0.8 | 11.76 | 8 |
| panovggt | hotel_0/synthetic_0.5hz_s1/pano | 100 | 0.97 | 0.8 | 11.76 | 8 |
| panovggt | hotel_0/synthetic_5.0hz_s1/pano | 10 | 2.72 | 20.6 | 28.64 | 57 |
| panovggt | hotel_0/synthetic_2.0hz_s0/pano | 25 | 2.23 | 4.0 | 16.84 | 26 |
| panovggt | hotel_0/synthetic_5.0hz_s0/pano | 10 | 2.74 | 19.0 | 27.86 | 56 |
| panovggt | hotel_0/loop_2.0hz_s1/pano | 25 | 2.79 | 8.8 | 21.37 | 41 |
| panovggt | apartment_0/loop_2.0hz_s0/pano | 25 | 2.65 | 16.9 | 29.07 | 50 |
| panovggt | apartment_0/stopgo_2.0hz_s1/pano | 25 | 2.74 | 20.7 | 29.04 | 57 |
| panovggt | apartment_0/synthetic_2.0hz_s1/pano | 25 | 2.87 | 13.6 | 25.10 | 50 |
| panovggt | apartment_0/stopgo_2.0hz_s0/pano | 25 | 2.77 | 17.6 | 27.27 | 55 |
| panovggt | apartment_0/synthetic_0.5hz_s0/pano | 100 | 1.53 | 1.5 | 13.51 | 14 |
| panovggt | apartment_0/synthetic_0.5hz_s1/pano | 100 | 1.64 | 1.7 | 13.50 | 16 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 25 | 2.59 | 11.6 | 85.39 | 44 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 100 | 1.34 | 1.6 | 75.57 | 15 |
| panovggt | apartment_0/synthetic_5.0hz/pano | 10 | 2.47 | 0.0 | 101.68 | 83 |
| panovggt | apartment_0/synthetic_5.0hz_s1/pano | 10 | 2.00 | 74.3 | 48.11 | 75 |
| panovggt | apartment_0/synthetic_2.0hz_s0/pano | 25 | 2.76 | 11.1 | 23.34 | 45 |
| panovggt | apartment_0/synthetic_5.0hz_s0/pano | 10 | 2.08 | 58.1 | 43.58 | 69 |
| panovggt | apartment_0/loop_2.0hz_s1/pano | 25 | 2.79 | 17.4 | 27.27 | 54 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 25 | 3.17 | 14.3 | 9.02 | 2 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 100 | 0.92 | 12.8 | 8.31 | 4 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 10 | 7.94 | 14.2 | 9.02 | 3 |
| vggtslam | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 25 | 6.04 | 15.6 | 9.02 | 4 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 5.10 | 13.6 | 9.02 | 4 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 3.77 | 13.6 | 9.02 | 4 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 6.41 | 13.9 | 9.02 | 2 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.43 | 12.6 | 8.60 | 0 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.08 | 12.5 | 8.31 | 1 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 8.89 | 14.2 | 9.02 | 4 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 4.95 | 14.5 | 9.02 | 2 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 11.34 | 15.6 | 9.02 | 4 |
| vggtslam | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 25 | 4.58 | 14.6 | 9.02 | 3 |
| vggtslam | apartment_1/loop_2.0hz_s0/synthetic_fov | 25 | 5.02 | 15.0 | 9.02 | 2 |
| vggtslam | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 25 | 5.28 | 15.5 | 9.02 | 3 |
| vggtslam | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 25 | 4.35 | 14.6 | 9.02 | 8 |
| vggtslam | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 25 | 4.26 | 14.1 | 9.02 | 2 |
| vggtslam | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 100 | 0.88 | 12.4 | 8.17 | 2 |
| vggtslam | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.20 | 13.6 | 8.89 | 1 |
| vggtslam | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 10 | 9.79 | 16.0 | 9.02 | 11 |
| vggtslam | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 25 | 2.98 | 14.3 | 9.02 | 4 |
| vggtslam | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 10 | 6.57 | 16.0 | 9.02 | 6 |
| vggtslam | apartment_1/loop_2.0hz_s1/synthetic_fov | 25 | 5.26 | 16.5 | 9.02 | 6 |
| vggtslam | hotel_0/loop_2.0hz_s0/synthetic_fov | 25 | 2.80 | 14.1 | 9.02 | 6 |
| vggtslam | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 3.61 | 14.5 | 9.02 | 8 |
| vggtslam | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 2.56 | 13.7 | 9.02 | 6 |
| vggtslam | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 3.86 | 13.3 | 9.02 | 3 |
| vggtslam | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 0.75 | 12.2 | 7.53 | 3 |
| vggtslam | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 0.73 | 12.5 | 8.17 | 3 |
| vggtslam | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 5.76 | 15.0 | 9.02 | 3 |
| vggtslam | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 2.52 | 13.2 | 9.02 | 6 |
| vggtslam | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 5.86 | 14.3 | 9.02 | 3 |
| vggtslam | hotel_0/loop_2.0hz_s1/synthetic_fov | 25 | 3.65 | 14.8 | 9.02 | 7 |
| vggtslam | apartment_0/loop_2.0hz_s0/synthetic_fov | 25 | 5.13 | 15.5 | 9.02 | 2 |
| vggtslam | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 6.11 | 14.4 | 9.02 | 5 |
| vggtslam | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 4.67 | 15.1 | 9.02 | 3 |
| vggtslam | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 5.84 | 13.9 | 9.02 | 2 |
| vggtslam | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.25 | 13.0 | 8.75 | 3 |
| vggtslam | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.32 | 13.7 | 9.02 | 5 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 4.27 | 14.9 | 9.02 | 2 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 1.24 | 13.2 | 8.75 | 2 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 8.23 | 19.1 | 101.40 | 6 |
| vggtslam | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 10.57 | 16.5 | 9.02 | 4 |
| vggtslam | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 3.91 | 16.4 | 9.02 | 4 |
| vggtslam | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 9.42 | 16.4 | 9.02 | 5 |
| vggtslam | apartment_0/loop_2.0hz_s1/synthetic_fov | 25 | 4.93 | 16.3 | 9.02 | 4 |
| prism_sl4 | office_4/synthetic_2.0hz/pano | 25 | 2.88 | 5.6 | 85.90 | 25 |
| prism_sl4 | office_4/synthetic_0.5hz/pano | 100 | 0.72 | 3.1 | 87.63 | 11 |
| prism_sl4 | office_4/synthetic_5.0hz/pano | 10 | 4.57 | 15.2 | 86.01 | 45 |
| prism_sl4 | apartment_0/synthetic_2.0hz/pano | 25 | 3.08 | 10.5 | 86.01 | 31 |
| prism_sl4 | apartment_0/synthetic_0.5hz/pano | 100 | 1.13 | 5.3 | 91.76 | 16 |
| prism_sl4 | apartment_0/synthetic_5.0hz/pano | 10 | 4.60 | 24.5 | 86.49 | 50 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 25 | 4.43 | 2.5 | 97.29 | 25 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 100 | 1.59 | 0.8 | 78.03 | 7 |
| pi3 | office_4/synthetic_5.0hz/synthetic_fov | 10 | 12.60 | 0.0 | 102.14 | 18 |
| pi3 | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 25 | 5.98 | 6.9 | 32.89 | 39 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 5.48 | 4.3 | 35.68 | 31 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 4.69 | 2.9 | 38.83 | 21 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 5.76 | 6.3 | 31.50 | 39 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 2.18 | 1.1 | 21.05 | 11 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.83 | 0.9 | 18.21 | 10 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 6.03 | 10.9 | 50.82 | 51 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 5.55 | 4.5 | 36.70 | 35 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 5.82 | 19.2 | 86.72 | 59 |
| pi3 | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 25 | 5.46 | 4.1 | 35.48 | 34 |
| pi3 | apartment_1/loop_2.0hz_s0/synthetic_fov | 25 | 5.69 | 4.9 | 38.08 | 34 |
| pi3 | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 25 | 5.93 | 5.4 | 31.98 | 35 |
| pi3 | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 25 | 5.25 | 3.7 | 39.87 | 28 |
| pi3 | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 25 | 5.36 | 3.6 | 38.23 | 31 |
| pi3 | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.42 | 0.8 | 17.15 | 6 |
| pi3 | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 100 | 2.20 | 1.0 | 15.81 | 10 |
| pi3 | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 10 | 6.08 | 15.7 | 70.98 | 58 |
| pi3 | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 25 | 4.34 | 2.3 | 33.99 | 20 |
| pi3 | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 10 | 5.87 | 8.0 | 38.40 | 44 |
| pi3 | apartment_1/loop_2.0hz_s1/synthetic_fov | 25 | 6.08 | 5.9 | 34.28 | 41 |
| pi3 | hotel_0/loop_2.0hz_s0/synthetic_fov | 25 | 4.30 | 2.1 | 32.07 | 22 |
| pi3 | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 5.08 | 3.0 | 39.51 | 23 |
| pi3 | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 4.07 | 1.9 | 29.15 | 20 |
| pi3 | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 4.92 | 2.9 | 38.83 | 30 |
| pi3 | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.26 | 0.7 | 15.39 | 3 |
| pi3 | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.33 | 0.7 | 15.39 | 7 |
| pi3 | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 5.78 | 6.1 | 33.65 | 39 |
| pi3 | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 3.81 | 1.8 | 28.55 | 20 |
| pi3 | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 5.89 | 5.7 | 32.14 | 39 |
| pi3 | hotel_0/loop_2.0hz_s1/synthetic_fov | 25 | 5.04 | 3.1 | 40.47 | 30 |
| pi3 | apartment_0/loop_2.0hz_s0/synthetic_fov | 25 | 5.75 | 5.2 | 31.61 | 37 |
| pi3 | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 5.98 | 6.3 | 34.43 | 40 |
| pi3 | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 5.57 | 4.4 | 36.35 | 30 |
| pi3 | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 5.71 | 5.4 | 31.98 | 39 |
| pi3 | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 2.10 | 1.0 | 15.81 | 10 |
| pi3 | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 2.43 | 1.1 | 21.05 | 7 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 4.95 | 3.8 | 82.57 | 28 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 2.15 | 1.0 | 77.68 | 11 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 6.05 | 15.1 | 69.69 | 55 |
| pi3 | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 5.92 | 19.0 | 85.28 | 61 |
| pi3 | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 5.12 | 3.7 | 39.87 | 31 |
| pi3 | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 5.84 | 15.3 | 69.69 | 55 |
| pi3 | apartment_0/loop_2.0hz_s1/synthetic_fov | 25 | 5.82 | 5.4 | 31.98 | 40 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s0/pano | 25 | 3.77 | 16.2 | 15.28 | 42 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.41 | 11.3 | 13.94 | 37 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 25 | 3.09 | 8.1 | 13.77 | 31 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.74 | 15.8 | 14.12 | 43 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 100 | 1.35 | 4.1 | 18.25 | 15 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 100 | 1.03 | 4.1 | 18.10 | 14 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 10 | 4.78 | 17.9 | 13.81 | 49 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 25 | 3.39 | 12.0 | 13.90 | 34 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 10 | 4.99 | 27.2 | 14.82 | 53 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s1/pano | 25 | 3.52 | 10.0 | 13.94 | 34 |
| prism_sim3 | apartment_1/loop_2.0hz_s0/pano | 25 | 5.37 | 0.0 | 14.42 | 21 |
| prism_sim3 | apartment_1/stopgo_2.0hz_s1/pano | 25 | 3.41 | 14.7 | 15.93 | 39 |
| prism_sim3 | apartment_1/synthetic_2.0hz_s1/pano | 25 | 3.19 | 11.0 | 19.43 | 35 |
| prism_sim3 | apartment_1/stopgo_2.0hz_s0/pano | 25 | 4.04 | 0.0 | 14.42 | 27 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s0/pano | 100 | 0.84 | 3.5 | 15.76 | 11 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s1/pano | 100 | 1.19 | 4.4 | 17.41 | 17 |
| prism_sim3 | apartment_1/synthetic_5.0hz_s1/pano | 10 | 3.50 | 37.6 | 24.34 | 42 |
| prism_sim3 | apartment_1/synthetic_2.0hz_s0/pano | 25 | 3.06 | 0.0 | 14.25 | 25 |
| prism_sim3 | apartment_1/synthetic_5.0hz_s0/pano | 10 | 6.66 | 0.0 | 13.94 | 27 |
| prism_sim3 | apartment_1/loop_2.0hz_s1/pano | 25 | 3.71 | 14.8 | 15.27 | 42 |
| prism_sim3 | hotel_0/loop_2.0hz_s0/pano | 25 | 2.91 | 0.0 | 13.70 | 26 |
| prism_sim3 | hotel_0/stopgo_2.0hz_s1/pano | 25 | 3.94 | 0.0 | 13.94 | 25 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s1/pano | 25 | 2.45 | 5.1 | 13.94 | 23 |
| prism_sim3 | hotel_0/stopgo_2.0hz_s0/pano | 25 | 3.42 | 0.0 | 13.57 | 29 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s0/pano | 100 | 0.71 | 3.3 | 14.91 | 10 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s1/pano | 100 | 0.66 | 3.8 | 16.03 | 11 |
| prism_sim3 | hotel_0/synthetic_5.0hz_s1/pano | 10 | 5.81 | 0.0 | 13.57 | 28 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s0/pano | 25 | 2.44 | 4.0 | 13.70 | 18 |
| prism_sim3 | hotel_0/synthetic_5.0hz_s0/pano | 10 | 4.85 | 0.0 | 13.94 | 38 |
| prism_sim3 | hotel_0/loop_2.0hz_s1/pano | 25 | 3.13 | 8.4 | 13.74 | 32 |
| prism_sim3 | apartment_0/loop_2.0hz_s0/pano | 25 | 3.41 | 14.5 | 14.87 | 40 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.66 | 14.9 | 15.03 | 39 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s1/pano | 25 | 3.01 | 14.5 | 16.53 | 35 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.46 | 14.4 | 18.90 | 39 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s0/pano | 100 | 1.15 | 5.2 | 19.69 | 16 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s1/pano | 100 | 1.33 | 4.5 | 17.54 | 16 |
| prism_sim3 | apartment_0/synthetic_5.0hz_s1/pano | 10 | 11.71 | 0.0 | 13.63 | 19 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s0/pano | 25 | 3.15 | 10.8 | 13.94 | 33 |
| prism_sim3 | apartment_0/synthetic_5.0hz_s0/pano | 10 | 4.58 | 25.1 | 14.53 | 48 |
| prism_sim3 | apartment_0/loop_2.0hz_s1/pano | 25 | 3.28 | 15.7 | 15.19 | 39 |
| prism | office_4/synthetic_2.0hz/pano | 25 | 2.05 | 6.0 | 75.81 | 17 |
| prism | office_4/synthetic_0.5hz/pano | 100 | 0.88 | 3.0 | 77.44 | 10 |
| prism | office_4/synthetic_5.0hz/pano | 10 | 4.51 | 15.4 | 75.74 | 39 |
| prism | frl_apartment_0/loop_2.0hz_s0/pano | 25 | 3.91 | 16.0 | 14.39 | 42 |
| prism | frl_apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.40 | 11.5 | 13.94 | 38 |
| prism | frl_apartment_0/synthetic_2.0hz_s1/pano | 25 | 2.98 | 8.2 | 13.94 | 30 |
| prism | frl_apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.81 | 14.9 | 13.94 | 40 |
| prism | frl_apartment_0/synthetic_0.5hz_s0/pano | 100 | 1.37 | 4.2 | 18.28 | 15 |
| prism | frl_apartment_0/synthetic_0.5hz_s1/pano | 100 | 1.02 | 4.1 | 18.10 | 15 |
| prism | frl_apartment_0/synthetic_5.0hz_s1/pano | 10 | 4.75 | 18.2 | 13.94 | 47 |
| prism | frl_apartment_0/synthetic_2.0hz_s0/pano | 25 | 3.38 | 11.4 | 13.77 | 36 |
| prism | frl_apartment_0/synthetic_5.0hz_s0/pano | 10 | 5.27 | 25.8 | 13.94 | 53 |
| prism | frl_apartment_0/loop_2.0hz_s1/pano | 25 | 3.46 | 10.1 | 13.94 | 37 |
| prism | apartment_1/loop_2.0hz_s0/pano | 25 | 5.52 | 0.0 | 14.38 | 23 |
| prism | apartment_1/stopgo_2.0hz_s1/pano | 25 | 3.38 | 15.1 | 15.35 | 37 |
| prism | apartment_1/synthetic_2.0hz_s1/pano | 25 | 2.70 | 14.3 | 17.57 | 34 |
| prism | apartment_1/stopgo_2.0hz_s0/pano | 25 | 4.05 | 0.0 | 14.42 | 31 |
| prism | apartment_1/synthetic_0.5hz_s0/pano | 100 | 0.84 | 3.6 | 15.76 | 12 |
| prism | apartment_1/synthetic_0.5hz_s1/pano | 100 | 1.20 | 4.4 | 17.41 | 18 |
| prism | apartment_1/synthetic_5.0hz_s1/pano | 10 | 4.49 | 27.6 | 16.31 | 51 |
| prism | apartment_1/synthetic_2.0hz_s0/pano | 25 | 2.96 | 0.0 | 14.31 | 22 |
| prism | apartment_1/synthetic_5.0hz_s0/pano | 10 | 7.03 | 0.0 | 13.94 | 30 |
| prism | apartment_1/loop_2.0hz_s1/pano | 25 | 3.12 | 19.6 | 18.87 | 39 |
| prism | hotel_0/loop_2.0hz_s0/pano | 25 | 2.95 | 0.0 | 13.70 | 24 |
| prism | hotel_0/stopgo_2.0hz_s1/pano | 25 | 3.85 | 0.0 | 13.87 | 21 |
| prism | hotel_0/synthetic_2.0hz_s1/pano | 25 | 2.43 | 5.3 | 13.94 | 19 |
| prism | hotel_0/stopgo_2.0hz_s0/pano | 25 | 3.56 | 0.0 | 13.70 | 31 |
| prism | hotel_0/synthetic_0.5hz_s0/pano | 100 | 0.72 | 3.3 | 14.91 | 14 |
| prism | hotel_0/synthetic_0.5hz_s1/pano | 100 | 0.70 | 3.7 | 16.03 | 13 |
| prism | hotel_0/synthetic_5.0hz_s1/pano | 10 | 5.82 | 0.0 | 13.70 | 29 |
| prism | hotel_0/synthetic_2.0hz_s0/pano | 25 | 2.46 | 4.0 | 13.53 | 17 |
| prism | hotel_0/synthetic_5.0hz_s0/pano | 10 | 4.89 | 0.0 | 13.81 | 39 |
| prism | hotel_0/loop_2.0hz_s1/pano | 25 | 2.23 | 15.5 | 29.78 | 34 |
| prism | apartment_0/loop_2.0hz_s0/pano | 25 | 3.28 | 15.0 | 14.73 | 36 |
| prism | apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.50 | 16.1 | 15.64 | 39 |
| prism | apartment_0/synthetic_2.0hz_s1/pano | 25 | 3.00 | 14.2 | 15.82 | 34 |
| prism | apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.48 | 14.4 | 13.94 | 41 |
| prism | apartment_0/synthetic_0.5hz_s0/pano | 100 | 1.14 | 5.2 | 19.69 | 15 |
| prism | apartment_0/synthetic_0.5hz_s1/pano | 100 | 1.30 | 4.5 | 17.54 | 18 |
| prism | apartment_0/synthetic_2.0hz/pano | 25 | 3.10 | 10.9 | 75.81 | 33 |
| prism | apartment_0/synthetic_0.5hz/pano | 100 | 1.10 | 5.2 | 81.56 | 17 |
| prism | apartment_0/synthetic_5.0hz/pano | 10 | 4.53 | 25.6 | 76.39 | 48 |
| prism | apartment_0/synthetic_5.0hz_s1/pano | 10 | 5.15 | 25.7 | 13.63 | 52 |
| prism | apartment_0/synthetic_2.0hz_s0/pano | 25 | 2.87 | 11.3 | 13.94 | 32 |
| prism | apartment_0/synthetic_5.0hz_s0/pano | 10 | 4.68 | 25.2 | 15.06 | 50 |
| prism | apartment_0/loop_2.0hz_s1/pano | 25 | 3.30 | 16.3 | 16.72 | 41 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 25 | 2.87 | 5.9 | 13.94 | 29 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 100 | 0.90 | 3.1 | 15.57 | 9 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 10 | 4.49 | 15.6 | 13.77 | 43 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s0/pano | 25 | 3.90 | 15.8 | 14.39 | 43 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.45 | 11.5 | 13.94 | 40 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.82 | 14.9 | 13.91 | 42 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s1/pano | 25 | 3.48 | 10.1 | 13.84 | 34 |
| prism_nostill | apartment_1/loop_2.0hz_s0/pano | 25 | 5.56 | 0.0 | 14.42 | 23 |
| prism_nostill | apartment_1/stopgo_2.0hz_s1/pano | 25 | 3.42 | 15.0 | 18.97 | 41 |
| prism_nostill | apartment_1/stopgo_2.0hz_s0/pano | 25 | 3.94 | 0.0 | 14.42 | 31 |
| prism_nostill | apartment_1/loop_2.0hz_s1/pano | 25 | 3.12 | 19.0 | 18.91 | 40 |
| prism_nostill | hotel_0/loop_2.0hz_s0/pano | 25 | 3.02 | 0.0 | 13.63 | 22 |
| prism_nostill | hotel_0/stopgo_2.0hz_s1/pano | 25 | 3.64 | 0.0 | 13.91 | 22 |
| prism_nostill | hotel_0/stopgo_2.0hz_s0/pano | 25 | 3.55 | 0.0 | 13.60 | 30 |
| prism_nostill | hotel_0/loop_2.0hz_s1/pano | 25 | 2.21 | 15.4 | 29.78 | 32 |
| prism_nostill | apartment_0/loop_2.0hz_s0/pano | 25 | 3.51 | 14.5 | 14.70 | 38 |
| prism_nostill | apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.58 | 16.1 | 15.64 | 38 |
| prism_nostill | apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.46 | 14.4 | 13.94 | 40 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 25 | 3.23 | 10.8 | 13.94 | 33 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 100 | 1.09 | 5.2 | 19.69 | 14 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 10 | 4.08 | 29.2 | 14.53 | 45 |
| prism_nostill | apartment_0/loop_2.0hz_s1/pano | 25 | 3.21 | 16.4 | 16.72 | 40 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 25 | 2.78 | 6.1 | 13.74 | 19 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 100 | 0.88 | 3.0 | 15.57 | 15 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 10 | 4.66 | 15.9 | 13.87 | 44 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s0/pano | 25 | 3.95 | 15.7 | 14.36 | 39 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.45 | 11.4 | 13.94 | 35 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.76 | 14.9 | 13.94 | 40 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s1/pano | 25 | 3.49 | 10.0 | 13.84 | 34 |
| prism_nolock | apartment_1/loop_2.0hz_s0/pano | 25 | 5.45 | 0.0 | 14.42 | 24 |
| prism_nolock | apartment_1/stopgo_2.0hz_s1/pano | 25 | 3.43 | 15.0 | 14.70 | 38 |
| prism_nolock | apartment_1/stopgo_2.0hz_s0/pano | 25 | 4.07 | 0.0 | 14.28 | 31 |
| prism_nolock | apartment_1/loop_2.0hz_s1/pano | 25 | 3.15 | 19.4 | 18.91 | 40 |
| prism_nolock | hotel_0/loop_2.0hz_s0/pano | 25 | 2.91 | 0.0 | 13.70 | 25 |
| prism_nolock | hotel_0/stopgo_2.0hz_s1/pano | 25 | 3.94 | 0.0 | 13.94 | 24 |
| prism_nolock | hotel_0/stopgo_2.0hz_s0/pano | 25 | 3.33 | 0.0 | 13.57 | 28 |
| prism_nolock | hotel_0/loop_2.0hz_s1/pano | 25 | 2.22 | 15.5 | 29.78 | 33 |
| prism_nolock | apartment_0/loop_2.0hz_s0/pano | 25 | 3.33 | 14.6 | 14.73 | 38 |
| prism_nolock | apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.51 | 16.1 | 15.64 | 40 |
| prism_nolock | apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.51 | 14.3 | 13.94 | 40 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 25 | 3.12 | 11.2 | 14.06 | 34 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 100 | 1.10 | 5.2 | 19.69 | 20 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 10 | 4.08 | 29.4 | 15.62 | 46 |
| prism_nolock | apartment_0/loop_2.0hz_s1/pano | 25 | 3.26 | 16.3 | 16.72 | 39 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 25 | 1.94 | 6.3 | 91.19 | 7 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 100 | 0.81 | 1.5 | 93.22 | 3 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 10 | 3.88 | 15.2 | 94.41 | 15 |
| mapanything | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 25 | 3.70 | 12.6 | 65.12 | 13 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 3.22 | 8.9 | 49.89 | 11 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 2.63 | 6.4 | 39.01 | 8 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 3.61 | 11.8 | 61.89 | 13 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.20 | 2.2 | 18.60 | 4 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 0.97 | 1.7 | 13.76 | 3 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 3.95 | 17.4 | 70.13 | 17 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 3.28 | 9.2 | 51.46 | 10 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 4.34 | 26.2 | 71.49 | 21 |
| mapanything | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 25 | 3.16 | 8.5 | 48.02 | 11 |
| mapanything | apartment_1/loop_2.0hz_s0/synthetic_fov | 25 | 3.44 | 9.7 | 53.64 | 11 |
| mapanything | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 25 | 3.42 | 10.5 | 56.60 | 12 |
| mapanything | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 25 | 3.13 | 8.0 | 45.91 | 10 |
| mapanything | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 25 | 3.05 | 7.7 | 44.56 | 9 |
| mapanything | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 100 | 0.81 | 1.4 | 12.73 | 1 |
| mapanything | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.13 | 2.0 | 13.27 | 3 |
| mapanything | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 10 | 4.30 | 22.6 | 70.76 | 20 |
| mapanything | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 25 | 2.44 | 5.2 | 33.74 | 9 |
| mapanything | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 10 | 3.85 | 14.0 | 69.06 | 15 |
| mapanything | apartment_1/loop_2.0hz_s1/synthetic_fov | 25 | 3.65 | 11.3 | 60.02 | 13 |
| mapanything | hotel_0/loop_2.0hz_s0/synthetic_fov | 25 | 2.34 | 4.9 | 32.09 | 6 |
| mapanything | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 2.82 | 6.6 | 40.10 | 8 |
| mapanything | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 2.01 | 4.3 | 27.98 | 6 |
| mapanything | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 2.74 | 6.4 | 39.01 | 8 |
| mapanything | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 0.68 | 1.2 | 10.05 | 3 |
| mapanything | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 0.67 | 1.2 | 14.18 | 3 |
| mapanything | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 3.57 | 11.4 | 60.31 | 13 |
| mapanything | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 2.06 | 4.1 | 21.54 | 5 |
| mapanything | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 3.51 | 10.9 | 58.47 | 12 |
| mapanything | hotel_0/loop_2.0hz_s1/synthetic_fov | 25 | 2.76 | 6.7 | 40.58 | 9 |
| mapanything | apartment_0/loop_2.0hz_s0/synthetic_fov | 25 | 3.47 | 10.4 | 56.04 | 13 |
| mapanything | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 25 | 3.66 | 11.7 | 61.36 | 14 |
| mapanything | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 25 | 3.32 | 9.1 | 50.92 | 10 |
| mapanything | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 25 | 3.49 | 10.5 | 56.60 | 13 |
| mapanything | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 100 | 1.16 | 2.0 | 18.35 | 4 |
| mapanything | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 100 | 1.24 | 2.3 | 15.12 | 3 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 25 | 2.91 | 8.0 | 92.13 | 10 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 100 | 1.11 | 2.1 | 76.19 | 4 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 10 | 4.14 | 22.2 | 96.28 | 19 |
| mapanything | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10 | 4.40 | 26.1 | 71.39 | 22 |
| mapanything | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 25 | 2.83 | 8.0 | 45.91 | 9 |
| mapanything | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 10 | 4.32 | 22.4 | 70.89 | 20 |
| mapanything | apartment_0/loop_2.0hz_s1/synthetic_fov | 25 | 3.52 | 10.5 | 56.60 | 12 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 25 | 3.07 | 6.0 | 13.87 | 23 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 100 | 0.93 | 3.1 | 15.57 | 14 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 10 | 4.46 | 15.2 | 13.94 | 45 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s0/pano | 25 | 3.82 | 15.8 | 14.39 | 41 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.38 | 11.6 | 13.94 | 39 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.80 | 14.8 | 13.94 | 41 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s1/pano | 25 | 3.55 | 10.0 | 13.94 | 35 |
| prism_noguards | apartment_1/loop_2.0hz_s0/pano | 25 | 5.05 | 0.0 | 14.42 | 20 |
| prism_noguards | apartment_1/stopgo_2.0hz_s1/pano | 25 | 3.50 | 14.3 | 14.25 | 40 |
| prism_noguards | apartment_1/stopgo_2.0hz_s0/pano | 25 | 3.93 | 0.0 | 14.25 | 27 |
| prism_noguards | apartment_1/loop_2.0hz_s1/pano | 25 | 3.05 | 19.5 | 18.41 | 39 |
| prism_noguards | hotel_0/loop_2.0hz_s0/pano | 25 | 2.78 | 0.0 | 13.70 | 21 |
| prism_noguards | hotel_0/stopgo_2.0hz_s1/pano | 25 | 3.98 | 0.0 | 13.94 | 21 |
| prism_noguards | hotel_0/stopgo_2.0hz_s0/pano | 25 | 3.52 | 0.0 | 13.70 | 31 |
| prism_noguards | hotel_0/loop_2.0hz_s1/pano | 25 | 1.85 | 19.9 | 36.31 | 34 |
| prism_noguards | apartment_0/loop_2.0hz_s0/pano | 25 | 3.38 | 14.6 | 14.73 | 41 |
| prism_noguards | apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.51 | 16.0 | 15.59 | 40 |
| prism_noguards | apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.51 | 14.0 | 13.94 | 38 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 25 | 3.08 | 11.0 | 14.06 | 34 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 100 | 1.12 | 5.2 | 19.69 | 15 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 10 | 4.34 | 28.1 | 14.79 | 47 |
| prism_noguards | apartment_0/loop_2.0hz_s1/pano | 25 | 3.22 | 16.4 | 16.72 | 40 |
| prism_se3 | office_4/synthetic_2.0hz/pano | 25 | 2.64 | 5.8 | 101.17 | 23 |
| prism_se3 | office_4/synthetic_0.5hz/pano | 100 | 0.97 | 0.0 | 102.62 | 1 |
| prism_se3 | office_4/synthetic_5.0hz/pano | 10 | 4.52 | 15.3 | 77.56 | 47 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s0/pano | 25 | 3.88 | 16.1 | 15.22 | 42 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.48 | 11.2 | 13.84 | 36 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 25 | 3.04 | 8.1 | 13.94 | 33 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.71 | 15.7 | 13.94 | 42 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 100 | 1.36 | 4.1 | 18.25 | 15 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 100 | 0.97 | 4.2 | 18.10 | 15 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 10 | 4.77 | 18.0 | 13.81 | 48 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 25 | 3.43 | 12.0 | 13.90 | 37 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 10 | 4.93 | 27.4 | 14.82 | 53 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s1/pano | 25 | 3.47 | 10.1 | 13.94 | 34 |
| prism_se3 | apartment_1/loop_2.0hz_s0/pano | 25 | 5.57 | 0.0 | 14.42 | 28 |
| prism_se3 | apartment_1/stopgo_2.0hz_s1/pano | 25 | 3.30 | 16.2 | 16.34 | 40 |
| prism_se3 | apartment_1/synthetic_2.0hz_s1/pano | 25 | 3.19 | 11.0 | 19.36 | 35 |
| prism_se3 | apartment_1/stopgo_2.0hz_s0/pano | 25 | 4.02 | 0.0 | 14.42 | 28 |
| prism_se3 | apartment_1/synthetic_0.5hz_s0/pano | 100 | 0.86 | 3.6 | 15.76 | 11 |
| prism_se3 | apartment_1/synthetic_0.5hz_s1/pano | 100 | 1.17 | 4.4 | 17.41 | 18 |
| prism_se3 | apartment_1/synthetic_5.0hz_s1/pano | 10 | 3.77 | 34.3 | 24.34 | 46 |
| prism_se3 | apartment_1/synthetic_2.0hz_s0/pano | 25 | 3.12 | 0.0 | 14.42 | 27 |
| prism_se3 | apartment_1/synthetic_5.0hz_s0/pano | 10 | 6.94 | 0.0 | 13.94 | 30 |
| prism_se3 | apartment_1/loop_2.0hz_s1/pano | 25 | 3.63 | 14.8 | 15.25 | 42 |
| prism_se3 | hotel_0/loop_2.0hz_s0/pano | 25 | 2.90 | 0.0 | 13.70 | 22 |
| prism_se3 | hotel_0/stopgo_2.0hz_s1/pano | 25 | 3.95 | 0.0 | 13.94 | 24 |
| prism_se3 | hotel_0/synthetic_2.0hz_s1/pano | 25 | 2.48 | 5.0 | 13.94 | 20 |
| prism_se3 | hotel_0/stopgo_2.0hz_s0/pano | 25 | 3.55 | 0.0 | 13.67 | 28 |
| prism_se3 | hotel_0/synthetic_0.5hz_s0/pano | 100 | 0.74 | 3.3 | 14.91 | 11 |
| prism_se3 | hotel_0/synthetic_0.5hz_s1/pano | 100 | 0.70 | 3.7 | 16.03 | 11 |
| prism_se3 | hotel_0/synthetic_5.0hz_s1/pano | 10 | 5.83 | 0.0 | 13.63 | 29 |
| prism_se3 | hotel_0/synthetic_2.0hz_s0/pano | 25 | 2.55 | 4.1 | 13.57 | 18 |
| prism_se3 | hotel_0/synthetic_5.0hz_s0/pano | 10 | 4.82 | 0.0 | 13.94 | 39 |
| prism_se3 | hotel_0/loop_2.0hz_s1/pano | 25 | 3.14 | 8.4 | 14.91 | 30 |
| prism_se3 | apartment_0/loop_2.0hz_s0/pano | 25 | 3.45 | 14.6 | 14.87 | 40 |
| prism_se3 | apartment_0/stopgo_2.0hz_s1/pano | 25 | 3.81 | 14.6 | 14.42 | 39 |
| prism_se3 | apartment_0/synthetic_2.0hz_s1/pano | 25 | 3.16 | 13.7 | 19.38 | 36 |
| prism_se3 | apartment_0/stopgo_2.0hz_s0/pano | 25 | 3.39 | 14.5 | 18.93 | 39 |
| prism_se3 | apartment_0/synthetic_0.5hz_s0/pano | 100 | 1.14 | 5.2 | 19.69 | 17 |
| prism_se3 | apartment_0/synthetic_0.5hz_s1/pano | 100 | 1.27 | 4.4 | 17.54 | 18 |
| prism_se3 | apartment_0/synthetic_2.0hz/pano | 25 | 3.02 | 11.5 | 84.93 | 32 |
| prism_se3 | apartment_0/synthetic_0.5hz/pano | 100 | 1.11 | 5.2 | 19.69 | 15 |
| prism_se3 | apartment_0/synthetic_5.0hz/pano | 10 | 4.59 | 25.1 | 86.48 | 49 |
| prism_se3 | apartment_0/synthetic_5.0hz_s1/pano | 10 | 4.93 | 27.3 | 16.69 | 53 |
| prism_se3 | apartment_0/synthetic_2.0hz_s0/pano | 25 | 3.16 | 10.8 | 13.84 | 35 |
| prism_se3 | apartment_0/synthetic_5.0hz_s0/pano | 10 | 4.66 | 25.4 | 14.44 | 50 |
| prism_se3 | apartment_0/loop_2.0hz_s1/pano | 25 | 3.14 | 15.6 | 14.84 | 36 |


## Table B — Metric accuracy (absolute scale vs. rendered GT)

| Method | Run | Scale est. | Scale err %↓ | Extent err %↓ |
| --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| laser | office_4/synthetic_0.5hz | N/A (scale-free) | — | — |
| laser | office_4/synthetic_5.0hz | N/A (scale-free) | — | — |
| laser | frl_apartment_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| laser | frl_apartment_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_1/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_1/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_1/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_1/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_1/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_1/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_1/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_1/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_1/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_1/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | hotel_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | hotel_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | hotel_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | hotel_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | hotel_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| laser | hotel_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| laser | hotel_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| laser | hotel_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | hotel_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| laser | hotel_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_0.5hz | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_5.0hz | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| laser | apartment_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| panovggt | office_4/synthetic_0.5hz | N/A (scale-free) | — | — |
| panovggt | office_4/synthetic_5.0hz | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | frl_apartment_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_1/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_1/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_1/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_1/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_1/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_1/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_1/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_1/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_1/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_1/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | hotel_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | hotel_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | hotel_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | hotel_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | hotel_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| panovggt | hotel_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| panovggt | hotel_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | hotel_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | hotel_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | hotel_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_0.5hz | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| panovggt | apartment_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| vggtslam | office_4/synthetic_0.5hz | N/A (scale-free) | — | — |
| vggtslam | office_4/synthetic_5.0hz | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | frl_apartment_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_1/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | hotel_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/loop_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/stopgo_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_2.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/stopgo_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_0.5hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_0.5hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_0.5hz | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_5.0hz | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_5.0hz_s1 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_2.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/synthetic_5.0hz_s0 | N/A (scale-free) | — | — |
| vggtslam | apartment_0/loop_2.0hz_s1 | N/A (scale-free) | — | — |
| prism_sl4 | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| prism_sl4 | office_4/synthetic_0.5hz | N/A (scale-free) | — | — |
| prism_sl4 | office_4/synthetic_5.0hz | N/A (scale-free) | — | — |
| prism_sl4 | apartment_0/synthetic_2.0hz | N/A (scale-free) | — | — |
| prism_sl4 | apartment_0/synthetic_0.5hz | N/A (scale-free) | — | — |
| prism_sl4 | apartment_0/synthetic_5.0hz | N/A (scale-free) | — | — |
| pi3 | office_4/synthetic_2.0hz | 0.863 | 13.7 | 61.5 |
| pi3 | office_4/synthetic_0.5hz | 0.871 | 12.9 | 58.2 |
| pi3 | frl_apartment_0/loop_2.0hz_s0 | 0.962 | 3.8 | 32.0 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s1 | 0.991 | 0.9 | 32.1 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s1 | 0.990 | 1.0 | 32.4 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s0 | 0.973 | 2.7 | 29.7 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s0 | 0.953 | 4.7 | 37.0 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s1 | 0.978 | 2.2 | 32.0 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s1 | 0.976 | 2.4 | 35.0 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s0 | 0.971 | 2.9 | 29.7 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s0 | 0.963 | 3.7 | 31.7 |
| pi3 | frl_apartment_0/loop_2.0hz_s1 | 0.973 | 2.7 | 34.3 |
| pi3 | apartment_1/loop_2.0hz_s0 | 0.945 | 5.5 | 7.9 |
| pi3 | apartment_1/stopgo_2.0hz_s1 | 1.325 | 32.5 | 1.4 |
| pi3 | apartment_1/synthetic_2.0hz_s1 | 1.191 | 19.1 | 0.4 |
| pi3 | apartment_1/stopgo_2.0hz_s0 | 0.873 | 12.7 | 1.3 |
| pi3 | apartment_1/synthetic_0.5hz_s0 | 0.883 | 11.7 | 4.4 |
| pi3 | apartment_1/synthetic_0.5hz_s1 | 1.520 | 52.0 | 4.5 |
| pi3 | apartment_1/synthetic_5.0hz_s1 | 0.943 | 5.7 | 6.6 |
| pi3 | apartment_1/synthetic_2.0hz_s0 | 0.824 | 17.6 | 4.2 |
| pi3 | apartment_1/synthetic_5.0hz_s0 | 0.762 | 23.8 | 2.5 |
| pi3 | apartment_1/loop_2.0hz_s1 | 0.857 | 14.3 | 0.1 |
| pi3 | hotel_0/loop_2.0hz_s0 | 0.978 | 2.2 | 21.5 |
| pi3 | hotel_0/stopgo_2.0hz_s1 | 1.015 | 1.5 | 26.6 |
| pi3 | hotel_0/synthetic_2.0hz_s1 | 1.036 | 3.6 | 27.7 |
| pi3 | hotel_0/stopgo_2.0hz_s0 | 0.916 | 8.4 | 28.3 |
| pi3 | hotel_0/synthetic_0.5hz_s0 | 0.868 | 13.2 | 17.7 |
| pi3 | hotel_0/synthetic_0.5hz_s1 | 0.978 | 2.2 | 28.0 |
| pi3 | hotel_0/synthetic_5.0hz_s1 | 1.083 | 8.3 | 24.9 |
| pi3 | hotel_0/synthetic_2.0hz_s0 | 0.932 | 6.8 | 17.4 |
| pi3 | hotel_0/synthetic_5.0hz_s0 | 0.942 | 5.8 | 26.1 |
| pi3 | hotel_0/loop_2.0hz_s1 | 1.114 | 11.4 | 19.0 |
| pi3 | apartment_0/loop_2.0hz_s0 | 0.945 | 5.5 | 17.9 |
| pi3 | apartment_0/stopgo_2.0hz_s1 | 0.918 | 8.2 | 19.5 |
| pi3 | apartment_0/synthetic_2.0hz_s1 | 0.942 | 5.8 | 14.0 |
| pi3 | apartment_0/stopgo_2.0hz_s0 | 0.937 | 6.3 | 20.8 |
| pi3 | apartment_0/synthetic_0.5hz_s0 | 0.953 | 4.7 | 16.3 |
| pi3 | apartment_0/synthetic_0.5hz_s1 | 0.945 | 5.5 | 12.4 |
| pi3 | apartment_0/synthetic_2.0hz | 0.941 | 5.9 | 18.5 |
| pi3 | apartment_0/synthetic_0.5hz | 0.953 | 4.7 | 16.3 |
| pi3 | apartment_0/synthetic_5.0hz | 0.938 | 6.2 | 19.4 |
| pi3 | apartment_0/synthetic_5.0hz_s1 | 0.942 | 5.8 | 16.6 |
| pi3 | apartment_0/synthetic_2.0hz_s0 | 0.941 | 5.9 | 18.5 |
| pi3 | apartment_0/synthetic_5.0hz_s0 | 0.938 | 6.2 | 19.4 |
| pi3 | apartment_0/loop_2.0hz_s1 | 0.920 | 8.0 | 17.8 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s0 | 0.846 | 15.4 | 34.2 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s1 | 0.993 | 0.7 | 20.0 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s1 | 0.991 | 0.9 | 17.3 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s0 | 0.927 | 7.3 | 17.4 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s0 | 0.990 | 1.0 | 16.5 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s1 | 0.989 | 1.1 | 19.7 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s1 | 0.992 | 0.8 | 18.3 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s0 | 0.927 | 7.3 | 20.3 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s0 | 0.901 | 9.9 | 24.5 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s1 | 0.988 | 1.2 | 22.0 |
| prism_sim3 | apartment_1/stopgo_2.0hz_s1 | 0.321 | 67.9 | 36.2 |
| prism_sim3 | apartment_1/synthetic_2.0hz_s1 | 0.603 | 39.7 | 28.4 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s0 | 0.738 | 26.2 | 12.4 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s1 | 0.650 | 35.0 | 4.1 |
| prism_sim3 | apartment_1/synthetic_5.0hz_s1 | 0.446 | 55.4 | 59.5 |
| prism_sim3 | apartment_1/loop_2.0hz_s1 | 0.472 | 52.8 | 29.1 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s1 | 0.886 | 11.4 | 25.4 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s0 | 0.979 | 2.1 | 20.2 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s1 | 0.999 | 0.1 | 56.1 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s0 | 0.949 | 5.1 | 1.4 |
| prism_sim3 | hotel_0/loop_2.0hz_s1 | 1.209 | 20.9 | 33.4 |
| prism_sim3 | apartment_0/loop_2.0hz_s0 | 0.742 | 25.8 | 4.6 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s1 | 1.035 | 3.5 | 7.4 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s1 | 0.964 | 3.6 | 2.5 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s0 | 1.004 | 0.4 | 2.5 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s0 | 0.886 | 11.4 | 2.0 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s1 | 1.004 | 0.4 | 17.3 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s0 | 0.977 | 2.3 | 2.4 |
| prism_sim3 | apartment_0/synthetic_5.0hz_s0 | 1.034 | 3.4 | 0.5 |
| prism_sim3 | apartment_0/loop_2.0hz_s1 | 0.941 | 5.9 | 7.2 |
| prism | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.6 |
| prism | office_4/synthetic_0.5hz | 1.002 | 0.2 | 4.0 |
| prism | office_4/synthetic_5.0hz | 0.982 | 1.8 | 11.4 |
| prism | frl_apartment_0/loop_2.0hz_s0 | 0.927 | 7.3 | 23.6 |
| prism | frl_apartment_0/stopgo_2.0hz_s1 | 0.982 | 1.8 | 21.3 |
| prism | frl_apartment_0/synthetic_2.0hz_s1 | 0.988 | 1.2 | 18.2 |
| prism | frl_apartment_0/stopgo_2.0hz_s0 | 0.963 | 3.7 | 17.1 |
| prism | frl_apartment_0/synthetic_0.5hz_s0 | 0.989 | 1.1 | 16.8 |
| prism | frl_apartment_0/synthetic_0.5hz_s1 | 0.990 | 1.0 | 19.5 |
| prism | frl_apartment_0/synthetic_5.0hz_s1 | 0.991 | 0.9 | 18.9 |
| prism | frl_apartment_0/synthetic_2.0hz_s0 | 0.965 | 3.5 | 16.1 |
| prism | frl_apartment_0/synthetic_5.0hz_s0 | 0.940 | 6.0 | 19.1 |
| prism | frl_apartment_0/loop_2.0hz_s1 | 0.977 | 2.3 | 22.9 |
| prism | apartment_1/stopgo_2.0hz_s1 | 0.463 | 53.7 | 41.2 |
| prism | apartment_1/synthetic_2.0hz_s1 | 0.481 | 51.9 | 49.1 |
| prism | apartment_1/synthetic_0.5hz_s0 | 0.738 | 26.2 | 12.4 |
| prism | apartment_1/synthetic_0.5hz_s1 | 0.650 | 35.0 | 4.1 |
| prism | apartment_1/synthetic_5.0hz_s1 | 0.547 | 45.3 | 39.0 |
| prism | apartment_1/loop_2.0hz_s1 | 0.506 | 49.4 | 44.0 |
| prism | hotel_0/synthetic_2.0hz_s1 | 0.904 | 9.6 | 25.3 |
| prism | hotel_0/synthetic_0.5hz_s0 | 0.979 | 2.1 | 20.2 |
| prism | hotel_0/synthetic_0.5hz_s1 | 0.999 | 0.1 | 56.2 |
| prism | hotel_0/synthetic_2.0hz_s0 | 0.992 | 0.8 | 0.2 |
| prism | hotel_0/loop_2.0hz_s1 | 0.002 | 99.8 | 264.7 |
| prism | apartment_0/loop_2.0hz_s0 | 0.766 | 23.4 | 5.5 |
| prism | apartment_0/stopgo_2.0hz_s1 | 1.003 | 0.3 | 4.0 |
| prism | apartment_0/synthetic_2.0hz_s1 | 0.953 | 4.7 | 4.1 |
| prism | apartment_0/stopgo_2.0hz_s0 | 0.991 | 0.9 | 0.3 |
| prism | apartment_0/synthetic_0.5hz_s0 | 0.886 | 11.4 | 2.1 |
| prism | apartment_0/synthetic_0.5hz_s1 | 1.004 | 0.4 | 17.3 |
| prism | apartment_0/synthetic_2.0hz | 0.977 | 2.3 | 2.4 |
| prism | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.1 |
| prism | apartment_0/synthetic_5.0hz | 1.034 | 3.4 | 0.6 |
| prism | apartment_0/synthetic_5.0hz_s1 | 1.003 | 0.3 | 10.6 |
| prism | apartment_0/synthetic_2.0hz_s0 | 0.999 | 0.1 | 0.9 |
| prism | apartment_0/synthetic_5.0hz_s0 | 0.969 | 3.1 | 1.7 |
| prism | apartment_0/loop_2.0hz_s1 | 0.939 | 6.1 | 10.8 |
| prism_nostill | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.6 |
| prism_nostill | office_4/synthetic_0.5hz | 1.001 | 0.1 | 4.3 |
| prism_nostill | office_4/synthetic_5.0hz | 0.982 | 1.8 | 12.1 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s0 | 0.927 | 7.3 | 23.5 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s1 | 0.982 | 1.8 | 21.4 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s0 | 0.963 | 3.7 | 17.0 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s1 | 0.978 | 2.2 | 22.9 |
| prism_nostill | apartment_1/stopgo_2.0hz_s1 | 0.464 | 53.6 | 41.5 |
| prism_nostill | apartment_1/loop_2.0hz_s1 | 0.505 | 49.5 | 44.2 |
| prism_nostill | hotel_0/loop_2.0hz_s1 | 0.002 | 99.8 | 264.7 |
| prism_nostill | apartment_0/loop_2.0hz_s0 | 0.766 | 23.4 | 5.7 |
| prism_nostill | apartment_0/stopgo_2.0hz_s1 | 1.003 | 0.3 | 4.1 |
| prism_nostill | apartment_0/stopgo_2.0hz_s0 | 0.991 | 0.9 | 0.4 |
| prism_nostill | apartment_0/synthetic_2.0hz | 0.977 | 2.3 | 2.5 |
| prism_nostill | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.1 |
| prism_nostill | apartment_0/synthetic_5.0hz | 1.034 | 3.4 | 0.6 |
| prism_nostill | apartment_0/loop_2.0hz_s1 | 0.938 | 6.2 | 10.8 |
| prism_nolock | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.7 |
| prism_nolock | office_4/synthetic_0.5hz | 1.002 | 0.2 | 4.1 |
| prism_nolock | office_4/synthetic_5.0hz | 0.991 | 0.9 | 9.8 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s0 | 0.927 | 7.3 | 23.6 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s1 | 0.983 | 1.7 | 21.3 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s0 | 0.963 | 3.7 | 16.9 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s1 | 0.978 | 2.2 | 22.8 |
| prism_nolock | apartment_1/stopgo_2.0hz_s1 | 0.464 | 53.6 | 41.4 |
| prism_nolock | apartment_1/loop_2.0hz_s1 | 0.505 | 49.5 | 44.2 |
| prism_nolock | hotel_0/loop_2.0hz_s1 | 0.002 | 99.8 | 264.4 |
| prism_nolock | apartment_0/loop_2.0hz_s0 | 0.766 | 23.4 | 5.5 |
| prism_nolock | apartment_0/stopgo_2.0hz_s1 | 1.004 | 0.4 | 4.1 |
| prism_nolock | apartment_0/stopgo_2.0hz_s0 | 0.990 | 1.0 | 0.4 |
| prism_nolock | apartment_0/synthetic_2.0hz | 0.967 | 3.3 | 2.5 |
| prism_nolock | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.0 |
| prism_nolock | apartment_0/synthetic_5.0hz | 0.927 | 7.3 | 3.5 |
| prism_nolock | apartment_0/loop_2.0hz_s1 | 0.938 | 6.2 | 10.8 |
| mapanything | office_4/synthetic_2.0hz | 0.978 | 2.2 | 5.4 |
| mapanything | office_4/synthetic_0.5hz | 0.973 | 2.7 | 0.9 |
| mapanything | office_4/synthetic_5.0hz | 0.981 | 1.9 | 6.8 |
| mapanything | frl_apartment_0/loop_2.0hz_s0 | 0.896 | 10.4 | 13.6 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s1 | 0.884 | 11.6 | 26.8 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s1 | 0.880 | 12.0 | 28.6 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s0 | 0.945 | 5.5 | 13.2 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s0 | 0.916 | 8.4 | 23.1 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s1 | 0.833 | 16.7 | 27.5 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s1 | 0.888 | 11.2 | 29.3 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s0 | 0.942 | 5.8 | 13.7 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s0 | 0.944 | 5.6 | 14.0 |
| mapanything | frl_apartment_0/loop_2.0hz_s1 | 0.804 | 19.6 | 26.4 |
| mapanything | apartment_1/loop_2.0hz_s0 | 0.436 | 56.4 | 440.1 |
| mapanything | apartment_1/stopgo_2.0hz_s1 | 0.242 | 75.8 | 4.2 |
| mapanything | apartment_1/synthetic_2.0hz_s1 | 0.310 | 69.0 | 2.7 |
| mapanything | apartment_1/stopgo_2.0hz_s0 | 0.393 | 60.7 | 111.1 |
| mapanything | apartment_1/synthetic_0.5hz_s0 | 0.779 | 22.1 | 15.3 |
| mapanything | apartment_1/synthetic_0.5hz_s1 | 0.401 | 59.9 | 390.2 |
| mapanything | apartment_1/synthetic_5.0hz_s1 | 0.315 | 68.5 | 0.2 |
| mapanything | apartment_1/synthetic_2.0hz_s0 | 0.575 | 42.5 | 87.9 |
| mapanything | apartment_1/synthetic_5.0hz_s0 | 0.589 | 41.1 | 160.0 |
| mapanything | apartment_1/loop_2.0hz_s1 | 0.728 | 27.2 | 0.1 |
| mapanything | hotel_0/loop_2.0hz_s0 | 0.828 | 17.2 | 17.0 |
| mapanything | hotel_0/stopgo_2.0hz_s1 | 0.933 | 6.7 | 32.0 |
| mapanything | hotel_0/synthetic_2.0hz_s1 | 0.953 | 4.7 | 33.5 |
| mapanything | hotel_0/stopgo_2.0hz_s0 | 0.762 | 23.8 | 15.9 |
| mapanything | hotel_0/synthetic_0.5hz_s0 | 0.820 | 18.0 | 12.4 |
| mapanything | hotel_0/synthetic_0.5hz_s1 | 0.856 | 14.4 | 21.7 |
| mapanything | hotel_0/synthetic_5.0hz_s1 | 0.970 | 3.0 | 27.7 |
| mapanything | hotel_0/synthetic_2.0hz_s0 | 0.826 | 17.4 | 13.5 |
| mapanything | hotel_0/synthetic_5.0hz_s0 | 0.848 | 15.2 | 34.0 |
| mapanything | hotel_0/loop_2.0hz_s1 | 0.958 | 4.2 | 34.0 |
| mapanything | apartment_0/loop_2.0hz_s0 | 0.894 | 10.6 | 18.4 |
| mapanything | apartment_0/stopgo_2.0hz_s1 | 0.861 | 13.9 | 22.4 |
| mapanything | apartment_0/synthetic_2.0hz_s1 | 0.862 | 13.8 | 20.2 |
| mapanything | apartment_0/stopgo_2.0hz_s0 | 0.889 | 11.1 | 14.8 |
| mapanything | apartment_0/synthetic_0.5hz_s0 | 0.837 | 16.3 | 14.7 |
| mapanything | apartment_0/synthetic_0.5hz_s1 | 0.884 | 11.6 | 22.1 |
| mapanything | apartment_0/synthetic_2.0hz | 0.891 | 10.9 | 14.8 |
| mapanything | apartment_0/synthetic_0.5hz | 0.837 | 16.3 | 14.7 |
| mapanything | apartment_0/synthetic_5.0hz | 0.901 | 9.9 | 21.6 |
| mapanything | apartment_0/synthetic_5.0hz_s1 | 0.854 | 14.6 | 23.5 |
| mapanything | apartment_0/synthetic_2.0hz_s0 | 0.891 | 10.9 | 14.8 |
| mapanything | apartment_0/synthetic_5.0hz_s0 | 0.901 | 9.9 | 21.6 |
| mapanything | apartment_0/loop_2.0hz_s1 | 0.888 | 11.2 | 17.7 |
| prism_noguards | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.6 |
| prism_noguards | office_4/synthetic_0.5hz | 1.002 | 0.2 | 4.3 |
| prism_noguards | office_4/synthetic_5.0hz | 0.990 | 1.0 | 9.8 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s0 | 0.926 | 7.4 | 23.7 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s1 | 0.983 | 1.7 | 21.3 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s0 | 0.963 | 3.7 | 17.1 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s1 | 0.977 | 2.3 | 22.9 |
| prism_noguards | apartment_1/stopgo_2.0hz_s1 | 0.424 | 57.6 | 27.9 |
| prism_noguards | apartment_1/loop_2.0hz_s1 | 0.539 | 46.1 | 51.1 |
| prism_noguards | hotel_0/loop_2.0hz_s1 | 0.002 | 99.8 | 291.2 |
| prism_noguards | apartment_0/loop_2.0hz_s0 | 0.767 | 23.3 | 5.7 |
| prism_noguards | apartment_0/stopgo_2.0hz_s1 | 0.963 | 3.7 | 2.6 |
| prism_noguards | apartment_0/stopgo_2.0hz_s0 | 0.991 | 0.9 | 0.4 |
| prism_noguards | apartment_0/synthetic_2.0hz | 0.967 | 3.3 | 2.5 |
| prism_noguards | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.1 |
| prism_noguards | apartment_0/synthetic_5.0hz | 0.926 | 7.4 | 3.4 |
| prism_noguards | apartment_0/loop_2.0hz_s1 | 0.935 | 6.5 | 11.3 |
| prism_se3 | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.6 |
| prism_se3 | office_4/synthetic_5.0hz | 0.982 | 1.8 | 12.1 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s0 | 0.846 | 15.4 | 34.2 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s1 | 0.994 | 0.6 | 19.8 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s1 | 0.992 | 0.8 | 17.3 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s0 | 0.927 | 7.3 | 17.3 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s0 | 0.990 | 1.0 | 16.7 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s1 | 0.989 | 1.1 | 19.5 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s1 | 0.992 | 0.8 | 18.4 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s0 | 0.928 | 7.2 | 20.2 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s0 | 0.901 | 9.9 | 24.6 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s1 | 0.988 | 1.2 | 22.1 |
| prism_se3 | apartment_1/stopgo_2.0hz_s1 | 0.374 | 62.6 | 46.9 |
| prism_se3 | apartment_1/synthetic_2.0hz_s1 | 0.601 | 39.9 | 28.1 |
| prism_se3 | apartment_1/synthetic_0.5hz_s0 | 0.738 | 26.2 | 12.4 |
| prism_se3 | apartment_1/synthetic_0.5hz_s1 | 0.650 | 35.0 | 4.1 |
| prism_se3 | apartment_1/synthetic_5.0hz_s1 | 0.446 | 55.4 | 59.5 |
| prism_se3 | apartment_1/loop_2.0hz_s1 | 0.469 | 53.1 | 28.7 |
| prism_se3 | hotel_0/synthetic_2.0hz_s1 | 0.884 | 11.6 | 25.1 |
| prism_se3 | hotel_0/synthetic_0.5hz_s0 | 0.979 | 2.1 | 20.2 |
| prism_se3 | hotel_0/synthetic_0.5hz_s1 | 0.998 | 0.2 | 56.5 |
| prism_se3 | hotel_0/synthetic_2.0hz_s0 | 0.949 | 5.1 | 1.3 |
| prism_se3 | hotel_0/loop_2.0hz_s1 | 1.190 | 19.0 | 37.9 |
| prism_se3 | apartment_0/loop_2.0hz_s0 | 0.742 | 25.8 | 4.7 |
| prism_se3 | apartment_0/stopgo_2.0hz_s1 | 1.030 | 3.0 | 13.1 |
| prism_se3 | apartment_0/synthetic_2.0hz_s1 | 0.962 | 3.8 | 11.0 |
| prism_se3 | apartment_0/stopgo_2.0hz_s0 | 1.016 | 1.6 | 2.2 |
| prism_se3 | apartment_0/synthetic_0.5hz_s0 | 0.886 | 11.4 | 2.1 |
| prism_se3 | apartment_0/synthetic_0.5hz_s1 | 1.004 | 0.4 | 17.3 |
| prism_se3 | apartment_0/synthetic_2.0hz | 0.977 | 2.3 | 2.2 |
| prism_se3 | apartment_0/synthetic_0.5hz | 0.886 | 11.4 | 2.1 |
| prism_se3 | apartment_0/synthetic_5.0hz | 1.035 | 3.5 | 0.5 |
| prism_se3 | apartment_0/synthetic_5.0hz_s1 | 1.022 | 2.2 | 10.7 |
| prism_se3 | apartment_0/synthetic_2.0hz_s0 | 0.977 | 2.3 | 2.4 |
| prism_se3 | apartment_0/synthetic_5.0hz_s0 | 1.035 | 3.5 | 0.5 |
| prism_se3 | apartment_0/loop_2.0hz_s1 | 0.940 | 6.0 | 9.6 |


## Table C — Reconstruction, co-visibility masked (fair)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.0 | 2.8 | 6.8 | 0.870 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 2.6 | 2.5 | 5.0 | 0.956 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 5.6 | 3.0 | 8.6 | 0.792 |
| laser | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 46.3 | 51.5 | 97.8 | 0.086 |
| laser | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 9.5 | 3.8 | 13.3 | 0.615 |
| laser | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 8.5 | 4.2 | 12.7 | 0.629 |
| laser | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 13.1 | 9.9 | 22.9 | 0.495 |
| laser | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 13.3 | 10.6 | 23.9 | 0.401 |
| laser | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 5.8 | 4.5 | 10.3 | 0.771 |
| laser | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 14.0 | 8.6 | 22.6 | 0.449 |
| laser | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 12.6 | 10.7 | 23.3 | 0.460 |
| laser | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 21.4 | 17.4 | 38.9 | 0.314 |
| laser | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 11.0 | 4.2 | 15.2 | 0.542 |
| laser | apartment_1/loop_2.0hz_s0/synthetic_fov | 36.0 | 139.0 | 175.0 | 0.109 |
| laser | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 40.4 | 186.7 | 227.1 | 0.049 |
| laser | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 33.1 | 72.9 | 106.1 | 0.199 |
| laser | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 41.3 | 192.1 | 233.5 | 0.027 |
| laser | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 32.5 | 102.5 | 134.9 | 0.151 |
| laser | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 31.1 | 121.1 | 152.2 | 0.173 |
| laser | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 30.7 | 51.7 | 82.4 | 0.212 |
| laser | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 39.6 | 156.3 | 196.0 | 0.056 |
| laser | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 26.7 | 24.7 | 51.4 | 0.278 |
| laser | apartment_1/loop_2.0hz_s1/synthetic_fov | 31.2 | 59.1 | 90.3 | 0.215 |
| laser | hotel_0/loop_2.0hz_s0/synthetic_fov | 23.2 | 41.9 | 65.0 | 0.169 |
| laser | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 26.1 | 174.7 | 200.7 | 0.070 |
| laser | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 27.6 | 179.9 | 207.5 | 0.070 |
| laser | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 23.0 | 57.4 | 80.4 | 0.214 |
| laser | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 5.6 | 7.9 | 13.5 | 0.619 |
| laser | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 10.9 | 16.6 | 27.5 | 0.353 |
| laser | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 20.0 | 35.1 | 55.0 | 0.190 |
| laser | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 22.8 | 64.8 | 87.7 | 0.226 |
| laser | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 16.9 | 33.6 | 50.6 | 0.374 |
| laser | hotel_0/loop_2.0hz_s1/synthetic_fov | 26.0 | 53.8 | 79.7 | 0.197 |
| laser | apartment_0/loop_2.0hz_s0/synthetic_fov | 32.2 | 48.1 | 80.3 | 0.187 |
| laser | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 9.4 | 5.8 | 15.1 | 0.626 |
| laser | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 11.5 | 8.3 | 19.8 | 0.489 |
| laser | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 10.5 | 7.3 | 17.8 | 0.590 |
| laser | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 7.4 | 4.0 | 11.4 | 0.691 |
| laser | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 6.4 | 6.1 | 12.5 | 0.688 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 9.6 | 6.2 | 15.8 | 0.641 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 7.4 | 4.0 | 11.4 | 0.694 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 11.9 | 6.4 | 18.3 | 0.483 |
| laser | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 20.5 | 13.8 | 34.3 | 0.313 |
| laser | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 9.6 | 6.3 | 15.8 | 0.642 |
| laser | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 11.9 | 6.5 | 18.3 | 0.483 |
| laser | apartment_0/loop_2.0hz_s1/synthetic_fov | 12.0 | 7.4 | 19.4 | 0.483 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.5 | 0.9 | 3.4 | 0.966 |
| panovggt | office_4/synthetic_0.5hz/pano | 2.2 | 1.1 | 3.2 | 0.977 |
| panovggt | office_4/synthetic_5.0hz/pano | 2.9 | 0.8 | 3.7 | 0.950 |
| panovggt | frl_apartment_0/loop_2.0hz_s0/pano | 5.6 | 1.4 | 7.0 | 0.803 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s1/pano | 4.2 | 2.0 | 6.2 | 0.863 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s1/pano | 4.2 | 2.1 | 6.2 | 0.862 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s0/pano | 4.2 | 1.9 | 6.1 | 0.868 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s0/pano | 3.5 | 2.1 | 5.6 | 0.893 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s1/pano | 3.4 | 2.9 | 6.2 | 0.883 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s1/pano | 4.9 | 1.7 | 6.7 | 0.833 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s0/pano | 4.2 | 1.9 | 6.1 | 0.868 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s0/pano | 5.1 | 1.8 | 6.9 | 0.830 |
| panovggt | frl_apartment_0/loop_2.0hz_s1/pano | 4.3 | 2.1 | 6.4 | 0.853 |
| panovggt | apartment_1/loop_2.0hz_s0/pano | 39.4 | 135.3 | 174.7 | 0.090 |
| panovggt | apartment_1/stopgo_2.0hz_s1/pano | 43.7 | 138.9 | 182.6 | 0.063 |
| panovggt | apartment_1/synthetic_2.0hz_s1/pano | 41.1 | 110.0 | 151.2 | 0.097 |
| panovggt | apartment_1/stopgo_2.0hz_s0/pano | 32.0 | 26.9 | 58.9 | 0.254 |
| panovggt | apartment_1/synthetic_0.5hz_s0/pano | 38.1 | 70.6 | 108.7 | 0.118 |
| panovggt | apartment_1/synthetic_0.5hz_s1/pano | 36.7 | 86.0 | 122.7 | 0.094 |
| panovggt | apartment_1/synthetic_5.0hz_s1/pano | 41.0 | 116.8 | 157.7 | 0.093 |
| panovggt | apartment_1/synthetic_2.0hz_s0/pano | 29.9 | 37.8 | 67.6 | 0.341 |
| panovggt | apartment_1/synthetic_5.0hz_s0/pano | 28.8 | 24.2 | 53.0 | 0.281 |
| panovggt | apartment_1/loop_2.0hz_s1/pano | 35.7 | 93.4 | 129.0 | 0.191 |
| panovggt | hotel_0/loop_2.0hz_s0/pano | 4.0 | 2.2 | 6.2 | 0.833 |
| panovggt | hotel_0/stopgo_2.0hz_s1/pano | 6.2 | 3.8 | 10.0 | 0.675 |
| panovggt | hotel_0/synthetic_2.0hz_s1/pano | 12.1 | 12.8 | 24.9 | 0.314 |
| panovggt | hotel_0/stopgo_2.0hz_s0/pano | 3.4 | 2.5 | 5.9 | 0.875 |
| panovggt | hotel_0/synthetic_0.5hz_s0/pano | 3.3 | 3.4 | 6.7 | 0.860 |
| panovggt | hotel_0/synthetic_0.5hz_s1/pano | 2.6 | 2.2 | 4.9 | 0.901 |
| panovggt | hotel_0/synthetic_5.0hz_s1/pano | 12.1 | 10.5 | 22.6 | 0.327 |
| panovggt | hotel_0/synthetic_2.0hz_s0/pano | 4.9 | 3.2 | 8.1 | 0.774 |
| panovggt | hotel_0/synthetic_5.0hz_s0/pano | 4.5 | 2.5 | 7.0 | 0.824 |
| panovggt | hotel_0/loop_2.0hz_s1/pano | 10.5 | 8.8 | 19.3 | 0.334 |
| panovggt | apartment_0/loop_2.0hz_s0/pano | 13.1 | 5.9 | 19.0 | 0.373 |
| panovggt | apartment_0/stopgo_2.0hz_s1/pano | 5.9 | 1.5 | 7.3 | 0.773 |
| panovggt | apartment_0/synthetic_2.0hz_s1/pano | 5.9 | 1.4 | 7.4 | 0.756 |
| panovggt | apartment_0/stopgo_2.0hz_s0/pano | 7.5 | 2.5 | 10.0 | 0.630 |
| panovggt | apartment_0/synthetic_0.5hz_s0/pano | 17.5 | 13.6 | 31.1 | 0.261 |
| panovggt | apartment_0/synthetic_0.5hz_s1/pano | 4.8 | 2.0 | 6.8 | 0.810 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 7.6 | 2.7 | 10.3 | 0.619 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 17.5 | 13.6 | 31.2 | 0.261 |
| panovggt | apartment_0/synthetic_5.0hz_s1/pano | 7.2 | 1.3 | 8.5 | 0.706 |
| panovggt | apartment_0/synthetic_2.0hz_s0/pano | 7.6 | 2.7 | 10.3 | 0.619 |
| panovggt | apartment_0/synthetic_5.0hz_s0/pano | 7.4 | 1.8 | 9.2 | 0.661 |
| panovggt | apartment_0/loop_2.0hz_s1/pano | 6.6 | 1.5 | 8.1 | 0.698 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3.3 | 7.3 | 10.6 | 0.726 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 3.2 | 8.0 | 11.3 | 0.802 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3.9 | 5.9 | 9.7 | 0.755 |
| vggtslam | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 20.3 | 16.7 | 37.0 | 0.324 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 3.5 | 8.8 | 12.3 | 0.752 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 3.5 | 8.8 | 12.3 | 0.752 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 15.4 | 14.2 | 29.6 | 0.302 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 16.5 | 23.5 | 40.0 | 0.397 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 3.2 | 4.0 | 7.2 | 0.847 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 5.0 | 10.4 | 15.4 | 0.631 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 15.4 | 14.2 | 29.7 | 0.302 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 64.3 | 113.2 | 177.5 | 0.052 |
| vggtslam | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 3.2 | 3.6 | 6.8 | 0.828 |
| vggtslam | apartment_1/loop_2.0hz_s0/synthetic_fov | 50.6 | 134.0 | 184.6 | 0.057 |
| vggtslam | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 47.8 | 193.2 | 241.0 | 0.021 |
| vggtslam | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 47.9 | 193.9 | 241.8 | 0.022 |
| vggtslam | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 14.2 | 290.1 | 304.2 | 0.014 |
| vggtslam | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 38.2 | 214.3 | 252.4 | 0.020 |
| vggtslam | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 41.2 | 187.5 | 228.7 | 0.038 |
| vggtslam | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 48.0 | 144.2 | 192.2 | 0.034 |
| vggtslam | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 50.6 | 101.0 | 151.6 | 0.031 |
| vggtslam | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 23.6 | 84.0 | 107.6 | 0.311 |
| vggtslam | apartment_1/loop_2.0hz_s1/synthetic_fov | 38.4 | 209.1 | 247.5 | 0.039 |
| vggtslam | hotel_0/loop_2.0hz_s0/synthetic_fov | 37.9 | 122.7 | 160.6 | 0.056 |
| vggtslam | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 37.4 | 166.8 | 204.2 | 0.066 |
| vggtslam | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 21.9 | 213.4 | 235.3 | 0.058 |
| vggtslam | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 43.3 | 120.9 | 164.2 | 0.025 |
| vggtslam | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 4.7 | 13.6 | 18.3 | 0.510 |
| vggtslam | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 22.5 | 111.4 | 133.9 | 0.129 |
| vggtslam | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 30.9 | 132.0 | 162.9 | 0.101 |
| vggtslam | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 43.3 | 121.0 | 164.3 | 0.025 |
| vggtslam | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 16.5 | 158.3 | 174.8 | 0.084 |
| vggtslam | hotel_0/loop_2.0hz_s1/synthetic_fov | 27.4 | 37.9 | 65.3 | 0.166 |
| vggtslam | apartment_0/loop_2.0hz_s0/synthetic_fov | 37.9 | 82.7 | 120.6 | 0.091 |
| vggtslam | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 20.4 | 45.8 | 66.1 | 0.230 |
| vggtslam | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 20.3 | 45.8 | 66.1 | 0.229 |
| vggtslam | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 35.4 | 156.4 | 191.8 | 0.049 |
| vggtslam | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 30.6 | 37.1 | 67.7 | 0.172 |
| vggtslam | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 5.1 | 17.8 | 22.8 | 0.624 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 35.7 | 156.6 | 192.3 | 0.050 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 30.6 | 37.3 | 68.0 | 0.170 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 25.4 | 153.6 | 179.1 | 0.072 |
| vggtslam | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 32.5 | 79.8 | 112.3 | 0.088 |
| vggtslam | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 36.0 | 156.9 | 193.0 | 0.050 |
| vggtslam | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 25.3 | 153.1 | 178.4 | 0.073 |
| vggtslam | apartment_0/loop_2.0hz_s1/synthetic_fov | 17.5 | 34.0 | 51.5 | 0.255 |
| prism_sl4 | office_4/synthetic_2.0hz/pano | 1.7 | 2.7 | 4.5 | 0.948 |
| prism_sl4 | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism_sl4 | office_4/synthetic_5.0hz/pano | 2.0 | 2.6 | 4.6 | 0.950 |
| prism_sl4 | apartment_0/synthetic_2.0hz/pano | 6.7 | 8.6 | 15.3 | 0.519 |
| prism_sl4 | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.221 |
| prism_sl4 | apartment_0/synthetic_5.0hz/pano | 14.1 | 17.5 | 31.6 | 0.368 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.5 | 1.5 | 4.0 | 0.960 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 2.4 | 2.1 | 4.5 | 0.965 |
| pi3 | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 9.3 | 5.7 | 15.0 | 0.583 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 5.1 | 2.7 | 7.8 | 0.723 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 5.2 | 2.7 | 7.9 | 0.714 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 7.4 | 5.9 | 13.2 | 0.594 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 7.2 | 8.9 | 16.1 | 0.533 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 5.9 | 4.1 | 10.0 | 0.628 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 5.9 | 2.5 | 8.4 | 0.678 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 6.6 | 5.8 | 12.4 | 0.616 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 7.6 | 5.6 | 13.2 | 0.600 |
| pi3 | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 4.7 | 2.0 | 6.7 | 0.782 |
| pi3 | apartment_1/loop_2.0hz_s0/synthetic_fov | 31.2 | 62.3 | 93.5 | 0.205 |
| pi3 | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 36.7 | 35.7 | 72.3 | 0.190 |
| pi3 | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 35.5 | 29.9 | 65.5 | 0.184 |
| pi3 | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 37.4 | 84.7 | 122.1 | 0.179 |
| pi3 | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 31.3 | 90.8 | 122.1 | 0.175 |
| pi3 | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 30.1 | 61.2 | 91.3 | 0.101 |
| pi3 | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 40.8 | 63.7 | 104.5 | 0.118 |
| pi3 | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 36.4 | 101.1 | 137.6 | 0.180 |
| pi3 | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 38.2 | 112.9 | 151.0 | 0.091 |
| pi3 | apartment_1/loop_2.0hz_s1/synthetic_fov | 37.6 | 82.7 | 120.3 | 0.109 |
| pi3 | hotel_0/loop_2.0hz_s0/synthetic_fov | 5.3 | 5.0 | 10.3 | 0.618 |
| pi3 | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 10.4 | 11.6 | 22.1 | 0.385 |
| pi3 | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 4.2 | 3.6 | 7.8 | 0.773 |
| pi3 | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 12.3 | 29.3 | 41.6 | 0.341 |
| pi3 | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 12.3 | 21.7 | 33.9 | 0.334 |
| pi3 | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 11.3 | 16.8 | 28.0 | 0.366 |
| pi3 | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 3.1 | 2.6 | 5.7 | 0.896 |
| pi3 | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 11.3 | 14.2 | 25.5 | 0.405 |
| pi3 | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 11.9 | 16.9 | 28.8 | 0.375 |
| pi3 | hotel_0/loop_2.0hz_s1/synthetic_fov | 3.4 | 3.0 | 6.4 | 0.873 |
| pi3 | apartment_0/loop_2.0hz_s0/synthetic_fov | 5.6 | 3.1 | 8.6 | 0.717 |
| pi3 | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 7.5 | 5.2 | 12.7 | 0.509 |
| pi3 | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 6.7 | 4.4 | 11.2 | 0.576 |
| pi3 | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 5.3 | 2.6 | 7.9 | 0.760 |
| pi3 | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 5.1 | 4.8 | 10.0 | 0.732 |
| pi3 | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 7.5 | 7.3 | 14.8 | 0.431 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 4.7 | 2.2 | 6.9 | 0.818 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 5.1 | 4.8 | 9.9 | 0.732 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 5.7 | 2.0 | 7.6 | 0.779 |
| pi3 | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 7.0 | 3.5 | 10.5 | 0.614 |
| pi3 | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 4.7 | 2.2 | 6.9 | 0.819 |
| pi3 | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 5.7 | 2.0 | 7.7 | 0.779 |
| pi3 | apartment_0/loop_2.0hz_s1/synthetic_fov | 7.7 | 5.2 | 12.8 | 0.491 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s0/pano | 22.8 | 24.6 | 47.5 | 0.304 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 3.5 | 12.5 | 16.1 | 0.695 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 3.1 | 12.6 | 15.7 | 0.720 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 9.5 | 19.1 | 28.6 | 0.381 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 2.7 | 18.4 | 21.1 | 0.751 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 2.8 | 10.7 | 13.5 | 0.761 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 3.1 | 14.2 | 17.4 | 0.698 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 8.7 | 18.4 | 27.1 | 0.369 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 13.1 | 23.4 | 36.5 | 0.292 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s1/pano | 3.2 | 11.8 | 15.0 | 0.733 |
| prism_sim3 | apartment_1/stopgo_2.0hz_s1/pano | 42.3 | 161.0 | 203.3 | 0.036 |
| prism_sim3 | apartment_1/synthetic_2.0hz_s1/pano | 32.0 | 99.9 | 131.9 | 0.128 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s0/pano | 35.5 | 100.6 | 136.0 | 0.082 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s1/pano | 34.2 | 119.1 | 153.2 | 0.127 |
| prism_sim3 | apartment_1/synthetic_5.0hz_s1/pano | 38.1 | 100.3 | 138.4 | 0.108 |
| prism_sim3 | apartment_1/loop_2.0hz_s1/pano | 29.8 | 125.4 | 155.2 | 0.116 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s1/pano | 15.5 | 91.0 | 106.5 | 0.218 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s0/pano | 7.4 | 11.1 | 18.5 | 0.608 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s1/pano | 20.1 | 28.5 | 48.6 | 0.252 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s0/pano | 4.6 | 13.7 | 18.3 | 0.554 |
| prism_sim3 | hotel_0/loop_2.0hz_s1/pano | 8.9 | 27.2 | 36.0 | 0.368 |
| prism_sim3 | apartment_0/loop_2.0hz_s0/pano | 37.7 | 68.1 | 105.8 | 0.100 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s1/pano | 11.2 | 36.8 | 47.9 | 0.331 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s1/pano | 13.7 | 28.4 | 42.1 | 0.372 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s0/pano | 9.6 | 16.1 | 25.7 | 0.475 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s0/pano | 17.0 | 19.6 | 36.6 | 0.223 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s1/pano | 3.4 | 12.2 | 15.6 | 0.791 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s0/pano | 9.8 | 10.2 | 20.0 | 0.525 |
| prism_sim3 | apartment_0/synthetic_5.0hz_s0/pano | 12.7 | 18.9 | 31.6 | 0.360 |
| prism_sim3 | apartment_0/loop_2.0hz_s1/pano | 10.1 | 27.8 | 37.9 | 0.392 |
| prism | office_4/synthetic_2.0hz/pano | 2.3 | 7.7 | 10.0 | 0.830 |
| prism | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism | office_4/synthetic_5.0hz/pano | 3.1 | 13.5 | 16.6 | 0.715 |
| prism | frl_apartment_0/loop_2.0hz_s0/pano | 12.2 | 11.0 | 23.1 | 0.426 |
| prism | frl_apartment_0/stopgo_2.0hz_s1/pano | 3.9 | 17.9 | 21.7 | 0.639 |
| prism | frl_apartment_0/synthetic_2.0hz_s1/pano | 3.4 | 21.1 | 24.5 | 0.643 |
| prism | frl_apartment_0/stopgo_2.0hz_s0/pano | 3.5 | 5.0 | 8.5 | 0.777 |
| prism | frl_apartment_0/synthetic_0.5hz_s0/pano | 2.6 | 18.4 | 21.0 | 0.752 |
| prism | frl_apartment_0/synthetic_0.5hz_s1/pano | 2.9 | 10.6 | 13.5 | 0.760 |
| prism | frl_apartment_0/synthetic_5.0hz_s1/pano | 3.5 | 20.6 | 24.1 | 0.634 |
| prism | frl_apartment_0/synthetic_2.0hz_s0/pano | 4.1 | 6.5 | 10.6 | 0.726 |
| prism | frl_apartment_0/synthetic_5.0hz_s0/pano | 5.0 | 7.7 | 12.6 | 0.655 |
| prism | frl_apartment_0/loop_2.0hz_s1/pano | 3.5 | 13.8 | 17.3 | 0.670 |
| prism | apartment_1/stopgo_2.0hz_s1/pano | 40.5 | 108.5 | 149.0 | 0.065 |
| prism | apartment_1/synthetic_2.0hz_s1/pano | 32.3 | 88.6 | 120.8 | 0.167 |
| prism | apartment_1/synthetic_0.5hz_s0/pano | 35.4 | 100.0 | 135.4 | 0.081 |
| prism | apartment_1/synthetic_0.5hz_s1/pano | 34.3 | 118.8 | 153.1 | 0.127 |
| prism | apartment_1/synthetic_5.0hz_s1/pano | 33.3 | 89.1 | 122.4 | 0.129 |
| prism | apartment_1/loop_2.0hz_s1/pano | 32.1 | 76.5 | 108.6 | 0.162 |
| prism | hotel_0/synthetic_2.0hz_s1/pano | 20.3 | 90.4 | 110.7 | 0.217 |
| prism | hotel_0/synthetic_0.5hz_s0/pano | 7.4 | 11.1 | 18.5 | 0.608 |
| prism | hotel_0/synthetic_0.5hz_s1/pano | 20.1 | 28.5 | 48.6 | 0.251 |
| prism | hotel_0/synthetic_2.0hz_s0/pano | 2.4 | 11.2 | 13.6 | 0.801 |
| prism | hotel_0/loop_2.0hz_s1/pano | 19.0 | 304.2 | 323.2 | 0.000 |
| prism | apartment_0/loop_2.0hz_s0/pano | 36.1 | 57.8 | 93.9 | 0.135 |
| prism | apartment_0/stopgo_2.0hz_s1/pano | 26.3 | 46.9 | 73.1 | 0.146 |
| prism | apartment_0/synthetic_2.0hz_s1/pano | 27.5 | 47.9 | 75.4 | 0.152 |
| prism | apartment_0/stopgo_2.0hz_s0/pano | 9.3 | 8.2 | 17.5 | 0.523 |
| prism | apartment_0/synthetic_0.5hz_s0/pano | 17.1 | 19.7 | 36.8 | 0.220 |
| prism | apartment_0/synthetic_0.5hz_s1/pano | 3.4 | 12.0 | 15.4 | 0.789 |
| prism | apartment_0/synthetic_2.0hz/pano | 9.8 | 10.2 | 20.0 | 0.524 |
| prism | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.223 |
| prism | apartment_0/synthetic_5.0hz/pano | 12.7 | 18.8 | 31.5 | 0.358 |
| prism | apartment_0/synthetic_5.0hz_s1/pano | 6.5 | 10.0 | 16.5 | 0.656 |
| prism | apartment_0/synthetic_2.0hz_s0/pano | 6.7 | 8.6 | 15.3 | 0.521 |
| prism | apartment_0/synthetic_5.0hz_s0/pano | 14.1 | 17.6 | 31.7 | 0.367 |
| prism | apartment_0/loop_2.0hz_s1/pano | 28.6 | 54.3 | 82.9 | 0.142 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 2.3 | 7.6 | 9.9 | 0.831 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 3.1 | 13.5 | 16.6 | 0.716 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s0/pano | 12.2 | 11.1 | 23.2 | 0.423 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s1/pano | 3.9 | 17.9 | 21.8 | 0.640 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s0/pano | 3.5 | 5.0 | 8.5 | 0.777 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s1/pano | 3.5 | 13.9 | 17.4 | 0.669 |
| prism_nostill | apartment_1/stopgo_2.0hz_s1/pano | 40.6 | 108.9 | 149.5 | 0.065 |
| prism_nostill | apartment_1/loop_2.0hz_s1/pano | 32.0 | 76.7 | 108.7 | 0.161 |
| prism_nostill | hotel_0/loop_2.0hz_s1/pano | 19.1 | 303.8 | 322.9 | 0.000 |
| prism_nostill | apartment_0/loop_2.0hz_s0/pano | 36.1 | 58.2 | 94.3 | 0.134 |
| prism_nostill | apartment_0/stopgo_2.0hz_s1/pano | 26.4 | 47.0 | 73.4 | 0.146 |
| prism_nostill | apartment_0/stopgo_2.0hz_s0/pano | 9.2 | 8.0 | 17.3 | 0.525 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 9.8 | 10.1 | 19.9 | 0.527 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.221 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 12.7 | 19.0 | 31.7 | 0.362 |
| prism_nostill | apartment_0/loop_2.0hz_s1/pano | 28.5 | 54.2 | 82.7 | 0.142 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 2.3 | 7.5 | 9.8 | 0.829 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 2.8 | 4.9 | 7.7 | 0.855 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s0/pano | 12.1 | 11.0 | 23.2 | 0.418 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s1/pano | 3.8 | 18.0 | 21.8 | 0.646 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s0/pano | 3.6 | 5.3 | 8.9 | 0.760 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s1/pano | 3.5 | 13.8 | 17.3 | 0.671 |
| prism_nolock | apartment_1/stopgo_2.0hz_s1/pano | 40.6 | 108.7 | 149.2 | 0.064 |
| prism_nolock | apartment_1/loop_2.0hz_s1/pano | 32.0 | 76.9 | 109.0 | 0.162 |
| prism_nolock | hotel_0/loop_2.0hz_s1/pano | 19.8 | 304.1 | 323.8 | 0.000 |
| prism_nolock | apartment_0/loop_2.0hz_s0/pano | 36.0 | 58.1 | 94.1 | 0.139 |
| prism_nolock | apartment_0/stopgo_2.0hz_s1/pano | 26.3 | 47.0 | 73.3 | 0.148 |
| prism_nolock | apartment_0/stopgo_2.0hz_s0/pano | 9.6 | 8.0 | 17.5 | 0.528 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 5.7 | 7.7 | 13.4 | 0.563 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 17.1 | 19.8 | 36.8 | 0.220 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 19.3 | 24.9 | 44.2 | 0.214 |
| prism_nolock | apartment_0/loop_2.0hz_s1/pano | 28.6 | 54.4 | 83.0 | 0.141 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.5 | 11.9 | 23.5 | 0.441 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 13.5 | 15.9 | 29.3 | 0.398 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 12.1 | 10.7 | 22.7 | 0.420 |
| mapanything | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 39.0 | 25.9 | 65.0 | 0.186 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 26.9 | 23.6 | 50.5 | 0.217 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 26.2 | 24.4 | 50.6 | 0.228 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 26.8 | 14.9 | 41.6 | 0.238 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 23.3 | 20.0 | 43.3 | 0.245 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 38.6 | 31.9 | 70.5 | 0.131 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 26.4 | 18.4 | 44.8 | 0.214 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 28.1 | 15.9 | 44.1 | 0.252 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 22.5 | 11.0 | 33.5 | 0.310 |
| mapanything | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 47.5 | 39.8 | 87.2 | 0.082 |
| mapanything | apartment_1/loop_2.0hz_s0/synthetic_fov | 35.7 | 181.2 | 216.9 | 0.042 |
| mapanything | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 24.2 | 252.9 | 277.0 | 0.027 |
| mapanything | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 36.9 | 210.2 | 247.1 | 0.032 |
| mapanything | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 42.4 | 190.2 | 232.6 | 0.021 |
| mapanything | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 38.4 | 129.8 | 168.2 | 0.080 |
| mapanything | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 36.7 | 231.4 | 268.1 | 0.044 |
| mapanything | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 48.1 | 219.2 | 267.3 | 0.036 |
| mapanything | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 33.3 | 143.3 | 176.6 | 0.149 |
| mapanything | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 31.6 | 142.6 | 174.3 | 0.145 |
| mapanything | apartment_1/loop_2.0hz_s1/synthetic_fov | 39.5 | 97.4 | 136.9 | 0.081 |
| mapanything | hotel_0/loop_2.0hz_s0/synthetic_fov | 9.8 | 27.0 | 36.8 | 0.417 |
| mapanything | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 9.2 | 10.1 | 19.4 | 0.397 |
| mapanything | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 10.1 | 12.7 | 22.8 | 0.358 |
| mapanything | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 15.9 | 37.7 | 53.6 | 0.306 |
| mapanything | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 9.0 | 20.2 | 29.2 | 0.399 |
| mapanything | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 17.0 | 21.7 | 38.7 | 0.281 |
| mapanything | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 8.9 | 8.7 | 17.5 | 0.421 |
| mapanything | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 10.7 | 27.8 | 38.5 | 0.419 |
| mapanything | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 12.4 | 16.7 | 29.0 | 0.375 |
| mapanything | hotel_0/loop_2.0hz_s1/synthetic_fov | 10.2 | 10.0 | 20.2 | 0.446 |
| mapanything | apartment_0/loop_2.0hz_s0/synthetic_fov | 12.8 | 10.7 | 23.5 | 0.329 |
| mapanything | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 12.0 | 11.6 | 23.6 | 0.384 |
| mapanything | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 11.7 | 11.4 | 23.1 | 0.375 |
| mapanything | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 14.0 | 15.0 | 29.0 | 0.396 |
| mapanything | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 27.0 | 27.6 | 54.6 | 0.213 |
| mapanything | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 9.8 | 14.6 | 24.3 | 0.416 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 13.5 | 13.4 | 26.9 | 0.397 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 27.0 | 27.7 | 54.7 | 0.213 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 13.3 | 9.5 | 22.8 | 0.353 |
| mapanything | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 13.5 | 10.1 | 23.6 | 0.368 |
| mapanything | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 13.5 | 13.4 | 26.9 | 0.397 |
| mapanything | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 13.3 | 9.6 | 22.9 | 0.352 |
| mapanything | apartment_0/loop_2.0hz_s1/synthetic_fov | 10.9 | 10.1 | 21.0 | 0.412 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 2.3 | 7.0 | 9.3 | 0.835 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 1.9 | 2.2 | 4.0 | 0.958 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 2.7 | 4.7 | 7.5 | 0.867 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s0/pano | 12.1 | 11.0 | 23.2 | 0.426 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s1/pano | 3.8 | 18.3 | 22.1 | 0.650 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s0/pano | 3.5 | 5.0 | 8.6 | 0.772 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s1/pano | 3.5 | 13.9 | 17.4 | 0.671 |
| prism_noguards | apartment_1/stopgo_2.0hz_s1/pano | 39.9 | 166.5 | 206.4 | 0.072 |
| prism_noguards | apartment_1/loop_2.0hz_s1/pano | 32.6 | 72.1 | 104.7 | 0.170 |
| prism_noguards | hotel_0/loop_2.0hz_s1/pano | 19.0 | 303.9 | 322.9 | 0.000 |
| prism_noguards | apartment_0/loop_2.0hz_s0/pano | 35.8 | 58.3 | 94.1 | 0.142 |
| prism_noguards | apartment_0/stopgo_2.0hz_s1/pano | 27.7 | 46.6 | 74.3 | 0.139 |
| prism_noguards | apartment_0/stopgo_2.0hz_s0/pano | 9.1 | 7.5 | 16.6 | 0.521 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 5.6 | 7.8 | 13.4 | 0.565 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.223 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 20.0 | 25.5 | 45.5 | 0.185 |
| prism_noguards | apartment_0/loop_2.0hz_s1/pano | 29.1 | 53.3 | 82.4 | 0.134 |
| prism_se3 | office_4/synthetic_2.0hz/pano | 2.3 | 7.3 | 9.6 | 0.831 |
| prism_se3 | office_4/synthetic_5.0hz/pano | 3.1 | 13.5 | 16.6 | 0.715 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s0/pano | 22.9 | 24.5 | 47.4 | 0.302 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 3.5 | 13.1 | 16.6 | 0.696 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 3.1 | 12.4 | 15.6 | 0.721 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 9.5 | 21.0 | 30.5 | 0.381 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 2.7 | 18.3 | 21.0 | 0.751 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 2.9 | 10.5 | 13.4 | 0.761 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 3.1 | 14.4 | 17.6 | 0.697 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 8.7 | 18.4 | 27.1 | 0.367 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 13.0 | 23.4 | 36.4 | 0.293 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s1/pano | 3.2 | 12.1 | 15.3 | 0.734 |
| prism_se3 | apartment_1/stopgo_2.0hz_s1/pano | 39.9 | 146.0 | 185.9 | 0.086 |
| prism_se3 | apartment_1/synthetic_2.0hz_s1/pano | 31.8 | 99.5 | 131.2 | 0.140 |
| prism_se3 | apartment_1/synthetic_0.5hz_s0/pano | 35.2 | 100.8 | 135.9 | 0.082 |
| prism_se3 | apartment_1/synthetic_0.5hz_s1/pano | 34.3 | 119.5 | 153.8 | 0.125 |
| prism_se3 | apartment_1/synthetic_5.0hz_s1/pano | 38.2 | 99.9 | 138.1 | 0.107 |
| prism_se3 | apartment_1/loop_2.0hz_s1/pano | 30.2 | 126.7 | 157.0 | 0.108 |
| prism_se3 | hotel_0/synthetic_2.0hz_s1/pano | 14.5 | 88.8 | 103.2 | 0.201 |
| prism_se3 | hotel_0/synthetic_0.5hz_s0/pano | 7.4 | 11.2 | 18.6 | 0.608 |
| prism_se3 | hotel_0/synthetic_0.5hz_s1/pano | 20.1 | 28.8 | 48.9 | 0.251 |
| prism_se3 | hotel_0/synthetic_2.0hz_s0/pano | 4.7 | 13.9 | 18.6 | 0.551 |
| prism_se3 | hotel_0/loop_2.0hz_s1/pano | 11.0 | 29.5 | 40.5 | 0.298 |
| prism_se3 | apartment_0/loop_2.0hz_s0/pano | 37.7 | 68.2 | 105.9 | 0.099 |
| prism_se3 | apartment_0/stopgo_2.0hz_s1/pano | 13.6 | 29.9 | 43.5 | 0.307 |
| prism_se3 | apartment_0/synthetic_2.0hz_s1/pano | 11.7 | 28.0 | 39.7 | 0.383 |
| prism_se3 | apartment_0/stopgo_2.0hz_s0/pano | 10.6 | 21.5 | 32.1 | 0.369 |
| prism_se3 | apartment_0/synthetic_0.5hz_s0/pano | 17.0 | 19.7 | 36.7 | 0.221 |
| prism_se3 | apartment_0/synthetic_0.5hz_s1/pano | 3.4 | 11.9 | 15.3 | 0.791 |
| prism_se3 | apartment_0/synthetic_2.0hz/pano | 9.8 | 10.2 | 20.0 | 0.527 |
| prism_se3 | apartment_0/synthetic_0.5hz/pano | 17.0 | 19.7 | 36.7 | 0.223 |
| prism_se3 | apartment_0/synthetic_5.0hz/pano | 12.8 | 19.0 | 31.8 | 0.359 |
| prism_se3 | apartment_0/synthetic_5.0hz_s1/pano | 13.4 | 19.9 | 33.3 | 0.420 |
| prism_se3 | apartment_0/synthetic_2.0hz_s0/pano | 9.8 | 10.1 | 19.9 | 0.528 |
| prism_se3 | apartment_0/synthetic_5.0hz_s0/pano | 12.7 | 19.1 | 31.8 | 0.360 |
| prism_se3 | apartment_0/loop_2.0hz_s1/pano | 8.3 | 16.4 | 24.7 | 0.443 |


## Table C2 — Reconstruction, full-360 (no mask; pano methods)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.4 | 7.8 | 12.2 | 0.728 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 2.7 | 21.6 | 24.2 | 0.748 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 7.8 | 7.7 | 15.4 | 0.692 |
| laser | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 88.1 | 48.8 | 136.9 | 0.076 |
| laser | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 33.8 | 9.0 | 42.8 | 0.418 |
| laser | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 32.3 | 8.6 | 40.9 | 0.436 |
| laser | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 36.2 | 10.8 | 47.1 | 0.313 |
| laser | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 32.5 | 13.3 | 45.7 | 0.332 |
| laser | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 27.5 | 9.5 | 37.0 | 0.573 |
| laser | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 46.1 | 9.5 | 55.6 | 0.217 |
| laser | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 35.0 | 10.2 | 45.3 | 0.299 |
| laser | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 52.3 | 15.7 | 68.0 | 0.170 |
| laser | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 32.1 | 7.5 | 39.5 | 0.407 |
| laser | apartment_1/loop_2.0hz_s0/synthetic_fov | 33.5 | 237.0 | 270.5 | 0.076 |
| laser | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 40.1 | 236.5 | 276.5 | 0.027 |
| laser | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 35.8 | 86.4 | 122.2 | 0.146 |
| laser | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 36.3 | 262.2 | 298.4 | 0.031 |
| laser | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 38.5 | 148.0 | 186.5 | 0.110 |
| laser | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 27.4 | 160.2 | 187.5 | 0.130 |
| laser | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 53.0 | 56.3 | 109.3 | 0.116 |
| laser | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 36.4 | 218.4 | 254.7 | 0.037 |
| laser | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 36.0 | 62.1 | 98.1 | 0.181 |
| laser | apartment_1/loop_2.0hz_s1/synthetic_fov | 32.0 | 98.5 | 130.5 | 0.185 |
| laser | hotel_0/loop_2.0hz_s0/synthetic_fov | 19.8 | 59.8 | 79.6 | 0.149 |
| laser | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 487.8 | 166.1 | 654.0 | 0.039 |
| laser | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 42.6 | 160.8 | 203.5 | 0.058 |
| laser | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 24.3 | 72.1 | 96.4 | 0.148 |
| laser | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 10.1 | 64.5 | 74.5 | 0.338 |
| laser | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 14.0 | 20.3 | 34.3 | 0.277 |
| laser | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 78.8 | 34.5 | 113.2 | 0.111 |
| laser | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 22.3 | 73.7 | 96.0 | 0.158 |
| laser | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 15.3 | 40.8 | 56.1 | 0.279 |
| laser | hotel_0/loop_2.0hz_s1/synthetic_fov | 54.3 | 50.4 | 104.7 | 0.168 |
| laser | apartment_0/loop_2.0hz_s0/synthetic_fov | 50.8 | 92.5 | 143.3 | 0.122 |
| laser | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 14.8 | 76.4 | 91.2 | 0.328 |
| laser | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 16.0 | 76.7 | 92.7 | 0.284 |
| laser | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 12.2 | 69.9 | 82.1 | 0.328 |
| laser | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 7.7 | 75.2 | 82.9 | 0.350 |
| laser | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 9.4 | 79.3 | 88.8 | 0.322 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 11.0 | 70.9 | 81.9 | 0.357 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 7.7 | 75.2 | 82.8 | 0.351 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 12.2 | 71.5 | 83.7 | 0.297 |
| laser | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 43.6 | 65.6 | 109.1 | 0.183 |
| laser | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 11.0 | 70.5 | 81.5 | 0.357 |
| laser | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 12.2 | 71.6 | 83.8 | 0.296 |
| laser | apartment_0/loop_2.0hz_s1/synthetic_fov | 17.7 | 75.0 | 92.7 | 0.284 |
| panovggt | office_4/synthetic_2.0hz/pano | 2.7 | 1.7 | 4.4 | 0.922 |
| panovggt | office_4/synthetic_0.5hz/pano | 2.3 | 2.1 | 4.4 | 0.925 |
| panovggt | office_4/synthetic_5.0hz/pano | 3.1 | 1.5 | 4.6 | 0.905 |
| panovggt | frl_apartment_0/loop_2.0hz_s0/pano | 29.4 | 2.4 | 31.9 | 0.581 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s1/pano | 32.9 | 4.8 | 37.7 | 0.613 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s1/pano | 33.3 | 4.8 | 38.0 | 0.611 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s0/pano | 28.9 | 3.7 | 32.5 | 0.643 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s0/pano | 32.1 | 4.2 | 36.4 | 0.671 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s1/pano | 38.3 | 5.9 | 44.2 | 0.619 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s1/pano | 31.0 | 4.3 | 35.2 | 0.589 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s0/pano | 28.9 | 3.6 | 32.5 | 0.643 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s0/pano | 27.5 | 3.4 | 30.9 | 0.611 |
| panovggt | frl_apartment_0/loop_2.0hz_s1/pano | 31.5 | 4.6 | 36.1 | 0.607 |
| panovggt | apartment_1/loop_2.0hz_s0/pano | 37.7 | 186.6 | 224.3 | 0.068 |
| panovggt | apartment_1/stopgo_2.0hz_s1/pano | 41.7 | 205.2 | 246.9 | 0.049 |
| panovggt | apartment_1/synthetic_2.0hz_s1/pano | 38.6 | 164.5 | 203.1 | 0.081 |
| panovggt | apartment_1/stopgo_2.0hz_s0/pano | 33.7 | 18.6 | 52.2 | 0.217 |
| panovggt | apartment_1/synthetic_0.5hz_s0/pano | 36.8 | 103.6 | 140.4 | 0.100 |
| panovggt | apartment_1/synthetic_0.5hz_s1/pano | 34.0 | 140.8 | 174.8 | 0.077 |
| panovggt | apartment_1/synthetic_5.0hz_s1/pano | 38.5 | 169.1 | 207.7 | 0.079 |
| panovggt | apartment_1/synthetic_2.0hz_s0/pano | 24.1 | 29.7 | 53.8 | 0.278 |
| panovggt | apartment_1/synthetic_5.0hz_s0/pano | 44.9 | 18.0 | 63.0 | 0.163 |
| panovggt | apartment_1/loop_2.0hz_s1/pano | 34.4 | 114.6 | 149.0 | 0.166 |
| panovggt | hotel_0/loop_2.0hz_s0/pano | 4.0 | 3.6 | 7.6 | 0.806 |
| panovggt | hotel_0/stopgo_2.0hz_s1/pano | 5.8 | 4.9 | 10.7 | 0.650 |
| panovggt | hotel_0/synthetic_2.0hz_s1/pano | 11.4 | 13.7 | 25.1 | 0.323 |
| panovggt | hotel_0/stopgo_2.0hz_s0/pano | 3.5 | 4.1 | 7.6 | 0.826 |
| panovggt | hotel_0/synthetic_0.5hz_s0/pano | 3.3 | 5.2 | 8.5 | 0.800 |
| panovggt | hotel_0/synthetic_0.5hz_s1/pano | 2.7 | 3.6 | 6.2 | 0.861 |
| panovggt | hotel_0/synthetic_5.0hz_s1/pano | 11.5 | 11.4 | 22.9 | 0.330 |
| panovggt | hotel_0/synthetic_2.0hz_s0/pano | 4.7 | 4.8 | 9.6 | 0.745 |
| panovggt | hotel_0/synthetic_5.0hz_s0/pano | 4.4 | 3.6 | 8.0 | 0.798 |
| panovggt | hotel_0/loop_2.0hz_s1/pano | 10.1 | 9.7 | 19.8 | 0.340 |
| panovggt | apartment_0/loop_2.0hz_s0/pano | 13.9 | 43.2 | 57.1 | 0.298 |
| panovggt | apartment_0/stopgo_2.0hz_s1/pano | 6.9 | 73.1 | 80.0 | 0.475 |
| panovggt | apartment_0/synthetic_2.0hz_s1/pano | 6.7 | 73.8 | 80.5 | 0.475 |
| panovggt | apartment_0/stopgo_2.0hz_s0/pano | 8.7 | 61.8 | 70.5 | 0.446 |
| panovggt | apartment_0/synthetic_0.5hz_s0/pano | 16.3 | 70.8 | 87.1 | 0.195 |
| panovggt | apartment_0/synthetic_0.5hz_s1/pano | 5.2 | 76.1 | 81.3 | 0.464 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 9.3 | 62.0 | 71.4 | 0.440 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 16.3 | 70.6 | 87.0 | 0.195 |
| panovggt | apartment_0/synthetic_5.0hz_s1/pano | 8.3 | 73.0 | 81.3 | 0.454 |
| panovggt | apartment_0/synthetic_2.0hz_s0/pano | 9.3 | 62.0 | 71.3 | 0.440 |
| panovggt | apartment_0/synthetic_5.0hz_s0/pano | 10.3 | 60.2 | 70.5 | 0.476 |
| panovggt | apartment_0/loop_2.0hz_s1/pano | 7.2 | 74.4 | 81.6 | 0.461 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 5.8 | 10.4 | 16.2 | 0.553 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 3.6 | 22.5 | 26.1 | 0.625 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3.9 | 10.6 | 14.5 | 0.672 |
| vggtslam | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 20.2 | 18.9 | 39.0 | 0.292 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 6.4 | 10.9 | 17.2 | 0.582 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 6.4 | 10.9 | 17.2 | 0.582 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 14.8 | 17.3 | 32.2 | 0.280 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 20.7 | 20.6 | 41.3 | 0.291 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 3.8 | 10.7 | 14.5 | 0.694 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10.1 | 12.0 | 22.2 | 0.460 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 14.8 | 17.4 | 32.2 | 0.281 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 71.2 | 114.6 | 185.8 | 0.053 |
| vggtslam | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 7.5 | 7.2 | 14.7 | 0.620 |
| vggtslam | apartment_1/loop_2.0hz_s0/synthetic_fov | 54.5 | 202.9 | 257.4 | 0.045 |
| vggtslam | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 46.1 | 246.2 | 292.3 | 0.015 |
| vggtslam | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 46.2 | 246.7 | 292.9 | 0.015 |
| vggtslam | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 11.7 | 358.6 | 370.3 | 0.015 |
| vggtslam | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 33.5 | 287.8 | 321.3 | 0.014 |
| vggtslam | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 38.9 | 238.7 | 277.6 | 0.019 |
| vggtslam | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 43.8 | 222.9 | 266.7 | 0.025 |
| vggtslam | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 45.9 | 170.1 | 215.9 | 0.024 |
| vggtslam | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 23.1 | 135.2 | 158.3 | 0.190 |
| vggtslam | apartment_1/loop_2.0hz_s1/synthetic_fov | 34.4 | 266.7 | 301.1 | 0.022 |
| vggtslam | hotel_0/loop_2.0hz_s0/synthetic_fov | 35.3 | 178.9 | 214.3 | 0.039 |
| vggtslam | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 35.7 | 163.0 | 198.8 | 0.059 |
| vggtslam | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 20.4 | 207.1 | 227.5 | 0.041 |
| vggtslam | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 41.4 | 180.5 | 221.9 | 0.017 |
| vggtslam | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 5.2 | 79.7 | 84.9 | 0.273 |
| vggtslam | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 41.6 | 110.4 | 151.9 | 0.103 |
| vggtslam | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 28.9 | 132.5 | 161.4 | 0.077 |
| vggtslam | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 41.4 | 180.7 | 222.2 | 0.017 |
| vggtslam | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 14.5 | 181.4 | 195.9 | 0.056 |
| vggtslam | hotel_0/loop_2.0hz_s1/synthetic_fov | 28.7 | 35.5 | 64.3 | 0.162 |
| vggtslam | apartment_0/loop_2.0hz_s0/synthetic_fov | 30.4 | 105.8 | 136.2 | 0.087 |
| vggtslam | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 19.5 | 175.6 | 195.1 | 0.093 |
| vggtslam | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 19.5 | 175.3 | 194.8 | 0.093 |
| vggtslam | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 31.0 | 186.4 | 217.4 | 0.032 |
| vggtslam | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 24.2 | 93.7 | 118.0 | 0.105 |
| vggtslam | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 6.9 | 135.7 | 142.7 | 0.226 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 31.3 | 186.2 | 217.4 | 0.032 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 24.2 | 93.8 | 118.1 | 0.104 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 23.2 | 161.4 | 184.6 | 0.057 |
| vggtslam | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 31.0 | 171.1 | 202.1 | 0.039 |
| vggtslam | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 31.5 | 186.1 | 217.5 | 0.033 |
| vggtslam | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 23.1 | 161.5 | 184.7 | 0.058 |
| vggtslam | apartment_0/loop_2.0hz_s1/synthetic_fov | 16.8 | 161.7 | 178.5 | 0.107 |
| prism_sl4 | office_4/synthetic_2.0hz/pano | 1.9 | 4.2 | 6.1 | 0.878 |
| prism_sl4 | office_4/synthetic_0.5hz/pano | 1.9 | 3.9 | 5.8 | 0.890 |
| prism_sl4 | office_4/synthetic_5.0hz/pano | 2.3 | 3.7 | 6.0 | 0.879 |
| prism_sl4 | apartment_0/synthetic_2.0hz/pano | 7.8 | 70.7 | 78.5 | 0.336 |
| prism_sl4 | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.8 | 101.1 | 0.137 |
| prism_sl4 | apartment_0/synthetic_5.0hz/pano | 18.3 | 77.1 | 95.4 | 0.220 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.7 | 6.9 | 9.5 | 0.844 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 2.5 | 19.7 | 22.2 | 0.783 |
| pi3 | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 25.5 | 7.0 | 32.5 | 0.454 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 22.3 | 7.0 | 29.3 | 0.564 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 22.4 | 7.0 | 29.4 | 0.549 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 23.9 | 8.2 | 32.1 | 0.457 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 26.6 | 10.6 | 37.2 | 0.403 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 27.1 | 10.6 | 37.7 | 0.498 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 20.7 | 6.3 | 27.0 | 0.530 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 23.5 | 8.1 | 31.6 | 0.467 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 22.9 | 7.8 | 30.7 | 0.465 |
| pi3 | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 22.6 | 5.2 | 27.8 | 0.622 |
| pi3 | apartment_1/loop_2.0hz_s0/synthetic_fov | 35.8 | 115.3 | 151.1 | 0.155 |
| pi3 | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 35.5 | 48.3 | 83.8 | 0.159 |
| pi3 | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 35.3 | 64.2 | 99.5 | 0.166 |
| pi3 | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 37.9 | 146.0 | 184.0 | 0.114 |
| pi3 | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 36.8 | 148.2 | 185.0 | 0.111 |
| pi3 | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 88.2 | 51.4 | 139.7 | 0.056 |
| pi3 | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 40.0 | 116.5 | 156.4 | 0.120 |
| pi3 | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 35.7 | 161.9 | 197.6 | 0.116 |
| pi3 | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 37.1 | 174.8 | 211.8 | 0.068 |
| pi3 | apartment_1/loop_2.0hz_s1/synthetic_fov | 36.8 | 116.5 | 153.3 | 0.113 |
| pi3 | hotel_0/loop_2.0hz_s0/synthetic_fov | 5.3 | 31.7 | 37.0 | 0.419 |
| pi3 | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 10.7 | 20.8 | 31.5 | 0.317 |
| pi3 | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 4.2 | 14.0 | 18.2 | 0.615 |
| pi3 | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 11.4 | 59.2 | 70.6 | 0.242 |
| pi3 | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 12.8 | 97.5 | 110.2 | 0.189 |
| pi3 | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 11.5 | 33.3 | 44.8 | 0.268 |
| pi3 | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 3.6 | 11.6 | 15.2 | 0.715 |
| pi3 | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 10.4 | 46.3 | 56.8 | 0.280 |
| pi3 | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 12.3 | 26.9 | 39.2 | 0.294 |
| pi3 | hotel_0/loop_2.0hz_s1/synthetic_fov | 4.0 | 10.5 | 14.5 | 0.711 |
| pi3 | apartment_0/loop_2.0hz_s0/synthetic_fov | 5.9 | 66.1 | 72.0 | 0.435 |
| pi3 | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 8.4 | 80.1 | 88.4 | 0.304 |
| pi3 | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 7.7 | 80.1 | 87.8 | 0.333 |
| pi3 | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 5.4 | 72.4 | 77.8 | 0.433 |
| pi3 | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 5.4 | 73.7 | 79.0 | 0.380 |
| pi3 | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 8.1 | 86.5 | 94.5 | 0.229 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 4.9 | 71.5 | 76.4 | 0.464 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 5.4 | 73.8 | 79.2 | 0.380 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 5.9 | 71.4 | 77.3 | 0.461 |
| pi3 | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 8.6 | 78.0 | 86.6 | 0.353 |
| pi3 | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 4.9 | 71.6 | 76.4 | 0.465 |
| pi3 | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 5.9 | 71.6 | 77.5 | 0.461 |
| pi3 | apartment_0/loop_2.0hz_s1/synthetic_fov | 8.2 | 81.2 | 89.3 | 0.304 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s0/pano | 24.6 | 24.1 | 48.7 | 0.264 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 7.0 | 16.8 | 23.9 | 0.547 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 5.8 | 23.8 | 29.6 | 0.591 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 12.5 | 15.2 | 27.7 | 0.334 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 3.5 | 18.7 | 22.3 | 0.648 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 4.5 | 18.7 | 23.1 | 0.627 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 6.5 | 22.2 | 28.6 | 0.562 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 11.8 | 12.6 | 24.4 | 0.317 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 19.5 | 17.7 | 37.3 | 0.236 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s1/pano | 6.8 | 16.7 | 23.5 | 0.573 |
| prism_sim3 | apartment_1/stopgo_2.0hz_s1/pano | 41.0 | 225.2 | 266.1 | 0.020 |
| prism_sim3 | apartment_1/synthetic_2.0hz_s1/pano | 43.3 | 130.3 | 173.5 | 0.095 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s0/pano | 35.7 | 151.4 | 187.1 | 0.058 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s1/pano | 30.9 | 149.6 | 180.5 | 0.117 |
| prism_sim3 | apartment_1/synthetic_5.0hz_s1/pano | 37.7 | 118.2 | 155.9 | 0.091 |
| prism_sim3 | apartment_1/loop_2.0hz_s1/pano | 32.4 | 174.1 | 206.5 | 0.078 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s1/pano | 42.6 | 84.2 | 126.8 | 0.179 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s0/pano | 17.9 | 14.3 | 32.1 | 0.507 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s1/pano | 50.7 | 24.7 | 75.4 | 0.220 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s0/pano | 4.8 | 41.5 | 46.3 | 0.411 |
| prism_sim3 | hotel_0/loop_2.0hz_s1/pano | 64.8 | 18.7 | 83.6 | 0.178 |
| prism_sim3 | apartment_0/loop_2.0hz_s0/pano | 31.1 | 98.8 | 129.9 | 0.077 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s1/pano | 58.7 | 110.5 | 169.3 | 0.137 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s1/pano | 50.5 | 104.2 | 154.7 | 0.149 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s0/pano | 12.1 | 70.0 | 82.0 | 0.275 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s0/pano | 16.3 | 84.8 | 101.0 | 0.137 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s1/pano | 4.9 | 139.7 | 144.6 | 0.342 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s0/pano | 9.3 | 70.8 | 80.1 | 0.345 |
| prism_sim3 | apartment_0/synthetic_5.0hz_s0/pano | 21.3 | 71.7 | 93.0 | 0.210 |
| prism_sim3 | apartment_0/loop_2.0hz_s1/pano | 36.9 | 93.2 | 130.2 | 0.171 |
| prism | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.1 | 0.711 |
| prism | office_4/synthetic_0.5hz/pano | 1.9 | 3.8 | 5.8 | 0.890 |
| prism | office_4/synthetic_5.0hz/pano | 6.3 | 6.2 | 12.4 | 0.637 |
| prism | frl_apartment_0/loop_2.0hz_s0/pano | 20.0 | 12.0 | 32.0 | 0.373 |
| prism | frl_apartment_0/stopgo_2.0hz_s1/pano | 6.9 | 21.7 | 28.6 | 0.501 |
| prism | frl_apartment_0/synthetic_2.0hz_s1/pano | 6.6 | 25.7 | 32.3 | 0.517 |
| prism | frl_apartment_0/stopgo_2.0hz_s0/pano | 5.6 | 8.1 | 13.7 | 0.646 |
| prism | frl_apartment_0/synthetic_0.5hz_s0/pano | 3.5 | 18.6 | 22.2 | 0.649 |
| prism | frl_apartment_0/synthetic_0.5hz_s1/pano | 4.5 | 18.4 | 22.9 | 0.627 |
| prism | frl_apartment_0/synthetic_5.0hz_s1/pano | 7.2 | 23.0 | 30.2 | 0.506 |
| prism | frl_apartment_0/synthetic_2.0hz_s0/pano | 6.1 | 8.2 | 14.3 | 0.629 |
| prism | frl_apartment_0/synthetic_5.0hz_s0/pano | 7.9 | 8.8 | 16.7 | 0.549 |
| prism | frl_apartment_0/loop_2.0hz_s1/pano | 6.4 | 17.6 | 24.1 | 0.540 |
| prism | apartment_1/stopgo_2.0hz_s1/pano | 37.2 | 154.0 | 191.2 | 0.052 |
| prism | apartment_1/synthetic_2.0hz_s1/pano | 32.8 | 148.8 | 181.5 | 0.100 |
| prism | apartment_1/synthetic_0.5hz_s0/pano | 35.7 | 151.2 | 186.8 | 0.058 |
| prism | apartment_1/synthetic_0.5hz_s1/pano | 30.9 | 149.5 | 180.4 | 0.118 |
| prism | apartment_1/synthetic_5.0hz_s1/pano | 43.6 | 126.1 | 169.7 | 0.096 |
| prism | apartment_1/loop_2.0hz_s1/pano | 35.7 | 147.2 | 182.9 | 0.107 |
| prism | hotel_0/synthetic_2.0hz_s1/pano | 44.8 | 82.1 | 127.0 | 0.177 |
| prism | hotel_0/synthetic_0.5hz_s0/pano | 17.8 | 14.3 | 32.1 | 0.507 |
| prism | hotel_0/synthetic_0.5hz_s1/pano | 50.7 | 24.7 | 75.4 | 0.220 |
| prism | hotel_0/synthetic_2.0hz_s0/pano | 2.8 | 35.8 | 38.6 | 0.606 |
| prism | hotel_0/loop_2.0hz_s1/pano | 19.0 | 305.7 | 324.7 | 0.000 |
| prism | apartment_0/loop_2.0hz_s0/pano | 31.9 | 96.0 | 127.9 | 0.095 |
| prism | apartment_0/stopgo_2.0hz_s1/pano | 76.6 | 124.5 | 201.1 | 0.073 |
| prism | apartment_0/synthetic_2.0hz_s1/pano | 66.1 | 112.6 | 178.8 | 0.074 |
| prism | apartment_0/stopgo_2.0hz_s0/pano | 9.8 | 71.0 | 80.8 | 0.350 |
| prism | apartment_0/synthetic_0.5hz_s0/pano | 16.3 | 84.7 | 101.0 | 0.137 |
| prism | apartment_0/synthetic_0.5hz_s1/pano | 4.9 | 140.0 | 144.9 | 0.341 |
| prism | apartment_0/synthetic_2.0hz/pano | 9.3 | 71.1 | 80.4 | 0.345 |
| prism | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.9 | 101.2 | 0.138 |
| prism | apartment_0/synthetic_5.0hz/pano | 21.4 | 72.2 | 93.6 | 0.209 |
| prism | apartment_0/synthetic_5.0hz_s1/pano | 12.3 | 134.4 | 146.7 | 0.305 |
| prism | apartment_0/synthetic_2.0hz_s0/pano | 7.8 | 70.8 | 78.6 | 0.337 |
| prism | apartment_0/synthetic_5.0hz_s0/pano | 18.3 | 77.2 | 95.6 | 0.219 |
| prism | apartment_0/loop_2.0hz_s1/pano | 65.8 | 96.5 | 162.3 | 0.068 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 5.7 | 5.4 | 11.1 | 0.710 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 1.9 | 3.9 | 5.8 | 0.890 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 6.3 | 6.2 | 12.4 | 0.638 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s0/pano | 20.0 | 12.1 | 32.0 | 0.371 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s1/pano | 6.9 | 22.0 | 29.0 | 0.500 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s0/pano | 5.6 | 8.1 | 13.7 | 0.645 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s1/pano | 6.5 | 17.6 | 24.0 | 0.539 |
| prism_nostill | apartment_1/stopgo_2.0hz_s1/pano | 37.3 | 154.0 | 191.3 | 0.052 |
| prism_nostill | apartment_1/loop_2.0hz_s1/pano | 35.5 | 147.7 | 183.3 | 0.107 |
| prism_nostill | hotel_0/loop_2.0hz_s1/pano | 19.1 | 305.1 | 324.1 | 0.000 |
| prism_nostill | apartment_0/loop_2.0hz_s0/pano | 31.9 | 96.2 | 128.1 | 0.094 |
| prism_nostill | apartment_0/stopgo_2.0hz_s1/pano | 76.7 | 124.2 | 200.8 | 0.073 |
| prism_nostill | apartment_0/stopgo_2.0hz_s0/pano | 9.8 | 71.0 | 80.7 | 0.352 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 9.2 | 71.0 | 80.2 | 0.346 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.8 | 101.1 | 0.136 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 21.2 | 71.8 | 93.0 | 0.211 |
| prism_nostill | apartment_0/loop_2.0hz_s1/pano | 65.7 | 96.5 | 162.2 | 0.068 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.0 | 0.707 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 1.9 | 3.9 | 5.8 | 0.889 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 3.7 | 4.7 | 8.4 | 0.776 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s0/pano | 19.7 | 12.1 | 31.8 | 0.369 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s1/pano | 6.9 | 21.8 | 28.8 | 0.506 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s0/pano | 5.5 | 8.0 | 13.6 | 0.640 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s1/pano | 6.5 | 17.5 | 24.0 | 0.541 |
| prism_nolock | apartment_1/stopgo_2.0hz_s1/pano | 37.3 | 154.3 | 191.6 | 0.051 |
| prism_nolock | apartment_1/loop_2.0hz_s1/pano | 35.6 | 147.8 | 183.5 | 0.107 |
| prism_nolock | hotel_0/loop_2.0hz_s1/pano | 19.8 | 305.5 | 325.3 | 0.000 |
| prism_nolock | apartment_0/loop_2.0hz_s0/pano | 31.9 | 96.3 | 128.2 | 0.097 |
| prism_nolock | apartment_0/stopgo_2.0hz_s1/pano | 76.7 | 124.4 | 201.1 | 0.074 |
| prism_nolock | apartment_0/stopgo_2.0hz_s0/pano | 9.9 | 71.0 | 81.0 | 0.354 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 6.4 | 69.9 | 76.2 | 0.370 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.4 | 100.7 | 0.137 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 23.8 | 84.8 | 108.6 | 0.127 |
| prism_nolock | apartment_0/loop_2.0hz_s1/pano | 65.5 | 96.6 | 162.0 | 0.068 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.1 | 19.2 | 30.3 | 0.390 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 12.6 | 33.9 | 46.5 | 0.328 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 11.8 | 16.5 | 28.3 | 0.375 |
| mapanything | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 41.1 | 27.9 | 69.0 | 0.183 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 36.4 | 30.8 | 67.2 | 0.197 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 37.2 | 31.4 | 68.6 | 0.204 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 33.8 | 17.9 | 51.6 | 0.224 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 34.0 | 23.2 | 57.2 | 0.221 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 45.2 | 44.5 | 89.8 | 0.136 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 34.9 | 24.5 | 59.4 | 0.204 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 35.1 | 18.6 | 53.6 | 0.233 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 30.9 | 14.4 | 45.3 | 0.277 |
| mapanything | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 50.6 | 44.9 | 95.5 | 0.087 |
| mapanything | apartment_1/loop_2.0hz_s0/synthetic_fov | 33.1 | 278.2 | 311.4 | 0.024 |
| mapanything | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 24.7 | 325.8 | 350.5 | 0.013 |
| mapanything | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 37.0 | 296.8 | 333.8 | 0.015 |
| mapanything | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 37.9 | 260.2 | 298.1 | 0.022 |
| mapanything | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 43.8 | 174.6 | 218.4 | 0.042 |
| mapanything | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 40.6 | 220.0 | 260.6 | 0.020 |
| mapanything | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 48.1 | 270.5 | 318.6 | 0.019 |
| mapanything | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 31.6 | 191.1 | 222.7 | 0.085 |
| mapanything | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 30.1 | 195.4 | 225.5 | 0.087 |
| mapanything | apartment_1/loop_2.0hz_s1/synthetic_fov | 36.3 | 123.5 | 159.8 | 0.073 |
| mapanything | hotel_0/loop_2.0hz_s0/synthetic_fov | 9.2 | 54.4 | 63.6 | 0.277 |
| mapanything | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 9.3 | 19.1 | 28.5 | 0.307 |
| mapanything | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 13.7 | 19.4 | 33.1 | 0.269 |
| mapanything | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 14.0 | 71.0 | 85.0 | 0.215 |
| mapanything | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 8.4 | 92.4 | 100.9 | 0.216 |
| mapanything | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 14.1 | 35.3 | 49.4 | 0.232 |
| mapanything | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 11.6 | 16.8 | 28.4 | 0.322 |
| mapanything | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 9.8 | 58.3 | 68.0 | 0.286 |
| mapanything | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 13.5 | 28.8 | 42.2 | 0.275 |
| mapanything | hotel_0/loop_2.0hz_s1/synthetic_fov | 16.3 | 16.7 | 33.0 | 0.337 |
| mapanything | apartment_0/loop_2.0hz_s0/synthetic_fov | 14.0 | 70.6 | 84.6 | 0.206 |
| mapanything | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 15.4 | 73.6 | 89.0 | 0.201 |
| mapanything | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 14.9 | 75.3 | 90.2 | 0.201 |
| mapanything | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 14.8 | 75.5 | 90.4 | 0.215 |
| mapanything | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 23.1 | 87.2 | 110.3 | 0.124 |
| mapanything | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 16.2 | 93.8 | 110.0 | 0.164 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 14.7 | 75.6 | 90.3 | 0.219 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 23.1 | 87.3 | 110.4 | 0.124 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 16.4 | 69.6 | 86.0 | 0.215 |
| mapanything | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 16.6 | 74.2 | 90.9 | 0.209 |
| mapanything | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 14.7 | 75.5 | 90.2 | 0.219 |
| mapanything | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 16.4 | 69.7 | 86.1 | 0.215 |
| mapanything | apartment_0/loop_2.0hz_s1/synthetic_fov | 13.0 | 79.5 | 92.6 | 0.225 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.0 | 0.709 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 1.9 | 3.9 | 5.8 | 0.889 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 3.7 | 4.7 | 8.4 | 0.776 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s0/pano | 19.9 | 12.1 | 31.9 | 0.373 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s1/pano | 6.9 | 21.3 | 28.1 | 0.511 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s0/pano | 5.5 | 8.0 | 13.5 | 0.651 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s1/pano | 6.4 | 17.6 | 24.0 | 0.541 |
| prism_noguards | apartment_1/stopgo_2.0hz_s1/pano | 39.3 | 183.4 | 222.7 | 0.051 |
| prism_noguards | apartment_1/loop_2.0hz_s1/pano | 36.8 | 133.3 | 170.1 | 0.116 |
| prism_noguards | hotel_0/loop_2.0hz_s1/pano | 19.0 | 305.4 | 324.4 | 0.000 |
| prism_noguards | apartment_0/loop_2.0hz_s0/pano | 31.9 | 96.2 | 128.1 | 0.097 |
| prism_noguards | apartment_0/stopgo_2.0hz_s1/pano | 70.1 | 133.0 | 203.1 | 0.066 |
| prism_noguards | apartment_0/stopgo_2.0hz_s0/pano | 9.9 | 71.8 | 81.8 | 0.339 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 6.4 | 69.9 | 76.3 | 0.369 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 16.3 | 84.8 | 101.1 | 0.138 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 24.7 | 85.4 | 110.0 | 0.117 |
| prism_noguards | apartment_0/loop_2.0hz_s1/pano | 64.8 | 96.4 | 161.2 | 0.066 |
| prism_se3 | office_4/synthetic_2.0hz/pano | 5.6 | 5.4 | 11.0 | 0.712 |
| prism_se3 | office_4/synthetic_5.0hz/pano | 6.2 | 6.2 | 12.4 | 0.637 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s0/pano | 24.6 | 24.3 | 48.9 | 0.265 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 7.1 | 16.7 | 23.8 | 0.547 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 5.8 | 23.9 | 29.7 | 0.592 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 12.5 | 15.1 | 27.6 | 0.332 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 3.6 | 18.6 | 22.2 | 0.647 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 4.5 | 18.3 | 22.8 | 0.628 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 6.5 | 22.3 | 28.8 | 0.561 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 11.8 | 12.6 | 24.5 | 0.316 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 19.5 | 17.8 | 37.3 | 0.237 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s1/pano | 6.8 | 16.5 | 23.3 | 0.574 |
| prism_se3 | apartment_1/stopgo_2.0hz_s1/pano | 35.6 | 206.8 | 242.4 | 0.058 |
| prism_se3 | apartment_1/synthetic_2.0hz_s1/pano | 43.1 | 130.6 | 173.7 | 0.102 |
| prism_se3 | apartment_1/synthetic_0.5hz_s0/pano | 35.5 | 151.4 | 186.9 | 0.057 |
| prism_se3 | apartment_1/synthetic_0.5hz_s1/pano | 30.9 | 149.7 | 180.6 | 0.116 |
| prism_se3 | apartment_1/synthetic_5.0hz_s1/pano | 37.8 | 118.1 | 155.9 | 0.091 |
| prism_se3 | apartment_1/loop_2.0hz_s1/pano | 32.5 | 174.8 | 207.3 | 0.073 |
| prism_se3 | hotel_0/synthetic_2.0hz_s1/pano | 43.8 | 83.2 | 127.1 | 0.150 |
| prism_se3 | hotel_0/synthetic_0.5hz_s0/pano | 17.9 | 14.3 | 32.2 | 0.508 |
| prism_se3 | hotel_0/synthetic_0.5hz_s1/pano | 50.8 | 24.6 | 75.5 | 0.220 |
| prism_se3 | hotel_0/synthetic_2.0hz_s0/pano | 4.8 | 41.8 | 46.6 | 0.411 |
| prism_se3 | hotel_0/loop_2.0hz_s1/pano | 67.3 | 20.6 | 88.0 | 0.158 |
| prism_se3 | apartment_0/loop_2.0hz_s0/pano | 31.0 | 99.0 | 130.1 | 0.077 |
| prism_se3 | apartment_0/stopgo_2.0hz_s1/pano | 48.2 | 116.8 | 165.0 | 0.129 |
| prism_se3 | apartment_0/synthetic_2.0hz_s1/pano | 41.6 | 106.6 | 148.1 | 0.158 |
| prism_se3 | apartment_0/stopgo_2.0hz_s0/pano | 13.4 | 69.9 | 83.4 | 0.221 |
| prism_se3 | apartment_0/synthetic_0.5hz_s0/pano | 16.3 | 84.8 | 101.0 | 0.137 |
| prism_se3 | apartment_0/synthetic_0.5hz_s1/pano | 4.9 | 140.0 | 144.9 | 0.340 |
| prism_se3 | apartment_0/synthetic_2.0hz/pano | 9.3 | 70.9 | 80.1 | 0.346 |
| prism_se3 | apartment_0/synthetic_0.5hz/pano | 16.3 | 85.0 | 101.3 | 0.137 |
| prism_se3 | apartment_0/synthetic_5.0hz/pano | 21.3 | 71.9 | 93.2 | 0.210 |
| prism_se3 | apartment_0/synthetic_5.0hz_s1/pano | 18.7 | 130.5 | 149.3 | 0.197 |
| prism_se3 | apartment_0/synthetic_2.0hz_s0/pano | 9.3 | 71.2 | 80.5 | 0.345 |
| prism_se3 | apartment_0/synthetic_5.0hz_s0/pano | 21.2 | 71.7 | 92.9 | 0.211 |
| prism_se3 | apartment_0/loop_2.0hz_s1/pano | 36.8 | 124.1 | 160.9 | 0.201 |


## Table D — Cloud cleanliness & size

*Outlier% = kNN statistical outliers (density-independent fluffiness — the fair noise measure across sparse vs dense clouds); Acc-p95 = 95th-pct pred→GT distance (worst floaters); noise% = points >10 cm from GT; prec@2cm = within 2 cm.*

| Method | Run | Points | Size MB↓ | Outlier %↓ | Acc-p95 cm↓ | Noise %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 122538 | 1.8 | 2.7 | 11.9 | 6.1 | 39.9 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 66040 | 1.0 | 2.4 | 6.5 | 3.3 | 63.8 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 148265 | 2.2 | 3.3 | 15.6 | 10.4 | 23.3 |
| laser | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 591539 | 8.9 | 3.8 | 116.4 | 87.2 | 1.9 |
| laser | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 522728 | 7.8 | 3.4 | 31.5 | 29.2 | 15.7 |
| laser | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 486520 | 7.3 | 3.2 | 27.0 | 27.1 | 16.3 |
| laser | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 473668 | 7.1 | 4.1 | 42.6 | 41.5 | 11.6 |
| laser | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 177192 | 2.7 | 4.0 | 35.1 | 43.6 | 11.8 |
| laser | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 146673 | 2.2 | 3.1 | 21.3 | 12.1 | 25.8 |
| laser | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 752813 | 11.3 | 3.8 | 47.7 | 45.1 | 9.9 |
| laser | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 414160 | 6.2 | 4.0 | 46.2 | 36.5 | 11.1 |
| laser | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 616196 | 9.2 | 4.0 | 61.1 | 62.4 | 7.0 |
| laser | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 565478 | 8.5 | 3.1 | 33.1 | 38.2 | 12.0 |
| laser | apartment_1/loop_2.0hz_s0/synthetic_fov | 382857 | 5.7 | 3.7 | 80.0 | 80.2 | 3.5 |
| laser | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 480298 | 7.2 | 3.2 | 85.7 | 84.6 | 2.8 |
| laser | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 554361 | 8.3 | 3.3 | 79.5 | 72.4 | 5.5 |
| laser | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 185163 | 2.8 | 3.4 | 82.9 | 87.1 | 1.9 |
| laser | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 79113 | 1.2 | 3.5 | 88.8 | 70.3 | 6.7 |
| laser | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 121682 | 1.8 | 2.8 | 80.3 | 68.2 | 8.0 |
| laser | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 660616 | 9.9 | 3.0 | 77.7 | 68.8 | 5.5 |
| laser | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 182768 | 2.7 | 3.5 | 77.2 | 88.3 | 2.7 |
| laser | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 441437 | 6.6 | 3.8 | 70.0 | 64.6 | 8.7 |
| laser | apartment_1/loop_2.0hz_s1/synthetic_fov | 812425 | 12.2 | 3.5 | 79.9 | 71.6 | 5.5 |
| laser | hotel_0/loop_2.0hz_s0/synthetic_fov | 242056 | 3.6 | 2.5 | 53.4 | 71.3 | 7.3 |
| laser | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 154408 | 2.3 | 2.9 | 62.6 | 69.7 | 6.4 |
| laser | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 281603 | 4.2 | 3.0 | 59.5 | 76.7 | 4.6 |
| laser | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 213881 | 3.2 | 2.4 | 81.8 | 61.6 | 9.5 |
| laser | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 70989 | 1.1 | 2.5 | 17.4 | 13.2 | 29.3 |
| laser | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 120563 | 1.8 | 2.9 | 35.9 | 37.7 | 15.1 |
| laser | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 250330 | 3.8 | 2.5 | 52.8 | 62.0 | 11.4 |
| laser | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 197652 | 3.0 | 2.3 | 75.6 | 59.2 | 11.3 |
| laser | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 336764 | 5.0 | 2.9 | 68.7 | 40.4 | 17.4 |
| laser | hotel_0/loop_2.0hz_s1/synthetic_fov | 432089 | 6.5 | 3.2 | 73.1 | 67.1 | 8.2 |
| laser | apartment_0/loop_2.0hz_s0/synthetic_fov | 379968 | 5.7 | 3.6 | 81.2 | 72.7 | 3.5 |
| laser | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 683836 | 10.3 | 3.7 | 37.7 | 23.1 | 11.3 |
| laser | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 696143 | 10.4 | 3.8 | 36.4 | 35.8 | 8.3 |
| laser | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 346365 | 5.2 | 3.6 | 42.1 | 28.7 | 11.7 |
| laser | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 124669 | 1.9 | 3.9 | 26.0 | 17.9 | 12.8 |
| laser | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 175767 | 2.6 | 4.0 | 22.4 | 13.3 | 16.5 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 319033 | 4.8 | 3.5 | 39.9 | 24.3 | 12.5 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 124669 | 1.9 | 3.9 | 26.1 | 17.9 | 12.9 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 642544 | 9.6 | 3.5 | 40.3 | 36.1 | 6.1 |
| laser | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 1241884 | 18.6 | 3.5 | 63.9 | 57.2 | 4.6 |
| laser | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 319033 | 4.8 | 3.5 | 39.9 | 24.2 | 12.4 |
| laser | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 642544 | 9.6 | 3.5 | 40.3 | 36.1 | 6.1 |
| laser | apartment_0/loop_2.0hz_s1/synthetic_fov | 808130 | 12.1 | 3.7 | 39.1 | 37.0 | 7.1 |
| panovggt | office_4/synthetic_2.0hz/pano | 4664513 | 70.0 | 2.4 | 5.2 | 1.4 | 52.7 |
| panovggt | office_4/synthetic_0.5hz/pano | 2694678 | 40.4 | 2.2 | 4.4 | 0.6 | 57.9 |
| panovggt | office_4/synthetic_5.0hz/pano | 6147230 | 92.2 | 2.6 | 6.4 | 2.6 | 47.9 |
| panovggt | frl_apartment_0/loop_2.0hz_s0/pano | 10920457 | 163.8 | 3.0 | 19.0 | 12.7 | 24.0 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s1/pano | 7527491 | 112.9 | 3.3 | 12.0 | 6.6 | 29.1 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s1/pano | 7567192 | 113.5 | 3.3 | 11.9 | 6.5 | 29.3 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s0/pano | 9048700 | 135.7 | 3.0 | 11.5 | 6.4 | 28.7 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s0/pano | 4343225 | 65.2 | 3.3 | 8.8 | 3.9 | 33.6 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s1/pano | 3708676 | 55.6 | 3.4 | 7.8 | 3.5 | 34.5 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s1/pano | 11062839 | 165.9 | 3.2 | 15.5 | 9.5 | 25.6 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s0/pano | 8957231 | 134.4 | 3.0 | 11.4 | 6.3 | 28.8 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s0/pano | 12704841 | 190.6 | 3.0 | 15.2 | 9.8 | 25.1 |
| panovggt | frl_apartment_0/loop_2.0hz_s1/pano | 8506550 | 127.6 | 3.1 | 12.5 | 7.1 | 28.5 |
| panovggt | apartment_1/loop_2.0hz_s0/pano | 7719641 | 115.8 | 4.3 | 81.7 | 81.9 | 3.1 |
| panovggt | apartment_1/stopgo_2.0hz_s1/pano | 6634108 | 99.5 | 4.6 | 83.0 | 87.3 | 2.1 |
| panovggt | apartment_1/synthetic_2.0hz_s1/pano | 7336468 | 110.0 | 4.1 | 83.2 | 83.6 | 3.1 |
| panovggt | apartment_1/stopgo_2.0hz_s0/pano | 5491120 | 82.4 | 5.0 | 81.4 | 71.2 | 5.5 |
| panovggt | apartment_1/synthetic_0.5hz_s0/pano | 2366072 | 35.5 | 4.4 | 81.9 | 82.7 | 3.0 |
| panovggt | apartment_1/synthetic_0.5hz_s1/pano | 3355533 | 50.3 | 5.0 | 88.1 | 82.3 | 2.7 |
| panovggt | apartment_1/synthetic_5.0hz_s1/pano | 10231573 | 153.5 | 3.9 | 79.2 | 84.5 | 2.7 |
| panovggt | apartment_1/synthetic_2.0hz_s0/pano | 5080754 | 76.2 | 5.2 | 79.4 | 64.6 | 9.1 |
| panovggt | apartment_1/synthetic_5.0hz_s0/pano | 7957552 | 119.4 | 5.1 | 75.1 | 69.5 | 5.8 |
| panovggt | apartment_1/loop_2.0hz_s1/pano | 8029592 | 120.4 | 4.7 | 82.9 | 77.2 | 5.4 |
| panovggt | hotel_0/loop_2.0hz_s0/pano | 5711654 | 85.7 | 4.2 | 11.1 | 6.2 | 30.6 |
| panovggt | hotel_0/stopgo_2.0hz_s1/pano | 5440559 | 81.6 | 3.2 | 20.1 | 12.7 | 17.4 |
| panovggt | hotel_0/synthetic_2.0hz_s1/pano | 4954687 | 74.3 | 3.0 | 31.2 | 49.3 | 8.2 |
| panovggt | hotel_0/stopgo_2.0hz_s0/pano | 5030245 | 75.5 | 4.0 | 9.1 | 4.1 | 36.3 |
| panovggt | hotel_0/synthetic_0.5hz_s0/pano | 2292223 | 34.4 | 4.8 | 8.2 | 3.2 | 36.2 |
| panovggt | hotel_0/synthetic_0.5hz_s1/pano | 2296357 | 34.5 | 4.4 | 7.1 | 2.8 | 55.6 |
| panovggt | hotel_0/synthetic_5.0hz_s1/pano | 7478115 | 112.2 | 2.7 | 34.9 | 48.4 | 8.7 |
| panovggt | hotel_0/synthetic_2.0hz_s0/pano | 4873958 | 73.1 | 4.1 | 11.5 | 6.7 | 19.9 |
| panovggt | hotel_0/synthetic_5.0hz_s0/pano | 7413916 | 111.2 | 3.4 | 13.0 | 7.8 | 30.3 |
| panovggt | hotel_0/loop_2.0hz_s1/pano | 6235272 | 93.5 | 2.8 | 31.4 | 39.0 | 9.3 |
| panovggt | apartment_0/loop_2.0hz_s0/pano | 8077956 | 121.2 | 4.4 | 34.9 | 43.7 | 3.8 |
| panovggt | apartment_0/stopgo_2.0hz_s1/pano | 7592198 | 113.9 | 4.4 | 16.1 | 12.2 | 13.0 |
| panovggt | apartment_0/synthetic_2.0hz_s1/pano | 7377577 | 110.7 | 4.3 | 15.7 | 12.8 | 11.7 |
| panovggt | apartment_0/stopgo_2.0hz_s0/pano | 7338410 | 110.1 | 4.2 | 20.2 | 24.4 | 9.8 |
| panovggt | apartment_0/synthetic_0.5hz_s0/pano | 3357864 | 50.4 | 3.6 | 49.6 | 58.3 | 3.6 |
| panovggt | apartment_0/synthetic_0.5hz_s1/pano | 3492385 | 52.4 | 3.6 | 11.6 | 7.0 | 14.5 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 7467450 | 112.0 | 4.3 | 20.6 | 24.2 | 9.5 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 3357864 | 50.4 | 3.6 | 49.5 | 58.2 | 3.5 |
| panovggt | apartment_0/synthetic_5.0hz_s1/pano | 10814174 | 162.2 | 4.8 | 21.2 | 18.6 | 10.5 |
| panovggt | apartment_0/synthetic_2.0hz_s0/pano | 7467450 | 112.0 | 4.3 | 20.6 | 24.2 | 9.4 |
| panovggt | apartment_0/synthetic_5.0hz_s0/pano | 11260789 | 168.9 | 4.6 | 20.4 | 21.1 | 9.7 |
| panovggt | apartment_0/loop_2.0hz_s1/pano | 7503919 | 112.6 | 4.5 | 17.1 | 16.8 | 9.6 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3177384 | 85.8 | 4.3 | 6.4 | 1.0 | 28.2 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 1589087 | 42.9 | 3.7 | 10.9 | 6.1 | 39.6 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 3797683 | 102.5 | 4.6 | 10.8 | 5.7 | 33.6 |
| vggtslam | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 6377059 | 172.2 | 3.4 | 64.3 | 53.8 | 7.4 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 2845586 | 76.8 | 3.6 | 7.3 | 2.9 | 29.4 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 2845586 | 76.8 | 3.6 | 7.3 | 2.8 | 29.3 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 4410610 | 119.1 | 3.3 | 30.4 | 60.6 | 8.6 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 1975686 | 53.3 | 3.3 | 47.4 | 45.6 | 12.8 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 1675019 | 45.2 | 4.1 | 7.0 | 1.9 | 30.8 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 4110661 | 111.0 | 3.8 | 14.6 | 10.0 | 22.4 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 4410610 | 119.1 | 3.3 | 30.5 | 60.6 | 8.6 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 5610697 | 151.5 | 4.0 | 122.5 | 87.6 | 2.3 |
| vggtslam | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 3804462 | 102.7 | 4.2 | 6.8 | 1.4 | 30.5 |
| vggtslam | apartment_1/loop_2.0hz_s0/synthetic_fov | 4722169 | 127.5 | 3.8 | 89.5 | 85.9 | 2.7 |
| vggtslam | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 2862919 | 77.3 | 3.1 | 89.1 | 81.8 | 4.8 |
| vggtslam | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 2862919 | 77.3 | 3.1 | 89.2 | 81.9 | 4.8 |
| vggtslam | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 3768547 | 101.8 | 4.3 | 41.6 | 48.1 | 10.7 |
| vggtslam | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 974939 | 26.3 | 3.6 | 80.7 | 80.3 | 2.8 |
| vggtslam | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 1495078 | 40.4 | 3.8 | 96.0 | 78.5 | 2.8 |
| vggtslam | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 5891383 | 159.1 | 4.9 | 79.5 | 93.1 | 1.1 |
| vggtslam | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 3058545 | 82.6 | 4.5 | 87.2 | 88.9 | 2.0 |
| vggtslam | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 4049742 | 109.3 | 3.5 | 72.6 | 55.3 | 15.9 |
| vggtslam | apartment_1/loop_2.0hz_s1/synthetic_fov | 4825477 | 130.3 | 3.2 | 95.4 | 66.5 | 7.7 |
| vggtslam | hotel_0/loop_2.0hz_s0/synthetic_fov | 3597457 | 97.1 | 4.3 | 68.0 | 82.2 | 3.2 |
| vggtslam | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 4909788 | 132.6 | 4.0 | 52.3 | 88.5 | 2.3 |
| vggtslam | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 3026397 | 81.7 | 2.9 | 56.1 | 62.0 | 8.0 |
| vggtslam | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 2834285 | 76.5 | 4.0 | 72.5 | 89.5 | 1.2 |
| vggtslam | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 1064556 | 28.7 | 5.0 | 10.9 | 7.5 | 22.8 |
| vggtslam | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 1333506 | 36.0 | 4.8 | 39.3 | 76.2 | 8.7 |
| vggtslam | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 5313185 | 143.5 | 4.2 | 67.3 | 77.8 | 5.2 |
| vggtslam | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 2834285 | 76.5 | 4.0 | 72.3 | 89.5 | 1.2 |
| vggtslam | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 4000990 | 108.0 | 3.1 | 50.4 | 46.8 | 12.0 |
| vggtslam | hotel_0/loop_2.0hz_s1/synthetic_fov | 3986361 | 107.6 | 3.4 | 64.0 | 72.1 | 6.1 |
| vggtslam | apartment_0/loop_2.0hz_s0/synthetic_fov | 5815657 | 157.0 | 3.7 | 79.8 | 79.4 | 2.1 |
| vggtslam | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 5001792 | 135.1 | 3.4 | 60.8 | 53.1 | 6.4 |
| vggtslam | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 5001792 | 135.1 | 3.4 | 60.7 | 53.1 | 6.3 |
| vggtslam | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 3155185 | 85.2 | 2.9 | 78.4 | 82.3 | 1.6 |
| vggtslam | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 2127018 | 57.4 | 4.0 | 73.2 | 70.3 | 3.3 |
| vggtslam | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 2588196 | 69.9 | 3.7 | 13.6 | 9.2 | 14.9 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 3155185 | 85.2 | 2.9 | 79.0 | 82.7 | 1.6 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 2127018 | 57.4 | 4.0 | 73.1 | 70.4 | 3.2 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 6077135 | 164.1 | 3.5 | 67.7 | 64.4 | 3.4 |
| vggtslam | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 6823396 | 184.2 | 3.0 | 75.9 | 77.1 | 2.1 |
| vggtslam | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 3155185 | 85.2 | 2.9 | 78.7 | 83.0 | 1.7 |
| vggtslam | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 6077135 | 164.1 | 3.5 | 67.4 | 63.9 | 3.2 |
| vggtslam | apartment_0/loop_2.0hz_s1/synthetic_fov | 6228001 | 168.2 | 3.6 | 55.9 | 48.3 | 6.6 |
| prism_sl4 | office_4/synthetic_2.0hz/pano | 523023 | 7.8 | 1.9 | 3.6 | 0.4 | 72.2 |
| prism_sl4 | office_4/synthetic_0.5hz/pano | 544861 | 8.2 | 2.2 | 3.9 | 0.2 | 66.3 |
| prism_sl4 | office_4/synthetic_5.0hz/pano | 557085 | 8.4 | 1.9 | 4.1 | 0.2 | 59.7 |
| prism_sl4 | apartment_0/synthetic_2.0hz/pano | 1368265 | 20.5 | 2.3 | 18.8 | 21.6 | 9.2 |
| prism_sl4 | apartment_0/synthetic_0.5hz/pano | 1383444 | 20.8 | 2.2 | 52.4 | 57.5 | 3.7 |
| prism_sl4 | apartment_0/synthetic_5.0hz/pano | 1647020 | 24.7 | 2.5 | 51.0 | 38.7 | 7.0 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 1077863 | 16.2 | 2.3 | 5.2 | 0.5 | 47.6 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 680452 | 10.2 | 1.7 | 4.5 | 0.3 | 45.3 |
| pi3 | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 3291721 | 49.4 | 2.9 | 28.1 | 31.0 | 16.3 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 2303501 | 34.5 | 3.0 | 11.9 | 8.9 | 22.0 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 2342016 | 35.1 | 3.0 | 12.4 | 9.9 | 22.3 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 2574163 | 38.6 | 2.6 | 19.7 | 26.0 | 15.9 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 1422184 | 21.3 | 2.9 | 18.3 | 24.7 | 17.1 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 1295285 | 19.4 | 3.1 | 14.2 | 18.3 | 20.6 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 3228876 | 48.4 | 2.9 | 14.7 | 14.1 | 18.9 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 2562224 | 38.4 | 2.7 | 16.7 | 21.7 | 17.2 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 3416287 | 51.2 | 2.8 | 21.3 | 25.9 | 16.6 |
| pi3 | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 2795276 | 41.9 | 2.9 | 11.5 | 8.5 | 23.9 |
| pi3 | apartment_1/loop_2.0hz_s0/synthetic_fov | 1345312 | 20.2 | 2.4 | 80.6 | 72.1 | 6.0 |
| pi3 | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 1315851 | 19.7 | 2.8 | 85.1 | 77.0 | 4.9 |
| pi3 | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 1449382 | 21.7 | 2.7 | 82.5 | 77.5 | 4.2 |
| pi3 | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 877222 | 13.2 | 1.8 | 93.1 | 73.7 | 7.8 |
| pi3 | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 434858 | 6.5 | 1.5 | 85.1 | 66.0 | 14.4 |
| pi3 | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 585680 | 8.8 | 2.0 | 72.3 | 74.2 | 4.4 |
| pi3 | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 2559287 | 38.4 | 3.5 | 85.1 | 85.1 | 2.6 |
| pi3 | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 879557 | 13.2 | 1.8 | 89.3 | 72.3 | 7.7 |
| pi3 | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 1250805 | 18.8 | 2.4 | 83.2 | 83.2 | 2.9 |
| pi3 | apartment_1/loop_2.0hz_s1/synthetic_fov | 1537373 | 23.1 | 2.7 | 80.8 | 83.2 | 2.9 |
| pi3 | hotel_0/loop_2.0hz_s0/synthetic_fov | 542591 | 8.1 | 1.7 | 13.3 | 10.8 | 19.1 |
| pi3 | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 574658 | 8.6 | 2.6 | 38.8 | 32.7 | 15.5 |
| pi3 | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 544351 | 8.2 | 2.4 | 10.4 | 5.7 | 25.4 |
| pi3 | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 488893 | 7.3 | 1.6 | 34.9 | 44.3 | 12.3 |
| pi3 | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 268661 | 4.0 | 1.8 | 35.7 | 43.1 | 17.2 |
| pi3 | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 295478 | 4.4 | 3.0 | 36.5 | 38.6 | 16.3 |
| pi3 | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 638648 | 9.6 | 2.5 | 8.8 | 4.3 | 46.0 |
| pi3 | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 494614 | 7.4 | 1.7 | 34.8 | 39.0 | 17.3 |
| pi3 | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 700483 | 10.5 | 3.1 | 31.3 | 46.2 | 16.6 |
| pi3 | hotel_0/loop_2.0hz_s1/synthetic_fov | 631840 | 9.5 | 2.3 | 8.1 | 3.6 | 34.7 |
| pi3 | apartment_0/loop_2.0hz_s0/synthetic_fov | 2182175 | 32.7 | 3.3 | 13.4 | 9.8 | 12.5 |
| pi3 | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 2027788 | 30.4 | 3.8 | 20.0 | 19.8 | 6.9 |
| pi3 | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 1976732 | 29.6 | 3.6 | 17.8 | 14.2 | 7.4 |
| pi3 | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 1927303 | 28.9 | 3.5 | 13.2 | 8.8 | 13.5 |
| pi3 | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 1023680 | 15.4 | 3.1 | 12.4 | 8.0 | 14.7 |
| pi3 | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 954729 | 14.3 | 3.3 | 20.6 | 16.7 | 6.0 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 1937315 | 29.1 | 3.4 | 11.0 | 6.0 | 16.6 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 1023680 | 15.4 | 3.1 | 12.4 | 8.0 | 14.6 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 2697310 | 40.5 | 3.4 | 14.8 | 9.9 | 13.9 |
| pi3 | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 2876468 | 43.1 | 3.2 | 19.7 | 16.6 | 8.2 |
| pi3 | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 1937315 | 29.1 | 3.4 | 11.0 | 6.0 | 16.6 |
| pi3 | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 2697310 | 40.5 | 3.4 | 14.8 | 9.9 | 13.9 |
| pi3 | apartment_0/loop_2.0hz_s1/synthetic_fov | 2129710 | 31.9 | 3.6 | 21.2 | 19.3 | 6.0 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s0/pano | 1847554 | 27.7 | 2.9 | 71.8 | 55.9 | 9.3 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 1091258 | 16.4 | 2.8 | 8.3 | 3.5 | 29.5 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 951353 | 14.3 | 2.8 | 6.7 | 2.2 | 34.2 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 1635979 | 24.5 | 2.6 | 28.2 | 34.1 | 11.7 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 845380 | 12.7 | 2.9 | 5.7 | 1.0 | 41.5 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 887439 | 13.3 | 2.6 | 6.0 | 1.5 | 36.9 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 981679 | 14.7 | 2.7 | 6.7 | 1.9 | 33.1 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 1373331 | 20.6 | 2.5 | 23.4 | 31.1 | 11.8 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 1653748 | 24.8 | 2.7 | 35.1 | 46.4 | 8.8 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s1/pano | 1164496 | 17.5 | 3.1 | 6.7 | 1.8 | 29.5 |
| prism_sim3 | apartment_1/stopgo_2.0hz_s1/pano | 1816653 | 27.2 | 2.0 | 80.0 | 88.2 | 2.4 |
| prism_sim3 | apartment_1/synthetic_2.0hz_s1/pano | 1533038 | 23.0 | 2.1 | 76.0 | 71.8 | 6.3 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s0/pano | 794068 | 11.9 | 2.2 | 83.2 | 79.2 | 3.8 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s1/pano | 914813 | 13.7 | 2.0 | 80.3 | 74.2 | 9.0 |
| prism_sim3 | apartment_1/synthetic_5.0hz_s1/pano | 3290692 | 49.4 | 2.5 | 83.1 | 78.8 | 4.2 |
| prism_sim3 | apartment_1/loop_2.0hz_s1/pano | 1800211 | 27.0 | 2.3 | 74.4 | 71.3 | 5.9 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s1/pano | 810796 | 12.2 | 2.4 | 49.7 | 46.1 | 11.2 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s0/pano | 730238 | 10.9 | 2.5 | 38.8 | 16.1 | 29.2 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s1/pano | 856253 | 12.8 | 2.2 | 59.7 | 55.6 | 14.2 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s0/pano | 396202 | 5.9 | 2.2 | 12.2 | 7.4 | 29.9 |
| prism_sim3 | hotel_0/loop_2.0hz_s1/pano | 1033983 | 15.5 | 2.5 | 34.9 | 27.1 | 23.8 |
| prism_sim3 | apartment_0/loop_2.0hz_s0/pano | 1811783 | 27.2 | 2.2 | 84.1 | 79.2 | 1.9 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s1/pano | 1859232 | 27.9 | 2.5 | 46.1 | 27.9 | 9.8 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s1/pano | 2169831 | 32.5 | 2.3 | 53.3 | 37.5 | 7.5 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s0/pano | 1689047 | 25.3 | 2.2 | 30.7 | 26.1 | 9.4 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s0/pano | 1388062 | 20.8 | 2.4 | 52.1 | 57.4 | 3.8 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s1/pano | 1013367 | 15.2 | 2.8 | 6.7 | 1.5 | 21.3 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s0/pano | 1496889 | 22.4 | 2.5 | 37.2 | 23.8 | 10.0 |
| prism_sim3 | apartment_0/synthetic_5.0hz_s0/pano | 1851591 | 27.8 | 2.4 | 42.9 | 34.9 | 6.4 |
| prism_sim3 | apartment_0/loop_2.0hz_s1/pano | 2083596 | 31.2 | 2.7 | 34.6 | 28.1 | 7.8 |
| prism | office_4/synthetic_2.0hz/pano | 647577 | 9.7 | 2.3 | 4.7 | 0.4 | 49.5 |
| prism | office_4/synthetic_0.5hz/pano | 547120 | 8.2 | 2.1 | 3.9 | 0.2 | 66.4 |
| prism | office_4/synthetic_5.0hz/pano | 657041 | 9.9 | 2.2 | 6.3 | 1.7 | 31.9 |
| prism | frl_apartment_0/loop_2.0hz_s0/pano | 1592557 | 23.9 | 2.6 | 36.6 | 38.0 | 12.3 |
| prism | frl_apartment_0/stopgo_2.0hz_s1/pano | 1124055 | 16.9 | 2.7 | 9.3 | 4.4 | 26.4 |
| prism | frl_apartment_0/synthetic_2.0hz_s1/pano | 981810 | 14.7 | 2.9 | 7.7 | 3.0 | 29.8 |
| prism | frl_apartment_0/stopgo_2.0hz_s0/pano | 1359989 | 20.4 | 2.8 | 9.2 | 3.9 | 30.8 |
| prism | frl_apartment_0/synthetic_0.5hz_s0/pano | 851049 | 12.8 | 2.7 | 5.7 | 1.0 | 42.0 |
| prism | frl_apartment_0/synthetic_0.5hz_s1/pano | 882301 | 13.2 | 2.3 | 6.0 | 1.5 | 37.1 |
| prism | frl_apartment_0/synthetic_5.0hz_s1/pano | 999165 | 15.0 | 2.8 | 7.9 | 2.6 | 28.1 |
| prism | frl_apartment_0/synthetic_2.0hz_s0/pano | 1158370 | 17.4 | 2.4 | 10.1 | 5.2 | 28.1 |
| prism | frl_apartment_0/synthetic_5.0hz_s0/pano | 1317008 | 19.8 | 2.3 | 13.1 | 10.4 | 24.5 |
| prism | frl_apartment_0/loop_2.0hz_s1/pano | 1119230 | 16.8 | 2.9 | 7.9 | 2.4 | 27.8 |
| prism | apartment_1/stopgo_2.0hz_s1/pano | 1849756 | 27.8 | 2.5 | 82.9 | 85.1 | 2.4 |
| prism | apartment_1/synthetic_2.0hz_s1/pano | 2697005 | 40.5 | 2.6 | 78.9 | 69.6 | 6.6 |
| prism | apartment_1/synthetic_0.5hz_s0/pano | 794449 | 11.9 | 2.1 | 83.2 | 79.1 | 3.8 |
| prism | apartment_1/synthetic_0.5hz_s1/pano | 917360 | 13.8 | 2.1 | 80.4 | 74.3 | 8.8 |
| prism | apartment_1/synthetic_5.0hz_s1/pano | 2389014 | 35.8 | 2.6 | 79.2 | 76.2 | 4.1 |
| prism | apartment_1/loop_2.0hz_s1/pano | 2993085 | 44.9 | 2.9 | 78.5 | 70.6 | 6.2 |
| prism | hotel_0/synthetic_2.0hz_s1/pano | 851453 | 12.8 | 2.1 | 59.0 | 60.1 | 10.4 |
| prism | hotel_0/synthetic_0.5hz_s0/pano | 730285 | 10.9 | 2.3 | 38.8 | 16.1 | 29.5 |
| prism | hotel_0/synthetic_0.5hz_s1/pano | 856691 | 12.8 | 2.2 | 59.7 | 55.5 | 14.0 |
| prism | hotel_0/synthetic_2.0hz_s0/pano | 351138 | 5.3 | 2.2 | 6.3 | 2.3 | 56.3 |
| prism | hotel_0/loop_2.0hz_s1/pano | 3071507 | 46.1 | 1.8 | 20.0 | 100.0 | 0.0 |
| prism | apartment_0/loop_2.0hz_s0/pano | 1807416 | 27.1 | 2.3 | 82.5 | 75.4 | 2.7 |
| prism | apartment_0/stopgo_2.0hz_s1/pano | 2172279 | 32.6 | 2.6 | 66.5 | 71.6 | 3.1 |
| prism | apartment_0/synthetic_2.0hz_s1/pano | 2109746 | 31.6 | 2.3 | 70.2 | 69.4 | 3.7 |
| prism | apartment_0/stopgo_2.0hz_s0/pano | 1674573 | 25.1 | 2.2 | 37.9 | 26.2 | 9.6 |
| prism | apartment_0/synthetic_0.5hz_s0/pano | 1383716 | 20.8 | 2.0 | 52.4 | 57.4 | 3.7 |
| prism | apartment_0/synthetic_0.5hz_s1/pano | 1010537 | 15.2 | 3.0 | 6.7 | 1.6 | 21.3 |
| prism | apartment_0/synthetic_2.0hz/pano | 1493304 | 22.4 | 2.4 | 37.2 | 23.7 | 9.9 |
| prism | apartment_0/synthetic_0.5hz/pano | 1389184 | 20.8 | 2.1 | 52.2 | 57.4 | 3.9 |
| prism | apartment_0/synthetic_5.0hz/pano | 1845611 | 27.7 | 2.4 | 42.7 | 34.8 | 6.5 |
| prism | apartment_0/synthetic_5.0hz_s1/pano | 1282390 | 19.2 | 2.6 | 21.1 | 8.7 | 13.4 |
| prism | apartment_0/synthetic_2.0hz_s0/pano | 1371046 | 20.6 | 2.1 | 18.7 | 21.4 | 9.2 |
| prism | apartment_0/synthetic_5.0hz_s0/pano | 1647176 | 24.7 | 2.3 | 51.4 | 38.5 | 6.9 |
| prism | apartment_0/loop_2.0hz_s1/pano | 2280631 | 34.2 | 2.4 | 70.4 | 71.8 | 3.6 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 648498 | 9.7 | 2.3 | 4.7 | 0.4 | 49.7 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 547419 | 8.2 | 2.2 | 3.9 | 0.2 | 66.3 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 656400 | 9.8 | 2.2 | 6.3 | 1.8 | 32.5 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s0/pano | 1592801 | 23.9 | 2.7 | 36.6 | 38.0 | 11.9 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s1/pano | 1117398 | 16.8 | 2.9 | 9.3 | 4.3 | 26.6 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s0/pano | 1360272 | 20.4 | 2.8 | 9.2 | 3.9 | 30.8 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s1/pano | 1113365 | 16.7 | 3.0 | 7.9 | 2.4 | 27.7 |
| prism_nostill | apartment_1/stopgo_2.0hz_s1/pano | 1846054 | 27.7 | 2.6 | 83.0 | 85.1 | 2.4 |
| prism_nostill | apartment_1/loop_2.0hz_s1/pano | 3010047 | 45.1 | 3.0 | 78.4 | 70.6 | 6.2 |
| prism_nostill | hotel_0/loop_2.0hz_s1/pano | 3073182 | 46.1 | 2.2 | 20.1 | 100.0 | 0.0 |
| prism_nostill | apartment_0/loop_2.0hz_s0/pano | 1802353 | 27.0 | 2.2 | 82.6 | 75.5 | 2.7 |
| prism_nostill | apartment_0/stopgo_2.0hz_s1/pano | 2172553 | 32.6 | 2.4 | 66.7 | 71.8 | 3.0 |
| prism_nostill | apartment_0/stopgo_2.0hz_s0/pano | 1691020 | 25.4 | 2.2 | 37.2 | 26.0 | 9.7 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 1493421 | 22.4 | 2.4 | 37.1 | 23.7 | 10.0 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 1386487 | 20.8 | 2.4 | 52.1 | 57.4 | 3.7 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 1849178 | 27.7 | 2.5 | 42.8 | 34.8 | 6.6 |
| prism_nostill | apartment_0/loop_2.0hz_s1/pano | 2280499 | 34.2 | 2.4 | 70.1 | 71.7 | 3.5 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 649959 | 9.8 | 2.3 | 4.7 | 0.5 | 49.6 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 547936 | 8.2 | 2.3 | 3.9 | 0.2 | 66.4 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 601999 | 9.0 | 2.1 | 5.7 | 0.4 | 37.1 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s0/pano | 1581117 | 23.7 | 2.7 | 37.4 | 37.7 | 12.1 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s1/pano | 1109859 | 16.6 | 2.8 | 9.2 | 4.3 | 26.6 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s0/pano | 1331938 | 20.0 | 2.9 | 9.2 | 3.9 | 30.3 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s1/pano | 1112052 | 16.7 | 3.0 | 7.8 | 2.4 | 27.8 |
| prism_nolock | apartment_1/stopgo_2.0hz_s1/pano | 1839103 | 27.6 | 2.6 | 83.1 | 85.2 | 2.4 |
| prism_nolock | apartment_1/loop_2.0hz_s1/pano | 3006352 | 45.1 | 2.8 | 78.4 | 70.5 | 6.2 |
| prism_nolock | hotel_0/loop_2.0hz_s1/pano | 3071019 | 46.1 | 2.0 | 20.9 | 100.0 | 0.0 |
| prism_nolock | apartment_0/loop_2.0hz_s0/pano | 1806455 | 27.1 | 2.2 | 82.4 | 75.3 | 2.8 |
| prism_nolock | apartment_0/stopgo_2.0hz_s1/pano | 2172615 | 32.6 | 2.6 | 66.6 | 71.7 | 3.0 |
| prism_nolock | apartment_0/stopgo_2.0hz_s0/pano | 1681956 | 25.2 | 2.2 | 42.3 | 25.7 | 9.7 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 1475587 | 22.1 | 2.3 | 14.0 | 13.8 | 10.4 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 1384292 | 20.8 | 2.0 | 52.4 | 57.6 | 3.7 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 1856064 | 27.8 | 2.4 | 63.7 | 54.2 | 3.2 |
| prism_nolock | apartment_0/loop_2.0hz_s1/pano | 2284686 | 34.3 | 2.4 | 70.0 | 71.7 | 3.4 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 1220150 | 18.3 | 4.5 | 33.9 | 42.8 | 14.5 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 574014 | 8.6 | 3.4 | 35.2 | 48.7 | 14.9 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 1628324 | 24.4 | 4.2 | 34.2 | 46.2 | 13.2 |
| mapanything | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 3364149 | 50.5 | 3.9 | 120.5 | 75.6 | 3.8 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 2626151 | 39.4 | 4.7 | 78.3 | 71.0 | 5.2 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 2616258 | 39.2 | 4.7 | 74.9 | 69.0 | 5.4 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 2848936 | 42.7 | 4.2 | 85.3 | 70.7 | 5.3 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 1246049 | 18.7 | 3.7 | 77.2 | 63.9 | 6.3 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 1176418 | 17.6 | 3.9 | 114.3 | 80.8 | 3.2 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 3860375 | 57.9 | 4.6 | 80.2 | 71.7 | 4.6 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 2856594 | 42.9 | 4.5 | 89.8 | 70.3 | 6.0 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 4140302 | 62.1 | 4.2 | 73.6 | 62.7 | 6.5 |
| mapanything | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 3110676 | 46.7 | 4.4 | 125.2 | 89.1 | 1.8 |
| mapanything | apartment_1/loop_2.0hz_s0/synthetic_fov | 1997686 | 30.0 | 0.0 | 82.4 | 82.2 | 2.8 |
| mapanything | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 1814800 | 27.2 | 3.8 | 53.7 | 76.0 | 4.3 |
| mapanything | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 1666386 | 25.0 | 3.8 | 83.6 | 71.3 | 6.8 |
| mapanything | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 1253286 | 18.8 | 0.1 | 80.4 | 89.4 | 1.6 |
| mapanything | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 546800 | 8.2 | 3.3 | 80.2 | 81.8 | 3.6 |
| mapanything | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 624228 | 9.4 | 0.3 | 78.6 | 82.7 | 3.0 |
| mapanything | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 2895960 | 43.4 | 4.3 | 88.1 | 86.4 | 2.7 |
| mapanything | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 1221509 | 18.3 | 0.1 | 78.4 | 75.6 | 7.3 |
| mapanything | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 1799136 | 27.0 | 0.1 | 77.4 | 73.7 | 5.9 |
| mapanything | apartment_1/loop_2.0hz_s1/synthetic_fov | 1813111 | 27.2 | 4.2 | 78.4 | 86.4 | 2.3 |
| mapanything | hotel_0/loop_2.0hz_s0/synthetic_fov | 651253 | 9.8 | 4.3 | 33.5 | 32.0 | 17.0 |
| mapanything | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 725070 | 10.9 | 3.7 | 25.1 | 35.5 | 14.5 |
| mapanything | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 702873 | 10.5 | 3.5 | 28.2 | 36.4 | 12.8 |
| mapanything | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 608991 | 9.1 | 3.8 | 49.8 | 49.2 | 12.1 |
| mapanything | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 254872 | 3.8 | 3.4 | 35.6 | 27.5 | 20.5 |
| mapanything | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 284279 | 4.3 | 3.8 | 49.3 | 51.0 | 13.9 |
| mapanything | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 967328 | 14.5 | 4.2 | 22.9 | 32.9 | 13.2 |
| mapanything | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 613702 | 9.2 | 3.7 | 33.8 | 36.6 | 17.5 |
| mapanything | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 1033603 | 15.5 | 4.1 | 36.0 | 43.6 | 14.5 |
| mapanything | hotel_0/loop_2.0hz_s1/synthetic_fov | 1083448 | 16.2 | 4.4 | 28.8 | 38.8 | 15.3 |
| mapanything | apartment_0/loop_2.0hz_s0/synthetic_fov | 3092328 | 46.4 | 3.7 | 35.9 | 48.8 | 4.3 |
| mapanything | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 2445253 | 36.7 | 4.3 | 37.5 | 40.2 | 5.8 |
| mapanything | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 2422676 | 36.3 | 4.1 | 35.9 | 40.6 | 5.6 |
| mapanything | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 2778677 | 41.7 | 3.7 | 40.2 | 45.4 | 6.6 |
| mapanything | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 1045511 | 15.7 | 3.7 | 69.2 | 69.5 | 4.1 |
| mapanything | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 949386 | 14.2 | 3.5 | 30.9 | 28.7 | 7.8 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 2814956 | 42.2 | 3.7 | 43.0 | 44.5 | 6.4 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 1045511 | 15.7 | 3.7 | 69.2 | 69.5 | 4.1 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 4682508 | 70.2 | 3.6 | 38.5 | 47.1 | 4.3 |
| mapanything | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 3713273 | 55.7 | 4.1 | 39.3 | 46.7 | 5.0 |
| mapanything | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 2815222 | 42.2 | 3.7 | 43.1 | 44.5 | 6.4 |
| mapanything | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 4682494 | 70.2 | 3.6 | 38.5 | 47.1 | 4.3 |
| mapanything | apartment_0/loop_2.0hz_s1/synthetic_fov | 2619778 | 39.3 | 4.3 | 31.7 | 38.8 | 6.4 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 655566 | 9.8 | 2.2 | 4.7 | 0.5 | 49.6 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 546736 | 8.2 | 2.2 | 3.9 | 0.2 | 66.1 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 604559 | 9.1 | 2.2 | 5.7 | 0.4 | 37.1 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s0/pano | 1589384 | 23.8 | 2.7 | 37.2 | 37.7 | 11.6 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s1/pano | 1112054 | 16.7 | 2.7 | 8.9 | 4.1 | 27.2 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s0/pano | 1335516 | 20.0 | 2.8 | 9.1 | 3.7 | 30.9 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s1/pano | 1112493 | 16.7 | 3.0 | 7.7 | 2.3 | 27.5 |
| prism_noguards | apartment_1/stopgo_2.0hz_s1/pano | 1657887 | 24.9 | 2.6 | 87.8 | 80.9 | 3.1 |
| prism_noguards | apartment_1/loop_2.0hz_s1/pano | 3086951 | 46.3 | 2.7 | 77.7 | 72.6 | 5.2 |
| prism_noguards | hotel_0/loop_2.0hz_s1/pano | 4002703 | 60.0 | 2.1 | 19.9 | 100.0 | 0.0 |
| prism_noguards | apartment_0/loop_2.0hz_s0/pano | 1812639 | 27.2 | 2.3 | 82.4 | 75.0 | 2.9 |
| prism_noguards | apartment_0/stopgo_2.0hz_s1/pano | 2114893 | 31.7 | 2.4 | 67.5 | 73.0 | 2.7 |
| prism_noguards | apartment_0/stopgo_2.0hz_s0/pano | 1569992 | 23.6 | 2.2 | 36.7 | 22.9 | 8.2 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 1486957 | 22.3 | 2.3 | 13.9 | 13.7 | 10.6 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 1384402 | 20.8 | 2.2 | 52.1 | 57.5 | 3.9 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 1731263 | 26.0 | 2.4 | 63.9 | 56.4 | 3.1 |
| prism_noguards | apartment_0/loop_2.0hz_s1/pano | 2294151 | 34.4 | 2.3 | 70.2 | 73.3 | 3.2 |
| prism_se3 | office_4/synthetic_2.0hz/pano | 648058 | 9.7 | 2.4 | 4.7 | 0.5 | 49.5 |
| prism_se3 | office_4/synthetic_5.0hz/pano | 657228 | 9.9 | 2.2 | 6.3 | 1.7 | 32.1 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s0/pano | 1837296 | 27.6 | 2.9 | 72.3 | 55.6 | 9.5 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 1088240 | 16.3 | 2.8 | 8.1 | 3.3 | 29.8 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 945952 | 14.2 | 3.0 | 6.7 | 2.2 | 34.2 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 1630968 | 24.5 | 2.6 | 28.5 | 34.3 | 11.8 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 843615 | 12.7 | 2.9 | 5.7 | 1.1 | 41.4 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 886148 | 13.3 | 2.7 | 6.0 | 1.5 | 37.0 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 980490 | 14.7 | 2.6 | 6.7 | 1.9 | 33.2 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 1378304 | 20.7 | 2.5 | 23.4 | 31.1 | 11.7 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 1651547 | 24.8 | 2.6 | 34.9 | 46.3 | 8.8 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s1/pano | 1160775 | 17.4 | 3.0 | 6.8 | 1.8 | 29.7 |
| prism_se3 | apartment_1/stopgo_2.0hz_s1/pano | 2267777 | 34.0 | 2.0 | 86.8 | 78.5 | 3.8 |
| prism_se3 | apartment_1/synthetic_2.0hz_s1/pano | 1526113 | 22.9 | 2.1 | 76.9 | 70.4 | 7.0 |
| prism_se3 | apartment_1/synthetic_0.5hz_s0/pano | 797725 | 12.0 | 2.1 | 83.2 | 78.6 | 3.9 |
| prism_se3 | apartment_1/synthetic_0.5hz_s1/pano | 917680 | 13.8 | 2.1 | 80.4 | 74.4 | 8.7 |
| prism_se3 | apartment_1/synthetic_5.0hz_s1/pano | 3290521 | 49.4 | 2.7 | 83.2 | 79.0 | 4.2 |
| prism_se3 | apartment_1/loop_2.0hz_s1/pano | 1810857 | 27.2 | 2.1 | 74.6 | 72.6 | 5.3 |
| prism_se3 | hotel_0/synthetic_2.0hz_s1/pano | 808070 | 12.1 | 2.3 | 46.2 | 47.7 | 9.2 |
| prism_se3 | hotel_0/synthetic_0.5hz_s0/pano | 727494 | 10.9 | 2.5 | 38.6 | 16.1 | 29.3 |
| prism_se3 | hotel_0/synthetic_0.5hz_s1/pano | 858187 | 12.9 | 2.1 | 59.8 | 55.5 | 14.0 |
| prism_se3 | hotel_0/synthetic_2.0hz_s0/pano | 390558 | 5.9 | 2.3 | 12.3 | 7.5 | 29.4 |
| prism_se3 | hotel_0/loop_2.0hz_s1/pano | 1039431 | 15.6 | 2.5 | 36.0 | 41.9 | 23.2 |
| prism_se3 | apartment_0/loop_2.0hz_s0/pano | 1813841 | 27.2 | 2.2 | 84.0 | 79.1 | 1.9 |
| prism_se3 | apartment_0/stopgo_2.0hz_s1/pano | 1813467 | 27.2 | 2.6 | 48.2 | 37.9 | 6.8 |
| prism_se3 | apartment_0/synthetic_2.0hz_s1/pano | 1857926 | 27.9 | 2.4 | 46.3 | 33.6 | 8.5 |
| prism_se3 | apartment_0/stopgo_2.0hz_s0/pano | 1670352 | 25.1 | 2.3 | 35.0 | 28.4 | 7.1 |
| prism_se3 | apartment_0/synthetic_0.5hz_s0/pano | 1385350 | 20.8 | 2.1 | 52.2 | 57.4 | 3.7 |
| prism_se3 | apartment_0/synthetic_0.5hz_s1/pano | 1014048 | 15.2 | 2.9 | 6.7 | 1.5 | 21.4 |
| prism_se3 | apartment_0/synthetic_2.0hz/pano | 1492273 | 22.4 | 2.4 | 37.5 | 23.7 | 10.0 |
| prism_se3 | apartment_0/synthetic_0.5hz/pano | 1387279 | 20.8 | 2.2 | 52.3 | 57.5 | 3.8 |
| prism_se3 | apartment_0/synthetic_5.0hz/pano | 1853219 | 27.8 | 2.5 | 43.2 | 34.9 | 6.4 |
| prism_se3 | apartment_0/synthetic_5.0hz_s1/pano | 1630047 | 24.4 | 2.4 | 50.6 | 35.9 | 8.4 |
| prism_se3 | apartment_0/synthetic_2.0hz_s0/pano | 1495496 | 22.4 | 2.3 | 37.6 | 23.7 | 10.0 |
| prism_se3 | apartment_0/synthetic_5.0hz_s0/pano | 1849707 | 27.8 | 2.5 | 43.1 | 34.8 | 6.6 |
| prism_se3 | apartment_0/loop_2.0hz_s1/pano | 1952186 | 29.3 | 2.1 | 27.1 | 22.0 | 8.6 |


## Trajectory (ATE + drift/m, Sim(3)-aligned)

*Drift/m = relative pose error per metre of GT motion — fair across dense vs keyframe-sparse methods (replaces the frame-delta RPE, which penalised keyframes).*

| Method | Run | ATE RMSE cm↓ | Drift %/m↓ |
| --- | --- | --- | --- |
| laser | office_4/synthetic_2.0hz/synthetic_fov | 4.2 | 9.7 |
| laser | office_4/synthetic_0.5hz/synthetic_fov | 4.0 | 4.3 |
| laser | office_4/synthetic_5.0hz/synthetic_fov | 6.0 | 13.9 |
| laser | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 119.1 | 51.5 |
| laser | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 6.5 | 9.0 |
| laser | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 4.6 | 6.6 |
| laser | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 23.2 | 27.2 |
| laser | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 82.5 | 45.6 |
| laser | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 3.0 | 3.2 |
| laser | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 11.2 | 17.0 |
| laser | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 18.2 | 20.5 |
| laser | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 49.7 | 23.3 |
| laser | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 7.2 | 6.5 |
| laser | apartment_1/loop_2.0hz_s0/synthetic_fov | 224.5 | 121.1 |
| laser | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 237.9 | 101.9 |
| laser | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 216.6 | 97.3 |
| laser | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 213.2 | 98.7 |
| laser | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 161.5 | 120.3 |
| laser | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 242.7 | 95.5 |
| laser | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 160.6 | 120.7 |
| laser | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 219.0 | 155.5 |
| laser | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 94.6 | 116.7 |
| laser | apartment_1/loop_2.0hz_s1/synthetic_fov | 226.7 | 92.7 |
| laser | hotel_0/loop_2.0hz_s0/synthetic_fov | 34.0 | 34.5 |
| laser | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 118.9 | 144.8 |
| laser | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 157.0 | 94.4 |
| laser | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 35.6 | 34.9 |
| laser | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 27.9 | 34.9 |
| laser | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 64.1 | 81.9 |
| laser | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 68.9 | 73.3 |
| laser | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 34.2 | 33.1 |
| laser | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 23.6 | 28.4 |
| laser | hotel_0/loop_2.0hz_s1/synthetic_fov | 135.6 | 83.1 |
| laser | apartment_0/loop_2.0hz_s0/synthetic_fov | 164.0 | 64.3 |
| laser | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 32.5 | 46.4 |
| laser | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 38.4 | 37.9 |
| laser | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 32.1 | 18.7 |
| laser | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 47.3 | 29.4 |
| laser | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 5.3 | 4.3 |
| laser | apartment_0/synthetic_2.0hz/synthetic_fov | 22.6 | 9.3 |
| laser | apartment_0/synthetic_0.5hz/synthetic_fov | 47.3 | 29.4 |
| laser | apartment_0/synthetic_5.0hz/synthetic_fov | 21.3 | 10.7 |
| laser | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 47.3 | 38.0 |
| laser | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 22.6 | 9.3 |
| laser | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 21.3 | 10.7 |
| laser | apartment_0/loop_2.0hz_s1/synthetic_fov | 38.1 | 35.9 |
| panovggt | office_4/synthetic_2.0hz/pano | 0.9 | 2.5 |
| panovggt | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| panovggt | office_4/synthetic_5.0hz/pano | 0.8 | 3.2 |
| panovggt | frl_apartment_0/loop_2.0hz_s0/pano | 10.6 | 12.0 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s1/pano | 1.4 | 2.1 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s1/pano | 1.4 | 2.1 |
| panovggt | frl_apartment_0/stopgo_2.0hz_s0/pano | 2.7 | 5.0 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s0/pano | 3.6 | 2.9 |
| panovggt | frl_apartment_0/synthetic_0.5hz_s1/pano | 1.3 | 1.0 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s1/pano | 1.4 | 3.5 |
| panovggt | frl_apartment_0/synthetic_2.0hz_s0/pano | 3.1 | 5.1 |
| panovggt | frl_apartment_0/synthetic_5.0hz_s0/pano | 2.3 | 6.8 |
| panovggt | frl_apartment_0/loop_2.0hz_s1/pano | 1.2 | 2.1 |
| panovggt | apartment_1/loop_2.0hz_s0/pano | 222.0 | 162.1 |
| panovggt | apartment_1/stopgo_2.0hz_s1/pano | 230.1 | 112.9 |
| panovggt | apartment_1/synthetic_2.0hz_s1/pano | 241.9 | 122.9 |
| panovggt | apartment_1/stopgo_2.0hz_s0/pano | 112.8 | 80.1 |
| panovggt | apartment_1/synthetic_0.5hz_s0/pano | 198.6 | 150.3 |
| panovggt | apartment_1/synthetic_0.5hz_s1/pano | 235.2 | 97.4 |
| panovggt | apartment_1/synthetic_5.0hz_s1/pano | 246.1 | 120.9 |
| panovggt | apartment_1/synthetic_2.0hz_s0/pano | 189.3 | 62.1 |
| panovggt | apartment_1/synthetic_5.0hz_s0/pano | 146.2 | 82.2 |
| panovggt | apartment_1/loop_2.0hz_s1/pano | 221.6 | 169.0 |
| panovggt | hotel_0/loop_2.0hz_s0/pano | 3.9 | 7.9 |
| panovggt | hotel_0/stopgo_2.0hz_s1/pano | 36.8 | 52.2 |
| panovggt | hotel_0/synthetic_2.0hz_s1/pano | 52.3 | 62.8 |
| panovggt | hotel_0/stopgo_2.0hz_s0/pano | 1.8 | 5.5 |
| panovggt | hotel_0/synthetic_0.5hz_s0/pano | 2.0 | 2.7 |
| panovggt | hotel_0/synthetic_0.5hz_s1/pano | 1.9 | 3.0 |
| panovggt | hotel_0/synthetic_5.0hz_s1/pano | 50.6 | 70.7 |
| panovggt | hotel_0/synthetic_2.0hz_s0/pano | 24.6 | 38.4 |
| panovggt | hotel_0/synthetic_5.0hz_s0/pano | 4.3 | 12.3 |
| panovggt | hotel_0/loop_2.0hz_s1/pano | 42.9 | 42.0 |
| panovggt | apartment_0/loop_2.0hz_s0/pano | 76.3 | 109.3 |
| panovggt | apartment_0/stopgo_2.0hz_s1/pano | 19.4 | 34.9 |
| panovggt | apartment_0/synthetic_2.0hz_s1/pano | 18.8 | 30.1 |
| panovggt | apartment_0/stopgo_2.0hz_s0/pano | 42.8 | 51.7 |
| panovggt | apartment_0/synthetic_0.5hz_s0/pano | 81.1 | 49.9 |
| panovggt | apartment_0/synthetic_0.5hz_s1/pano | 3.4 | 2.9 |
| panovggt | apartment_0/synthetic_2.0hz/pano | 46.7 | 49.8 |
| panovggt | apartment_0/synthetic_0.5hz/pano | 81.1 | 49.9 |
| panovggt | apartment_0/synthetic_5.0hz_s1/pano | 19.0 | 42.5 |
| panovggt | apartment_0/synthetic_2.0hz_s0/pano | 46.7 | 49.8 |
| panovggt | apartment_0/synthetic_5.0hz_s0/pano | 33.6 | 44.6 |
| panovggt | apartment_0/loop_2.0hz_s1/pano | 30.5 | 43.0 |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 30.7 | 62.7 |
| vggtslam | office_4/synthetic_0.5hz/synthetic_fov | 39.3 | 28.5 |
| vggtslam | office_4/synthetic_5.0hz/synthetic_fov | 27.1 | 105.7 |
| vggtslam | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 73.2 | 123.6 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 13.6 | 26.5 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 13.6 | 26.5 |
| vggtslam | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 87.7 | 132.9 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 61.2 | 51.9 |
| vggtslam | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 4.4 | 5.9 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 22.7 | 38.4 |
| vggtslam | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 87.7 | 132.9 |
| vggtslam | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 209.8 | 393.8 |
| vggtslam | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 9.3 | 21.6 |
| vggtslam | apartment_1/loop_2.0hz_s0/synthetic_fov | 225.4 | 232.6 |
| vggtslam | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 286.5 | 230.8 |
| vggtslam | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 286.5 | 230.8 |
| vggtslam | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 197.6 | 135.6 |
| vggtslam | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 217.1 | 133.2 |
| vggtslam | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 241.8 | 139.7 |
| vggtslam | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 272.7 | 205.0 |
| vggtslam | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 126.9 | 220.0 |
| vggtslam | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 157.8 | 273.0 |
| vggtslam | apartment_1/loop_2.0hz_s1/synthetic_fov | 299.9 | 205.6 |
| vggtslam | hotel_0/loop_2.0hz_s0/synthetic_fov | 88.8 | 129.4 |
| vggtslam | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 148.0 | 149.3 |
| vggtslam | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 152.5 | 125.5 |
| vggtslam | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 90.6 | 132.7 |
| vggtslam | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 7.1 | 10.5 |
| vggtslam | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 74.9 | 91.6 |
| vggtslam | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 130.4 | 206.1 |
| vggtslam | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 90.6 | 132.7 |
| vggtslam | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 95.1 | 190.0 |
| vggtslam | hotel_0/loop_2.0hz_s1/synthetic_fov | 87.0 | 134.3 |
| vggtslam | apartment_0/loop_2.0hz_s0/synthetic_fov | 157.7 | 332.7 |
| vggtslam | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 126.1 | 248.5 |
| vggtslam | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 126.1 | 248.5 |
| vggtslam | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 207.3 | 250.4 |
| vggtslam | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 88.2 | 57.3 |
| vggtslam | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 25.8 | 14.3 |
| vggtslam | apartment_0/synthetic_2.0hz/synthetic_fov | 207.3 | 250.4 |
| vggtslam | apartment_0/synthetic_0.5hz/synthetic_fov | 88.2 | 57.3 |
| vggtslam | apartment_0/synthetic_5.0hz/synthetic_fov | 193.8 | 266.6 |
| vggtslam | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 166.3 | 223.4 |
| vggtslam | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 207.3 | 250.4 |
| vggtslam | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 193.8 | 266.6 |
| vggtslam | apartment_0/loop_2.0hz_s1/synthetic_fov | 119.0 | 222.3 |
| prism_sl4 | office_4/synthetic_2.0hz/pano | 0.7 | 2.2 |
| prism_sl4 | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism_sl4 | office_4/synthetic_5.0hz/pano | 0.9 | 2.8 |
| prism_sl4 | apartment_0/synthetic_2.0hz/pano | 29.0 | 33.3 |
| prism_sl4 | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism_sl4 | apartment_0/synthetic_5.0hz/pano | 59.8 | 47.6 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 5.2 | 16.3 |
| pi3 | office_4/synthetic_0.5hz/synthetic_fov | 6.1 | 5.9 |
| pi3 | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 25.0 | 37.0 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 9.6 | 9.3 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 11.0 | 10.7 |
| pi3 | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 17.1 | 27.4 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 17.6 | 14.7 |
| pi3 | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 13.3 | 9.6 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 13.0 | 17.5 |
| pi3 | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 16.6 | 25.4 |
| pi3 | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 11.9 | 27.5 |
| pi3 | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 7.1 | 9.7 |
| pi3 | apartment_1/loop_2.0hz_s0/synthetic_fov | 167.9 | 130.1 |
| pi3 | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 139.5 | 142.5 |
| pi3 | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 170.2 | 149.8 |
| pi3 | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 173.6 | 99.8 |
| pi3 | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 191.9 | 115.2 |
| pi3 | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 183.0 | 146.3 |
| pi3 | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 205.9 | 207.7 |
| pi3 | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 205.6 | 113.4 |
| pi3 | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 206.6 | 119.2 |
| pi3 | apartment_1/loop_2.0hz_s1/synthetic_fov | 201.3 | 133.8 |
| pi3 | hotel_0/loop_2.0hz_s0/synthetic_fov | 14.7 | 34.9 |
| pi3 | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 76.5 | 93.5 |
| pi3 | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 41.8 | 87.4 |
| pi3 | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 21.2 | 54.9 |
| pi3 | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 40.2 | 41.6 |
| pi3 | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 20.6 | 24.3 |
| pi3 | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 37.2 | 93.4 |
| pi3 | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 23.4 | 54.4 |
| pi3 | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 29.9 | 101.3 |
| pi3 | hotel_0/loop_2.0hz_s1/synthetic_fov | 21.4 | 41.1 |
| pi3 | apartment_0/loop_2.0hz_s0/synthetic_fov | 47.5 | 80.2 |
| pi3 | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 12.9 | 22.5 |
| pi3 | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 20.7 | 32.7 |
| pi3 | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 9.7 | 18.6 |
| pi3 | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 37.5 | 25.6 |
| pi3 | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 13.2 | 9.2 |
| pi3 | apartment_0/synthetic_2.0hz/synthetic_fov | 9.6 | 16.8 |
| pi3 | apartment_0/synthetic_0.5hz/synthetic_fov | 37.5 | 25.6 |
| pi3 | apartment_0/synthetic_5.0hz/synthetic_fov | 8.2 | 23.0 |
| pi3 | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 10.7 | 24.4 |
| pi3 | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 9.6 | 16.8 |
| pi3 | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 8.2 | 23.0 |
| pi3 | apartment_0/loop_2.0hz_s1/synthetic_fov | 14.8 | 24.6 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s0/pano | 60.7 | 49.1 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 1.7 | 2.1 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 1.5 | 2.0 |
| prism_sim3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 16.7 | 12.0 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 1.3 | 1.3 |
| prism_sim3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 1.3 | 1.0 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 2.6 | 3.2 |
| prism_sim3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 27.6 | 28.3 |
| prism_sim3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 26.8 | 35.8 |
| prism_sim3 | frl_apartment_0/loop_2.0hz_s1/pano | 2.0 | 2.3 |
| prism_sim3 | apartment_1/stopgo_2.0hz_s1/pano | 225.0 | 137.3 |
| prism_sim3 | apartment_1/synthetic_2.0hz_s1/pano | 176.4 | 166.5 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s0/pano | 198.6 | 150.3 |
| prism_sim3 | apartment_1/synthetic_0.5hz_s1/pano | 184.5 | 141.0 |
| prism_sim3 | apartment_1/synthetic_5.0hz_s1/pano | 231.9 | 158.0 |
| prism_sim3 | apartment_1/loop_2.0hz_s1/pano | 259.7 | 137.6 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s1/pano | 54.3 | 44.0 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s0/pano | 2.0 | 2.7 |
| prism_sim3 | hotel_0/synthetic_0.5hz_s1/pano | 1.9 | 3.0 |
| prism_sim3 | hotel_0/synthetic_2.0hz_s0/pano | 3.5 | 4.8 |
| prism_sim3 | hotel_0/loop_2.0hz_s1/pano | 62.7 | 57.8 |
| prism_sim3 | apartment_0/loop_2.0hz_s0/pano | 195.2 | 105.8 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s1/pano | 34.4 | 25.7 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s1/pano | 31.9 | 23.8 |
| prism_sim3 | apartment_0/stopgo_2.0hz_s0/pano | 83.5 | 39.4 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s0/pano | 66.5 | 45.3 |
| prism_sim3 | apartment_0/synthetic_0.5hz_s1/pano | 2.2 | 2.0 |
| prism_sim3 | apartment_0/synthetic_2.0hz_s0/pano | 28.3 | 30.5 |
| prism_sim3 | apartment_0/synthetic_5.0hz_s0/pano | 50.4 | 37.8 |
| prism_sim3 | apartment_0/loop_2.0hz_s1/pano | 31.0 | 21.9 |
| prism | office_4/synthetic_2.0hz/pano | 1.7 | 2.8 |
| prism | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism | office_4/synthetic_5.0hz/pano | 5.9 | 4.4 |
| prism | frl_apartment_0/loop_2.0hz_s0/pano | 53.8 | 44.1 |
| prism | frl_apartment_0/stopgo_2.0hz_s1/pano | 4.1 | 2.8 |
| prism | frl_apartment_0/synthetic_2.0hz_s1/pano | 3.0 | 2.6 |
| prism | frl_apartment_0/stopgo_2.0hz_s0/pano | 7.1 | 6.9 |
| prism | frl_apartment_0/synthetic_0.5hz_s0/pano | 1.3 | 1.3 |
| prism | frl_apartment_0/synthetic_0.5hz_s1/pano | 1.3 | 1.0 |
| prism | frl_apartment_0/synthetic_5.0hz_s1/pano | 4.1 | 4.0 |
| prism | frl_apartment_0/synthetic_2.0hz_s0/pano | 21.9 | 23.2 |
| prism | frl_apartment_0/synthetic_5.0hz_s0/pano | 19.2 | 29.2 |
| prism | frl_apartment_0/loop_2.0hz_s1/pano | 4.2 | 2.9 |
| prism | apartment_1/stopgo_2.0hz_s1/pano | 198.1 | 160.9 |
| prism | apartment_1/synthetic_2.0hz_s1/pano | 171.7 | 159.7 |
| prism | apartment_1/synthetic_0.5hz_s0/pano | 198.6 | 150.3 |
| prism | apartment_1/synthetic_0.5hz_s1/pano | 184.5 | 141.0 |
| prism | apartment_1/synthetic_5.0hz_s1/pano | 212.5 | 178.0 |
| prism | apartment_1/loop_2.0hz_s1/pano | 235.2 | 161.7 |
| prism | hotel_0/synthetic_2.0hz_s1/pano | 55.6 | 42.2 |
| prism | hotel_0/synthetic_0.5hz_s0/pano | 2.0 | 2.7 |
| prism | hotel_0/synthetic_0.5hz_s1/pano | 1.9 | 3.0 |
| prism | hotel_0/synthetic_2.0hz_s0/pano | 0.8 | 2.6 |
| prism | hotel_0/loop_2.0hz_s1/pano | 172.0 | 107.9 |
| prism | apartment_0/loop_2.0hz_s0/pano | 172.9 | 135.6 |
| prism | apartment_0/stopgo_2.0hz_s1/pano | 25.9 | 28.8 |
| prism | apartment_0/synthetic_2.0hz_s1/pano | 26.0 | 23.6 |
| prism | apartment_0/stopgo_2.0hz_s0/pano | 24.5 | 27.9 |
| prism | apartment_0/synthetic_0.5hz_s0/pano | 66.5 | 45.3 |
| prism | apartment_0/synthetic_0.5hz_s1/pano | 2.2 | 2.0 |
| prism | apartment_0/synthetic_2.0hz/pano | 28.3 | 30.5 |
| prism | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism | apartment_0/synthetic_5.0hz/pano | 50.3 | 37.8 |
| prism | apartment_0/synthetic_5.0hz_s1/pano | 40.4 | 25.8 |
| prism | apartment_0/synthetic_2.0hz_s0/pano | 29.0 | 33.3 |
| prism | apartment_0/synthetic_5.0hz_s0/pano | 59.8 | 47.6 |
| prism | apartment_0/loop_2.0hz_s1/pano | 24.6 | 20.5 |
| prism_nostill | office_4/synthetic_2.0hz/pano | 1.8 | 2.8 |
| prism_nostill | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism_nostill | office_4/synthetic_5.0hz/pano | 5.9 | 4.3 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s0/pano | 53.8 | 44.1 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s1/pano | 4.1 | 2.8 |
| prism_nostill | frl_apartment_0/stopgo_2.0hz_s0/pano | 7.1 | 6.9 |
| prism_nostill | frl_apartment_0/loop_2.0hz_s1/pano | 4.2 | 2.9 |
| prism_nostill | apartment_1/stopgo_2.0hz_s1/pano | 198.1 | 160.9 |
| prism_nostill | apartment_1/loop_2.0hz_s1/pano | 235.2 | 161.8 |
| prism_nostill | hotel_0/loop_2.0hz_s1/pano | 172.0 | 107.9 |
| prism_nostill | apartment_0/loop_2.0hz_s0/pano | 172.9 | 135.6 |
| prism_nostill | apartment_0/stopgo_2.0hz_s1/pano | 25.9 | 28.8 |
| prism_nostill | apartment_0/stopgo_2.0hz_s0/pano | 24.5 | 27.9 |
| prism_nostill | apartment_0/synthetic_2.0hz/pano | 28.3 | 30.5 |
| prism_nostill | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism_nostill | apartment_0/synthetic_5.0hz/pano | 50.4 | 37.8 |
| prism_nostill | apartment_0/loop_2.0hz_s1/pano | 24.6 | 20.5 |
| prism_nolock | office_4/synthetic_2.0hz/pano | 1.7 | 2.8 |
| prism_nolock | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism_nolock | office_4/synthetic_5.0hz/pano | 3.2 | 3.1 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s0/pano | 53.8 | 44.0 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s1/pano | 4.1 | 2.7 |
| prism_nolock | frl_apartment_0/stopgo_2.0hz_s0/pano | 7.1 | 7.0 |
| prism_nolock | frl_apartment_0/loop_2.0hz_s1/pano | 4.2 | 2.9 |
| prism_nolock | apartment_1/stopgo_2.0hz_s1/pano | 198.2 | 160.8 |
| prism_nolock | apartment_1/loop_2.0hz_s1/pano | 235.2 | 161.8 |
| prism_nolock | hotel_0/loop_2.0hz_s1/pano | 172.0 | 107.9 |
| prism_nolock | apartment_0/loop_2.0hz_s0/pano | 172.9 | 135.6 |
| prism_nolock | apartment_0/stopgo_2.0hz_s1/pano | 26.0 | 28.9 |
| prism_nolock | apartment_0/stopgo_2.0hz_s0/pano | 24.5 | 28.5 |
| prism_nolock | apartment_0/synthetic_2.0hz/pano | 30.0 | 33.8 |
| prism_nolock | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism_nolock | apartment_0/synthetic_5.0hz/pano | 72.5 | 49.9 |
| prism_nolock | apartment_0/loop_2.0hz_s1/pano | 24.6 | 20.5 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 26.1 | 61.6 |
| mapanything | office_4/synthetic_0.5hz/synthetic_fov | 28.2 | 34.1 |
| mapanything | office_4/synthetic_5.0hz/synthetic_fov | 25.3 | 74.7 |
| mapanything | frl_apartment_0/loop_2.0hz_s0/synthetic_fov | 122.6 | 111.6 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s1/synthetic_fov | 41.4 | 50.1 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s1/synthetic_fov | 46.2 | 48.1 |
| mapanything | frl_apartment_0/stopgo_2.0hz_s0/synthetic_fov | 50.2 | 70.7 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s0/synthetic_fov | 41.1 | 40.6 |
| mapanything | frl_apartment_0/synthetic_0.5hz_s1/synthetic_fov | 43.3 | 27.0 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s1/synthetic_fov | 47.1 | 66.6 |
| mapanything | frl_apartment_0/synthetic_2.0hz_s0/synthetic_fov | 51.3 | 69.7 |
| mapanything | frl_apartment_0/synthetic_5.0hz_s0/synthetic_fov | 47.4 | 87.1 |
| mapanything | frl_apartment_0/loop_2.0hz_s1/synthetic_fov | 53.0 | 53.2 |
| mapanything | apartment_1/loop_2.0hz_s0/synthetic_fov | 226.9 | 153.8 |
| mapanything | apartment_1/stopgo_2.0hz_s1/synthetic_fov | 245.8 | 102.1 |
| mapanything | apartment_1/synthetic_2.0hz_s1/synthetic_fov | 264.0 | 152.2 |
| mapanything | apartment_1/stopgo_2.0hz_s0/synthetic_fov | 210.8 | 147.1 |
| mapanything | apartment_1/synthetic_0.5hz_s0/synthetic_fov | 186.7 | 135.7 |
| mapanything | apartment_1/synthetic_0.5hz_s1/synthetic_fov | 266.8 | 123.4 |
| mapanything | apartment_1/synthetic_5.0hz_s1/synthetic_fov | 265.1 | 121.0 |
| mapanything | apartment_1/synthetic_2.0hz_s0/synthetic_fov | 212.2 | 178.2 |
| mapanything | apartment_1/synthetic_5.0hz_s0/synthetic_fov | 203.2 | 192.9 |
| mapanything | apartment_1/loop_2.0hz_s1/synthetic_fov | 236.7 | 103.9 |
| mapanything | hotel_0/loop_2.0hz_s0/synthetic_fov | 28.1 | 55.7 |
| mapanything | hotel_0/stopgo_2.0hz_s1/synthetic_fov | 56.5 | 102.7 |
| mapanything | hotel_0/synthetic_2.0hz_s1/synthetic_fov | 59.0 | 124.7 |
| mapanything | hotel_0/stopgo_2.0hz_s0/synthetic_fov | 37.2 | 83.5 |
| mapanything | hotel_0/synthetic_0.5hz_s0/synthetic_fov | 17.1 | 23.5 |
| mapanything | hotel_0/synthetic_0.5hz_s1/synthetic_fov | 45.7 | 52.2 |
| mapanything | hotel_0/synthetic_5.0hz_s1/synthetic_fov | 65.2 | 140.3 |
| mapanything | hotel_0/synthetic_2.0hz_s0/synthetic_fov | 35.4 | 79.9 |
| mapanything | hotel_0/synthetic_5.0hz_s0/synthetic_fov | 45.0 | 160.5 |
| mapanything | hotel_0/loop_2.0hz_s1/synthetic_fov | 45.0 | 86.3 |
| mapanything | apartment_0/loop_2.0hz_s0/synthetic_fov | 79.6 | 149.4 |
| mapanything | apartment_0/stopgo_2.0hz_s1/synthetic_fov | 22.4 | 50.9 |
| mapanything | apartment_0/synthetic_2.0hz_s1/synthetic_fov | 26.6 | 52.0 |
| mapanything | apartment_0/stopgo_2.0hz_s0/synthetic_fov | 77.6 | 123.1 |
| mapanything | apartment_0/synthetic_0.5hz_s0/synthetic_fov | 83.7 | 62.1 |
| mapanything | apartment_0/synthetic_0.5hz_s1/synthetic_fov | 25.4 | 24.0 |
| mapanything | apartment_0/synthetic_2.0hz/synthetic_fov | 85.0 | 120.3 |
| mapanything | apartment_0/synthetic_0.5hz/synthetic_fov | 83.7 | 62.1 |
| mapanything | apartment_0/synthetic_5.0hz/synthetic_fov | 72.6 | 166.1 |
| mapanything | apartment_0/synthetic_5.0hz_s1/synthetic_fov | 24.0 | 66.7 |
| mapanything | apartment_0/synthetic_2.0hz_s0/synthetic_fov | 85.0 | 120.3 |
| mapanything | apartment_0/synthetic_5.0hz_s0/synthetic_fov | 72.6 | 166.1 |
| mapanything | apartment_0/loop_2.0hz_s1/synthetic_fov | 33.2 | 57.9 |
| prism_noguards | office_4/synthetic_2.0hz/pano | 1.7 | 2.7 |
| prism_noguards | office_4/synthetic_0.5hz/pano | 0.7 | 0.9 |
| prism_noguards | office_4/synthetic_5.0hz/pano | 3.2 | 3.1 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s0/pano | 53.8 | 44.0 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s1/pano | 4.1 | 2.7 |
| prism_noguards | frl_apartment_0/stopgo_2.0hz_s0/pano | 6.9 | 6.7 |
| prism_noguards | frl_apartment_0/loop_2.0hz_s1/pano | 4.2 | 2.9 |
| prism_noguards | apartment_1/stopgo_2.0hz_s1/pano | 188.2 | 123.2 |
| prism_noguards | apartment_1/loop_2.0hz_s1/pano | 222.5 | 154.9 |
| prism_noguards | hotel_0/loop_2.0hz_s1/pano | 172.0 | 106.8 |
| prism_noguards | apartment_0/loop_2.0hz_s0/pano | 172.9 | 135.5 |
| prism_noguards | apartment_0/stopgo_2.0hz_s1/pano | 21.8 | 23.4 |
| prism_noguards | apartment_0/stopgo_2.0hz_s0/pano | 24.3 | 28.2 |
| prism_noguards | apartment_0/synthetic_2.0hz/pano | 30.0 | 33.8 |
| prism_noguards | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism_noguards | apartment_0/synthetic_5.0hz/pano | 72.5 | 49.5 |
| prism_noguards | apartment_0/loop_2.0hz_s1/pano | 22.9 | 18.2 |
| prism_se3 | office_4/synthetic_2.0hz/pano | 1.7 | 2.8 |
| prism_se3 | office_4/synthetic_5.0hz/pano | 5.9 | 4.4 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s0/pano | 60.7 | 49.3 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s1/pano | 1.7 | 2.2 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s1/pano | 1.5 | 2.0 |
| prism_se3 | frl_apartment_0/stopgo_2.0hz_s0/pano | 16.7 | 12.0 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s0/pano | 1.3 | 1.3 |
| prism_se3 | frl_apartment_0/synthetic_0.5hz_s1/pano | 1.3 | 1.0 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s1/pano | 2.6 | 3.2 |
| prism_se3 | frl_apartment_0/synthetic_2.0hz_s0/pano | 27.6 | 28.3 |
| prism_se3 | frl_apartment_0/synthetic_5.0hz_s0/pano | 26.8 | 35.8 |
| prism_se3 | frl_apartment_0/loop_2.0hz_s1/pano | 2.0 | 2.3 |
| prism_se3 | apartment_1/stopgo_2.0hz_s1/pano | 215.7 | 142.9 |
| prism_se3 | apartment_1/synthetic_2.0hz_s1/pano | 176.9 | 166.2 |
| prism_se3 | apartment_1/synthetic_0.5hz_s0/pano | 198.6 | 150.3 |
| prism_se3 | apartment_1/synthetic_0.5hz_s1/pano | 184.5 | 141.0 |
| prism_se3 | apartment_1/synthetic_5.0hz_s1/pano | 231.8 | 158.1 |
| prism_se3 | apartment_1/loop_2.0hz_s1/pano | 260.2 | 137.5 |
| prism_se3 | hotel_0/synthetic_2.0hz_s1/pano | 54.2 | 44.2 |
| prism_se3 | hotel_0/synthetic_0.5hz_s0/pano | 2.0 | 2.7 |
| prism_se3 | hotel_0/synthetic_0.5hz_s1/pano | 1.9 | 3.0 |
| prism_se3 | hotel_0/synthetic_2.0hz_s0/pano | 3.5 | 4.8 |
| prism_se3 | hotel_0/loop_2.0hz_s1/pano | 55.9 | 56.5 |
| prism_se3 | apartment_0/loop_2.0hz_s0/pano | 195.1 | 105.8 |
| prism_se3 | apartment_0/stopgo_2.0hz_s1/pano | 37.1 | 26.3 |
| prism_se3 | apartment_0/synthetic_2.0hz_s1/pano | 33.9 | 24.5 |
| prism_se3 | apartment_0/stopgo_2.0hz_s0/pano | 65.7 | 34.7 |
| prism_se3 | apartment_0/synthetic_0.5hz_s0/pano | 66.5 | 45.3 |
| prism_se3 | apartment_0/synthetic_0.5hz_s1/pano | 2.2 | 2.0 |
| prism_se3 | apartment_0/synthetic_2.0hz/pano | 28.3 | 30.5 |
| prism_se3 | apartment_0/synthetic_0.5hz/pano | 66.5 | 45.3 |
| prism_se3 | apartment_0/synthetic_5.0hz/pano | 50.7 | 38.0 |
| prism_se3 | apartment_0/synthetic_5.0hz_s1/pano | 40.1 | 31.4 |
| prism_se3 | apartment_0/synthetic_2.0hz_s0/pano | 28.3 | 30.5 |
| prism_se3 | apartment_0/synthetic_5.0hz_s0/pano | 50.7 | 37.9 |
| prism_se3 | apartment_0/loop_2.0hz_s1/pano | 33.2 | 22.6 |

