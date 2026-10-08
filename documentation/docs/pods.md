# Running the benchmark on one GPU pod (rerun-v2)

Render on your PC (CPU), run on one pod (GPU, everything sequential so timings are
clean), score on your PC (CPU).

## 1. Your PC — render once (WSL Ubuntu)

```bash
sudo apt update && sudo apt install -y git make wget pigz unzip curl
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.local/bin/env
cd /mnt/c/Dev/ualberta/PRISM-benchmarks      # your Windows checkout works (or clone into ~ for speed)
git config core.fileMode false              # hide exec-bit noise from the Windows filesystem
make inputs                 # Replica meshes (streamed) -> split -> check -> render -> export -> pack
export HF_TOKEN=hf_...      # a WRITE token
make inputs-push INPUTS_HF_REPO=<hf-user>/prism-bench-inputs
```

`make replica` streams the official archive (one ~34 GB tar.gz in 17 parts, which can
only be decoded from the start) and keeps just `<scene>/mesh.ply` for the 6 scenes in
`datasets.replica.download_scenes` — about 3 GB on disk, no parts left behind.
`make replica-full` still runs the official script if you ever need textures.

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
