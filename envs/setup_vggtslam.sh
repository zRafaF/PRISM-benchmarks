#!/usr/bin/env bash
# VGGT-SLAM (MIT-SPARK) isolated env — the heavy one.
# Repo: https://github.com/MIT-SPARK/VGGT-SLAM (pinned in bench.env)
# Drags in GTSAM + custom SL(4) bindings + DINOv2-SALAD retrieval. Prefer the
# repo's own installer; this wrapper just drives it in an isolated venv.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule VGGT-SLAM
ensure_uv
cd "$REPO_ROOT/submodules/VGGT-SLAM"

echo "[vggtslam] initialise the repo's own third-party submodules (vggt, salad, ...)"
git submodule update --init --recursive || true

echo "[vggtslam] creating isolated venv (Python 3.11)"
uv venv --python 3.11 .venv

# Follow the repo README's install (it typically ships an install.sh / requirements).
if [ -f install.sh ]; then
    echo "[vggtslam] delegating to repo install.sh"
    VIRTUAL_ENV="$PWD/.venv" bash install.sh || true
elif [ -f requirements.txt ]; then
    uv pip install --python .venv -r requirements.txt
elif [ -f pyproject.toml ]; then
    uv pip install --python .venv -e .
else
    echo "[vggtslam][!] confirm the repo README install steps and encode them here." >&2
fi
# GTSAM: prefer the wheel the repo pins; build from source only if it fails on the 6000.
echo "[vggtslam] done.  (GTSAM/SL4/DINO-SALAD per repo; see docs/decisions.md D4)"
