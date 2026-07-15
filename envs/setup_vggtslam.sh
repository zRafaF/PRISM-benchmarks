#!/usr/bin/env bash
# VGGT-SLAM 2.0 (MIT-SPARK) isolated env — the heavy streaming baseline.
# Repo: https://github.com/MIT-SPARK/VGGT-SLAM (pinned in bench.env)
# Mirrors the repo's setup.sh but SKIPS Perception-Encoder + SAM3 (only needed for the
# optional --run_os open-set detection, which we never use), and overrides torch with the
# cu128 build for Blackwell (sm_120). GTSAM ships the SL(4) optimiser upstream now.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule VGGT-SLAM
ensure_uv
cd "$REPO_ROOT/submodules/VGGT-SLAM"

echo "[vggtslam] isolated venv (Python 3.11)"
[ -d .venv ] || uv venv --python 3.11 .venv

echo "[vggtslam] base requirements"
[ -f requirements.txt ] && uv pip install --python .venv -r requirements.txt || true

mkdir -p third_party
echo "[vggtslam] SALAD (DINO retrieval for loop closure)"
[ -d third_party/salad ] || git clone --depth 1 https://github.com/Dominic101/salad.git third_party/salad
uv pip install --python .venv -e ./third_party/salad

echo "[vggtslam] VGGT fork (MIT-SPARK/VGGT_SPARK)"
[ -d third_party/vggt ] || git clone --depth 1 https://github.com/MIT-SPARK/VGGT_SPARK.git third_party/vggt
uv pip install --python .venv -e ./third_party/vggt

echo "[vggtslam] the repo itself"
uv pip install --python .venv -e .
# NOTE: do NOT `pip install gtsam` — requirements.txt already pulls `gtsam-develop`
# (4.3 dev), which is the build that carries the SL(4) optimiser VGGT-SLAM needs.
# Stable `gtsam==4.2.x` lacks SL(4) and would shadow the dev build.

# torch LAST so nothing downgrades it: cu128 = Blackwell sm_120 kernels (matches PRISM).
install_torch_cu128 .venv
# ...but the cu128 wheels pull numpy 2.x; VGGT-SLAM/VGGT-fork pin numpy 1.26 -> re-pin it
# (numpy 2.0 breaks older np APIs used by the SLAM code). torch 2.8 works with numpy 1.26.
uv pip install --python .venv "numpy==1.26.4"

echo "[vggtslam] done. (PE/SAM3 skipped — only needed for --run_os; VGGT-1B weights pull from HF on first run)"
