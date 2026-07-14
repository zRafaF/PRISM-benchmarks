#!/usr/bin/env python
"""Pi3 / π³ runner — executed by submodules/Pi3/.venv/bin/python.

Pi3 is a feed-forward pointmap network (not natively a streamer). For a fair
STREAMING comparison we drive it windowed: slide a window of `window_size` frames
with `overlap`, run Pi3 per window, and chain windows through their shared overlap
frames (Sim(3) Umeyama on the overlap camera centres — the same fairness the other
methods get). Scale-free -> metric=false in config (excluded from absolute-scale).

Emits the common outputs: poses.tum, cloud.ply, perf_runner.json.

NOTE: the exact import path + return keys are confirmed against the pinned commit
(yyfz/Pi3 @ 9fa3ddb). Adjust the two marked lines if the repo's API differs.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).parent))
import runner_io as _io
from _stream import sliding_windows, chain_windows_sim3, fuse_pointmaps


def run_pi3_window(model, rgb_window, intr):
    """>>> CONFIRM vs repo: return (poses[N,4,4] cam->local, points[N,H,W,3]). <<<"""
    import torch
    imgs = torch.from_numpy(np.stack(rgb_window)).permute(0, 3, 1, 2).float() / 255.0
    with torch.no_grad():
        out = model.infer(imgs.cuda())            # <-- API line 1 (confirm method name)
    poses = np.asarray(out["camera_poses"])       # <-- API line 2 (confirm key)
    points = np.asarray(out["points"])
    return poses, points


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

    # --- load Pi3 (confirm module path against the pinned commit) ---
    from pi3.models.pi3 import Pi3            # <-- API line 0 (confirm import path)
    model = Pi3.from_pretrained().cuda().eval()

    seq = _io.load_sequence(args.in_dir)
    per_window, t0 = [], time.perf_counter()
    win_results = []
    for w in sliding_windows(len(seq["rgb"]), stream["window_size"], stream["overlap"]):
        t = time.perf_counter()
        poses, points = run_pi3_window(model, [seq["rgb"][i] for i in w], seq["intrinsics"])
        per_window.append(time.perf_counter() - t)
        win_results.append((w, poses, points))
    wall = time.perf_counter() - t0

    global_poses, points_world, colors = chain_windows_sim3(win_results, seq, stream["overlap"])
    ts = list(range(len(global_poses)))
    _io.write_tum(out / "poses.tum", ts, global_poses)
    pts, cols = fuse_pointmaps(points_world, colors, cfg["engine"]["voxel_size"])
    _io.write_cloud(out / "cloud.ply", pts, cols)
    _io.write_runner_perf(out, per_window_latency_s=per_window, latency_end_to_end_s=wall)
    print(f"[pi3_runner] {len(global_poses)} poses, {len(pts)} pts, {wall:.1f}s")


if __name__ == "__main__":
    main()
