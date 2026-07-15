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

    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())
    vs = cfg.get("vggtslam", {})
    submap = int(vs.get("submap_size", cfg["engine"]["window_size"]))
    max_loops = int(vs.get("max_loops", 1))          # 1 = loop closure on (native); 0 = off
    min_disp = float(vs.get("min_disparity", 50))    # optical-flow keyframe threshold

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
    rc = subprocess.run(cmd).returncode
    wall = time.perf_counter() - t0
    if rc != 0:
        print(f"[vggtslam_runner] main.py exited {rc}")

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
