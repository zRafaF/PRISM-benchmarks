# PRISM-benchmarks — preliminary results

*Preliminary results; full evaluation is future work. Hardware: RTX PRO 6000.*

## Table A — Performance & resources

| Method | Run | Eff.FPS↑ | Latency s↓ | VRAM avg GB↓ | VRAM peak GB↓ | GPU util % | GPU W | ckpt MB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3.01 | 15.2 | 64.33 | 70.89 | 3 | 92 | 0 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 3.04 | 2.5 | 69.24 | 97.29 | 13 | 124 | 0 |
| prism | office_4/synthetic_2.0hz/pano | 2.37 | 6.0 | 66.56 | 75.81 | 23 | 121 | 3940 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 1.94 | 5.6 | 66.63 | 91.27 | 6 | 73 | 0 |


## Table B — Metric accuracy (absolute scale vs. rendered GT)

| Method | Run | Scale est. | Scale err %↓ | Extent err %↓ |
| --- | --- | --- | --- | --- |
| vggtslam | office_4/synthetic_2.0hz | N/A (scale-free) | — | — |
| pi3 | office_4/synthetic_2.0hz | 0.863 | 13.7 | 61.5 |
| prism | office_4/synthetic_2.0hz | 0.998 | 0.2 | 7.5 |
| mapanything | office_4/synthetic_2.0hz | 0.978 | 2.2 | 5.4 |


## Table C — Reconstruction, co-visibility masked (fair)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3.3 | 7.3 | 10.6 | 0.726 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.5 | 1.5 | 4.0 | 0.960 |
| prism | office_4/synthetic_2.0hz/pano | 2.3 | 8.0 | 10.2 | 0.830 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.5 | 11.9 | 23.4 | 0.441 |


## Table C2 — Reconstruction, full-360 (no mask; pano methods)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 5.8 | 10.4 | 16.2 | 0.552 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 2.7 | 6.8 | 9.5 | 0.845 |
| prism | office_4/synthetic_2.0hz/pano | 5.7 | 5.4 | 11.1 | 0.712 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 11.1 | 19.2 | 30.3 | 0.390 |


## Table D — Cloud cleanliness & size

*noise% = pred points far from any GT surface (fluffy floaters); precision@2cm = pred points within 2 cm of GT (sharpness).*

| Method | Run | Points | Size MB↓ | Noise %↓ | Prec@2cm %↑ |
| --- | --- | --- | --- | --- | --- |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 3177384 | 85.8 | 1.0 | 28.2 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 1077863 | 16.2 | 0.5 | 47.7 |
| prism | office_4/synthetic_2.0hz/pano | 647394 | 9.7 | 0.5 | 49.8 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 1220150 | 18.3 | 42.8 | 14.5 |


## Trajectory (ATE/RPE, Sim(3)-aligned)

| Method | Run | ATE RMSE cm↓ | RPE RMSE cm↓ |
| --- | --- | --- | --- |
| vggtslam | office_4/synthetic_2.0hz/synthetic_fov | 30.7 | 32.0 |
| pi3 | office_4/synthetic_2.0hz/synthetic_fov | 5.2 | 4.4 |
| prism | office_4/synthetic_2.0hz/pano | 1.8 | 0.8 |
| mapanything | office_4/synthetic_2.0hz/synthetic_fov | 26.1 | 18.0 |