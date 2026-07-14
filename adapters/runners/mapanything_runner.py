#!/usr/bin/env python
"""MapAnything runner — executed by submodules/map-anything/.venv/bin/python.

MapAnything (facebookresearch/map-anything @ c845b8f) is a universal FEED-FORWARD
METRIC 3D model: it ingests the whole set of views in one pass (memory-efficient up to
~2000 views) and returns metric geometry. Like Pi3 it is NOT a streamer, so we run it
FULL-BATCH over all frames. Metric -> appears in the metric-scale table.

API (pinned commit README):
  from mapanything.models import MapAnything
  from mapanything.utils.image import load_images
  model = MapAnything.from_pretrained("facebook/map-anything").to(device)
  views = load_images("<rgb_dir>")
  preds = model.infer(views, memory_efficient_inference=True, use_amp=True, amp_dtype="bf16")
  preds[i]["pts3d"] (1,H,W,3) world ; preds[i]["camera_poses"] (1,4,4) OpenCV cam2world
  preds[i]["img_no_norm"] (1,H,W,3) denormalised RGB

Emits the common outputs: poses.tum, cloud.ply, perf_runner.json.
"""
from __future__ import annotations

import argparse
import os
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

    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    import torch
    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())
    device = "cuda" if torch.cuda.is_available() else "cpu"

    from mapanything.models import MapAnything
    from mapanything.utils.image import load_images

    model = MapAnything.from_pretrained("facebook/map-anything").to(device)

    views = load_images(str(Path(args.in_dir) / "rgb"))      # list of N view dicts
    n_total = len(views)
    cap = (cfg.get("baselines") or {}).get("max_frames")
    idxs = list(range(n_total))
    if cap and n_total > cap:
        idxs = np.linspace(0, n_total - 1, int(cap)).astype(int).tolist()
        views = [views[i] for i in idxs]
        print(f"[mapanything_runner] subsampled {n_total} -> {len(idxs)} (baselines.max_frames={cap})")

    t0 = time.perf_counter()
    with torch.no_grad():
        preds = model.infer(views, memory_efficient_inference=True, use_amp=True,
                            amp_dtype="bf16", apply_mask=True, mask_edges=True)
    wall = time.perf_counter() - t0

    poses = np.stack([np.asarray(p["camera_poses"][0].float().cpu().numpy()) for p in preds])  # (M,4,4)
    _io.write_tum(out / "poses.tum", idxs, poses)
    pw = [np.asarray(p["pts3d"][0].float().cpu().numpy()).reshape(-1, 3) for p in preds]
    cw = [np.asarray(p["img_no_norm"][0].cpu().numpy()).reshape(-1, 3) for p in preds]
    pts, cols = fuse_pointmaps(pw, cw, cfg["engine"]["voxel_size"])
    _io.write_cloud(out / "cloud.ply", pts, cols)
    _io.write_runner_perf(out, per_window_latency_s=[wall], latency_end_to_end_s=wall)
    print(f"[mapanything_runner] FULL-BATCH {len(idxs)} frames -> {len(poses)} poses, {len(pts)} pts, {wall:.1f}s")


if __name__ == "__main__":
    main()
