#!/usr/bin/env bash
# MapAnything (facebookresearch) isolated env — optional baseline.
# Repo: https://github.com/facebookresearch/map-anything (pinned in bench.env)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule map-anything
ensure_uv
cd "$REPO_ROOT/submodules/map-anything"

echo "[mapanything] isolated venv (Python 3.12 — repo requires 3.12)"
[ -d .venv ] || uv venv --python 3.12 .venv     # reuse if it already exists (idempotent)
# Torch first (cu128 for Blackwell sm_120); MapAnything doesn't pin torch, so -e . keeps it.
install_torch_cu128 .venv
echo "[mapanything] installing package (pip install -e .)"
uv pip install --python .venv -e .
echo "[mapanything] done.  (weights auto-pulled from HF: facebook/map-anything)"
