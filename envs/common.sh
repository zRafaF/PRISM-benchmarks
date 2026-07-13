#!/usr/bin/env bash
# Shared helpers for the per-method setup scripts.
# Every method gets its OWN uv venv inside its submodule folder. We NEVER install
# a method's deps into the orchestrator env, and we NEVER loosen PRISM's locked
# stack (CUDA 12.8 / torch 2.8).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

require_submodule () {
    local path="submodules/$1"
    if [ ! -e "$REPO_ROOT/$path/.git" ] && [ ! -d "$REPO_ROOT/$path/.git" ]; then
        echo "[!] $path not present. Run 'make init' first." >&2
        exit 1
    fi
}

ensure_uv () {
    if ! command -v uv >/dev/null 2>&1; then
        echo "[*] installing uv ..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
}
