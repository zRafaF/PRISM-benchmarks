"""Shared streaming helpers for windowed baselines (runs in each method's env).

Non-streaming feed-forward methods (Pi3, MapAnything) are driven windowed and
chained through shared overlap frames with a Sim(3) Umeyama anchor — the SAME
fairness PRISM's own alignment gets. Depends only on numpy (+ open3d for fusion).
"""
from __future__ import annotations

import numpy as np


def sliding_windows(n_frames: int, window: int, overlap: int):
    step = max(1, window - overlap)
    starts = list(range(0, max(1, n_frames - overlap), step))
    return [list(range(s, min(s + window, n_frames))) for s in starts]


def umeyama_sim3(src: np.ndarray, tgt: np.ndarray):
    """Closed-form Sim(3) (s,R,t) mapping src->tgt point sets (both (N,3))."""
    mu_s, mu_t = src.mean(0), tgt.mean(0)
    s_c, t_c = src - mu_s, tgt - mu_t
    cov = t_c.T @ s_c / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    R = U @ S @ Vt
    var_s = (s_c ** 2).sum() / len(src)
    scale = np.trace(np.diag(D) @ S) / var_s if var_s > 1e-12 else 1.0
    t = mu_t - scale * R @ mu_s
    return scale, R, t


def chain_windows_sim3(win_results, seq, overlap: int):
    """Align each window into a single world frame via its overlap with the prev
    window's already-placed camera centres. Returns (global_poses[N,4,4],
    points_world (list per frame of (M,3)), colors (list per frame or None)).
    """
    global_poses = {}
    points_world = {}
    colors = {}
    world_from_win = np.eye(4)
    world_scale = 1.0
    prev_frames = None  # dict frame_idx -> world position

    for wi, (frame_ids, poses, points) in enumerate(win_results):
        poses = np.asarray(poses)
        if wi == 0:
            s, R, t = 1.0, np.eye(3), np.zeros(3)
        else:
            shared = [f for f in frame_ids if f in (prev_frames or {})]
            if len(shared) >= 3:
                local_idx = [frame_ids.index(f) for f in shared]
                src = poses[local_idx, :3, 3]
                tgt = np.array([prev_frames[f] for f in shared])
                s, R, t = umeyama_sim3(src, tgt)
            else:
                s, R, t = world_scale, world_from_win[:3, :3], world_from_win[:3, 3]

        cur_frames = {}
        for li, f in enumerate(frame_ids):
            Tl = poses[li]
            pos_w = s * R @ Tl[:3, 3] + t
            Rw = R @ Tl[:3, :3]
            Tw = np.eye(4); Tw[:3, :3] = Rw; Tw[:3, 3] = pos_w
            global_poses[f] = Tw
            cur_frames[f] = pos_w
            if points is not None:
                p = np.asarray(points[li]).reshape(-1, 3)
                points_world[f] = (s * (R @ p.T).T + t)
                colors[f] = np.asarray(seq["rgb"][f]).reshape(-1, 3)
        prev_frames = cur_frames
        world_from_win = np.eye(4); world_from_win[:3, :3] = R; world_from_win[:3, 3] = t
        world_scale = s

    order = sorted(global_poses)
    poses_arr = np.stack([global_poses[f] for f in order])
    pw = [points_world.get(f) for f in order if f in points_world]
    cw = [colors.get(f) for f in order if f in colors]
    return poses_arr, pw, (cw if cw else None)


def fuse_pointmaps(points_world, colors, voxel_size: float):
    """Concatenate per-frame world pointmaps + voxel-downsample. numpy-only (no open3d):
    hash each point to a voxel cell and keep one point per cell."""
    if not points_world:
        return np.zeros((0, 3)), None
    pts = np.concatenate([p for p in points_world if p is not None], axis=0)
    cols = None
    if colors and any(c is not None for c in colors):
        cols = np.concatenate([c for c in colors if c is not None], axis=0)
    finite = np.isfinite(pts).all(axis=1)      # drop masked/NaN points (feed-forward masks)
    pts = pts[finite]
    cols = cols[finite] if cols is not None else None
    if len(pts) == 0:
        return np.zeros((0, 3)), None
    keys = np.floor(pts / voxel_size).astype(np.int64)
    h = (keys[:, 0] * 73856093) ^ (keys[:, 1] * 19349663) ^ (keys[:, 2] * 83492791)
    _, idx = np.unique(h, return_index=True)   # one point per occupied voxel
    pts = pts[idx]
    cols = cols[idx] if cols is not None else None
    return pts, cols
