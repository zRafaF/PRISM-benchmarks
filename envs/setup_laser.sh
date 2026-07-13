#!/usr/bin/env bash
# LASER (neu-vi) isolated env — optional streaming baseline.
# Repo: https://github.com/neu-vi/LASER (pinned in bench.env)
# LASER is the training-free streaming wrapper PRISM's idea spun off from; it can
# consume the pano renders directly (camera: pano in config.yaml).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule LASER
ensure_uv
cd "$REPO_ROOT/submodules/LASER"

echo "[laser] creating isolated venv (Python 3.11)"
uv venv --python 3.11 .venv
if [ -f environment.yml ]; then
    echo "[laser][note] repo ships a conda environment.yml — mirror its pins into the venv or use conda; see docs/decisions.md."
fi
if [ -f pyproject.toml ]; then
    uv pip install --python .venv -e .
elif [ -f requirements.txt ]; then
    uv pip install --python .venv -r requirements.txt
else
    echo "[laser][!] confirm repo README install steps and encode them here." >&2
fi
echo "[laser] done."
