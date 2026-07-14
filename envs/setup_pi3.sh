#!/usr/bin/env bash
# Pi3 / π³ isolated env (feed-forward pointmap baseline).
# Repo: https://github.com/yyfz/Pi3  (pinned in bench.env)
# We prefer the repo's own install path; adjust once cloned if its README differs.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule Pi3
ensure_uv
cd "$REPO_ROOT/submodules/Pi3"

echo "[pi3] isolated venv (Python 3.11)"
[ -d .venv ] || uv venv --python 3.11 .venv     # reuse if it already exists (idempotent)

# Pi3's real deps (torch==2.5.1, torchvision, numpy, opencv, plyfile, hf_hub, ...) live
# in requirements.txt — its pyproject.toml is minimal. Install requirements FIRST, then
# the pi3 package itself without re-resolving deps.
if [ -f requirements.txt ]; then
    echo "[pi3] installing requirements.txt"
    uv pip install --python .venv -r requirements.txt
fi
# Pi3 pins torch==2.5.1 (no Blackwell sm_120 kernels) -> override with cu128 build.
install_torch_cu128 .venv
if [ -f pyproject.toml ]; then
    uv pip install --python .venv -e . --no-deps
fi
# Pi3/Pi3X weights are auto-pulled from HF at first run (huggingface_hub); no manual step.
echo "[pi3] done.  (weights: pulled from HuggingFace on first inference)"
