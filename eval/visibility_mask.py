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


# -- depth I/O ---------------------------------------------------------------
# Depth is stored as 16-bit PNG in MILLIMETRES, not float32 .npy. Depth was 78% of
# all export bytes (2.15 MB/frame for the pano alone) purely because .npy is
# uncompressed. 16-bit PNG is ~88% smaller, gives exactly 1 mm precision over a 65 m
# range (against a 4.5 m max_depth and a 20 mm voxel, so precision is nowhere near
# the binding constraint), and is what TUM / ScanNet / Replica all use. Readers stay
# backward compatible with existing .npy exports so old renders keep working.
DEPTH_SCALE = 1000.0          # metres -> millimetres


def load_depth(dir_, name):
    """Depth for frame `name` from <dir_>/depth/: .png (mm) or legacy .npy (m)."""
    import numpy as _np
    from pathlib import Path as _P
    d = _P(dir_) / "depth"
    p = d / f"{name}.png"
    if p.exists():
        import imageio.v2 as _imageio
        return _imageio.imread(p).astype(_np.float32) / DEPTH_SCALE
    p = d / f"{name}.npy"
    if p.exists():
        return _np.load(p).astype(_np.float32)
    return None



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
            gt_depth = load_depth(pinhole_export_dir, names[i])
            if gt_depth is not None:
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
