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
- System packages for the Replica downloader: `apt-get install -y wget pigz unzip`.
- An NVIDIA GPU + CUDA 12.8 for the PRISM env.

## Quick start (Replica, one room, ours end-to-end)

Run everything through `make` — never raw `python`.

```bash
# 1. envs
make init            # clone + pin every method submodule (bench.env)
make setup           # orchestrator env (light: open3d/evo/pynvml — NO torch)
make setup-prism     # PRISM env (CUDA 12.8/torch2.8 + nvblox wheel + PanoVGGT weights)

# 2. dataset — Replica (no approval).  make download prints these exact steps.
apt-get install -y wget pigz unzip
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
```

Add baselines once you've confirmed their runner API seams (see roadmap):

```bash
make setup-pi3      && make run-pi3
make setup-vggtslam && make run-vggtslam
```

## What is / isn't benchmarked

- **Streaming only.** Every method is driven incrementally (windowed/frame-fed) and
  timed identically. We do **not** run a full-batch pass of PRISM — that would only
  benchmark the underlying PanoVGGT net, not the streaming engine.
- **Methods:** PRISM-VGGT (ours, pano) · Pi3 · VGGT-SLAM (core baselines, pinhole) ·
  MapAnything · LASER (optional). Pins in `bench.env`.
- **Datasets:** ScanNet++ (start) → KITTI-360 (stretch) → Matterport3D & Stanford2D3D
  (panorama-native). Config in `config.yaml`.
- **Metrics:** trajectory (ATE/RPE, evo) · reconstruction (acc/compl/Chamfer/F-score,
  masked + full-360) · performance (FPS, latency, **avg & peak VRAM**, GPU util/power) ·
  **absolute metric-scale accuracy** (ours vs. rendered GT — baselines are scale-free → N/A).

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

Everything is labelled **preliminary** (few scenes, fixed seed, no variance study yet).
Rendered frames are noise/artifact-free → an optimistic upper bound.
