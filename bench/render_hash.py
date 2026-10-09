"""Fingerprint of everything that determines the RENDERED inputs (scripts/inputs.sh).

Only the config sections the renderer/exporter read (datasets incl. the frozen scene
list, camera, trajectories, engine, streaming) plus the trajectory/render code. Run
settings — methods, ablations, seeds per arm, eval — are deliberately NOT included, so
changing what runs never invalidates frames that are still correct.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bench.config import REPO_ROOT, load_config

SECTIONS = ("datasets", "camera", "trajectories", "engine", "streaming")
CODE = ("dataset/trajectories.py", "dataset/render_scene.py")


def render_hash() -> str:
    cfg = load_config("config.yaml")
    h = hashlib.sha256()
    h.update(json.dumps({k: cfg.get(k) for k in SECTIONS}, sort_keys=True, default=str).encode())
    for f in CODE:
        h.update((REPO_ROOT / f).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


if __name__ == "__main__":
    print(render_hash())
