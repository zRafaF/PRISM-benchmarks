#!/usr/bin/env python
"""PanoVGGT (raw backbone) adapter entrypoint. See runners/panovggt_runner.py.

Runs the panoramic backbone PRISM wraps, FULL-BATCH on the pano frames, with NO
streaming engine / TSDF / metric grounding — a 360° feed-forward reference that
isolates what PRISM's engine adds over the raw model. Uses the PRISM submodule env.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.base import run_method

if __name__ == "__main__":
    run_method("panovggt")
