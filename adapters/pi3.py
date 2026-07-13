#!/usr/bin/env python
"""Pi3 / π³ adapter entrypoint. See adapters/base.py + runners/pi3_runner.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.base import run_method

if __name__ == "__main__":
    run_method("pi3")
