# Running the benchmark

Everything runs through **`make`**, which runs Python inside a **uv**-managed venv.
There is no system `python` on the box — **never call `python …` directly**; use the
targets below (they all run `uv run python`). `make help` lists every target;
`make steps` prints the staged run-book.

## Prerequisites (once)

```bash
# uv installs itself if missing. System packages the Replica downloader needs:
apt-get install -y wget pigz unzip          # (sudo if not root)
```

An NVIDIA GPU + CUDA 12.8 is required for the PRISM env.

## Stage 0 — envs

```bash
make init          # clone + checkout the pinned commit of every method (bench.env)
make setup         # orchestrator env (open3d/evo/pynvml/matplotlib — NO torch)
make setup-prism   # PRISM env: CUDA 12.8/torch2.8 + nvblox prebuilt wheel + PanoVGGT weights
```

Weights: PanoVGGT's original HF repo went private, so `setup-prism` fetches the
checkpoint from the mirror in `bench.env` (`PANOVGGT_WEIGHTS_URL`) into
`submodules/PRISM-VGGT/checkpoints/model.pt`. nvblox uses the published wheel by
default (`NVBLOX_MODE=prebuilt`); only pass `NVBLOX_MODE=source` if the wheel ever
mismatches your GPU (then `apt-get install -y lsb-release` first).

## Stage 1 — dataset (Replica today)

`make download` prints the exact per-dataset steps. For Replica (no approval):

```bash
apt-get install -y wget pigz unzip
git clone https://github.com/facebookresearch/Replica-Dataset
cd Replica-Dataset && ./download.sh "$(pwd)/../dataset/raw/replica" && cd ..
```

Each scene must end up at `dataset/raw/replica/<scene>/mesh.ply`.

## Stage 2 — freeze, render, export

```bash
make split                          # freeze 1 scene (fixed seed) into config.yaml
make render TRAJ=synthetic_spline   # pano + pinhole(synthetic_fov & real_intrinsics) + GT
make export                         # per-method adapter inputs
```

Use `TRAJ=synthetic_spline` for now — the `dataset_path` (real camera path) variant
needs a per-dataset pose importer that isn't wired yet. Override scenes/params on the
CLI, e.g. `make render SCENES="room_0" TRAJ=synthetic_spline FACE_SIZE=768`.

## Stage 3 — run methods (each in its own env, streaming harness)

```bash
make run-prism                      # ours (pano) -> results/prism/...
make run-pi3                        # baseline (pinhole)   — after make setup-pi3
make run-vggtslam                   # baseline (pinhole)   — after make setup-vggtslam
```

Before the baselines, confirm the `<-- API line N` seams in
`adapters/runners/{pi3,vggtslam}_runner.py` against the repos `make init` cloned
(PRISM's runner uses the verified API and needs no changes).

## Stage 4 — evaluate + report

```bash
make eval-traj eval-recon eval-metric perf
make report                         # -> results/report/report.md (+ fps.png)
```

## One-shot

```bash
make all                            # init -> setup-all -> download -> render -> export ->
                                    # run-all -> eval-* -> perf -> report
```

## Common issues

- **`python: command not found`** — you called `python` directly. Use the `make`
  target instead (it runs `uv run python`), or prefix with `uv run` inside the repo.
- **Replica `download.sh` fails** — install `wget pigz unzip`.
- **PanoVGGT weights 403** — the mirror URL in `bench.env` is fetched automatically;
  if it changes, edit `PANOVGGT_WEIGHTS_URL` there.
