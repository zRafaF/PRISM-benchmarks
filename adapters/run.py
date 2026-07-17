#!/usr/bin/env python
"""Generic adapter entrypoint: run any configured method by name.

Used for ablations (prism_nolock, prism_noguards, ...) so we don't need a per-variant
adapter file. Usage: adapters/run.py --method <name> [--config .. --scenes .. --traj ..]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.base import run_method

if __name__ == "__main__":
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--method", required=True)
    a, rest = ap.parse_known_args()
    sys.argv = [sys.argv[0]] + rest          # leave --config/--scenes/--traj for run_method
    run_method(a.method)
