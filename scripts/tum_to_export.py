#!/usr/bin/env python
"""Convert a TUM RGB-D sequence into the benchmark's input layout (sanity check only).

  dataset/exports/tum/<name>/native/poses_gt.tum              (frame index timestamps)
  dataset/exports/tum/<name>/native/pinhole/synthetic_fov/{rgb/NNNNNN.png, intrinsics.json, meta.json}

Every RGB image becomes an input frame, in order. Ground truth is associated to each
image by nearest timestamp (<= 20 ms, as evo does) and written with the image's frame
index, so a runner's poses.tum (frame index) compares to it directly. Used by
scripts/sanity_tum.sh to run VGGT-SLAM through OUR runner on the data its paper uses.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

# TUM fr1 intrinsics (ROS default calibration). VGGT-SLAM does not use K; recorded for
# completeness.
FR1_K = {"fx": 517.3, "fy": 516.5, "cx": 318.6, "cy": 255.3, "width": 640, "height": 480}


def _read_list(p: Path):
    rows = []
    for ln in p.read_text().splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        rows.append(ln.split())
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", required=True, help="path to rgbd_dataset_freiburg1_xxx")
    ap.add_argument("--name", default="")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    seq = Path(a.seq)
    name = a.name or seq.name.replace("rgbd_dataset_freiburg", "fr")
    out = Path(a.root) / "dataset" / "exports" / "tum" / name / "native"
    vdir = out / "pinhole" / "synthetic_fov"
    if out.exists():
        shutil.rmtree(out)
    (vdir / "rgb").mkdir(parents=True)
    rgb = _read_list(seq / "rgb.txt")
    gt = np.array([[float(x) for x in r[:8]] for r in _read_list(seq / "groundtruth.txt")])
    lines = []
    for i, (ts, fn) in enumerate(rgb):
        shutil.copy2(seq / fn, vdir / "rgb" / f"{i:06d}.png")
        j = int(np.argmin(np.abs(gt[:, 0] - float(ts))))
        if abs(gt[j, 0] - float(ts)) <= 0.02:
            lines.append(" ".join([str(i)] + [f"{v:.6f}" for v in gt[j, 1:8]]))
    (out / "poses_gt.tum").write_text("\n".join(lines) + "\n")
    (vdir / "intrinsics.json").write_text(json.dumps({"projection": "pinhole", **FR1_K}, indent=2))
    (vdir / "meta.json").write_text(json.dumps({
        "dataset": "tum", "scene": name, "traj": "native", "camera_model": "pinhole",
        "variant": "synthetic_fov", "n_frames": len(rgb), "fps_nominal": 30.0,
        "camera_height_m": None}, indent=2))
    print(f"[tum] {seq.name}: {len(rgb)} frames, {len(lines)} with GT -> {out}")


if __name__ == "__main__":
    main()
