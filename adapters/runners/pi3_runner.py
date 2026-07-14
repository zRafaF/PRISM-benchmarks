#!/usr/bin/env python
"""Pi3 / π³ (Pi3X) runner — executed by submodules/Pi3/.venv/bin/python.

Pi3/Pi3X is a PERMUTATION-EQUIVARIANT feed-forward model: it must ingest the whole
set of frames in ONE pass (no fixed reference view), producing a single globally
consistent reconstruction. It is NOT a streamer — windowing + chaining produces
misaligned, overlapping submaps. So we run it FULL-BATCH over all frames.

(The streaming methods are PRISM and LASER; Pi3/MapAnything are full-batch baselines.)

API (pinned commit README):
  model = Pi3X.from_pretrained("yyfz233/Pi3X").to(device).eval()   # or Pi3
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
from _stream import fuse_pointmaps


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
    device = "cuda" if torch.cuda.is_available() else "cpu"

    from pi3.utils.basic import load_images_as_tensor
    try:
        from pi3.models.pi3x import Pi3X
        model = Pi3X.from_pretrained("yyfz233/Pi3X").to(device).eval()
        print("[pi3_runner] using Pi3X (approximate metric scale)")
    except Exception as e:
        from pi3.models.pi3 import Pi3
        model = Pi3.from_pretrained("yyfz233/Pi3").to(device).eval()
        print(f"[pi3_runner] Pi3X unavailable ({e}); using original Pi3 (scale-free)")

    imgs = load_images_as_tensor(str(Path(args.in_dir) / "rgb"), interval=1).to(device)  # (N,3,H,W)
    n_total = int(imgs.shape[0])

    # FULL-BATCH: all frames at once. Optional cap (baselines.max_frames) if a scene is
    # too big for GPU memory — uniformly subsample, keeping the global frame indices as
    # TUM timestamps so eval still associates against GT.
    cap = (cfg.get("baselines") or {}).get("max_frames")
    idxs = list(range(n_total))
    if cap and n_total > cap:
        idxs = np.linspace(0, n_total - 1, int(cap)).astype(int).tolist()
        imgs = imgs[idxs]
        print(f"[pi3_runner] subsampled {n_total} -> {len(idxs)} frames (baselines.max_frames={cap})")

    dtype = torch.bfloat16 if (device == "cuda" and torch.cuda.get_device_capability()[0] >= 8) else torch.float16
    t0 = time.perf_counter()
    with torch.no_grad(), torch.amp.autocast("cuda", dtype=dtype, enabled=(device == "cuda")):
        res = model(imgs[None])                              # (1,N,...)
    wall = time.perf_counter() - t0

    poses = res["camera_poses"][0].float().cpu().numpy()     # (M,4,4) global
    points = res["points"][0].float().cpu().numpy()          # (M,H,W,3) global
    rgb = (imgs.permute(0, 2, 3, 1).cpu().numpy() * 255).astype(np.uint8)  # (M,H,W,3)

    _io.write_tum(out / "poses.tum", idxs, poses)            # timestamps = global frame indices
    pw = [points[i].reshape(-1, 3) for i in range(len(idxs))]
    cw = [rgb[i].reshape(-1, 3) for i in range(len(idxs))]
    pts, cols = fuse_pointmaps(pw, cw, cfg["engine"]["voxel_size"])
    _io.write_cloud(out / "cloud.ply", pts, cols)
    _io.write_runner_perf(out, per_window_latency_s=[wall], latency_end_to_end_s=wall)
    print(f"[pi3_runner] FULL-BATCH {len(idxs)} frames -> {len(poses)} poses, {len(pts)} pts, {wall:.1f}s")


if __name__ == "__main__":
    main()
