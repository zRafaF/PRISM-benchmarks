#!/usr/bin/env python
"""VGGT-SLAM runner — executed by submodules/VGGT-SLAM/.venv/bin/python.

VGGT-SLAM is natively incremental (submap SL(4)/SE(3) factor graph + DINOv2-SALAD).
We drive it in streaming order over the PINHOLE sequence and read back its global
trajectory + fused map. Scale-free -> metric=false (Sim(3)+scale align for ATE).

Emits poses.tum, cloud.ply, perf_runner.json.

NOTE: confirm the entrypoint against the pinned commit
(MIT-SPARK/VGGT-SLAM @ 35327ac). The repo ships a runnable demo/main — prefer
calling its offline solver over reimplementing. The marked lines are the seams.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).parent))
import _io


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", dest="out_dir", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)

    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())
    stream = cfg["streaming"]
    seq = _io.load_sequence(args.in_dir)

    # --- build the VGGT-SLAM solver (confirm import/args vs pinned commit) ---
    from vggt_slam.solver import Solver        # <-- API line 0 (confirm module path)
    solver = Solver(                            # <-- API line 1 (confirm ctor args)
        max_loops=0,                            # non-looping to match PRISM's shipped mode
        vis=False,
    )

    per_window, t0 = [], time.perf_counter()
    # Feed frames in streaming order; VGGT-SLAM manages its own keyframe/submap graph.
    frame_paths = [str(Path(args.in_dir) / "rgb" / f"{nm}.png") for nm in seq["names"]]
    for w_start in range(0, len(frame_paths), max(1, stream["window_size"] - stream["overlap"])):
        chunk = frame_paths[w_start:w_start + stream["window_size"]]
        if not chunk:
            break
        t = time.perf_counter()
        solver.add_frames(chunk)                # <-- API line 2 (confirm incremental call)
        per_window.append(time.perf_counter() - t)
    solver.optimize()                           # <-- API line 3 (final graph solve)
    wall = time.perf_counter() - t0

    poses = np.asarray(solver.get_poses())      # <-- API line 4 (N,4,4 cam->world)
    pts, cols = solver.get_pointcloud()         # <-- API line 5 (points[,colors])
    _io.write_tum(out / "poses.tum", list(range(len(poses))), poses)
    _io.write_cloud(out / "cloud.ply", np.asarray(pts),
                    np.asarray(cols) if cols is not None else None)
    _io.write_runner_perf(out, per_window_latency_s=per_window, latency_end_to_end_s=wall)
    print(f"[vggtslam_runner] {len(poses)} poses, {wall:.1f}s")


if __name__ == "__main__":
    main()
