#!/usr/bin/env python
"""LASER runner — executed by submodules/LASER/.venv/bin/python.

LASER is a training-free STREAMING reconstruction wrapper (PRISM's idea spun off
from it). It consumes the PANO renders directly and streams frames incrementally,
so we drive it frame-by-frame and read its running trajectory + map.
Emits poses.tum, cloud.ply, perf_runner.json.

NOTE: confirm the streaming entrypoint vs the pinned commit
(neu-vi/LASER @ 7adbb7d). Marked lines are the seams.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).parent))
import runner_io as _io


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", dest="out_dir", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)

    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())
    seq = _io.load_sequence(args.in_dir)

    from laser.streamer import LaserStreamer      # <-- API line 0 (confirm import path)
    streamer = LaserStreamer(device="cuda")       # <-- API line 1 (confirm ctor)

    per_frame, t0 = [], time.perf_counter()
    for img in seq["rgb"]:
        t = time.perf_counter()
        streamer.push(img)                        # <-- API line 2 (incremental frame push)
        per_frame.append(time.perf_counter() - t)
    wall = time.perf_counter() - t0

    poses = np.asarray(streamer.get_poses())      # <-- API line 3
    pts, cols = streamer.get_pointcloud()         # <-- API line 4
    _io.write_tum(out / "poses.tum", list(range(len(poses))), poses)
    _io.write_cloud(out / "cloud.ply", np.asarray(pts),
                    np.asarray(cols) if cols is not None else None)
    _io.write_runner_perf(out, per_window_latency_s=per_frame, latency_end_to_end_s=wall)
    print(f"[laser_runner] {len(poses)} poses, {wall:.1f}s")


if __name__ == "__main__":
    main()
