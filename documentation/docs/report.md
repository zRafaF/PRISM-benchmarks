# PRISM-benchmarks — preliminary results

*Preliminary results; full evaluation is future work. Hardware: RTX PRO 6000.*

## Table A — Performance & resources

| Method | Run | Eff.FPS↑ | Latency s↓ | VRAM avg GB↓ | VRAM peak GB↓ | GPU util % | GPU W | ckpt MB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pi3 | office_4/synthetic_spline/synthetic_fov | 5.70 | 18.6 | 60.61 | 88.17 | 54 | 346 | 0 |
| prism | office_4/synthetic_spline/pano | 5.41 | 23.7 | 8.08 | 15.23 | 50 | 319 | 3940 |
| mapanything | office_4/synthetic_spline/synthetic_fov | 0.92 | 26.3 | 14.48 | 93.30 | 5 | 53 | 0 |


## Table B — Metric accuracy (absolute scale vs. rendered GT)

| Method | Run | Scale est. | Scale err %↓ | Extent err %↓ |
| --- | --- | --- | --- | --- |
| pi3 | office_4/synthetic_spline | 0.896 | 10.4 | 55.8 |
| prism | office_4/synthetic_spline | 0.977 | 2.3 | 7.9 |
| mapanything | office_4/synthetic_spline | 1.019 | 1.9 | 2.1 |


## Table C — Reconstruction, co-visibility masked (fair)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| pi3 | office_4/synthetic_spline/synthetic_fov | 2.9 | 1.2 | 4.1 | 0.957 |
| prism | office_4/synthetic_spline/pano | 3.7 | 14.3 | 17.9 | 0.617 |
| mapanything | office_4/synthetic_spline/synthetic_fov | 7.4 | 2.5 | 9.8 | 0.613 |


## Table C2 — Reconstruction, full-360 (no mask; pano methods)

| Method | Run | Acc cm↓ | Compl cm↓ | Chamfer cm↓ | F@5cm↑ |
| --- | --- | --- | --- | --- | --- |
| pi3 | office_4/synthetic_spline/synthetic_fov | 3.0 | 5.9 | 8.9 | 0.857 |
| prism | office_4/synthetic_spline/pano | 7.7 | 5.9 | 13.6 | 0.517 |
| mapanything | office_4/synthetic_spline/synthetic_fov | 7.5 | 7.9 | 15.4 | 0.546 |


## Trajectory (ATE/RPE, Sim(3)-aligned)

| Method | Run | ATE RMSE cm↓ | RPE RMSE cm↓ |
| --- | --- | --- | --- |
| pi3 | office_4/synthetic_spline/synthetic_fov | 4.7 | 3.2 |
| prism | office_4/synthetic_spline/pano | 5.7 | 0.4 |
| mapanything | office_4/synthetic_spline/synthetic_fov | 26.5 | 11.3 |