# RESULTS_CHANGELOG

What changed in the benchmark between the 2026-07 big run and the 2026-08 publication
run, which runs were excluded and why, how the numbers moved, and what still needs a GPU.

**Rule applied throughout: no fabricated or interpolated numbers.** Every value below
comes from a real recorded run, or is labelled as an *estimate* with the model that
produced it. Where the current data cannot support a result, the item is listed under
[§10 Not yet run](#10-not-yet-run) with the exact command, and no number is given.

## Run history

| Run | Matrix | Status |
|---|---|---|
| **2026-07 big run** (`documentation/docs/data/bigrun_2026-07/`) | 4 scenes × 2 seeds × 200 frames, 8 methods → 434 records / 368 seeded | Archived. Carries the two engine bugs in §3. Re-aggregated cleanly in §5–§7. |
| **2026-08-08 overnight** | — | **Void: zero method runs dispatched.** Driver bug, §4. |
| **2026-08-09 overnight** | 5 of 6 scenes × 3 seeds × 4–207 frames, 590 runs | **Void: not citable.** Six independent defects, §13. |
| **2026-08-10 rebuild** | fixes for all six landed; awaiting smoke + re-run | see §13 |

---

## 1. The headline correction: 43 "latency = 0.0" runs are failed runs, not a logging miss

`09_benchmark_findings_bigrun.md` §0 records "43/368 runs logged `latency = 0.0`
(logging miss); VRAM/FPS are sound". Re-deriving the per-run records from the archived
snapshot shows something materially worse.

The 43 zero-latency runs are **exactly** the 43 runs that produced **no evaluable
output at all** — no ATE, no reconstruction, no cleanliness row. The two sets are
identical, not merely overlapping. And they are not spread across the matrix:

| | |
|---|---|
| Methods affected | **PRISM arms only** — `prism` 9, `prism_sim3` 10, `prism_se3` 9, guard arms 5 each |
| Baselines affected | **zero** (laser, pi3, panovggt, mapanything, vggtslam: 40/40 each) |
| Scenes | `hotel_0` 24, `apartment_1` 18, `apartment_0` 1 |
| Motion | stop-and-go 18, loop 12, smooth 13 |
| Rate | **25.6% of all seeded PRISM-arm runs** (43 of 168) |

The mechanism is visible in the code. `adapters/base.py::_merge_runner_perf` only set
`latency_end_to_end_s` if the runner had written `perf_runner.json`; a runner that died
before its final write left the field at its `0.0` default. So `latency == 0.0` is not a
logging miss — it is *the crash signature*, and it coincides exactly with "no results to
evaluate".

**Three consequences the previous analysis did not account for:**

1. **Throughput was inflated.** `result.n_frames` was taken from the *input*
   `meta.json`, so a run that died after 20 of 84 frames still reported `84 / wall`.
   Those inflated values were averaged into the published fps.
2. **PRISM's quality metrics carry survivorship bias.** The 43 missing runs are
   concentrated on the two hardest scenes and the stress trajectories — precisely where
   PRISM would have scored worst. PRISM's ATE/F are means over the 75% of runs it
   survived; every baseline's are means over 100% of theirs. The two are not
   like-for-like, and no amount of re-aggregation fixes it — **only re-running does.**
3. **A 25.6% failure rate on the hard half of the matrix is itself a finding**, and
   arguably a more important one for a robotics venue than any metric in the table.

**Status: root cause found (§2), instrumentation and aggregation fixed (§7); the
survivorship bias is resolved only by the 2026-08-09 re-run.**

---

## 2. Root cause of the PRISM crashes — a diagnostic string

`prism_vggt/engine.py:838` formatted a value that is legitimately `None`:

```python
f"floor_scale={floor_scale:.4f}"     # TypeError when no floor was found this window
```

`floor_scale` is `None` whenever a window contains no floor-plane inlier — common in a
corridor, a window looking at a wall, or a dwell segment. The engine then died
*mid-sequence*, after some frames had been processed but before any result was written:
exactly the "no evaluable output + `latency = 0.0`" signature of §1. Fixed:

```python
_fs = ("n/a (no floor this window)" if floor_scale is None else f"{floor_scale:.4f}")
```

I then scanned the engine for siblings (other `:.Nf` formats on optionally-`None`
values); this was the only real hazard.

**Two hypotheses I published before this and which were wrong**, recorded so they are
not repeated: (a) that the failures were motion-family-specific — disproved by
`synthetic_2.0hz_s0` failing; (b) that they were caused by a short tail window —
disproved by the failing tails being 11–15 frames, well inside the safe range.

**What this does and does not establish.** The crash is reproduced and fixed, and its
signature matches §1 exactly. It is *not* proven that it explains all 43 archived
failures, because the 2026-07 per-run `run.log` files were not kept — only the aggregate
snapshot. Treat "this explains the 43" as the leading explanation, not a verified fact.
The publication run's `completion.csv` is what will settle it: a PRISM failure rate near
zero confirms it, anything else means there is a second cause.

---

## 3. Engine fix — PRISM was dropping the tail of every sequence

`prism_vggt/engine.py:647`:

```python
all_starts = range(0, num_frames - self.window_size + 1, self.window_size - self.overlap)
```

The `- window_size + 1` bound discards any window that would run past the end, so the
tail of every sequence was never posed or integrated. Dropped frames =
`(n - window_size) % (window_size - overlap)`.

| n | old poses | dropped | new poses |
|---|---|---|---|
| 20 | 16 | **4 (20%)** | 20 |
| 47 | 40 | **7** | 47 |
| 84 | 76 | **8** | 84 |
| 200 | 196 | **4** | 200 |
| < 16 | **0** | all | all |

So the **2026-07 big run carried this too** — PRISM was scored on 4–8 fewer frames than
every baseline, and the missing part is the drift-heavy end. It was invisible because
`perf.json.n_frames` was copied from the *input* meta; the `n_frames_done` change is what
surfaced it.

Fixed by bounding at `num_frames - overlap` (matching the harness's own
`sliding_windows`) and indexing the loop body by the actual window length `win_len`
rather than `self.window_size`, at the five sites that would otherwise `IndexError` on a
short tail window. Partial tail windows are no longer marked done, so streaming mode
re-runs them at full size when more frames arrive. Verified: every frame posed exactly
once, no duplicates, tail window always longer than the overlap, for n = 5…400.

**Second-order consequence:** `PRISM_ALIGN` is only consulted from the *second* window
onward (`is_first_window` short-circuits it). With one window it was a complete no-op —
which is why `prism`, `prism_sl4` and `prism_se3` returned identical numbers on short
sequences. The alignment study needs `n > 2·window_size − overlap` = **28 frames
minimum**; the smoke now enforces 120.

---

## 4. Post-mortem: the 2026-08-08 overnight ran nothing (my bug)

`scripts/run_overnight.sh` read the method lists from config like this:

```bash
print('CORE=' + ' '.join(core))      # -> CORE=prism panovggt pi3 mapanything vggtslam laser
eval "$(read_cfg)"
```

Unquoted, `eval` parses `CORE=prism panovggt pi3 …` as *"set CORE=prism for the duration
of the command `panovggt`"*. Hence the four lines at the top of that log:

```
scripts/run_overnight.sh: line 60: panovggt: command not found
[19:03:27] CORE  =
[19:03:27] ALIGN =
```

`run_set` looped over an empty list, every phase completed instantly, and the run
reported DONE. Grepping the log for `>>> RUN` returns **0**. The bundle produced that
night contained *leftover smoke results* that the checkpoints then aggregated as if
fresh. I verified that script with `bash -n` and by running the Python half in isolation
— never the bash `eval` path, which is exactly where it broke.

**Four independent defences now, because any one alone would have let this through:**

1. Values are emitted **shell-quoted** (`shlex.quote`) to a file and `source`d — no bare `eval`.
2. An empty method list is a **hard abort**, not a silent no-op.
3. The **full plan is printed** before anything runs — scenes, trajectories, methods,
   frames, total runs — and every run is counted `[n]`. A final
   `WARNING: ZERO runs were dispatched` fires if the count is 0.
4. `DRY_RUN=1` prints the plan and exits, so the matrix can be checked without GPU time.

Also added: an abort if `PRISM_CONFIG_OVERLAY` is set (the smoke overlay leaking into an
overnight would silently shrink the matrix), and a warning when `results/` already holds
runs from a previous matrix. All four paths were tested by execution, not inspection.

---

## 5. Runs excluded from the clean aggregate, and why

Exclusions are declarative (`EXCLUSIONS` in `eval/aggregate_clean.py`), each carrying a
stated reason that is printed and written into every output, so a run can never be
dropped silently or re-enter by being renamed.

| Excluded | Count | Reason |
|---|---|---|
| Unseeded trajectory ids (`synthetic_2.0hz` etc.) | 66 | Stale 2-scene experiment. VRAM co-tenancy-inflated to 70–102 GB — including *streaming* methods (laser 70.3 GB, prism 77.1 GB) whose seeded budget is 8.4 / 16.0 GB. |
| Scene `office_4` | (within the 66) | Only ever had stale data; never rendered under a seed. |
| Arm `prism_sl4` (2026-07 era) | 6 | Entirely stale 2-scene data (N=6). Its rosy ATE 26 / F 0.66 is not comparable to anything in the seeded matrix. |
| Runs with no evaluable output | 43 | See §1. Excluded from **every** aggregate including perf, because their `eff_fps` is inflated. |
| Sweep arms (`prism_vox*`, `prism_depth*`) | — | Never enter the headline tables; they are an operating-point curve, not competitors (§8). |

**434 input records → 368 seeded → 325 aggregated.**

`make verify-clean` asserts all of this and fails non-zero on violation. It was tested
against six injected contamination cases (unseeded run, `office_4` run, co-tenancy
streaming VRAM, full-batch VRAM outlier, incomplete run, silent zero-latency run) and
detects all six. Its column lookup is **by header name**, after an earlier version broke
silently when new columns shifted hardcoded indices and it began comparing masked-F
against the published outlier percentage.

---

## 6. New numbers vs old (2026-07 archive, re-aggregated)

Reconstruction and trajectory metrics are **unchanged** — incomplete runs contributed no
ATE/recon values, so they were never in those means. Only **perf** moves, and only for
the PRISM arms (the only ones with incomplete runs).

| Metric | Method | Published (`results_bigrun.md`) | Clean (complete runs only) | Δ |
|---|---|---|---|---|
| Eff. FPS | `prism` | 3.25 | **2.88** | −11.3% |
| Eff. FPS | `prism_sim3` | 3.43 | **2.84** | −17.0% |
| Eff. FPS | `prism_se3` | 3.29 | **2.93** | −11.0% |
| VRAM peak GB | `prism` | 15.51 | **15.95** | +2.9% |
| VRAM peak GB | `prism_sim3` | 15.40 | **15.89** | +3.2% |
| VRAM peak GB | `prism_se3` | 15.56 | **16.01** | +2.9% |

Everything else reproduces the published table exactly; `make verify-clean` enforces
that as a regression test (`--include-incomplete` reproduces `results_bigrun.md` to
within rounding for all 8 methods × 9 metrics).

### What this does to the real-time claim

The plan's framing — "PRISM is the slowest streamer (~3.4 fps Sim(3)) but still exceeds
the 2.5 Hz capture rate" — survives, but with a materially thinner margin:

| | Eff. FPS (clean) | vs 2.5 Hz capture |
|---|---|---|
| PRISM (Sim(3), deployed) | **2.84** | +13.8% |
| PRISM (SL(4)) | 2.88 | +15.2% |
| LASER | 4.83 | +93% |
| VGGT-SLAM | 4.61 | +84% |

2.84 fps, not 3.43. Still real-time against a 2.5 Hz capture rate, still the slowest
streamer, still doing strictly more work (dense metric fusion) — but "comfortably
real-time" is not supportable at a 13.8% margin, and the seed spread on fps is ±0.16
(5.7%), so the margin is only ~2.1 standard deviations. Recommend phrasing it as
"sustains the 2.5 Hz capture rate" rather than any claim of headroom.

**These numbers are superseded the moment the publication run finishes** — the tail-drop
fix (§3) changes PRISM's frame count and therefore its fps, and the crash fix (§2)
removes the survivorship bias. Do not cite this table alongside 2026-08 numbers.

---

## 7. Statistical rigour: what actually separates, and what does not

Two additions, because the previous analysis compared marginal means with no dispersion.

### 7a. Error bars now isolate seed noise

The replicate cell is `(method, scene, trajectory-family, rate)`; the seeds inside it are
the repeats. Reporting a std across `(scene, seed)` units instead — the obvious first
approach — mostly measures "apartment_0-loop differs from hotel_0-smooth", which is not
an error bar. `seed_repeatability.csv` gives the within-cell figure; `variance.csv`
keeps the between-cell heterogeneity separately.

**Seed-to-seed spread is large.** ATE within-cell seed std is **25–60% of the mean**
(prism 54%, pi3 25%, laser 54%, vggtslam 45%). The render seed changes the trajectory
instance — a different path through the same room — so this is real sensitivity, not
measurement noise. With 2 seeds each cell's variance has 1 d.o.f.; pooling across cells
is what makes it usable at all. **The publication run uses 3 seeds**, which gives each
cell 2 d.o.f. and makes the per-cell interval meaningful rather than merely poolable.

### 7b. Paired head-to-head (`paired_head_to_head.csv`)

Because every method saw the same rendered trajectories, runs can be matched on
`(scene, traj)` and differenced — cancelling the scene/motion spread that dominates the
marginal means. Reference arm = `prism_sim3` (the new deployed default). Separability is
called only when the 95% CI excludes zero **and** an exact sign test agrees (the sign
test assumes no distribution, which matters because ATE is heavy-tailed).

**Robustly separable:**

| vs | Metric | Mean Δ | Wins | Sign-test p |
|---|---|---|---|---|
| vggtslam | ATE | **−59.5 cm** | 29/30 | <0.0001 |
| vggtslam | Masked F | **+0.128** | 25/30 | 0.0003 |
| vggtslam | Map MB | **−76.7** | 30/30 | <0.0001 |
| mapanything | ATE | −21.7 cm | 23/30 | 0.005 |
| panovggt | Map MB | **−82.3** | 30/30 | <0.0001 |
| panovggt | Masked F | −0.204 *(PRISM worse)* | 4/30 | 0.0001 |
| pi3 | Masked F | −0.134 *(PRISM worse)* | 9/30 | 0.043 |

**NOT separable — claims that must be softened:**

| vs | Metric | Mean Δ | Wins | Sign-test p |
|---|---|---|---|---|
| **laser** | **ATE** | −10.9 cm | 20/30 | **0.099** |
| **laser** | **Masked F** | −0.008 | 10/30 | **0.099** |
| panovggt | ATE | +6.2 cm | 9/26 | 0.169 |
| pi3 | ATE | +17.0 cm | 11/30 | 0.201 |
| `prism` (SL4) | ATE / F / map / fps | all | — | 0.29–1.00 |
| guard arms | ATE / F / map / fps | all | — | 0.23–1.00 |

Three consequences for the paper:

1. **The VGGT-SLAM and map-compactness wins are rock solid** — they survive pairing at
   p < 0.001, and the 5× map advantage is 30/30. *(The VGGT-SLAM comparison is against
   its mis-configured w=16 arm; see §8.)*
2. **"PRISM beats LASER" does not survive pairing** (p = 0.099 on both ATE and F). The
   marginal means (86.8 vs 68.9 cm) suggested otherwise. Do not claim it.
3. **The guard ablation's negative result is now properly supported** — previously an
   eyeballed "no measurable benefit", now a paired test that fails to separate on every
   metric.

The alignment arms are also inseparable *pooled* — expected, not a contradiction,
because the SL(4)/Sim(3) difference is motion-dependent and lives in the stratified
table, where it is large (loop: ATE 110.5 vs 101.9, F 0.26 vs 0.34, scale 31.4% vs
20.3%).

---

## 8. Fairness and scope changes in the publication matrix

### 8a. VGGT-SLAM now runs its published configuration

Its own log said `Total number of submaps in map 1` / `Total number of loop closures in
map 0`. With one submap there is no SL(4) inter-submap registration and no loop closure:
it was running as plain feed-forward VGGT on 8 keyframes.

- **`submap_size` was 16; the published headline is w = 32.** Their appendix w-sweep
  shows TUM SL(4) ATE 0.115 (w=8) → 0.083 (w=16) → **0.053 (w=32)**. Running w=16 handed
  them a ~55% worse ATE than they publish — unprompted, and indefensible in a
  head-to-head. Now **32**, with `vggtslam_w16` kept as an explicit matched-window
  ablation so the w-effect is a *reported result*, not a hidden handicap.
- `min_disparity` 50 px kept: repo default, and what VGGT-SLAM 2.0 states it uses. (The
  1.0 paper text says 25 px — the divergence is recorded in the config.)
- They average over **≥5 runs** because RANSAC makes the method stochastic; we run 3
  seeds, which is fewer, and that should be stated.
- **Degeneracy guard:** the runner parses submap and loop-closure counts out of the log,
  writes them to `arm_config.json`, and warns loudly when submaps < 2.
  `completion.csv → n_degenerate` must be checked before any VGGT-SLAM comparison is
  cited. Expect degeneracy on the small rooms (`room_0`, `office_0`) — short sequences
  yield too few keyframes for a second submap at w=32.
- Loop closure is now an explicit two-arm study (`vggtslam_noloop` / `vggtslam_loop`),
  so the previous "max_loops was 0 or 1?" ambiguity cannot recur.

### 8b. Unbounded sequences and OOM as a recorded result

`trajectories.n_frames` was **200**, with the comment *"full-batch baselines are near the
VRAM limit at 200"* — capping every method's sequence length to protect the offline ones,
which suppresses exactly the property the streaming engine exists for. Methods are now
unbound (`baselines.max_frames: null`, nothing silently subsampled to survive), and OOM
is a first-class outcome:

- `adapters/base.py` classifies a failed run as `oom` / `killed` / `error` by scanning
  the log for CUDA-OOM signatures; `perf.json` gains `oom` and `failure_kind`.
- The aggregate separates `N failed` from `N OOM` — an OOM is a capacity result, not a
  defect — and emits **`capacity.csv`**: longest sequence completed, shortest sequence
  that OOMed, max peak VRAM, per method.
- Published precedent: LASER's KITTI table reports VGGT, Pi3 and Fast3R as **OOM on all
  11 sequences**.

The matrix operating point is **300 frames**, not 600. Cost scales linearly in frames
*and* seeds; at 600 × 4 seeds the matrix was ~39 h of GPU and ~427 GB of exports
(*estimate*, from fitting `wall = load + b·frames` per method on the 2026-07 runs). At
300 frames / 3 seeds / no stop-and-go / no guard arms / 16-bit PNG depth it is ~792 main
runs, ~10 h, ~30 GB — and 300 still lengthens the 5 Hz sequences past the old 200 cap,
which is where the extra length actually matters. The *exact* OOM limits come from
`make capacity-sweep`, which finds each method's real OOM frame count on one scene,
rather than from this matrix, which can only say "it OOMed at 300".

### 8c. Voxel / max-depth sweep is now part of the overnight

PRISM's reconstruction is scored after nvblox TSDF fusion, so voxel size and truncation
distance are fidelity/memory knobs that sit *between* the engine and the metric. A single
operating point makes "PRISM is 4th on masked F" unfalsifiable — it could be the engine
or it could be the fusion setting. Five arms now trace the curve, with `prism` itself
(0.02 m / 4.5 m) as the reference point:

`prism_vox010` (0.01 m), `prism_vox040` (0.04), `prism_vox080` (0.08),
`prism_depth30` (3.0 m), `prism_depth60` (6.0 m) → `voxel_sweep.csv`.

Two implementation notes that matter:

- The overrides are **PRISM-only env vars** (`PRISM_VOXEL_SIZE`, `PRISM_MAX_DEPTH`) read
  in `adapters/runners/prism_runner.py`. They deliberately do *not* touch
  `cfg["engine"]["voxel_size"]`, because `panovggt_runner.py:75` and `pi3_runner.py:81`
  read that same key for their own fusion dedup — changing it would have silently moved
  the baselines too.
- Sweep arms run a **reduced scene/traj set** (Phase 5 of the overnight, ~20 runs) and
  are excluded from every headline table by `is_sweep()`. Each writes `arm_config.json`
  recording the operating point actually applied; the smoke asserts all five differ.

### 8d. Matrix scope

- **6 scenes** with `must_include: [room_0, office_0]` pinned *before* the random draw,
  so the small/easy end of the difficulty range is a config property, not an RNG outcome.
  The 2026-07 matrix was four large/hard scenes, which made every absolute number
  pessimistic.
- **3 seeds** (1234 / 5678 / 9012).
- **Stop-and-go dropped** from the paper matrix (arms commented out, not deleted). It is
  the family with the unexplained PRISM collapse (§11) and there is no time to diagnose
  it; running it and omitting it would be worse than not running it. Kept: `synthetic`
  (0.5 / 2.0 / 5.0 Hz) and `loop` (2.0 Hz).
- **Guard arms dropped** — their negative result is already established at p ≈ 0.23–1.00
  (§7b) and re-running them costs a sixth of the night for nothing.

### 8e. Depth storage: 16-bit PNG in millimetres

`dataset/render_scene.py` wrote float32 `.npy`; depth was **78% of the export bytes**.
Now 16-bit PNG in mm (~90% smaller). Every reader got a self-contained `load_depth()`
with a `.png` → legacy `.npy` fallback, so old exports still work:
`eval/visibility_mask.py`, `eval/fig_cubemap.py`, `eval/fig_fusion.py`,
`adapters/runners/_io.py`, `adapters/runners/runner_io.py`.

At 0.5 mm quantisation this is far below any metric we report (ATE in cm, F-score at
5 cm); the loss is not measurable in any table.

---

## 9. Why the run is long, and why it is not parallelised

Two questions worth recording, because the answer is not obvious:

- **Time is real inference.** Fitting per-method wall time against frame count on the
  2026-07 runs gives ~84% frame-proportional inference and ~16% fixed model-load. IPC
  and dataset rendering are not the bottleneck; there is no cheap win from the harness.
- **Parallelising on one GPU would corrupt the results.** Peak-VRAM is a reported metric,
  and two methods co-resident on one device inflate each other's peak — this is the
  *documented* cause of the 70–102 GB co-tenancy contamination that forced the 66-run
  exclusion in §5. Sequential is a correctness requirement here, not a missed
  optimisation.

---

## 10. Not yet run

Tracked in `results/report_tables/MANIFEST.json → not_yet_run` so a stale table cannot be
cited by mistake.

| Item | Status | Command |
|---|---|---|
| Publication matrix (6 scenes, 3 seeds, 300 frames) | **Running** (launched 2026-08-09) | `make bench-overnight` / `make bench-status` |
| OOM + capacity limits | Target implemented, never run. Not part of the overnight — it is a separate frame-length prefix sweep | `make capacity-sweep` |
| Re-check of the published-baseline comparison | Blocked on VGGT-SLAM producing ≥2 submaps in the new run (`completion.csv → n_degenerate`) | after the matrix completes |
| Stop-and-go diagnosis | Deferred by decision; arms commented out in `config.yaml` | re-enable `extra_kinds.stopgo`, run one scene |
| Latency for the 2026-07 archive | Cannot be retro-filled; those runs stay excluded | n/a |

### Baseline numbers from the literature

`recon_literature.csv` exists because a naive "our F vs their F" table is not
constructible: **no baseline paper reports an F-score**, and the ones that report
accuracy/completeness do so on different datasets, in different units, under different
alignment. The table records what each paper actually publishes, with its dataset and
units, so the comparison in the paper is explicitly *indicative* rather than a
head-to-head. Two errors in `uofa-2026-report/resources/context/01_sota_papers.md` would
otherwise have propagated into it:

- `:46,61` — VGGT's DTU numbers are labelled ETH3D. 1.741 → 0.382 is **DTU**; ETH3D is
  0.709 → 0.677.
- `:394-395` — 0.011 m 7-Scenes accuracy is attributed to LASER; that is **offline
  Pi3**'s number. LASER's is 0.013 m.

There is also **no Pi3/Pi3X paper in the repo** (`references_sota.bib:259` flags it as a
to-do); its only documented numbers are third-party baseline rows in other papers'
tables, which should be stated wherever Pi3 is cited.

---

## 11. Code changes

| Area | File | Change |
|---|---|---|
| Engine — tail drop | `PRISM-VGGT/prism_vggt/engine.py` | Window bound `num_frames - overlap`; loop body indexed by `win_len`; partial tail windows not marked done (§3). |
| Engine — crash | `PRISM-VGGT/prism_vggt/engine.py` | `floor_scale=None` no longer formatted with `:.4f` (§2). |
| Latency instrumentation | `adapters/base.py` | `_merge_runner_perf` falls back to the orchestrator's `wall_s` when a runner writes no `perf_runner.json`, derives per-window latency from wall/window-count, and records **`latency_source`** (`runner` / `orchestrator_wall` / `derived_wall_over_windows` / `unavailable`) so a fallback can never be mistaken for a measurement. |
| Partial-run + failure classification | `adapters/base.py`, `bench/perf.py` | `n_frames_input` / `n_frames_done` / `completed` / `returncode` / `oom` / `failure_kind`. **`eff_fps` computed from frames actually produced**, so a crashed run cannot report throughput it did not achieve. |
| Config overlay | `bench/config.py` | `PRISM_CONFIG_OVERLAY` merged last — how the smoke profile applies without touching `config.yaml`. |
| Sweep overrides | `adapters/runners/prism_runner.py` | `PRISM_VOXEL_SIZE` / `PRISM_MAX_DEPTH`, PRISM-only by design (§8c); writes `arm_config.json`. |
| VGGT-SLAM | `adapters/runners/vggtslam_runner.py` | `VGGTSLAM_MAX_LOOPS` / `VGGTSLAM_SUBMAP_SIZE`; parses submap + loop-closure counts from stdout; `arm_config.json` with `degenerate_single_submap`. |
| Overnight driver | `scripts/run_overnight.sh` | Shell-quoted config read, hard abort on empty method list, printed plan + `[n]` counters, `DRY_RUN=1`, overlay-leak abort, stale-results detector, Phase 5 sweep (§4). |
| Smoke | `scripts/smoke_test.sh`, `config.smoke.yaml`, `eval/smoke_check.py` *(new)* | Tiny end-to-end matrix; **fails on degeneracy** — frame coverage, VGGT-SLAM single submap, loop ≈ smooth, alignment arms identical, sweep operating point not applied. Projects the full-run ETA. |
| Archive ingest | `eval/ingest_archive.py` *(new)* | Transcribes the committed `perf.csv` + `report_raw.md` snapshot into tidy per-run records. Pure transcription — nothing imputed. |
| Clean aggregation | `eval/aggregate_clean.py` *(new)* | Seeded-only + named exclusions + complete-only; per-seed values, seed repeatability, paired head-to-head, motion stratification, completion, capacity, voxel sweep, literature table. |
| Report interface | `eval/export_report_tables.py` *(new)* | Freezes the clean tables into the layout `uofa-2026-report` ingests, with `MANIFEST.json` provenance + `not_yet_run`. |
| Regression guard | `eval/verify_clean.py` *(new)* | 7 checks, columns resolved **by header name**; reproduces `results_bigrun.md`. |
| Snapshots | `eval/snapshots.py` | Three co-visibility variants — `full`, `covis` (masked points greyed at low opacity), `masked` (dropped entirely); tunable grey/alpha. |
| Depth storage | `dataset/render_scene.py` + 5 readers | 16-bit PNG mm with `.npy` fallback (§8e). |
| Scene selection | `dataset/make_split.py`, `config.yaml` | `must_include` pinned **before** the random draw; honours `PRISM_CONFIG_OVERLAY` when freezing. |
| Studio | `tools/preview.py` | New make targets allowlisted; one-button pipeline ends `report-clean → report-tables → verify-clean`; "Clean results & smoke test" and "Download results" tabs; mask-variant and trajectory filters; fixed `_snap_scene` splitting on the literal `"_synthetic_"` (broke loop/stopgo and pinhole runs). |
| Bundling | `eval/bundle_results.py` *(new)* | Categorised zip (reports / metrics / poses / snapshots / figures / logs / config / clouds); clouds off by default; `--estimate` sizes every category. |
| Make targets | `Makefile` | `report-clean`, `aggregate-clean`, `report-tables`, `verify-clean`, `publication`, `ingest-archive`, `smoke`, `smoke-check`, `bundle`, `bundle-estimate`, `capacity-sweep`, `ablation-voxel`, `run-vggtslam-arms`, `bench-overnight` / `bench-status` / `bench-stop`. |

### Divergences from the task spec (deliberate, code-is-ground-truth)

1. **`make clean-results` was NOT repurposed.** It is, and remains, `rm -rf results/*` —
   destructive housekeeping documented in `make help`. Turning a destructive target into
   an aggregator is a footgun for anyone with muscle memory. The seeded-only aggregation
   is **`make report-clean`** (alias `make aggregate-clean`).
2. **The spec says VGGT-SLAM ran with `max_loops=0`; `config.yaml` already had
   `max_loops: 1`** when this work started. Rather than trust either, both arms are now
   explicitly named and neither depends on the mutable global.
3. **`config.yaml` contradicted itself on the default alignment group** (line 123 said
   SL(4), line 142 said Sim(3)) and `make_report.py` hardcoded `prism → SL(4)`. Resolved
   to Sim(3) everywhere, with an era map in `aggregate_clean.py` so the 2026-07 archive
   (where `prism` *was* SL(4)) is still labelled correctly.
4. **Spec item "fix latency logging for 43 runs" was not a logging fix.** Those runs were
   crashes (§1, §2). Fixing the logging alone would have made the failure *less* visible.

---

## 12. Caveats that must stay visible

Carried into every generated output (`clean_report.md`, `MANIFEST.json`):

- Rendered frames are noise-free → an **optimistic upper bound** vs real Theta-X captures.
- Metric scale degrades on loops: Sim(3) ~20%, SL(4) ~31%.
- Shipped PRISM has **no loop closure**; the full-batch nets implicitly close loops.
- The VGGT-SLAM head-to-head must state its `submap_size` and loop-closure arm, and must
  be checked against `n_degenerate` before it is cited.
- No baseline paper reports F-score; cross-paper reconstruction comparisons are
  indicative only (§10).
- **Reconstruction framing:** ours is denser and sharper but metrically worse. On the
  2026-07 data PRISM is 4th of 6 on masked F; the defensible wins are cleanliness
  (outlier 2.35% vs 3.89 / 4.57) and compactness (6.1 MB vs ~40 MB). Whether the voxel
  sweep (§8c) changes this is an open question until it runs.
- Stop-and-go is **not in the paper matrix**, and the reason (an undiagnosed PRISM
  collapse, masked F 0.717 → 0.088 on the smallest room while baselines degrade ~2×)
  should be stated rather than silently omitted.

---

## 13. The 2026-08-09 run: six defects, and what was changed

The run completed 134 dispatches (590 scene-runs) in 7 h and reported `134 ok / 0 failed`.
It is not citable. Every defect below was silent — each table looked normal.

### 13a. `eval_recon.py` crashed and 196 of 590 runs lost their reconstruction metrics

`vggtslam/office_0/synthetic_0.5hz_s1` produced a co-visibility mask that kept **0 of
198881** predicted points; `_metrics` then called `np.percentile` on an empty array and
raised `IndexError`. The overnight calls the script with `|| true`, so the crash was
invisible and every run after it in glob order got no `recon.json`.

Consequence: **laser and panovggt aggregated at N=57 while prism, pi3, mapanything and
the alignment arms aggregated at N=30.** The per-method table compared methods on
different subsets of the matrix — the exact unequal-N bias §1 exists to prevent,
reintroduced through the evaluator instead of the runner.

Fixed: `_metrics` returns `None` on an empty side and the run records
`masked_unevaluable: true` (a real result — the prediction lies wholly outside the
frustum union — distinct from "scored zero"); the per-cloud loop catches per-run
exceptions; the glob is `sorted()` so a failure at least cuts a *reproducible* subset;
the script exits non-zero; and `run_overnight.sh` prints `!!! EVAL STEP FAILED` plus a
final banner rather than reporting a clean checkpoint.

### 13b. `n_frames` was only ever a truncation

`dataset/trajectories.py` computed `n = min(max_frames, max(4, path_len/spacing + 1))`.
Frame count is `path_len × rate / speed`, so `n_frames` could not lengthen anything.
Real sequences came out at **4 to 207 frames** against a nominal 300. Therefore:

- no method ever approached its VRAM ceiling — `capacity.csv` reports **0 OOM for all 16
  methods**, longest completed 207. The whole "unbind the methods so OOM is possible"
  workstream produced no evidence;
- the 0.5 Hz arm was 6–21 frames, below PRISM's 16-frame window, so the alignment arms
  were inert there and three office_0 runs failed Umeyama with "Degenerate covariance
  rank".

Fixed in two steps, because the obvious fix was wrong.

**First attempt — make `n_frames` a target.** The path is lengthened by a longer circuit
(`n_waypoints` 8 → 12, and waypoints chosen by farthest-point sampling from a larger
accepted pool so the circuit's extent depends on the room rather than on RNG order), then
by **laps**, then by a **slower walk**. `max(4, …)` is gone: a path that cannot reach
`min_frames` (32) raises instead of emitting a stationary "trajectory".

That reached 300 frames everywhere, and the pre-flight then showed why it is not enough.
Holding the frame count fixed at a fixed baseline **forces** `path_len = 299 × baseline`,
so 2 Hz walks 75 m while 5 Hz walks 30 m of the same circuit. Measured on apartment_0
seed 5678: 118 m / 3 laps at 2 Hz against 34 m / 1 lap at 5 Hz, with the trajectory's
extent falling 12.99 → 11.65 m because the 5 Hz walk never finished the circuit. Three
things varied with "rate" simultaneously — path length (2.5× more accumulated drift at
2 Hz), how much of the room was ever observed (so reconstruction completeness was
penalised at 5 Hz), and how many revisits a loop-closure method got. None of them is the
rate. A first cut also capped laps at 4, which made small rooms slow down to reach 300
frames: room_1 seed 9012 came out at a 0.12 m baseline at "2.0 Hz", *denser* than another
scene's "5.0 Hz" at 0.10 m.

**Second attempt — the PATH is the invariant.** `path_target_m = (n_frames − 1) × speed /
reference_rate` = 74.75 m is walked identically at every rate, and the frame count
follows: **300 frames at 2 Hz, 748 at 5 Hz.** That is what capture rate means — one
motion, sampled more or less often — and it is the only definition under which a rate
comparison isolates the rate. Verified: the two rates produce byte-identical waypoints,
laps and walked distance, and the same trajectory extent to 1 cm.

`max_laps` is 12 rather than 4 so the slow-down lever (which changes the baseline) is
never needed; when it does fire it warns explicitly, and the 1%-shortfall case that used
to emit meaningless `speed 0.5->0.50 m/s` warnings is suppressed. `max_frames_hard`
(1000) is a safety ceiling only — below ~748 it would truncate the 5 Hz path relative to
2 Hz and break the comparison again, so hitting it warns.

Cost: ~4044 frames per scene per method against 2700 under the old scheme, ≈1.5× the
matrix. The 748-frame 5 Hz sequences are also the first in this benchmark long enough to
genuinely stress full-batch VRAM, which is the OOM/capacity evidence the previous design
could not produce.

### 13c. 0.5 Hz removed

It was not measuring capture rate, it was measuring near-absence of data. If the
wide-baseline regime is wanted back, get it by raising the walking speed at a fixed
rate, not by starving the sequence. `rates_hz: [2.0, 5.0]`.

### 13d. room_2 never rendered; office_0 rendered twelve stationary trajectories

Both trace to the floor estimate and the waypoint sampler:

- **room_2**: `floor_z` came from `np.percentile(vertex_z, 1)`, but that mesh extends
  ~0.8 m below the floor (z-extent 3.59 m vs ~2.8 m for every other Replica room), so
  the estimate was ~0.85 m too low. No candidate could pass `|ground − floor_z| ≤ 0.12`,
  `floor_frac` was 0.00 for all 6400 candidates, `render_scene.py` raised, and
  `make render`'s `|| true` dropped the scene. The night ran on 5 scenes with nothing in
  the summary saying so.
- **office_0**: the sampler returned a full 8/8 waypoints — all inside a **0.6 m patch**,
  because its `interior` score only clears 0.8 in one corner. Twelve 4-to-8-frame
  sequences followed, with the camera spanning ~0.1 × 0.5 m. On those, Umeyama is
  degenerate: PRISM and PanoVGGT "agreed" on ATE to six significant figures. ~65 runs
  were spent on it.

Fixed: floor height is estimated by **ray casting** (the mode of the downward-hit
histogram, taken from the lower half of the hit range so a tabletop or mezzanine cannot
win), with the p1-vertex value as fallback and a printed note when the two disagree by
more than 0.15 m. The sampler now requires the waypoint set to **span** the room
(`min_span_m`, scaled to the room diagonal), relaxes the interior threshold and retries
if it does not, re-estimates `floor_z` if nothing passes the bare-floor test at all, and
raises with a diagnostic rather than returning a cluster.

New pre-flight **`make check-scenes`**: builds the waypoints + spline for every
(scene, trajectory) pair using the renderer's own code and reports what each *would*
produce — no images, no GPU, seconds per scene. It would have caught both failures
before the run started. It gates the overnight (Stage 0b) and the smoke, and the smoke
runs it against the **full** config, because the smoke's single scene can never surface
a scene-specific failure. A render failure is now fatal unless `IGNORE_RENDER_FAIL=1`,
and every (scene, traj) export is verified before any GPU time is spent.

### 13e. PRISM's metric-scale lock — the cause of the broken maps

The visual breakage was not sparsity. On `apartment_1/synthetic_2.0hz_s0` PRISM had the
**best trajectory of any method** (ATE 0.84 m vs 1.9–2.2 m for the baselines) and a
**31.3% metric scale error** with masked F 0.070 at the same time; on the loop family the
scale error was 53.7%. The geometry was right and its *size* was wrong.

Three separate defects, all in the floor-derived scale:

1. **The lock committed samples that disagreed.** The engine took the median of the first
   3 "confident" floor estimates, where confident meant `conf ≥ 0.4`. apartment_1's
   samples were 0.4649 and 0.7272 — a **56% disagreement** — and it locked their median
   0.5056 anyway, a value no individual measurement supported.
2. **Pre-lock windows kept their provisional scale forever.** Windows 1–3 went into the
   TSDF at s = 0.4649, then 0.5898, then the lock settled at 0.5109. Nothing resized
   them. That is what the duplicated, offset floor slabs in the top-down snapshots are:
   the same room at three sizes.
3. **The vertical re-level trusted an unreliable plane.** `ZReLevel` nudges the anchor so
   the detected floor sits at Z=0, with no bound on how far away that plane may be. On
   apartment_1 it accepted floors at **+3.17 m, +3.27 m and +2.03 m** — ceilings and
   tabletops — and shifted whole windows vertically by up to 0.32 m each.

Fixed (all in `prism_vggt/engine.py`):

- a **separate, higher confidence bar for scale samples** (`SCALE_LOCK_MIN_CONF`, 0.50)
  than for leveling — a floor good enough to tell you which way is up is not necessarily
  good enough to set metric size;
- a **consistency gate**: refuse to lock while samples disagree by more than
  `SCALE_LOCK_MAX_SPREAD` (15%), collecting up to `SCALE_WARMUP_MAX_WINDOWS` (8), then
  committing to the **tightest cluster** rather than the raw median, and saying loudly
  when the cap forced a lock that the estimator never earned;
- **one provisional scale** for the whole warm-up instead of re-anchoring to a running
  median each window, so the pre-lock world is internally consistent;
- a **pre-lock buffer**: warm-up windows are held out of the TSDF and integrated once,
  after the world is resized by `k = s_locked / s_provisional` — exact, because depths
  and pose translations are lengths in the same frame, so scaling both is a global
  similarity that leaves shape and every rotation untouched. Cost: the map appears after
  the lock rather than after window 1, a startup latency of at most 6 windows. That is a
  real property of the deployed engine and should be reported as one;
- a **sanity clamp on ZReLevel** (`PRISM_Z_RELEVEL_MAX_M`, 0.5 m): a plane further than
  that from Z=0 is rejected as not-a-floor, with a log line;
- an end-of-sequence flush so a run whose scale never locks still produces a map (an
  imperfect scale beats an empty map) and records `scale_locked: false`.

Checked against the real failing samples: the spread gate blocks the apartment_1 lock at
3 samples (56% > 15%); at 4 samples the tightest cluster excludes the outlier and returns
**0.7201** against the confident measurement of 0.7272 — a ~1% error where the old code
locked 0.5056, a 30% error.

**New provenance.** `prism_runner.py` writes `scale_locked`, `metric_scale`,
`scale_provisional` and the full `floor_scale_samples` list into `arm_config.json` and
`perf.json`; `aggregate_clean.py` carries `scale_locked` into `runs_clean.csv` and adds
**`n_scale_unlocked`** to `completion.csv`. Nothing in the metrics could have revealed
this — apartment_1 had the best ATE in the matrix — so it has to travel with the run.

### 13f. VGGT-SLAM's loop-closure arm was inert

`vggtslam_loop` and `vggtslam_noloop` returned **identical ATE and identical point
counts** on all 28 matched runs, and `n_loop_closures = 0` in every run of both. Not a
config bug: at `submap_size: 32`, **21 of 28 runs built a single submap**, and loop
closure operates *between* submaps, so there was nothing to close. `vggtslam_w16` was the
only arm that closed any loops (6 runs) — precisely because a smaller window produced
more submaps. So the change made in good faith to be *fair* to VGGT-SLAM (w 16 → 32, its
published headline) was the one that made it degenerate at these sequence lengths.

The fix is sequence length (§13b) plus revisits from laps, not a smaller window. Until
then: `aggregate_clean.py` now **excludes degenerate runs from the paired head-to-head**
rather than footnoting them. "PRISM beats VGGT-SLAM by 27.8 cm, 26/28, p<0.0001" was
mostly a win over plain feed-forward VGGT, and a caveat in prose does not stop that
number being quoted — removing the runs does.

### 13g. New smoke gates

The smoke now fails on: a PRISM run whose metric scale never locked (and reports the
worst sample spread), any rendered trajectory under 32 frames or with no frames, any run
with a `cloud.ply` but no `recon.json`, and the pre-existing degeneracy checks. Plus the
`make check-scenes` pre-flight over the full scene list.
