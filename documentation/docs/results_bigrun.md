# Big-benchmark results & analysis (2026-07, Replica)

Raw data archived at `documentation/docs/data/bigrun_2026-07/` (`report_raw.md`,
`perf.csv`). This page is the **cleaned, unbiased analysis** we cite for the paper.
Numbers here are recomputed from the per-run tables, **not** copied from the report's
own summary tables (those are contaminated — see below).

## Provenance & caveats (read first)

- **The report's top "Global aggregate" and "Alignment-group study" tables are
  contaminated** and must not be cited. They mix the new seeded matrix with **stale
  runs from the earlier 2-scene experiment** (unsuffixed traj ids like
  `synthetic_2.0hz`, with co-tenancy-inflated 70–100 GB VRAM). In particular the
  `prism_sl4` row (N=6) is *entirely* stale 2-scene data — its rosy ATE 26 / F 0.66 is
  **not** comparable to anything here. Fix before the next run: `make clean-results`
  first so only the seeded matrix is aggregated.
- **Clean data = seeded runs only** (`_s0` / `_s1`), which is what this page uses:
  **4 scenes** (`apartment_0`, `apartment_1`, `frl_apartment_0`, `hotel_0`) × 2 seeds ×
  {smooth 0.5/2/5 Hz, stop-and-go 2 Hz, loop 2 Hz}. 368 clean run-records.
- **All 4 clean scenes are LARGE** (multi-room apartments + a hotel). There is **no
  small/easy room** in the seeded set (`office_4` has only stale data). So every
  absolute number here is **pessimistic** — all methods drift on these. Add a small
  scene (office/room) before the paper; the headline accuracy will improve for everyone.
- **Perf glitch:** 43/368 seeded runs recorded `latency = 0.0` (perf logging miss).
  VRAM/FPS look sound; treat per-run *latency* as partial.
- Rendered frames are noise-free → an optimistic upper bound vs real captures.

## Corrected per-method aggregate (seeded, 4 large scenes × 2 seeds)

Lower is better except F↑, Prec↑. "scale%" = |s−1| for metric methods (N/A = scale-free).

| Method | ATE cm | drift %/m | Masked F | Full-360 F | Map MB | Outlier % | Prec@2cm | Scale err % | VRAM GB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **prism** (SL4, ours) | **65.3** | 52.2 | 0.42 | 0.31 | 22.1 | **2.44** | 16.3 | 14.6 | 15.5 |
| prism_sim3 | 68.9 | 49.1 | 0.40 | 0.28 | 20.9 | 2.48 | 15.5 | 14.0 | 15.4 |
| prism_se3 | 67.1 | 48.6 | 0.39 | 0.28 | 21.0 | 2.46 | 15.1 | 13.4 | 15.6 |
| panovggt (ref, offline) | 66.6 | 49.0 | **0.58** | **0.45** | 103.0 | 3.93 | **17.0** | N/A | 24.9 |
| pi3 (offline) | **62.5** | 61.3 | 0.49 | 0.35 | 23.4 | 2.73 | 14.4 | **8.7** | 36.3 |
| mapanything (offline) | 95.7 | 95.4 | 0.26 | 0.19 | 28.9 | 3.51 | 7.4 | 22.0 | 44.9 |
| laser (stream) | 86.8 | 56.7 | 0.35 | 0.22 | **6.1** | 3.35 | 9.7 | N/A | **8.4** |
| vggtslam (stream) | 132.0 | 159.4 | 0.22 | 0.16 | 102.2 | 3.71 | 8.9 | N/A | 8.9 |

## Finding 1 — PRISM still dominates VGGT-SLAM (its direct competitor). Robust.

On the same 4 large scenes: PRISM **ATE 65 vs 132 cm (2×)**, Masked F **0.42 vs 0.22**,
map **22 vs 102 MB (~5×)**, cleaner (outlier 2.4 vs 3.7), and metric vs scale-free. This
holds across every trajectory type. This is the clearest, safest headline.

## Finding 2 — The alignment group is MOTION-DEPENDENT (the loop test paid off).

This is the important new result. Stratified by trajectory (2 Hz):

| Trajectory | SL(4)=prism ATE / F / scale% | Sim(3) ATE / F / scale% | SE(3) ATE / F / scale% |
| --- | --- | --- | --- |
| smooth | **44.0** / **0.46** / 10.3 | 46.2 / 0.41 / **10.0** | 46.6 / 0.41 / 10.1 |
| stop-and-go | **51.9** / **0.43** / **12.1** | 72.3 / 0.38 / 16.0 | 67.4 / 0.37 / 15.0 |
| **loop** | 110.5 / 0.26 / 31.4 | **101.9** / **0.34** / **20.3** | 101.2 / 0.33 / 20.1 |

- On **smooth & stop-and-go** (well-overlapped motion), **SL(4) wins** — its extra DoF
  fit the clean overlaps better (better ATE, F, and even scale).
- On **loop** (revisit), **SL(4) LOSES decisively**: ATE 110 vs ~102, F 0.26 vs 0.33–0.34,
  and metric scale blows up to **31% vs ~20%**. This is exactly the theorised failure —
  SL(4)'s projective freedom accumulates non-rigid drift when the path closes, which
  Sim(3)/SE(3) forbid by construction. The loop trajectory made the mechanism visible.

**Implication for the default.** SL(4) is best *only* when the trajectory never revisits.
Real deployment loops. Given SL(4)'s loop failure (and worse metric scale there), **Sim(3)
is the more defensible default** — near-identical on smooth/stop-go, materially more
robust on loops. Recommend flipping the default back to Sim(3) for the paper, and
reporting the trade-off table above as a contribution (it's a clean, mechanistic result).
The Sim(3) vs SE(3) gap is negligible here (the scale DoF barely matters once grounded).

## Finding 3 — The drift guards show NO measurable benefit. Honest negative.

Matched comparison on the stress trajectories (stop-and-go + loop, same runs):

| | ATE cm | drift %/m | Masked F | Outlier % |
| --- | --- | --- | --- | --- |
| guards ON (default) | 83.9 | 63.6 | 0.34 | 2.52 |
| guards OFF (noguards) | 81.2 | 58.8 | 0.34 | 2.53 |
| nolock / nostill | 83.9 | 63.7 | 0.33 | 2.6 |

Turning the guards off is, if anything, marginally *better* on ATE/drift and identical on
F/cleanliness. The guards may still prevent catastrophic *visual* failures the metrics
don't capture (flips, sinking floors), but there is **no quantitative case** for them on
this benchmark. Do not claim the guards improve accuracy. (The earlier impression that
they helped was a trajectory-mix confound — `prism` averaged in easy smooth runs the
guard arms never got.)

## Finding 4 — Trajectory accuracy: PRISM leads on smooth/stop-go, trails on loop.

ATE by trajectory (2 Hz), best in **bold**:

| Method | smooth | stop-and-go | loop |
| --- | --- | --- | --- |
| **prism (ours)** | **44.0** | **51.9** | 110.5 |
| pi3 (offline) | 62.4 | 57.5 | **62.5** |
| panovggt (offline) | 72.3 | 56.0 | 76.1 |
| vggtslam | 136.4 | 144.7 | 132.5 |
| laser | 88.8 | 87.5 | 118.7 |
| mapanything | 97.5 | 92.7 | 103.1 |

PRISM has the **best trajectory of all methods on smooth and stop-and-go** — including vs
the offline full-batch nets. On **loop it degrades** (110 cm): a streaming engine with no
global loop closure cannot correct the accumulated error that the full-batch nets (which
see all frames at once) implicitly close. This is the expected, honest limitation and
motivates the future loop-closure work.

## Finding 5 — Reconstruction & metric scale: reality check.

- **Reconstruction F:** offline **PanoVGGT (0.58) and Pi3 (0.49) beat PRISM (0.42)** —
  the streaming/fusion tax, consistent with before. PRISM's advantage is *cleanliness and
  compactness*, not raw F (outlier 2.4 = best; 22 MB vs PanoVGGT 103 MB).
- **Metric scale is NOT a PRISM win on hard scenes.** Pi3 is the most metric-accurate and
  stable (7–9% across all trajectories); PRISM is 10% on smooth but degrades to 31% (SL4)
  / 20% (Sim3) on loop. The preliminary "3.2%, only metric method" headline was an
  easy-2-scene artifact and **does not replicate**. Correct framing: PRISM is metric
  (unlike LASER/PanoVGGT/VGGT-SLAM) and competitive with Pi3 on smooth motion; Pi3 is
  more metric-robust overall.

## Finding 6 — Memory / compute.

Peak VRAM (seeded mean): PRISM **15.5 GB**, PanoVGGT 24.9, Pi3 36.3, MapAnything 44.9;
VGGT-SLAM 8.9, LASER 8.4 (both pinhole/sparse). So PRISM is the **most memory-bounded
dense/panoramic method** and far below the full-batch nets, but not below the pinhole
streamers. FPS ~3.2 (mid-pack). Latency partially unrecorded (see caveats) — re-run for a
clean compute-impact figure.

## Conclusions we can defend in the paper

Holds up (safe to claim, on 4 large scenes):

1. PRISM beats VGGT-SLAM ~2× ATE, ~2× F, ~5× map size — its advantage is the panoramic
   metric engine, not the pose-graph group.
2. PRISM has the best trajectory accuracy on non-looping motion (smooth, stop-and-go),
   beating even offline full-batch nets.
3. PRISM produces the cleanest and (among dense methods) most compact, most
   memory-bounded maps.
4. Alignment-group trade-off is real and mechanistic: SL(4) wins on open paths, Sim(3) is
   robust on loops → we adopt **Sim(3)** for deployment robustness.

Does NOT hold / must be stated honestly:

5. Reconstruction F trails offline full-batch (streaming tax).
6. Metric-scale accuracy is competitive-with-Pi3, not dominant; degrades on loops.
7. The drift guards have no measurable quantitative benefit here.
8. Loop-closure is a genuine gap (streaming, no global BA).

## Fix before the paper run

- `make clean-results` then re-run so **no stale/contaminated rows** enter the aggregate;
  fix the report to aggregate seeded runs only (or drop unsuffixed runs).
- Include at least one **small scene** (office/room) so the matrix isn't all hard rooms.
- Fix perf **latency logging** (43 zeros) for a clean compute-impact figure.
- Flip the default to **Sim(3)** (Finding 2) — or report both and let the trade-off table
  make the case.
- Later: add **ScanNet++** and **KITTI-360**; a **loop-closure** variant of PRISM to
  address Finding 4/8.
