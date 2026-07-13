# Architecture

## Repo layout

```
PRISM-benchmarks/
  bench.env              # pins (URL+commit) + default run params; included by the Makefile
  Makefile               # THE orchestrator — every stage is a target
  config.yaml            # single source of truth: datasets, cameras, engine knobs, thresholds
  pyproject.toml         # orchestrator's OWN light env (open3d/evo/pynvml/matplotlib — NO torch)
  scripts/add_submodules.sh   # clone + checkout each pinned commit
  envs/setup_*.sh        # per-method isolated env (delegates to each repo's installer)
  bench/                 # shared orchestrator libs (config, cameras, perf sampler)
  dataset/               # download / render / trajectories / split / export
  adapters/              # thin entrypoints + base driver
    runners/             # per-method runner, EXECUTED INSIDE each method's env
  eval/                  # visibility_mask, eval_traj, eval_recon, metric_accuracy, collect_perf, make_report
  results/               # gitignored outputs + final report
  documentation/         # this site (mkdocs)
```

## Isolation model

Each method is a git submodule under `submodules/<name>/` with its **own** `uv`
`.venv`. The orchestrator has a separate light env. An adapter (run in the
orchestrator env) launches the method's env python as a **subprocess** running
`adapters/runners/<method>_runner.py`; the runner imports the method and writes the
common outputs. The orchestrator wraps the subprocess in the uniform perf sampler
(`bench/perf.py`) so GPU/VRAM/latency are measured identically for every method.

```
orchestrator env (open3d/evo/pynvml)          method env (torch/nvblox/gtsam/...)
  adapters/base.py  ──subprocess──▶  submodules/<m>/.venv/bin/python runners/<m>_runner.py
        │  (ResourceSampler wraps it)                    │
        ▼                                                ▼
  results/<m>/.../perf.json                       results/<m>/.../{poses.tum,cloud.ply,perf_runner.json}
```

The eval scripts read **only** `results/` — they never import a method.

## Data flow

```
download → render_scene (RaycastingScene: pano radial-depth + pinhole; vertex-colour RGB)
        → export_inputs (per-method meta.json)
        → run-<m> (streaming harness, each in its own env)
        → eval-traj / eval-recon / eval-metric / perf
        → make_report (tables A/B/C/C2 + plots)
```

## Renderer

Open3D `RaycastingScene` casts one ray per output pixel for **both** camera models
from the **same** poses. Pano rays are an equirectangular lat/long grid (radial depth
falls out directly + validity mask from `inf` hits); pinhole rays come from `K`/FOV
(radial depth converted to optical Z). RGB is barycentric interpolation of the mesh
vertex colours. Identical intersection code for both models ⇒ any metric gap is the
method, not the data. Rasterization/texture sampling is the fallback for textured
meshes (ScanNet++ high-fidelity).
