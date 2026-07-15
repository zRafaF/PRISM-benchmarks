#!/usr/bin/env python
"""Raw PanoVGGT runner — executed by submodules/PRISM-VGGT/.venv/bin/python.

Runs the panoramic VGGT backbone (the model PRISM wraps) FULL-BATCH on the pano
frames — no streaming engine, no Sim(3) guards, no nvblox TSDF, no metric grounding.
This is the 360° feed-forward *reference*: comparing it to PRISM shows exactly what
the streaming alignment + fusion engine contributes; comparing it to Pi3X/MapAnything
shows pano vs pinhole at the same (full-batch feed-forward) footing. Scale-free.

Uses the verified backend API (03_prism_vggt_code_architecture.md):
  backend.process_sequence(rgb_list) -> {poses:[4x4], points:[HxWx3 local], depths:[HxW]}
Global cloud = per-frame local points transformed by each frame's pose.
Emits poses.tum, cloud.ply, perf_runner.json.
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

    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())

    from prism_vggt import PanoVGGTBackend, download_weights
    repo_root = Path(__file__).resolve().parents[2]
    prism_dir = repo_root / "submodules" / "PRISM-VGGT"
    ckpt = Path(os.environ.get("PANOVGGT_WEIGHTS_PATH", str(prism_dir / "checkpoints" / "model.pt")))
    if not ckpt.exists():
        url = os.environ.get("PANOVGGT_WEIGHTS_URL")
        download_weights(str(ckpt), url=url) if url else download_weights(str(ckpt))
    config_path = prism_dir / "third_party" / "PanoVGGT" / "training" / "config" / "default.yaml"
    backend = PanoVGGTBackend(config_path=str(config_path), weights_path=str(ckpt))

    seq = _io.load_sequence(args.in_dir)
    rgb = seq["rgb"]
    n_total = len(rgb)
    cap = (cfg.get("baselines") or {}).get("max_frames")
    idxs = list(range(n_total))
    if cap and n_total > cap:
        idxs = np.linspace(0, n_total - 1, int(cap)).astype(int).tolist()
        print(f"[panovggt_runner] subsampled {n_total} -> {len(idxs)} (baselines.max_frames={cap})")

    t0 = time.perf_counter()
    res = backend.process_sequence([rgb[i] for i in idxs])   # FULL-BATCH: all frames, one pass
    wall = time.perf_counter() - t0

    poses = np.asarray(res["poses"])                          # (M,4,4) cam->world (VGGT frame)
    points = res["points"]                                    # list of (H,W,3) local per frame
    pw, cw = [], []
    for k, i in enumerate(idxs):
        P = poses[k]
        lp = np.asarray(points[k]).reshape(-1, 3)             # local points
        world = (P[:3, :3] @ lp.T).T + P[:3, 3]               # -> VGGT world frame
        pw.append(world)
        cw.append(np.asarray(rgb[i]).reshape(-1, 3))

    _io.write_tum(out / "poses.tum", list(idxs), poses)
    pts, cols = fuse_pointmaps(pw, cw, cfg["engine"]["voxel_size"])
    _io.write_cloud(out / "cloud.ply", pts, cols)
    _io.write_runner_perf(out, per_window_latency_s=[wall], latency_end_to_end_s=wall)
    print(f"[panovggt_runner] FULL-BATCH {len(idxs)} pano frames -> {len(poses)} poses, {len(pts)} pts, {wall:.1f}s")


if __name__ == "__main__":
    main()
