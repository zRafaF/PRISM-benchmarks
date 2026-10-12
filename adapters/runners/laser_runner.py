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
import shutil
import json
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

    # LASER_WINDOW / LASER_OVERLAP: per-arm override (run_env). LASER's own evaluation
    # (eval_launch.py @ the pinned commit) uses window 20 / overlap 5; the harness
    # default is the shared streaming window (16/4).
    import os as _os
    laser_ws = int(_os.environ.get("LASER_WINDOW", stream["window_size"]))
    laser_ov = int(_os.environ.get("LASER_OVERLAP", stream["overlap"]))
    # LASER_CACHE_ROOT: put the per-window inference cache on another disk (it grows to
    # tens of GB on long cube-face runs). Deleted when the run ends.
    cache_dir = (Path(_os.environ["LASER_CACHE_ROOT"]) / f"laser_{_os.getpid()}"
                 if _os.environ.get("LASER_CACHE_ROOT") else out / "_laser_cache")
    print(f"[laser_runner] window={laser_ws} overlap={laser_ov}")
    from pi3.models.pi3 import Pi3
    from inference_engine import StreamingWindowEngine
    from utils.load_fn import load_and_preprocess_images

    model = StreamingWindowEngine(
        Pi3.from_pretrained("yyfz233/Pi3").to(device),
        inference_device=device, dtype=dtype,
        window_size=laser_ws, overlap=laser_ov,
        cache_root=str(cache_dir), depth_refine=True, top_conf_percentile=0.3,
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

    # Read LASER's per-window cache ONE WINDOW AT A TIME. Its own
    # parse_inference_cache_summary() concatenates every window (local points, colours,
    # homogenised world points) into single tensors: 2,324 cube-face images on the real
    # atrium sequence exceeded 123 GB of host RAM (rc -9). This loop applies exactly the
    # same steps per window — parse_cache_file's overlap slicing (first window kept
    # whole), _post_process_pred's per-frame depth/intrinsics (estimate_pseudo_depth_and_
    # intrinsics is independent per frame), extrinsic = camera_poses — so the poses and
    # the fused cloud are identical, in bounded memory.
    import glob as _glob
    from inference_engine.inference_utils import estimate_pseudo_depth_and_intrinsics
    tdir = Path(model.temp_cache_dir)
    files = sorted(_glob.glob(str(tdir / "window_cache_*.pt")),
                   key=lambda q: int(q.rsplit("_", 1)[-1].split(".")[0]))
    vox = cfg["engine"]["voxel_size"]
    pts, cols = np.zeros((0, 3), np.float32), None
    pose_list = []
    import os as _os
    _save_depth = _os.environ.get("LASER_SAVE_DEPTH", "0") == "1"
    _dd = out / "_depth"
    if _save_depth:
        _dd.mkdir(parents=True, exist_ok=True)
    for wi, fname in enumerate(files):
        wc = model.parse_cache_file(fname, overlap=0 if wi == 0 else model.overlap)
        f32 = lambda t: t.detach().float().cpu() if hasattr(t, "detach") else torch.as_tensor(np.asarray(t)).float()
        lp = f32(wc["local_points"])
        if lp.dim() == 5:
            lp = lp.squeeze(0)
        if "depth" in wc and "intrinsic" in wc:
            dep, K = f32(wc["depth"]), f32(wc["intrinsic"])
        else:
            dep, K = estimate_pseudo_depth_and_intrinsics(lp)
        cp = f32(wc["camera_poses"]).numpy().reshape(-1, *wc["camera_poses"].shape[-2:])
        im = f32(wc["images"]).numpy()
        if im.ndim == 5:
            im = im[0]
        dep = dep.numpy()
        if dep.ndim == 5 or (dep.ndim == 4 and dep.shape[0] == 1 and len(cp) > 1):
            dep = dep[0]
        if dep.ndim == 4 and dep.shape[-1] == 1:
            dep = dep[..., 0]
        K = K.numpy().reshape(-1, 3, 3)
        assert len(dep) == len(cp) == len(K) == len(im), (dep.shape, cp.shape, K.shape, im.shape)
        pw, cw = [], []
        for i in range(len(cp)):
            T = np.eye(4); T[:3, :] = cp[i][:3, :]
            pose_list.append(T)
            w, c = _unproject(np.squeeze(dep[i]), K[i], T, im[i])
            if _save_depth:
                # LASER_SAVE_DEPTH=1: keep per-frame depth for eval/fuse_tsdf.py (the
                # same-back-end control: LASER's depth fused by a TSDF like PRISM's).
                _im = np.transpose(im[i], (1, 2, 0)) if im[i].shape[0] == 3 else im[i]
                _im = np.clip(_im * (255.0 if _im.max() <= 1.0 else 1.0), 0, 255).astype(np.uint8)
                np.savez_compressed(_dd / f"f{len(pose_list) - 1:05d}.npz",
                                    depth=np.squeeze(dep[i]).astype(np.float16), K=K[i].astype(np.float32),
                                    c2w=T.astype(np.float32), rgb=_im)
            pw.append(w.astype(np.float32)); cw.append(c.astype(np.float32))
        p_, c_ = fuse_pointmaps(pw, cw, vox)
        del pw, cw, wc, lp, im, dep
        if cols is None:
            pts, cols = p_, c_
        else:
            pts, cols = fuse_pointmaps([pts, p_], [cols, c_], vox)
    poses = np.stack(pose_list)
    S = len(poses)
    _io.write_tum(out / "poses.tum", list(range(S)), poses)
    shutil.rmtree(tdir, ignore_errors=True)
    _io.write_cloud(out / "cloud.ply", pts, cols)
    cube = _io.collapse_cube_faces(Path(args.in_dir), out)     # D28: per-timestep poses
    (out / "arm_config.json").write_text(json.dumps(
        {"window_size": laser_ws, "overlap": laser_ov, **(cube or {})}, indent=2))
    _io.write_runner_perf(out, per_window_latency_s=[], latency_end_to_end_s=wall)
    # LASER's per-window inference cache (depth/images of every window) is only needed
    # to build the outputs above; left in the run dir it filled the pod disk on the
    # cube-face runs (2,324 images) and went into the results pack.
    shutil.rmtree(cache_dir, ignore_errors=True)
    print(f"[laser_runner] {S} frames -> {len(poses)} poses, {len(pts)} pts, {wall:.1f}s")


if __name__ == "__main__":
    main()
