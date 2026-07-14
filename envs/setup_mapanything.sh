#!/usr/bin/env bash
# MapAnything (facebookresearch) isolated env — optional baseline.
# Repo: https://github.com/facebookresearch/map-anything (pinned in bench.env)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
require_submodule map-anything
ensure_uv
cd "$REPO_ROOT/submodules/map-anything"

echo "[mapanything] isolated venv (Python 3.11)"
[ -d .venv ] || uv venv --python 3.11 .venv     # reuse if it already exists (idempotent)
if [ -f pyproject.toml ]; then
    uv pip install --python .venv -e .
elif [ -f requirements.txt ]; then
    uv pip install --python .venv -r requirements.txt
else
    echo "[mapanything][!] confirm repo README install steps and encode them here." >&2
fi
echo "[mapanything] done."
