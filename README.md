# PRISM-benchmarks

Neutral cross-method benchmark **orchestrator** for PRISM-VGGT vs. streaming
baselines. It owns the shared dataset rendering, the fair-comparison co-visibility
masking, the eval + perf/resource collection, and the final aggregated report. Each
method runs **in its own isolated env** as a subprocess; the eval layer imports no
method. The **Makefile is the orchestrator** — run everything through `make`.

```
make help      # targets + pipeline
make steps     # full run-book
```

## Prerequisites

- **uv** (installs itself if missing) — the only Python you need; every step runs
  inside a uv-managed venv. **Do not call `python` directly** (there is no system
  interpreter on the box — use the `make` targets, which run `uv run python`).
- **System packages:** `make deps` (installs `wget pigz unzip` for the Replica
  downloader + `tmux` for the overnight run). Add `APT_SUDO=sudo` if you are not root.
- An NVIDIA GPU + CUDA 12.8 for the PRISM env.

## Quick start (Replica, one room, ours end-to-end)

Run everything through `make` — never raw `python`.

```bash
# 1. envs
make init            # clone + pin every method submodule (bench.env)
make setup           # orchestrator env (light: open3d/evo/pynvml — NO torch)
make setup-prism     # PRISM env (CUDA 12.8/torch2.8 + nvblox wheel + PanoVGGT weights)

# 2. dataset — Replica (no approval).  make download prints these exact steps.
make deps            # wget pigz unzip tmux  (APT_SUDO=sudo if not root)
git clone https://github.com/facebookresearch/Replica-Dataset
cd Replica-Dataset && ./download.sh "$(pwd)/../dataset/raw/replica" && cd ..

# 3. freeze one room + render + export   (all via uv, through make)
make split                          # freezes 1 scene (fixed seed) into config.yaml
make render TRAJ=synthetic_spline   # pano + pinhole + GT  (spline needs NO dataset poses)
make export

# 4. run OURS + evaluate + report
make run-prism
make eval-traj eval-recon eval-metric perf
make report                         # -> results/report/report.md (+ fps.png)
make figures                        # -> results/figures/ (vram_vs_frames.png + csv, cubemap_projection.png)
```

Report figures (VRAM-vs-frames, cubemap projection, per-view-vs-fused) regenerate with
`make figures` / `fig-cubemap-export` / `fig-fusion` and download from the Studio's
"Report figures" tab — see `documentation/docs/figures.md`.

Add baselines once you've confirmed their runner API seams (see roadmap):

```bash
make setup-pi3      && make run-pi3
make setup-vggtslam && make run-vggtslam
```

## What is / isn't benchmarked

- **Streaming vs. full-batch.** Streaming methods (PRISM, VGGT-SLAM, LASER) are driven
  incrementally and timed identically. Permutation-equivariant feed-forward nets (Pi3,
  MapAnything) and raw PanoVGGT run **full-batch** (all frames at once — windowing
  misaligns them); PanoVGGT is the raw-backbone reference that isolates what the PRISM
  engine adds.
- **Methods:** PRISM-VGGT (ours, pano) · PanoVGGT (raw-backbone ref, pano) · Pi3 ·
  MapAnything · VGGT-SLAM · LASER (pinhole baselines). Pins in `bench.env`.
- **Datasets:** Replica (active) → ScanNet++ → KITTI-360 → Matterport3D & Stanford2D3D.
  Config in `config.yaml`.
- **Metrics:** trajectory (ATE + **drift %/m**, evo, Sim(3)-aligned) · reconstruction
  (acc/compl/Chamfer/F-score, masked + full-360) · **cloud cleanliness & size**
  (SOR-outlier %, acc-p95, precision@2cm, map MB) · performance (FPS, latency, **avg &
  peak VRAM**, GPU util) · **absolute metric-scale accuracy** (ours vs. rendered GT —
  scale-free baselines → N/A).

## Ablations, trajectories & the big benchmark

**Alignment-group ablation (core study).** PRISM's submap registration group is switchable
via `PRISM_ALIGN` in the PRISM engine — `sim3` (7-DoF similarity), `se3` (6-DoF rigid),
`sl4` (15-DoF projective, VGGT-SLAM's group). **The default is `sl4`** (best recon on the
preliminary run; floor grounding keeps it metric). The ablation arms `prism_sim3` /
`prism_se3` measure the other two with everything else held fixed. Key finding: running
VGGT-SLAM's *own* SL(4) group inside PRISM (`prism`) still beats VGGT-SLAM ~4× on ATE — so
PRISM's advantage is the panoramic metric engine, not the pose-graph math. Guard ablations
(`prism_nolock/nostill/noguards`) toggle the drift-control guards.

```bash
make ablations          # guard arms + alignment arms (sim3, se3) as their own "methods"
make ablations-align    # just the alignment-group study
```

**Trajectory families** (`config.trajectories`), rendered from the same poses for every
method — id scheme `<kind>_<rate>hz[_sN]`:

- `synthetic_<rate>hz` — smooth constant-velocity spline, full rate sweep (0.5/2/5 Hz).
- `stopgo_2.0hz` — walk / **dwell** / walk: noise accumulation + still-guard stress.
- `loop_2.0hz` — returns to & re-observes the start: drift / loop-closure stress.

**Big benchmark (overnight).** 6 scenes × 2 seeds × the trajectory families × all methods
+ ablations, on a **dedicated GPU** (clean VRAM). Resumable, priority-ordered (headline
first), report checkpoint after each phase:

```bash
make bench-overnight               # detached tmux; survives SSH disconnect
tmux attach -t bench               # reattach   |   tail -f logs/overnight_latest.log
# no tmux? setsid bash scripts/run_overnight.sh >/dev/null 2>&1 </dev/null &
```

The report gains a **Global aggregate** and an **Alignment-group study** table (compute
impact + fidelity) on top of the per-run tables A/B/C/C2/D.

## The adapter contract

Adapters read the fixed export layout and write the fixed results layout; `eval/*`
reads only the results layout. See `documentation/docs/adapter_contract.md`.

```
dataset/exports/<dataset>/<scene>/<traj>/
  pano/{rgb,depth,mask}/NNNNNN.*   intrinsics.json  meta.json
  pinhole/<variant>/{rgb,depth,mask}/...            intrinsics.json meta.json
  poses_gt.tum   gt_mesh.ply
results/<method>/<dataset>/<scene>/<traj>/<variant>/
  poses.tum  cloud.ply  perf.json  run.log  (+ ate/recon/metric.json after eval)
```

## Docs

```bash
make docs-serve      # browse the design docs + decisions locally
```

See `documentation/docs/roadmap.md` for **current findings & the paper framing** (a
systems/robotics contribution: the first *metric, streaming, bounded-memory 360°*
reconstruction in the VGGT family; beats VGGT-SLAM ~4× on trajectory with a 6× smaller
map) and `decisions.md` (D1–D16) for the design rationale.

Small-run numbers are labelled **preliminary** (2 scenes, fixed seed). The
`make bench-overnight` run (6 scenes × 2 seeds × motion-stress trajectories, dedicated
GPU) is what drops that label. Rendered frames are noise/artifact-free → an optimistic
upper bound.
