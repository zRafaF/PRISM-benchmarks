# Running the benchmark on one GPU pod (rerun-v2)

One pod, everything sequential on its single GPU, so every timing and VRAM number is
clean. Scoring is CPU work and can run on the pod (`POD_EVAL=1`) or on any Linux box.

## On your computer (once per code change)

Commit and push PRISM-VGGT `prism-v2` and PRISM-benchmarks `rerun-v2`; the pod clones
`rerun-v2` and checks out PRISM-VGGT `prism-v2` (bench.env `PRISM_REF`).

## On the pod

```bash
apt-get update && apt-get install -y git make tmux
git clone -b rerun-v2 https://github.com/zRafaF/PRISM-benchmarks.git
cd PRISM-benchmarks
make pod                 # tmux session 'pod'; follow with: make pod-status
```

`make pod` = `scripts/pod.sh all`:

| Stage | What |
|---|---|
| prep | apt packages, uv, pinned submodules, every method env, weights |
| check | GPU, CUDA in every env, prism-v2 engine, nvblox fuses a frame (falls back to a source build of nvblox), VGGT-SLAM reproduces its `office_loop` loop closure |
| data | `make replica split check-scenes render export` — the dataset |
| bench | the matrix (`run_overnight.sh`, `SKIP_EVAL=1 SKIP_RENDER=1`) |
| capacity | optional `POD_CAPACITY=1`: VRAM-vs-length sweep (Fig. vram) |
| eval | optional `POD_EVAL=1`: score on the pod |
| pack | `results/bundles/pod_*.tar`: run dirs + clouds + scoring inputs + logs (+ HF push if `RESULTS_HF_REPO`) |
| studio | public Gradio link; Download tab lists the pack |

Any stage can be re-run alone: `bash scripts/pod.sh <stage>`.

## Scoring elsewhere (WSL / Linux, CPU)

```bash
git clone -b rerun-v2 https://github.com/zRafaF/PRISM-benchmarks.git && cd PRISM-benchmarks
make setup
mkdir -p results/bundles            # put the downloaded pod_*.tar here
make results-merge PACKS="results/bundles/pod_*.tar"
make eval-all publication
```
