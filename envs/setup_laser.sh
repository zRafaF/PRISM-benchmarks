#!/usr/bin/env bash
# LASER (neu-vi) isolated env — training-free STREAMING baseline (wraps Pi3 with
# layer-wise Sim(3) scale alignment). Repo: https://github.com/neu-vi/LASER (pinned).
# Follows the repo README install: requirements + cython build_ext + editable viser.
# We skip the optional loop-closure weights/faiss (demo.py path doesn't need them).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule LASER
ensure_uv
cd "$REPO_ROOT/submodules/LASER"

echo "[laser] init recursive submodules (pi3, etc.)"
git submodule update --init --recursive || true

echo "[laser] isolated venv (Python 3.11)"
[ -d .venv ] || uv venv --python 3.11 .venv

echo "[laser] requirements"
[ -f requirements.txt ] && uv pip install --python .venv -r requirements.txt || true

echo "[laser] compiling cython modules (setup.py build_ext --inplace)"
.venv/bin/python setup.py build_ext --inplace || echo "[laser][!] build_ext failed — need a C compiler (apt-get install build-essential)"

if [ -d viser ]; then
    echo "[laser] editable viser"
    uv pip install --python .venv -e viser || true
fi

# torch LAST (cu128 for Blackwell sm_120); then re-pin numpy 1.26 (LASER pins it, and the
# cython .so was built against it).
install_torch_cu128 .venv
uv pip install --python .venv "numpy==1.26.4"

echo "[laser] done. (Pi3 backbone weights pull from HF on first run; loop-closure extras skipped)"
