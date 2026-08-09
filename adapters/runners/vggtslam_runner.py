#!/usr/bin/env python
"""VGGT-SLAM runner — executed by submodules/VGGT-SLAM/.venv/bin/python.

VGGT-SLAM 2.0 (MIT-SPARK @ 35327ac) is a real-time INCREMENTAL SLAM: it streams the
pinhole frames, selects keyframes by optical flow, builds SL(4) submaps in a GTSAM
factor graph with DINO-SALAD loop closure. It's the primary *streaming* comparison for
PRISM (both process frames online).

We drive the repo's own `main.py` (its documented entrypoint) and convert its outputs:
  * `--log_results --log_path poses.txt` -> TUM lines "frame_id tx ty tz qx qy qz qw"
    (frame_id = true global index -> aligns with our GT; keyframe subset is fine for evo).
  * `<log>_points.pcd` -> colored dense cloud.
Scale-free -> metric=false. Emits poses.tum, cloud.ply, perf_runner.json.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import runner_io as _io


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", dest="out_dir", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    import os
    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())
    vs = cfg.get("vggtslam", {})
    submap = int(vs.get("submap_size", cfg["engine"]["window_size"]))
    # Per-arm override via run_env, so the loop-closure-ON and loop-closure-OFF arms
    # are two independently named methods rather than one mutable global. Loop closure
    # is VGGT-SLAM's headline feature: publishing only the OFF arm understates it.
    max_loops = int(os.environ.get("VGGTSLAM_MAX_LOOPS", vs.get("max_loops", 1)))
    min_disp = float(os.environ.get("VGGTSLAM_MIN_DISPARITY", vs.get("min_disparity", 50)))
    submap = int(os.environ.get("VGGTSLAM_SUBMAP_SIZE", submap))
    print(f"[vggtslam_runner] submap_size={submap} max_loops={max_loops} "
          f"(loop closure {'ON' if max_loops else 'OFF'}) min_disparity={min_disp}")

    rgb_dir = Path(args.in_dir) / "rgb"
    poses_txt = out / "poses.txt"

    # cwd is the VGGT-SLAM repo (set by the adapter); main.py is its entrypoint.
    cmd = [sys.executable, "main.py",
           "--image_folder", str(rgb_dir),
           "--log_results", "--log_path", str(poses_txt),
           "--submap_size", str(submap),
           "--max_loops", str(max_loops),
           "--min_disparity", str(min_disp)]
    print("[vggtslam_runner] $", " ".join(cmd))
    t0 = time.perf_counter()
    # Capture stdout so the submap / loop-closure counts can be parsed out of it,
    # while still echoing everything to our own stdout (which the adapter tees to
    # run.log). Those two counts are the only way to tell whether VGGT-SLAM's method
    # actually engaged, and they decide whether the run is citable at all.
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    captured = []
    for line in proc.stdout:
        captured.append(line)
        sys.stdout.write(line)
    rc = proc.wait()
    wall = time.perf_counter() - t0
    if rc != 0:
        print(f"[vggtslam_runner] main.py exited {rc}")

    # ── Degeneracy check ────────────────────────────────────────────────────
    # VGGT-SLAM's contribution IS the multi-submap SL(4) pose graph plus loop
    # closure. With a single submap there is no inter-submap registration and no
    # loop closure: it degenerates to plain feed-forward VGGT, and any head-to-head
    # against it is meaningless (the 2026-08 smoke hit exactly this — 8 keyframes,
    # 1 submap, 0 loop closures, and the loop/no-loop arms returned identical ATE).
    log_text = "".join(captured)
    def _grab(pattern, cast=int, default=None):
        m = re.search(pattern, log_text)
        return cast(m.group(1)) if m else default
    n_submaps = _grab(r"Total number of submaps in map\s+(\d+)")
    n_loops = _grab(r"Total number of loop closures in map\s+(\d+)")
    degenerate = (n_submaps is not None and n_submaps < 2)
    if degenerate:
        print(f"[vggtslam_runner] *** WARNING: only {n_submaps} submap(s) and "
              f"{n_loops} loop closure(s). VGGT-SLAM's pose-graph and loop-closure "
              f"machinery did NOT engage — this run measures plain feed-forward VGGT, "
              f"not VGGT-SLAM. Do not cite it as a head-to-head. Raise the frame "
              f"count, or lower submap_size ({submap}) / min_disparity ({min_disp}) "
              f"so more than {submap} keyframes survive.")
    elif n_submaps is not None:
        print(f"[vggtslam_runner] {n_submaps} submaps, {n_loops} loop closures "
              f"— method engaged")

    # Record the exact configuration + engagement evidence next to the results, so
    # the arm is self-describing and the degeneracy is visible in the aggregate.
    (out / "arm_config.json").write_text(json.dumps(
        {"max_loops": max_loops, "loop_closure": bool(max_loops),
         "submap_size": submap, "min_disparity": min_disp,
         "n_submaps": n_submaps, "n_loop_closures": n_loops,
         "method_engaged": (not degenerate) if n_submaps is not None else None,
         "degenerate_single_submap": degenerate}, indent=2))

    # poses.txt is already TUM (frame_id = timestamp) -> poses.tum
    if poses_txt.exists():
        shutil.copyfile(poses_txt, out / "poses.tum")
        n = sum(1 for _ in open(out / "poses.tum"))
    else:
        n = 0
        print("[vggtslam_runner] WARN: no poses.txt produced")

    # dense cloud: <log>_points.pcd -> cloud.ply
    pcd = out / "poses_points.pcd"
    npts = 0
    if pcd.exists():
        import open3d as o3d
        pc = o3d.io.read_point_cloud(str(pcd))
        o3d.io.write_point_cloud(str(out / "cloud.ply"), pc)
        npts = len(pc.points)

    _io.write_runner_perf(out, per_window_latency_s=[], latency_end_to_end_s=wall)
    print(f"[vggtslam_runner] {n} keyframe poses, {npts} pts, {wall:.1f}s")


if __name__ == "__main__":
    main()
