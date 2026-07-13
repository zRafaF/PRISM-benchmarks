"""Co-visibility masking — the fairness core (shared by every recon eval).

Pano sees 360deg; pinhole baselines see a frustum. Restrict every cloud (ours,
each baseline, and the GT) to the SHARED observed volume so any remaining metric
gap is method quality, not coverage.

Two modes (config.eval.mask.mode):
  containment : keep points inside the UNION of bounded pinhole view frustums.
  rigorous    : + per-frame GT-depth occlusion test (point observed only if it
                projects into some pinhole frame AND range <= GT depth + tol).

Runs in the ORCHESTRATOR env (numpy only). Reads the shared pinhole GT poses +
intrinsics + GT depth from dataset/exports/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _load_tum_poses(path: Path):
    from scipy.spatial.transform import Rotation
    ts, poses = [], []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        v = [float(x) for x in line.split()]
        T = np.eye(4)
        T[:3, :3] = Rotation.from_quat(v[4:8]).as_matrix()
        T[:3, 3] = v[1:4]
        ts.append(v[0]); poses.append(T)
    return np.array(ts), np.array(poses)


def _project(points_w, T_wc, K, width, height):
    """Return (uv[N,2], z[N]) in a pinhole camera. z>0 in front."""
    T_cw = np.linalg.inv(T_wc)
    pc = (T_cw[:3, :3] @ points_w.T).T + T_cw[:3, 3]
    z = pc[:, 2]
    uv = (K @ (pc / np.where(z[:, None] == 0, 1e-9, z[:, None])).T).T[:, :2]
    return uv, z


def build_mask(points_w: np.ndarray, pinhole_export_dir: Path, cfg: dict) -> np.ndarray:
    """Boolean keep-mask over points_w using the pinhole trajectory in the export dir."""
    intr = json.loads((pinhole_export_dir / "intrinsics.json").read_text())
    K = np.array([[intr["fx"], 0, intr["cx"]], [0, intr["fy"], intr["cy"]], [0, 0, 1]])
    W, H = intr["width"], intr["height"]
    far = cfg["eval"]["mask"]["frustum_far_m"]
    tol = cfg["eval"]["mask"]["occlusion_tol_m"]
    rigorous = cfg["eval"]["mask"]["mode"] == "rigorous"

    gt_poses_path = pinhole_export_dir.parent.parent / "poses_gt.tum"
    _, poses = _load_tum_poses(gt_poses_path)

    keep = np.zeros(len(points_w), dtype=bool)
    depth_dir = pinhole_export_dir / "depth"
    names = sorted(p.stem for p in (pinhole_export_dir / "rgb").glob("*.png"))

    for i, T in enumerate(poses):
        uv, z = _project(points_w, T, K, W, H)
        in_img = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
        in_range = (z > 0) & (z <= far)
        vis = in_img & in_range
        if rigorous and i < len(names):
            dp = depth_dir / f"{names[i]}.npy"
            if dp.exists():
                gt_depth = np.load(dp)
                u = np.clip(uv[:, 0].astype(int), 0, W - 1)
                v = np.clip(uv[:, 1].astype(int), 0, H - 1)
                gd = gt_depth[v, u]
                not_occluded = z <= (gd + tol)
                vis = vis & (gd > 0) & not_occluded
        keep |= vis
    return keep


def apply_mask(points_w: np.ndarray, keep: np.ndarray, *arrays):
    out = [points_w[keep]]
    for a in arrays:
        out.append(a[keep] if a is not None else None)
    return tuple(out)
