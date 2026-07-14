#!/usr/bin/env python
"""Pi3 / π³ runner — executed by submodules/Pi3/.venv/bin/python.

Pi3 (yyfz/Pi3 @ 9fa3ddb) is a permutation-equivariant feed-forward pointmap network
(not natively a streamer). For a fair STREAMING comparison we drive it windowed:
slide a window of `window_size` frames with `overlap`, run Pi3 per window, and chain
windows through their shared overlap frames with a Sim(3) Umeyama anchor (the same
fairness PRISM's own alignment gets). Scale-free -> metric=false in config.

API confirmed against the pinned commit's README:
  from pi3.models.pi3 import Pi3
  model = Pi3.from_pretrained("yyfz233/Pi3").to(device).eval()
  out = model(imgs[None])           # imgs (N,3,H,W) in [0,1]
  out["camera_poses"] (1,N,4,4) OpenCV cam->world ; out["points"] (1,N,H,W,3) global

Emits the common outputs: poses.tum, cloud.ply, perf_runner.json.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", dest="out_dir", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)

    import torch
    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())
    stream = cfg["streaming"]
    device = "cuda" if torch.cuda.is_available() else "cpu"

    from pi3.models.pi3 import Pi3
    from pi3.utils.basic import load_images_as_tensor

    model = Pi3.from_pretrained("yyfz233/Pi3").to(device).eval()

    # Load frames at Pi3's expected resolution via the repo's own loader, so sizes
    # are always valid. Colours for fusion come from these SAME (resized) frames.
    imgs = load_images_as_tensor(str(Path(args.in_dir) / "rgb"), interval=1).to(device)  # (N,3,H,W) [0,1]
    n = int(imgs.shape[0])
    rgb_list = [(imgs[i].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8) for i in range(n)]
    seq = {"rgb": rgb_list}

    dtype = torch.bfloat16 if (device == "cuda" and torch.cuda.get_device_capability()[0] >= 8) else torch.float16

    per_window, t0, win_results = [], time.perf_counter(), []
    for w in sliding_windows(n, stream["window_size"], stream["overlap"]):
        t = time.perf_counter()
        with torch.no_grad(), torch.amp.autocast("cuda", dtype=dtype, enabled=(device == "cuda")):
            res = model(imgs[w][None])
        poses = res["camera_poses"][0].float().cpu().numpy()   # (len(w),4,4) cam->world
        points = res["points"][0].float().cpu().numpy()        # (len(w),H,W,3) global (window frame)
        per_window.append(time.perf_counter() - t)
        win_results.append((w, poses, points))
    wall = time.perf_counter() - t0

    global_poses, points_world, colors = chain_windows_sim3(win_results, seq, stream["overlap"])
    _io.write_tum(out / "poses.tum", list(range(len(global_poses))), global_poses)
    pts, cols = fuse_pointmaps(points_world, colors, cfg["engine"]["voxel_size"])
    _io.write_cloud(out / "cloud.ply", pts, cols)
    _io.write_runner_perf(out, per_window_latency_s=per_window, latency_end_to_end_s=wall)
    print(f"[pi3_runner] {len(global_poses)} poses, {len(pts)} pts, {n} frames, {wall:.1f}s")


if __name__ == "__main__":
    main()
