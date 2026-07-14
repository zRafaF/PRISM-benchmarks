#!/usr/bin/env python
"""MapAnything runner — executed by submodules/map-anything/.venv/bin/python.

Feed-forward multi-view geometry model; driven windowed + chained via Sim(3) for a
fair streaming comparison (same as Pi3). Scale-free -> metric=false.
Emits poses.tum, cloud.ply, perf_runner.json.

NOTE: confirm import path + inference API vs the pinned commit
(facebookresearch/map-anything @ c845b8f). Marked lines are the seams.
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


def run_window(model, rgb_window):
    """>>> CONFIRM vs repo: return (poses[N,4,4], points[N,H,W,3]). <<<"""
    import torch
    imgs = torch.from_numpy(np.stack(rgb_window)).permute(0, 3, 1, 2).float() / 255.0
    with torch.no_grad():
        out = model.infer(imgs.cuda())          # <-- API line 1 (confirm)
    return np.asarray(out["camera_poses"]), np.asarray(out["points"])  # <-- API line 2


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

    from mapanything.models import MapAnything    # <-- API line 0 (confirm import path)
    model = MapAnything.from_pretrained().cuda().eval()

    seq = _io.load_sequence(args.in_dir)
    per_window, t0, win_results = [], time.perf_counter(), []
    for w in sliding_windows(len(seq["rgb"]), stream["window_size"], stream["overlap"]):
        t = time.perf_counter()
        poses, points = run_window(model, [seq["rgb"][i] for i in w])
        per_window.append(time.perf_counter() - t)
        win_results.append((w, poses, points))
    wall = time.perf_counter() - t0

    gp, pw, cw = chain_windows_sim3(win_results, seq, stream["overlap"])
    _io.write_tum(out / "poses.tum", list(range(len(gp))), gp)
    pts, cols = fuse_pointmaps(pw, cw, cfg["engine"]["voxel_size"])
    _io.write_cloud(out / "cloud.ply", pts, cols)
    _io.write_runner_perf(out, per_window_latency_s=per_window, latency_end_to_end_s=wall)
    print(f"[mapanything_runner] {len(gp)} poses, {len(pts)} pts, {wall:.1f}s")


if __name__ == "__main__":
    main()
