# Adapter contract

The contract is the load-bearing interface: it lets us add a method without touching
the eval layer. An adapter **consumes** the fixed export layout and **produces** the
fixed results layout. `eval/*` reads only the results layout.

## Input (produced by `dataset/export_inputs.py`)

```
dataset/exports/<dataset>/<scene>/<traj>/
  pano/
    rgb/000000.png ...        # equirectangular uint8 RGB (e.g. 1036×518)
    depth/000000.npy ...      # RADIAL depth, metres, float32
    mask/000000.png ...       # validity (nonzero = valid)
    intrinsics.json           # {projection: equirect, width, height}
    meta.json                 # camera_height_m, n_frames, fps, seed, engine echo, streaming
  pinhole/<variant>/          # variant ∈ {synthetic_fov, real_intrinsics}
    rgb/ depth/ mask/         # depth = OPTICAL Z, metres, float32
    intrinsics.json           # {projection: pinhole, fx, fy, cx, cy, width, height}
    meta.json
  poses_gt.tum                # shared GT trajectory — for EVAL only; NOT fed to methods
  gt_mesh.ply                 # GT geometry for recon eval
```

A pano method reads `pano/`; a pinhole method reads each `pinhole/<variant>/`.

## Output (produced by the adapter/runner)

```
results/<method>/<dataset>/<scene>/<traj>/<variant>/
  poses.tum         # timestamp tx ty tz qx qy qz qw   (camera→world)
  cloud.ply         # reconstructed point cloud, method's world frame
  perf.json         # written by the orchestrator's uniform sampler (bench/perf.py)
  perf_runner.json  # method-reported timings (per-window latency, ckpt size, block count)
  run.log           # stdout/stderr
```

## How a runner is invoked

`adapters/base.py` (orchestrator env) launches:

```
submodules/<method>/.venv/bin/python  adapters/runners/<method>_runner.py \
    --in  dataset/exports/.../<camera_model>[/<variant>] \
    --out results/<method>/.../<variant> \
    --config config.yaml
```

The runner uses `adapters/runners/_io.py` (self-contained: numpy + best-effort image
reader + open3d writer) so every method emits byte-compatible `poses.tum` / `cloud.ply`.
Feed-forward baselines additionally use `_stream.py` (sliding windows + Sim(3) chaining
+ pointmap fusion) to be driven in the streaming harness.

## Adding a method

1. Add its submodule + pin to `bench.env` / `.gitmodules`.
2. Write `envs/setup_<m>.sh` (delegate to the repo's installer; isolated `.venv`).
3. Write `adapters/runners/<m>_runner.py` (import the method, produce the outputs).
4. Add a thin `adapters/<m>.py` and a config entry under `methods:`.
5. Wire `run-<m>` / `setup-<m>` in the Makefile.

The runner is the **only** place a method is imported.
