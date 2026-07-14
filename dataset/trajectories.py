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


def _interior_score(scene, point, max_range=30.0, n_dirs=24):
    """Fraction of rays cast from `point` that hit the mesh within max_range.

    An INTERIOR point (inside a room) hits geometry in essentially every
    direction -> score ~1.0. An EXTERIOR point (open space beyond the walls) sees
    the mesh only across a small solid angle -> low score. This distinguishes the
    two cases that unsigned distance-to-surface CANNOT (both look "far from a wall").
    """
    import open3d as o3d
    az = np.linspace(0, 2 * np.pi, n_dirs, endpoint=False)
    dirs = [(np.cos(a), np.sin(a), 0.0) for a in az]
    dirs += [(0, 0, 1), (0, 0, -1),
             (0.7, 0, 0.7), (-0.7, 0, 0.7), (0, 0.7, 0.7), (0, -0.7, 0.7)]
    dirs = np.array(dirs, dtype=np.float32)
    origins = np.tile(np.asarray(point, np.float32), (len(dirs), 1))
    rays = o3d.core.Tensor(np.concatenate([origins, dirs], axis=1))
    t_hit = scene.cast_rays(rays)["t_hit"].numpy()
    return float(np.mean(np.isfinite(t_hit) & (t_hit <= max_range)))


def ground_hit_z(scene, x: float, y: float, z_top: float):
    """Cast a ray straight DOWN from (x,y,z_top); return the world-Z of the first
    surface hit (the floor/furniture directly below), or None if nothing is hit."""
    import open3d as o3d
    ray = o3d.core.Tensor([[x, y, z_top, 0.0, 0.0, -1.0]], dtype=o3d.core.float32)
    t = scene.cast_rays(ray)["t_hit"].numpy()[0]
    return None if not np.isfinite(t) else float(z_top - t)


def clean_floor_patch(scene, x: float, y: float, z_top: float, floor_z: float,
                      radius: float = 0.4, n_ring: int = 12, tol: float = 0.06):
    """Probe a CYLINDER of downward rays (centre + a ring of radius `radius`).

    Returns (frac_on_floor, median_ground_z). A clean, flat floor patch — needed for
    PRISM's RANSAC floor fit — has ~all rays hitting near floor_z at a consistent
    height. A single ray can land on a sofa or a stray vertex; the disk is robust.
    """
    import open3d as o3d
    pts = [(x, y)]
    for a in np.linspace(0, 2 * np.pi, n_ring, endpoint=False):
        pts.append((x + radius * np.cos(a), y + radius * np.sin(a)))
    rays = np.array([[px, py, z_top, 0.0, 0.0, -1.0] for px, py in pts], dtype=np.float32)
    t = scene.cast_rays(o3d.core.Tensor(rays))["t_hit"].numpy()
    ground = z_top - t
    ok = np.isfinite(t) & (np.abs(ground - floor_z) <= tol)
    med = float(np.median(ground[ok])) if ok.any() else None
    return float(ok.mean()), med


def free_space_waypoints(mesh, n_waypoints: int, min_clearance_m: float, seed: int,
                         probe_z: float | None = None, floor_z: float | None = None,
                         ground_tol_m: float = 0.12, debug: bool = True) -> np.ndarray:
    """Sample n collision-free INTERIOR waypoints that sit OVER BARE FLOOR.

    A point is kept only if it is (a) >= min_clearance from any surface, (b) interior
    (most rays hit the mesh), AND (c) over bare floor — a ray cast straight down hits
    a surface within `ground_tol_m` of the global floor_z (i.e. NOT over furniture).
    (c) matters because PRISM's metric scale comes from a RANSAC floor fit under the
    camera; starting over a sofa gives the wrong camera-to-floor height (scale error).
    """
    import open3d as o3d  # local import: renderer env only

    rng = np.random.default_rng(seed)
    aabb = mesh.get_axis_aligned_bounding_box()
    lo = aabb.get_min_bound()
    hi = aabb.get_max_bound()
    z = probe_z if probe_z is not None else (lo[2] + hi[2]) / 2
    fz = floor_z if floor_z is not None else float(lo[2])
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))

    if debug:
        print(f"[waypoints] AABB lo={np.round(lo,2)} hi={np.round(hi,2)} "
              f"probe_z={z:.2f} floor_z={fz:.2f} ground_tol={ground_tol_m}")

    kept, tries, shown = [], 0, 0
    while len(kept) < n_waypoints and tries < n_waypoints * 800:
        tries += 1
        xy = rng.uniform(lo[:2], hi[:2])
        pt = np.array([xy[0], xy[1], z], dtype=np.float32)
        dist = scene.compute_distance(o3d.core.Tensor(pt[None])).numpy()[0]
        score = _interior_score(scene, pt)
        floor_frac, gz = clean_floor_patch(scene, xy[0], xy[1], z, fz, tol=ground_tol_m)
        clean_floor = floor_frac >= 0.85            # nearly the whole disk is bare floor
        ok = dist >= min_clearance_m and score >= 0.8 and clean_floor
        if debug and shown < 14:
            gzs = f"{gz:.2f}" if gz is not None else "none"
            print(f"[waypoints] cand xy={np.round(xy,2)} clearance={dist:.2f} "
                  f"interior={score:.2f} floor_frac={floor_frac:.2f} ground_z={gzs} "
                  f"-> {'KEEP' if ok else 'reject'}")
            shown += 1
        if ok:
            kept.append((xy, floor_frac))
    if debug:
        print(f"[waypoints] kept {len(kept)}/{n_waypoints} after {tries} tries")
    if len(kept) < 4:
        raise RuntimeError(
            f"free-space-over-floor sampling failed (kept {len(kept)} in {tries} tries). "
            f"Loosen ground_tol_m/min_clearance, or check the [mesh] floor_z. Debug above.")
    # Start at the cleanest-floor point (so PRISM locks metric scale over bare floor),
    # then visit the rest as a nearest-neighbour tour -> a SMOOTH walkthrough instead
    # of a spatial zig-zag (a scrambled order inflates drift and wrecks the recon).
    kept.sort(key=lambda kf: -kf[1])
    start = kept[0][0]
    remaining = [xy for xy, _ in kept[1:]]
    order, cur = [start], start
    while remaining:
        j = int(np.argmin([np.linalg.norm(cur - r) for r in remaining]))
        cur = remaining.pop(j)
        order.append(cur)
    if debug:
        print(f"[waypoints] tour order (NN from cleanest floor): "
              f"{[np.round(p, 2).tolist() for p in order]}")
    return np.array(order)
