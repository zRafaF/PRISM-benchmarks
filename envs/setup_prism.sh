#!/usr/bin/env bash
# PRISM-VGGT isolated env. Delegates to the repo's OWN setup.sh (do not
# reimplement its install). CUDA 12.8 / torch 2.8 locked; nvblox custom wheel.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule PRISM-VGGT
ensure_uv
cd "$REPO_ROOT/submodules/PRISM-VGGT"

# PanoVGGT weights: YijingGuo/PanoVGGT went private (403). Pre-fetch from our mirror
# bucket BEFORE setup.sh, so setup.sh's built-in (dead) download is skipped — it only
# downloads when checkpoints/model.pt is absent.
WURL="${PANOVGGT_WEIGHTS_URL:-https://huggingface.co/buckets/DoninhaD/PanoVGGT-bucket/resolve/model.pt?download=true}"
mkdir -p checkpoints
if [ ! -f checkpoints/model.pt ]; then
    echo "[prism] fetching PanoVGGT weights from $WURL"
    curl -L --fail -o checkpoints/model.pt "$WURL"
fi

echo "[prism] delegating to the repo's own setup.sh (nvblox: prebuilt wheel)"
# Use the published nvblox_torch wheel pinned in pyproject.toml — no source build.
# Override with NVBLOX_MODE=source only if the wheel ever mismatches your GPU/CUDA/ABI
# (and then `apt install lsb-release` first — the wheel's setup.py shells out to it).
NVBLOX_MODE="${NVBLOX_MODE:-prebuilt}" bash setup.sh

echo "[prism] benchmark extras (evo/sklearn/tensorboard)"
uv sync --extra benchmarks
echo "[prism] done (weights at submodules/PRISM-VGGT/checkpoints/model.pt)."
