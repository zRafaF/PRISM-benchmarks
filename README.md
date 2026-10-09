# PRISM-benchmarks

Benchmark harness for **PRISM-VGGT** against streaming baselines (VGGT-SLAM, LASER).
Every method runs in its own environment; everything is driven through `make`.

| What | Where |
|---|---|
| This repo (branch `rerun-v2`) | https://github.com/zRafaF/PRISM-benchmarks |
| PRISM-VGGT (branch `prism-v2`, pinned in `bench.env`) | https://github.com/zRafaF/PRISM-VGGT |
| Rendered inputs + results (private HF dataset) | https://huggingface.co/datasets/DoninhaD/prism-bench-inputs |
| PanoVGGT weights (private HF bucket) | https://huggingface.co/buckets/DoninhaD/PanoVGGT-bucket |

Inside the HF dataset: `inputs/rerun-v2/` = rendered frames (one tar per scene),
`results/rerun-v2/live/` = checkpoints written during a run, `results/rerun-v2/*.tar` = final results.

## The flow

1. **PC** renders the dataset once and uploads the frames to HF (CPU work, no GPU).
2. **One GPU pod** downloads the frames, runs every method one after another, uploads results.
3. **PC** downloads the results and scores them (CPU work, no GPU).

## What runs

- **6 Replica scenes:** `apartment_0 apartment_1 office_0 room_0 room_1 room_2`
- **2 camera paths** at 2 Hz, 300 frames (150 s of video) each: `synthetic` (smooth) and `loop` (revisits places)
- **3 seeds** per path → 36 sequences

| Method | Runs | Note |
|---|---|---|
| `prism` | 36 | ours, Sim(3) alignment |
| `vggtslam` | 36 | VGGT-SLAM as published: 32-frame submaps, loop closure on |
| `laser` | 36 | |
| `prism_sl4`, `prism_se3`, `prism_sim3lock` | 12 each | alignment ablation, seed 0 only |
| `vggtslam_noloop` | 12 | VGGT-SLAM with loop closure off, seed 0 only |

**156 runs, ~3 h on one RTX 5090.** Runs are strictly sequential, so timings are clean.

Offline methods (`panovggt`, `pi3`, `mapanything`) are **off by default**: they need
50–93 GB of VRAM at only 200 frames. Turn them on only on a 96 GB card (see Hardware).

## Hardware

| | |
|---|---|
| GPU | **RTX 5090 (32 GB)** — the default. For the offline methods use an **RTX PRO 6000 (96 GB)** and run `make pod BENCH_OFFLINE=1`. Both are Blackwell (`sm_120`); the prebuilt nvblox wheel works on both, no compiling. |
| Disk | **100 GB container disk.** 60 GB runs out. |
| Image | Ubuntu with root and `apt` (RunPod's PyTorch template works). NVIDIA driver for CUDA 12.8 (tested on 580). |
| GPU label | `hardware.hw_id` in `config.yaml` (`RTX 5090`) names the GPU in the tables; change it if you use another card. Each run also records the real GPU name. |

## Hugging Face token

https://huggingface.co/settings/tokens → **Fine-grained**, tick only:

- Read contents of your repos
- Create repos and write to repos created by this token
- Read contents of public gated repos you can access

If the dataset repo already exists and was created by another token, also tick
*Write contents/settings of your repos*. Revoke the token after the run.

---

## 1. PC: render and upload the inputs (once)

Windows: run in **WSL Ubuntu**, from the Windows checkout (or a clone in `~`, which is faster).

```bash
sudo apt update && sudo apt install -y git make wget pigz unzip curl
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.local/bin/env
cd /mnt/c/Dev/ualberta/PRISM-benchmarks
git config core.fileMode false

make inputs                 # Replica meshes -> scene split -> check -> render -> export -> pack (a few hours)
export HF_TOKEN=hf_xxx
make inputs-push            # uploads dataset/inputs/rerun-v2/ (~7.5 GB)
```

- `make replica` streams the 34 GB Replica archive and keeps only the 6 meshes (~3 GB on disk).
- Keep this checkout: scoring needs its depth maps and GT meshes.
- Inputs only need re-rendering if `config.yaml` render settings, `dataset/trajectories.py`
  or `dataset/render_scene.py` change — the pod refuses mismatched inputs. After changing
  only run settings: `bash scripts/inputs.sh rehash && make inputs-push`.

Optional, to start with no old results on HF (inputs are kept): `make results-hf-reset`.

## 2. Pod: run the benchmark

```bash
apt-get update && apt-get install -y git make tmux
git clone -b rerun-v2 https://github.com/zRafaF/PRISM-benchmarks.git && cd PRISM-benchmarks
export HF_TOKEN=hf_xxx
make pod
make watch
```

`make pod` runs in a background tmux session, so closing the terminal is fine. Stages:

| Stage | Time | What |
|---|---|---|
| prep | 30–60 min | system packages, method envs, model weights |
| check | ~3 min | GPU/CUDA in every env, nvblox fuses on the GPU, VGGT-SLAM closes a loop on its own sample |
| data | ~5 min | downloads the frames from HF, checks they match this code |
| precheck | ~15 min | every method on one real sequence + VGGT-SLAM on a loop path; any FAIL stops here |
| bench | ~3 h | 156 runs, one at a time; checkpoint to HF every 15 min |
| pack | ~2 min | results tar → HF `results/rerun-v2/` |
| studio | — | Gradio link to download the tar |

### While it runs

```bash
make watch                      # stage, progress bar, ETA, current run, flagged runs (Ctrl-C leaves; run continues)
tmux attach -t pod              # raw output (Ctrl-b then d to detach)
cat logs/precheck.json          # pre-check table
df -h /                         # disk
grep -o "https://[a-z0-9.-]*gradio.live" logs/pod_latest.log | tail -1   # download link at the end
```

### If something stops

Fix the cause, then run `make pod` again. It resumes:

- finished stages are skipped (`logs/.done_<stage>`; delete one to redo it),
- finished runs are skipped; half-done or crashed runs are wiped and redone,
- a crashed run is retried once automatically; failing twice it is kept as a failure,
- on a **new** pod, runs already checkpointed to HF are pulled first and skipped.

To stop: `make pod-stop`. Prefer stopping right after a run finishes (the stopped run is redone).

### Common problems

| Symptom | Fix |
|---|---|
| `libEGL.so.1` / `vggtslam_reference FAIL` | `apt-get install -y libegl1 libgl1 libgomp1 libglib2.0-0`, then `make pod` |
| `No space left on device` | pod needs 100 GB disk; quick space: `uv cache clean` |
| `dns error` during prep | transient; install steps retry 3×, otherwise `make pod` again |
| `OutOfMemoryError` on panovggt/pi3/mapanything | expected on 32 GB; keep `BENCH_OFFLINE=0` |
| pre-check FAIL | paste `logs/precheck.json`; the run log is in `results/<method>/replica/room_0/<traj>/*/run.log` |
| data stage: private repo not found | `HF_TOKEN` not exported in the shell that ran `make pod` |

## 3. PC: score

```bash
cd /mnt/c/Dev/ualberta/PRISM-benchmarks
export HF_TOKEN=hf_xxx
make results-fetch && make results-merge && make eval-all publication
```

Paper tables: `results/report_tables/`. Analysis: `results/report_clean/clean_report.md`.

---

## Options (`make pod VAR=value`)

| Variable | Default | |
|---|---|---|
| `BENCH_OFFLINE` | `0` | `1` = also run panovggt / pi3 / mapanything (96 GB GPU) |
| `BENCH_METHODS` | all | e.g. `"prism prism_sl4"` — split methods across pods (each pod a disjoint set) |
| `CKPT_EVERY_S` | `900` | seconds between HF checkpoints (always between runs) |
| `PRECHECK_FORCE` | `1` | `0` = reuse runs that already finished |

## Repo layout

```
config.yaml          scenes, trajectories, methods, ablations, VGGT-SLAM settings
bench.env            pinned method commits, HF repo, GPU label
adapters/            one runner per method (each runs in its own env)
dataset/             Replica fetch, trajectories, rendering, export
eval/                trajectory / reconstruction / metric-scale scoring, reports
scripts/pod.sh       the pod pipeline (stages above)
scripts/precheck.py  pre-check     scripts/progress.py  make watch
scripts/inputs.sh    inputs pack/push/fetch     scripts/results.sh  results pack/push/checkpoints/merge

dataset/exports/<ds>/<scene>/<traj>/{pano,pinhole/<variant>}/{rgb,depth,mask}/  poses_gt.tum  gt_mesh.ply
results/<method>/<ds>/<scene>/<traj>/<variant>/  poses.tum  cloud.ply  perf.json  arm_config.json  run.log
```

More: `make help`, `RESULTS_CHANGELOG.md` (what changed between result sets),
`documentation/docs/` (`make docs-serve`).

## Notes for the paper

- Timings come from one RTX 5090; don't mix them with the earlier RTX PRO 6000 numbers.
- Offline methods on 32 GB: report as **OOM**, with the 50–93 GB peaks measured on the 96 GB card.
- Ablation arms use seed 0 only (12 sequences each); main methods use 3 seeds.
- The 2026-07/08 alignment numbers are void (see `RESULTS_CHANGELOG.md` §14).
