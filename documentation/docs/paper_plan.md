# Paper plan (rerun-v3) — draft for discussion

Working thesis (Rafael, 2026-10-10): **PRISM does not get lost.** A 360 deg camera keeps
seeing structure behind it when it faces a blank wall; the engine turns that into a
streaming, metric, bounded-memory map. The Sim(3) alignment stays, as the mechanism
that makes the panoramic stream cheap to stitch (and its ablation as support), not as
the headline. Findings so far: `paper_findings.md`. Decisions: `decisions.md`.

## Claims and the evidence each one needs

| # | Claim | Evidence | Status |
|---|---|---|---|
| C1 | PRISM keeps track over long indoor walks where pinhole streaming methods lose it | loss metrics (tracked %, loss events, distance to failure) on all scenes x 3 seeds | pilot done; full matrix running |
| C2 | The 360 deg view is the reason, and the engine is what makes it usable | baselines on the same 360 deg data as cube faces (90 deg, 110 deg); engine ablation (se3 / sl4 / sim3cam) | matrix running (90 deg), 110 deg next |
| C3 | It is not the input regime or the harness | rate study 10/5/2 Hz (pilot); baselines' published settings; TUM check 4.1 = 4.1 cm | done |
| C4 | Sim(3) suffices for panoramic submaps | alignment-group study (sim3 / se3 / sl4) on accuracy, continuity and compute | in the matrix (seed 0) |
| C5 | Bounded memory, real time at the deployed rate | VRAM / fps vs sequence length; offline methods' memory growth (96 GB machine) | PRISM done; offline pending |
| C6 | Metric scale without a ranging sensor | metric scale error vs GT | in the matrix |

## Pre-empting "you cherry-picked the paths"
1. **Procedural, seeded paths.** Every walk comes from a published planner
   (`trajectories.grid_walk`) and a seed; nobody draws a path by hand. State the planner,
   the constraints (clearance, 0.5 m/s, 45 deg/s yaw limit) and the seeds; release code,
   seeds and renders.
2. **Every path is shown.** Supplementary figure: all 18 walks (6 scenes x 3 seeds),
   top-down over the walkable map, with each method's loss events marked on the path.
   The paper body shows one easy and one hard scene, chosen by a stated rule
   (median and worst sequence for the *best baseline*, not for PRISM).
3. **Path statistics table.** Length, walkable area, extent, median turn per frame,
   revisit fraction, min clearance — per sequence (`scripts/traj_audit.py` summary).
4. **Per-sequence results, not only means.** Supplementary table with every run; the
   worst PRISM sequence named in the text.
5. **Sensitivity.** Loss metrics at 3 / 5 / 10 cm; rate study; baselines in their own
   published settings; the TUM check showing the baselines are healthy on their data.
6. **Why the baselines fail, mechanistically.** At each baseline loss event, show what
   the pinhole saw (blank wall / close surface) next to the panorama. Quantify it: the
   fraction of loss events that coincide with a low-information pinhole view (GT depth
   very close or low image texture), vs the base rate over all frames. If loss events
   cluster on blank walls, the path is not adversarial — it is a normal indoor walk.

## Figures (draft)
- **F1 teaser:** a hard scene (e.g. office_0) top-down: GT path, PRISM and baselines
  aligned on the first 2 m, loss points marked; inset of a pinhole frame at a loss
  event vs the panorama.
- **F2 survival curve:** fraction of runs still within 0.30 m vs distance travelled,
  pooled over all sequences; PRISM, baselines (pinhole, cube 90, cube 110), offline refs.
- **F3 (supp.):** grid of every path with loss events.
- **F4 why pinholes get lost:** loss events vs pinhole view informativeness (histogram).
- **F5 alignment study:** accuracy, tracked %, and per-window cost for sim3 / se3 / sl4.
- **F6 memory/time vs length:** PRISM bounded; offline methods growing to OOM.
- **F7 real-world:** on-robot reconstructions (existing captures).

## Tables (draft)
- **T1 main:** per scene class (rooms / apartments): ATE, tracked %, loss events,
  distance to failure, F-score (co-visibility masked), metric scale error, fps, peak VRAM.
- **T2 360 control:** pinhole vs cube 90 vs cube 110 vs PRISM: accuracy, loss metrics,
  fps per 360 deg capture, rig consistency.
- **T3 rate study:** 10 / 5 / 2 Hz (pilot), incl. published baseline settings.
- **T4 alignment groups.**
- **T5 offline references (96 GB):** Pi3, MapAnything, PanoVGGT full batch — accuracy and
  memory; they see all frames at once (and are capped/subsampled at 200 frames), so they
  are a quality reference, not a streaming competitor.

## Offline methods (later, 96 GB machine)
Run the same inputs with `BENCH_OFFLINE=1`. Also score them with the loss metrics: a
batch method cannot "lose" a stream, but it can still tear; report whether it does.

## Open items / risks
- Synthetic only for quantitative results so far; a real 360 deg sequence with GT poses
  would strengthen C1 — 360Loc (one indoor scene) is the proposed addition (D31).
- The 360 deg advantage is partly the sensor; C2's cube-face control is what makes the
  comparison fair — it must be in the main paper, not the supplement.
- Old paper text: the alignment-study numbers and "globally consistent" are void
  (RESULTS_CHANGELOG §14-15); the abstract needs rewriting around C1.
- Optional: PRISM's per-window alignment residual as a self-reported "lost" signal,
  checked against the GT loss events.
