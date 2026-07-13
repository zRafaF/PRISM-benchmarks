#!/usr/bin/env python
"""PRISM-VGGT adapter entrypoint (ours). See adapters/base.py + runners/prism_runner.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.base import run_method

if __name__ == "__main__":
    run_method("prism")
