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

# Override a venv's torch with the CUDA 12.8 build. Baselines that pin an older torch
# (e.g. 2.5.1) ship no kernels for Blackwell (sm_120) -> "no kernel image available".
# Installing the cu128 wheels (torch 2.8) fixes it, matching PRISM's stack.
# Usage: install_torch_cu128 .venv
install_torch_cu128 () {
    local venv="$1"
    echo "[*] installing CUDA 12.8 torch 2.8 / torchvision (Blackwell sm_120 support)"
    # Pin 2.8.* + --reinstall: an unpinned 'torch' would be seen as already satisfied by
    # a repo's older pin (e.g. 2.5.1) and skipped, leaving a build with no sm_120 kernels.
    uv pip install --python "$venv" --reinstall \
        --index-url https://download.pytorch.org/whl/cu128 "torch==2.8.*" torchvision
    echo -n "[*] torch now: "
    uv run --python "$venv" python -c "import torch; print(torch.__version__, 'sm', torch.cuda.get_arch_list()[-3:])" || true
}
