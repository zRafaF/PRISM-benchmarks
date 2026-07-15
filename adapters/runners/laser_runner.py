#!/usr/bin/env python
"""LASER runner — executed by submodules/LASER/.venv/bin/python.

LASER (neu-vi @ 7adbb7d) is a training-free STREAMING system: it wraps Pi3 in a
sliding-window engine with layer-wise Sim(3) scale alignment across windows. It's the
closest cousin to PRISM (both convert a frozen feed-forward model into a streamer),
so it's a key streaming baseline. Pinhole. Scale-free -> metric=false.

Drives the repo's own StreamingWindowEngine (as in demo.py):
  model.begin(); for w in windows: model(imgs); model.end()
  sd = model.parse_inference_cache_summary()  -> per-frame extrinsic(c2w), intrinsic, depth, images
We write TUM ourselves (LASER's own writer uses wxyz quats — wrong for evo; runner_io
uses xyzw), and unproject depth+intrinsic+extrinsic to a fused cloud.
Emits poses.tum, cloud.ply, perf_runner.json.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import sys

# make the LASER repo importable (pi3, inference_engine, utils.*) — cwd is the repo,
# but this script lives elsewhere, so add the repo root explicitly.
_LASER = Path(__file__).resolve().parents[2] / "submodules" / "LASER"
sys.path.insert(0, str(_LASER))
sys.path.insert(0, str(Path(__file__).parent))
import runner_io as _io
from _stream import fuse_pointmaps


def _unproject(depth, K, c2w, img):
    """depth (H,W), K (3,3), c2w (4,4), img (3,H,W) or (H,W,3) -> world pts (N,3), colors (N,3)."""
    H, W = depth.shape
    u, v = np.meshgrid(np.arange(W), np.arange(H))
    z = depth.reshape(-1)
    x = (u.reshape(-1) - K[0, 2]) / K[0, 0] * z
    y = (v.reshape(-1) - K[1, 2]) / K[1, 1] * z
    cam = np.stack([x, y, z], axis=1)
    world = (c2w[:3, :3] @ cam.T).T + c2w[:3, 3]
    if img.shape[0] == 3:               # (3,H,W) -> (H,W,3)
        img = np.transpose(img, (1, 2, 0))
    cols = img.reshape(-1, 3)
    valid = z > 0
    return world[valid], cols[valid]


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
    dtype = torch.bfloat16 if (device == "cuda" and torch.cuda.get_device_capability()[0] >= 8) else torch.float16

    from pi3.models.pi3 import Pi3
    from inference_engine import StreamingWindowEngine
    from utils.load_fn import load_and_preprocess_images

    model = StreamingWindowEngine(
        Pi3.from_pretrained("yyfz233/Pi3").to(device),
        inference_device=device, dtype=dtype,
        window_size=int(stream["window_size"]), overlap=int(stream["overlap"]),
        cache_root=str(out / "_laser_cache"), depth_refine=True, top_conf_percentile=0.3,
    )
    model.eval()

    rgb_dir = Path(args.in_dir) / "rgb"
    img_names = sorted(str(p) for p in rgb_dir.glob("*.png"))
    windows = model.img_sliding_window(img_names)

    t0 = time.perf_counter()
    model.begin()
    for sample in windows:
        imgs = load_and_preprocess_images(sample).to(device)
        model(imgs)
    model.end()
    wall = time.perf_counter() - t0

    sd = model.parse_inference_cache_summary()
    npy = lambda k: (sd[k].cpu().numpy().squeeze(0) if hasattr(sd[k], "cpu") else np.asarray(sd[k]).squeeze(0))
    extr = npy("extrinsic")                     # (S,3,4) or (S,4,4) cam->world
    intr = npy("intrinsic")                     # (S,3,3)
    depth = npy("depth")                        # (S,H,W,1) or (S,H,W)
    images = npy("images")                      # (S,3,H,W) in [0,1]
    S = len(extr)

    poses = np.tile(np.eye(4), (S, 1, 1))
    poses[:, :3, :] = extr[:, :3, :]            # c2w (pad 3x4 -> 4x4)
    _io.write_tum(out / "poses.tum", list(range(S)), poses)

    pw, cw = [], []
    for i in range(S):
        d = np.squeeze(depth[i])
        w, c = _unproject(d, intr[i], poses[i], images[i])
        pw.append(w); cw.append(c)
    pts, cols = fuse_pointmaps(pw, cw, cfg["engine"]["voxel_size"])
    _io.write_cloud(out / "cloud.ply", pts, cols)
    _io.write_runner_perf(out, per_window_latency_s=[], latency_end_to_end_s=wall)
    print(f"[laser_runner] {S} frames -> {len(poses)} poses, {len(pts)} pts, {wall:.1f}s")


if __name__ == "__main__":
    main()
