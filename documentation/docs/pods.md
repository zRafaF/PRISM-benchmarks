# Running the benchmark on one GPU pod (rerun-v2)

Render on your PC (CPU), run on one pod (GPU, everything sequential so timings are
clean), score on your PC (CPU).

## 1. Your PC — render once (WSL Ubuntu)

```bash
sudo apt update && sudo apt install -y git make wget pigz unzip curl
git clone -b rerun-v2 https://github.com/zRafaF/PRISM-benchmarks.git ~/PRISM-benchmarks
cd ~/PRISM-benchmarks
make inputs                 # Replica (~34 GB download) -> split -> check -> render -> export -> pack
export HF_TOKEN=hf_...      # a WRITE token
make inputs-push INPUTS_HF_REPO=<hf-user>/prism-bench-inputs
```
Keep this checkout: it has the depth maps and GT meshes the scoring needs.

## 2. The pod

```bash
apt-get update && apt-get install -y git make tmux
git clone -b rerun-v2 https://github.com/zRafaF/PRISM-benchmarks.git
cd PRISM-benchmarks
export HF_TOKEN=hf_... INPUTS_HF_REPO=<hf-user>/prism-bench-inputs
make pod
make watch                  # live progress bar + ETA (Ctrl-C leaves; the run continues)
```

`make pod`: prep (envs) -> check (GPU, CUDA, nvblox fuses a frame, VGGT-SLAM reference)
-> data (downloads YOUR frames) -> precheck (every method on one real sequence; stops
here on any FAIL) -> bench -> pack -> Studio link. Re-run any stage with
`bash scripts/pod.sh <stage>`.

## 3. Your PC — score

```bash
cd ~/PRISM-benchmarks
cp /mnt/c/Users/<you>/Downloads/pod_rerun-v2_*.tar results/bundles/   # from the Studio link
make results-merge PACKS="results/bundles/pod_*.tar"
make eval-all publication
```
