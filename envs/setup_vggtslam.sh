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

# ── PINS (rerun-v2) ─────────────────────────────────────────────────────────────
# requirements.txt asks for an UNPINNED `gtsam-develop` (a nightly). PyPI only keeps
# about five weeks of those, so the build the 2026-07/08 runs used no longer exists and
# every fresh pod got a different GTSAM — the library that implements VGGT-SLAM's SL(4)
# optimisation. GTSAM 4.3.0 (stable, 2026-09-19) ships SL4 / PriorFactorSL4 /
# BetweenFactorSL4 (verified), so the env now uses that and nothing floats.
# The two third-party clones are pinned to commits for the same reason.
GTSAM_PIN="${GTSAM_PIN:-gtsam==4.3.0}"
VGGT_SPARK_REF="${VGGT_SPARK_REF:-6e6e16107b88e8e76c751826af10d4295d87ecd2}"
SALAD_REF="${SALAD_REF:-33ca9c0ca1e10cbb21efc0d6a5fcb6d45688e42d}"

clone_pinned () {   # clone_pinned <url> <dir> <commit>
    local url="$1" dir="$2" ref="$3"
    [ -d "$dir/.git" ] || git clone "$url" "$dir"
    git -C "$dir" fetch --quiet origin "$ref" 2>/dev/null || git -C "$dir" fetch --quiet --all
    git -C "$dir" checkout --quiet "$ref"
    echo "   $dir -> $(git -C "$dir" rev-parse --short HEAD)"
}

# Purge ANY gtsam first: a stray gtsam-develop alongside the stable wheel collides
# ("cannot import NonlinearFactorGraph").
uv pip uninstall --python .venv gtsam gtsam-develop >/dev/null 2>&1 || true

echo "[vggtslam] base requirements (gtsam-develop REPLACED by $GTSAM_PIN)"
if [ -f requirements.txt ]; then
    grep -v -E '^[[:space:]]*gtsam' requirements.txt > .requirements.pinned.txt
    uv pip install --python .venv -r .requirements.pinned.txt
fi
uv pip install --python .venv "$GTSAM_PIN"
.venv/bin/python -c "from gtsam import SL4, PriorFactorSL4, BetweenFactorSL4; print('[vggtslam] gtsam SL4 OK')"

mkdir -p third_party
echo "[vggtslam] SALAD (DINO retrieval for loop closure) @ $SALAD_REF"
clone_pinned https://github.com/Dominic101/salad.git third_party/salad "$SALAD_REF"
uv pip install --python .venv -e ./third_party/salad

echo "[vggtslam] VGGT fork (MIT-SPARK/VGGT_SPARK) @ $VGGT_SPARK_REF"
clone_pinned https://github.com/MIT-SPARK/VGGT_SPARK.git third_party/vggt "$VGGT_SPARK_REF"
uv pip install --python .venv -e ./third_party/vggt

echo "[vggtslam] the repo itself"
uv pip install --python .venv -e .
# NOTE: stable gtsam 4.2.x lacks SL(4); 4.3.0 has it. Never let gtsam-develop back in.

# torch LAST so nothing downgrades it: cu128 = Blackwell sm_120 kernels (matches PRISM).
install_torch_cu128 .venv
# ...but the cu128 wheels pull numpy 2.x; VGGT-SLAM/VGGT-fork pin numpy 1.26 -> re-pin it
# (numpy 2.0 breaks older np APIs used by the SLAM code). torch 2.8 works with numpy 1.26.
uv pip install --python .venv "numpy==1.26.4"

# DINO-SALAD loop-closure checkpoint: loop_closure.py loads it unconditionally from
# <torch_hub>/checkpoints/dino_salad.ckpt, but setup.sh never downloads it. Fetch from the
# SALAD Google Drive (gdown handles the confirm token).
CKPT_DIR="$(.venv/bin/python -c 'import torch; print(torch.hub.get_dir())')/checkpoints"
mkdir -p "$CKPT_DIR"
if [ ! -f "$CKPT_DIR/dino_salad.ckpt" ]; then
    echo "[vggtslam] fetching dino_salad.ckpt (SALAD loop-closure weights)"
    uv pip install --python .venv gdown
    .venv/bin/python -m gdown "https://drive.google.com/uc?id=1u83Dmqmm1-uikOPr58IIhfIzDYwFxCy1" \
        -O "$CKPT_DIR/dino_salad.ckpt" || \
        echo "[vggtslam][!] gdown failed (Drive quota?). Manually place dino_salad.ckpt in $CKPT_DIR"
else
    echo "[vggtslam] dino_salad.ckpt already present"
fi

# Record exactly what was installed (copied into every results bundle by `make pod`).
mkdir -p "$REPO_ROOT/logs/env"
uv pip freeze --python .venv > "$REPO_ROOT/logs/env/vggtslam.freeze.txt" 2>/dev/null || true

echo "[vggtslam] done. (PE/SAM3 skipped — only needed for --run_os; VGGT-1B weights pull from HF on first run)"
