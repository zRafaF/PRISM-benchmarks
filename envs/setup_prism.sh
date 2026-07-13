#!/usr/bin/env bash
# PRISM-VGGT isolated env. Delegates to the repo's OWN setup.sh (do not
# reimplement its install). CUDA 12.8 / torch 2.8 locked; nvblox custom wheel.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule PRISM-VGGT
ensure_uv
cd "$REPO_ROOT/submodules/PRISM-VGGT"

echo "[prism] delegating to the repo's own setup.sh (nvblox: prebuilt default)"
# NVBLOX_MODE=source recommended on the RTX PRO 6000 (Blackwell); make configurable.
NVBLOX_MODE="${NVBLOX_MODE:-source}" bash setup.sh

echo "[prism] benchmark extras (evo/sklearn/tensorboard)"
uv sync --extra benchmarks

echo "[prism] fetching PanoVGGT checkpoint -> checkpoints/model.pt"
uv run python -c "from prism_vggt import download_weights; download_weights('checkpoints/model.pt')"
echo "[prism] done."
