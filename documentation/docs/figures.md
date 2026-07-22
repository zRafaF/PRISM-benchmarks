# Report figures

Two report figures are produced by committed scripts and exposed for download in the
Studio ("Report figures" tab). Both write to `results/figures/`:

| File | Deliverable | Report slot |
| --- | --- | --- |
| `vram_vs_frames.png` + `vram_scaling.csv` | Peak VRAM vs. sequence length | new VRAM figure in `src/evaluation.typ` ("a sweep of memory against sequence length … is left to future work") |
| `cubemap_projection.png` | equirectangular → cubemap → fused volume | `fig-cubemap` in `src/engine.typ` |

The report author copies the finals into `uofa-2026-report/src/assets/` and points the
figure slots at them. `results/` is gitignored (run outputs); the figures are
**reproducible from the committed scripts + `documentation/docs/data/bigrun_2026-07/perf.csv`**.

## Regenerate

```bash
make figures            # both, no GPU: perf.csv VRAM figure + schematic cubemap
make fig-vram           # VRAM figure only (from committed seeded perf.csv)
make fig-cubemap        # cubemap figure only (schematic preview, no data)

# real cubemap from the rendered dataset (no GPU/engine — just render the scene first):
make render export SCENES="apartment_0" TRAJ=synthetic_5.0hz_s0
make fig-cubemap-export FIG_SCENE=apartment_0 FIG_TRAJ=synthetic_5.0hz_s0 FIG_FRAME=0

# on the reference GPU (RTX PRO 6000-class, ~96 GB), with method envs + exports ready:
make fig-vram-sweep     # real prefix sweep to each method's OOM cap
make fig-cubemap-engine # cubemap from the engine's own reprojection (needs PRISM env)
```

Overrides: `FIG_SCENE=` (default `auto` = best-covered seeded scene; cubemap treats
`auto` as the first configured scene), `FIG_TRAJ=` (default `synthetic_2.0hz_s0`),
`FIG_FRAME=` (cubemap pano frame, default `0`), `FIG_FRAMES=` (sweep grid, default
`1,2,4,8,16,32,64,128,256`), `FIG_TILE=1` (loop the sequence past its render length so
you can push frame counts beyond the rendered trajectory). The scripts read the same
`config.yaml` the engine uses (`window_size=16, overlap=4, voxel=0.02, max_depth=4.5,
face_size=768, processing_mode=parallel`).

## Deliverable 1 — VRAM vs. #frames (`eval/vram_scaling.py`)

Sweeps sequence length and reports peak GPU memory per method, measured the **same way
for every method** (`bench.perf.ResourceSampler`, the wrapper used across the whole
harness — not self-reported). PRISM's streaming curve is flat (~15 GB, bounded by
window + mapped volume); the offline batch nets (PanoVGGT-offline, Pi3, MapAnything)
grow with frame count toward the GPU's OOM ceiling.

* `--source perf-csv` (default, **no GPU**): plots the committed seeded run
  (`traj` ending `_s0`/`_s1`) for one scene's rate sweep — same scene, increasing
  frames = a controlled prefix-like sweep. This is the figure shipped now. In the
  committed data the batch methods already reach ~40–90 GB by ~170–198 frames on the
  102.6 GB card (this is why `trajectories.n_frames` is capped at 200).
* `--source sweep` (**on the reference GPU**): feeds increasing prefixes of one seeded
  trajectory to each method (default grid `1,2,4,8,16,32,64,128,256`), wrapped in the
  shared sampler, and records real OOM caps in `vram_scaling.csv` (`status =
  completed|oom`). A method's curve stops at the frame count where it OOMs, plotted with
  an `OOM` marker. The rendered trajectory is capped at 200 frames, so counts beyond the
  render (e.g. 256) need `--tile` (`FIG_TILE=1`), which loops the sequence — PRISM stays
  bounded on the revisited volume while the batch nets keep growing with frame count.

`vram_scaling.csv` columns: `method, num_frames, peak_vram_gb, status, notes`.

**Data hygiene.** Seeded runs only; the contaminated aggregate tables are never read.
The ~77–81 GB PRISM rows in the raw csv are GPU **co-tenancy** contamination (real
footprint ~14–15 GB, roadmap gap #3); the single-scene view avoids them and
`--drop-cotenancy-gb` (default 40) clips any physically-impossible PRISM outlier. OOM
points are labelled, never extrapolated through. Rendered scenes are noise-free
(optimistic vs. real capture) — stated in the caption.

## Deliverable 2 — Cubemap projection (`eval/fig_cubemap.py`)

Composes, left → right with arrows: (1) the input equirectangular panorama; (2) the six
reprojected 90° cube faces with per-face metric depth and the **validity / anti-erosion
seam mask** (the mask that drops smeared depth-discontinuity pixels before TSDF
integration); (3) the fused TSDF surface.

Three modes:

* `--mode dataset` (**default, recommended — real data, no GPU/engine**): builds the
  figure straight from the rendered export — the equirect RGB, the render's **GT depth**
  (`pano/depth/*.npy`), the **validity mask** (`pano/mask`), and the GT poses. Equirect→
  cube is a fixed geometric reprojection; per-face depth is converted radial→
  perpendicular; the per-face mask combines sampled validity with a depth-discontinuity
  + seam-border drop (mirroring PRISM's anti-erosion seam mask); the fused panel
  back-projects a short window of GT depth into world points (via the GT poses) and
  splats them top-down. Only needs `make render export` for the chosen scene/traj — run
  `make fig-cubemap-export`. Honest caveat: per-face depth here is the render's GT depth,
  not PRISM's *predicted* depth — the right choice for a projection-pipeline figure.
* `--mode export` (**needs the PRISM-VGGT env**): hooks the engine's own equirect→cubemap
  reprojection + `VRAMProfiler` to dump the engine's intermediates. Run
  `make fig-cubemap-engine`. If the engine's reprojection symbol isn't auto-found, fall
  back to `--mode dataset` (or point `_engine_cubemap()` at the right `prism_vggt` symbol).
* `--mode illustrative` (**no data**): a clearly-labelled **schematic** (synthetic
  panorama), banner-marked "SCHEMATIC", for wiring the report layout before any render.
  Run `make fig-cubemap`.

## Reference hardware / config

Benchmarked on an **RTX PRO 6000-class GPU (~96–103 GB)** (`hardware.hw_id` in
`config.yaml`). The committed measurements are
`NVIDIA RTX PRO 6000 Blackwell Workstation Edition`, 102.6 GB. Engine config as above.
