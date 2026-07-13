"""Trajectory generation — the two variants both benchmarks render from.

Variant A  `dataset_path`     : resample the dataset's own camera path.
Variant B  `synthetic_spline` : a smooth, collision-free walkthrough through free
                                 space (robot-like), sampled against the mesh.

Both return a list of 4x4 camera-to-world poses (world Z-up, OpenCV camera frame)
plus timestamps. The renderer feeds these IDENTICAL poses to both camera models.
"""
from __future__ import annotations

import numpy as np


def _look_at(eye: np.ndarray, target: np.ndarray, up=(0, 0, 1)) -> np.ndarray:
    """Camera-to-world pose looking from eye toward target (OpenCV: +Z forward, Y-down)."""
    up = np.asarray(up, dtype=np.float64)
    fwd = target - eye
    n = np.linalg.norm(fwd)
    fwd = fwd / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])
    right = np.cross(fwd, up)
    rn = np.linalg.norm(right)
    right = right / rn if rn > 1e-9 else np.array([1.0, 0.0, 0.0])
    down = np.cross(fwd, right)
    R = np.stack([right, down, fwd], axis=1)   # columns = camera axes in world
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = eye
    return T


def resample_path(poses: np.ndarray, n_frames: int) -> np.ndarray:
    """Variant A: uniformly resample an existing (M,4,4) pose array to n_frames."""
    m = len(poses)
    if m == 0:
        raise ValueError("empty source trajectory")
    idx = np.linspace(0, m - 1, n_frames)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, m - 1)
    frac = idx - lo
    out = np.empty((n_frames, 4, 4))
    for k, (a, b, f) in enumerate(zip(lo, hi, frac)):
        out[k] = poses[a].copy()
        out[k][:3, 3] = (1 - f) * poses[a][:3, 3] + f * poses[b][:3, 3]  # lerp position
        # (orientation: nearest-neighbour; good enough for a resample. SLERP = TODO.)
        out[k][:3, :3] = poses[a][:3, :3] if f < 0.5 else poses[b][:3, :3]
    return out


def synthetic_spline(waypoints: np.ndarray, n_frames: int, camera_height: float = 1.7) -> np.ndarray:
    """Variant B: Catmull-Rom spline through free-space waypoints (N>=4, world XY).

    `waypoints` are (K,2) floor positions chosen by the caller to be collision-free
    (see free_space_waypoints). Camera height is fixed; each pose looks along the
    path tangent. Returns (n_frames,4,4) camera-to-world poses.
    """
    wp = np.asarray(waypoints, dtype=np.float64)
    if len(wp) < 4:
        raise ValueError("need >= 4 waypoints for Catmull-Rom")
    xy = _catmull_rom(wp, n_frames)
    z = np.full(len(xy), camera_height)
    eyes = np.column_stack([xy, z])
    poses = np.empty((len(eyes), 4, 4))
    for i in range(len(eyes)):
        nxt = eyes[min(i + 1, len(eyes) - 1)]
        tgt = nxt if not np.allclose(nxt, eyes[i]) else eyes[i] + np.array([1.0, 0, 0])
        poses[i] = _look_at(eyes[i], tgt)
    return poses


def _catmull_rom(pts: np.ndarray, n: int) -> np.ndarray:
    segs = len(pts) - 1
    per = max(2, n // segs)
    out = []
    for i in range(segs):
        p0 = pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        t = np.linspace(0, 1, per, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t
                          + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t**2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t**3))
    arr = np.vstack(out)
    idx = np.linspace(0, len(arr) - 1, n).astype(int)
    return arr[idx]


def free_space_waypoints(mesh, n_waypoints: int, min_clearance_m: float, seed: int) -> np.ndarray:
    """Sample n collision-free floor waypoints from a mesh's XY bounds.

    Cheap approach: rejection-sample XY inside the mesh bounding box at the floor
    level, keep points whose nearest mesh surface is >= min_clearance. Replaced by
    a proper occupancy/ESDF sampler if the naive version places points in walls.
    (See docs/decisions.md D5 — open for refinement.)
    """
    import open3d as o3d  # local import: renderer env only

    rng = np.random.default_rng(seed)
    aabb = mesh.get_axis_aligned_bounding_box()
    lo = aabb.get_min_bound()
    hi = aabb.get_max_bound()
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))

    kept = []
    tries = 0
    while len(kept) < n_waypoints and tries < n_waypoints * 200:
        tries += 1
        xy = rng.uniform(lo[:2], hi[:2])
        probe = np.array([[xy[0], xy[1], (lo[2] + hi[2]) / 2]], dtype=np.float32)
        dist = scene.compute_distance(o3d.core.Tensor(probe)).numpy()[0]
        if dist >= min_clearance_m:
            kept.append(xy)
    if len(kept) < 4:
        raise RuntimeError("free-space sampling failed; loosen min_clearance or use dataset_path")
    return np.array(kept)
