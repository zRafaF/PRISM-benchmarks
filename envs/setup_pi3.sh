#!/usr/bin/env bash
# Pi3 / π³ isolated env (feed-forward pointmap baseline).
# Repo: https://github.com/yyfz/Pi3  (pinned in bench.env)
# We prefer the repo's own install path; adjust once cloned if its README differs.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule Pi3
ensure_uv
cd "$REPO_ROOT/submodules/Pi3"

echo "[pi3] creating isolated venv (Python 3.11)"
uv venv --python 3.11 .venv

# Install per the repo's own manifest, in priority order.
if [ -f pyproject.toml ]; then
    uv pip install --python .venv -e .
elif [ -f requirements.txt ]; then
    uv pip install --python .venv -r requirements.txt
else
    echo "[pi3][!] no pyproject/requirements found — check the repo README and pin deps here." >&2
fi
# Pi3 weights are auto-pulled from HF at first run (huggingface_hub); no manual step.
echo "[pi3] done.  (weights: pulled from HuggingFace on first inference)"
