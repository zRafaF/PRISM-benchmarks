#!/usr/bin/env python
"""PRISM-benchmarks Studio launcher (`make studio`).

The app lives in preview.py (build_app); this is the entrypoint under the current
name. One-button pipeline + config + snapshots + viewers. Prints a public share URL.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from preview import build_app

if __name__ == "__main__":
    build_app().launch(server_name="0.0.0.0", server_port=7860, share=True)
