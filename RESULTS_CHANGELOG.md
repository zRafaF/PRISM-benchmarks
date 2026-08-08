# RESULTS_CHANGELOG

What changed in the benchmark between the 2026-07 big run and the publication run,
which runs were excluded and why, how the numbers moved, and what still needs a GPU.

**Rule applied throughout: no fabricated or interpolated numbers.** Every value below
comes from a real recorded run. Where the current data cannot support a result, the
item is listed under [§7 Not yet run](#7-not-yet-run-needs-the-gpu-box) with the exact
command, and no number is given.

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

**Status: partially fixed.** The instrumentation and the aggregation are fixed (§3, §4);
the survivorship bias is *not* fixed and cannot be, because it requires the 43 runs to
actually succeed. See §7.

---

## 2. Runs excluded from the clean aggregate, and why

Exclusions are declarative (`EXCLUSIONS` in `eval/aggregate_clean.py`), each carrying a
stated reason that is printed and written into every output, so a run can never be
dropped silently or re-enter by being renamed.

| Excluded | Count | Reason |
|---|---|---|
| Unseeded trajectory ids (`synthetic_2.0hz` etc.) | 66 | Stale 2-scene experiment. VRAM co-tenancy-inflated to 70–102 GB — including *streaming* methods (laser 70.3 GB, prism 77.1 GB) whose seeded budget is 8.4 / 16.0 GB. |
| Scene `office_4` | (within the 66) | Only ever had stale data; never rendered under a seed. |
| Arm `prism_sl4` (2026-07 era) | 6 | Entirely stale 2-scene data (N=6). Its rosy ATE 26 / F 0.66 is not comparable to anything in the seeded matrix. |
| Runs with no evaluable output | 43 | See §1. Excluded from **every** aggregate including perf, because their `eff_fps` is inflated. |

**434 input records → 368 seeded → 325 aggregated.**

`make verify-clean` asserts all of this and fails non-zero on violation. It was tested
against six injected contamination cases (unseeded run, `office_4` run, co-tenancy
streaming VRAM, full-batch VRAM outlier, incomplete run, silent zero-latency run) and
detects all six.

---

## 3. New numbers vs old

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

---

## 4. Statistical rigour: what actually separates, and what does not

Two additions, because the previous analysis compared marginal means with no dispersion.

### 4a. Error bars now isolate seed noise

The replicate cell is `(method, scene, trajectory-family, rate)`; the seeds inside it are
the repeats. Reporting a std across `(scene, seed)` units instead — the obvious first
approach — mostly measures "apartment_0-loop differs from hotel_0-smooth", which is not
an error bar. `seed_repeatability.csv` gives the within-cell figure; `variance.csv`
keeps the between-cell heterogeneity separately.

**Seed-to-seed spread is large.** ATE within-cell seed std is **25–60% of the mean**
(prism 54%, pi3 25%, laser 54%, vggtslam 45%). The render seed changes the trajectory
instance — a different path through the same room — so this is real sensitivity, not
measurement noise. With 2 seeds each cell's variance has 1 d.o.f.; pooling across cells
is what makes it usable at all.

### 4b. Paired head-to-head (`paired_head_to_head.csv`)

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
   p < 0.001, and the 5× map advantage is 30/30.
2. **"PRISM beats LASER" does not survive pairing** (p = 0.099 on both ATE and F). The
   marginal means (86.8 vs 68.9 cm) suggested otherwise. Do not claim it.
3. **The guard ablation's negative result is now properly supported** — previously an
   eyeballed "no measurable benefit", now a paired test that fails to separate on every
   metric. This strengthens Finding 3 rather than weakening it.

The alignment arms are also inseparable *pooled* — which is expected and not a
contradiction, because the SL(4)/Sim(3) difference is motion-dependent and lives in the
stratified table, where it is large (loop: ATE 110.5 vs 101.9, F 0.26 vs 0.34,
scale 31.4% vs 20.3%).

---

## 5. Code changes

| Area | File | Change |
|---|---|---|
| Latency instrumentation | `adapters/base.py` | `_merge_runner_perf` now falls back to the orchestrator's `wall_s` when a runner writes no `perf_runner.json`, derives per-window latency from wall/window-count, and records **`latency_source`** (`runner` / `orchestrator_wall` / `derived_wall_over_windows` / `unavailable`) so a fallback can never be mistaken for a measurement. |
| Partial-run detection | `adapters/base.py`, `bench/perf.py` | New `n_frames_input` / `n_frames_done` / `completed` / `returncode`. **`eff_fps` is now computed from frames actually produced**, so a crashed run can no longer report a throughput it did not achieve. |
| Perf CSV | `eval/collect_perf.py` | Carries the new provenance + completion columns through to `perf.csv`. |
| Archive ingest | `eval/ingest_archive.py` *(new)* | Transcribes the committed `perf.csv` + `report_raw.md` snapshot into tidy per-run records. Pure transcription — nothing imputed. Makes the clean re-aggregation reproducible with no `results/` tree on disk. |
| Clean aggregation | `eval/aggregate_clean.py` *(new)* | Seeded-only + named exclusions + complete-only; per-seed values, seed repeatability, paired head-to-head, motion stratification, completion table; CSV + JSON + markdown. |
| Report interface | `eval/export_report_tables.py` *(new)* | Freezes the clean tables into the column layout `uofa-2026-report` ingests, with a `MANIFEST.json` recording provenance and what is not yet run. |
| Regression guard | `eval/verify_clean.py` *(new)* | 7 checks; fails non-zero on any contamination. Includes an end-to-end check that the recompute reproduces `results_bigrun.md`. |
| Legacy report | `eval/make_report.py` | Docstring warning that it aggregates everything; alignment-arm labels made era-aware. |
| Scene selection | `dataset/make_split.py`, `config.yaml` | New `must_include`, pinned **before** the random draw, so difficulty spread is a config property not an RNG outcome. |
| Alignment default | `config.yaml` | `prism` now sets `PRISM_ALIGN: sim3` **explicitly**; SL(4) moves to a `prism_sl4` arm. |
| VGGT-SLAM arms | `config.yaml`, `adapters/runners/vggtslam_runner.py` | Two named arms via `VGGTSLAM_MAX_LOOPS`; runner logs its config and writes `arm_config.json` beside the results. |
| Seeds | `config.yaml` | 2 → 4 seeds. |
| Make targets | `Makefile` | `report-clean`, `aggregate-clean`, `report-tables`, `verify-clean`, `publication`, `ingest-archive`, `run-vggtslam-arms`. |

### Divergences from the task spec (deliberate, code-is-ground-truth)

1. **`make clean-results` was NOT repurposed.** It is, and remains,
   `rm -rf results/*` — destructive housekeeping documented in `make help`. Turning a
   destructive target into an aggregator is a footgun for anyone with muscle memory.
   The seeded-only aggregation is **`make report-clean`** (alias `make aggregate-clean`).
2. **The spec says VGGT-SLAM ran with `max_loops=0`; `config.yaml` already had
   `max_loops: 1`** when this work started. Rather than trust either, both arms are now
   explicitly named and neither depends on the mutable global.
3. **`config.yaml` contradicted itself on the default alignment group** (line 123 said
   SL(4), line 142 said Sim(3)) and `make_report.py` hardcoded `prism → SL(4)`. Resolved
   to Sim(3) everywhere, with an era map in `aggregate_clean.py` so the 2026-07 archive
   (where `prism` *was* SL(4)) is still labelled correctly.

---

## 6. VGGT-SLAM fairness arm — configuration

```yaml
# config.yaml -> ablations
- {name: vggtslam_noloop, camera: pinhole, env: submodules/VGGT-SLAM, mode: stream,
   metric: false, role: baseline, runner: vggtslam, run_env: {VGGTSLAM_MAX_LOOPS: "0"}}
- {name: vggtslam_loop,   camera: pinhole, env: submodules/VGGT-SLAM, mode: stream,
   metric: false, role: baseline, runner: vggtslam, run_env: {VGGTSLAM_MAX_LOOPS: "1"}}
```

Held fixed across both arms: `submap_size: 16` (matches our window), `min_disparity: 50`,
pinhole `synthetic_fov` variant, same rendered trajectories, same perf sampler. The only
difference is `--max_loops`. Each run writes `arm_config.json` next to its results so a
results tree is self-describing.

**The existing 368-run archive is the `max_loops=0` arm.** Until `vggtslam_loop` is run,
the head-to-head must be labelled **indicative** and the disabled-loop-closure caveat
stated — VGGT-SLAM's published TUM ATE is ~5 cm against our 132 cm, a ~25× gap that is
as consistent with a setup mismatch as with a method gap.

---

## 7. Not yet run (needs the GPU box)

No GPU, no `dataset/raw`, no `dataset/exports`, and no `results/` tree were reachable
from the environment this work was done in. The following are **implemented and wired
but carry no numbers.** They are also listed in
`results/report_tables/MANIFEST.json → not_yet_run` so a stale table cannot be cited by
mistake.

| Item | Status | Command |
|---|---|---|
| Small/easy scene (`room_0`, `office_0`) | Pinned in `config.yaml` via `must_include`; not rendered or run | `make split && make render && make export && make run-all` |
| VGGT-SLAM loop-closure-ON arm | Arm defined; not run | `make run-vggtslam-arms` |
| Seeds 9012 / 3456 | Config extended to 4 seeds; only 1234/5678 have data | `make render && make export && make run-all` |
| Re-run of the 43 failed PRISM runs | Instrumentation fixed so failures are now visible and excluded; the **survivorship bias in PRISM's ATE/F is unresolved until these succeed** | investigate `run.log` on the GPU box, then `PRISM_FORCE=1 make run-prism` |
| Latency for the 2026-07 archive | Cannot be retro-filled; those runs stay excluded | n/a |

**Recommended order.** Diagnose the PRISM failures first (§1) — they are the largest
threat to the results, they are the only method-specific failure in the matrix, and
re-running the other items before fixing them would just reproduce the same 25% hole on
a bigger matrix.

---

## 8. Caveats that must stay visible

Carried into every generated output (`clean_report.md`, `MANIFEST.json`):

- Rendered frames are noise-free → an **optimistic upper bound** vs real Theta-X captures.
- Metric scale degrades on loops: Sim(3) ~20%, SL(4) ~31%.
- Shipped PRISM has **no loop closure**; the full-batch nets implicitly close loops.
- All four seeded scenes are large/hard — every absolute number is pessimistic until a
  small room is in the matrix.
- The VGGT-SLAM head-to-head is against loop-closure-OFF until `vggtslam_loop` runs.
- PRISM's quality metrics are computed over the 75% of runs it completed; the baselines'
  over 100% of theirs.
