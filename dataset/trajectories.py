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


def rate_limited_yaw(eyes: np.ndarray, rate_hz: float,
                     max_yaw_rate_dps: float | None, lookahead: int = 1) -> np.ndarray:
    """Per-frame camera yaw (radians, world Z-up) that follows the direction of travel
    but never turns faster than ``max_yaw_rate_dps``.

    WHY. The original trajectories pointed each camera at the NEXT position, so the
    yaw followed the spline tangent instantly. On the 2026-08 renders 3-7% of the
    2 Hz steps turned more than 45 deg in a single frame, some close to 180 deg (cusps
    of the Catmull-Rom spline and lap junctions). A 360 deg panorama is unaffected — a
    yaw is a column shift of the equirect — but a 90 deg pinhole camera loses ALL
    overlap with the previous frame, so the benchmark was biased against every
    pinhole baseline (VGGT-SLAM, LASER, Pi3, MapAnything). A real robot or person
    turns at a finite rate.

    HOW. Desired yaw = direction to the next position (the last frame keeps the
    previous heading instead of snapping to +X, the old fallback). The yaw is then
    rate-limited with a forward and a backward pass, so the camera starts turning
    BEFORE a sharp corner and finishes after it, and no frame-to-frame step exceeds
    ``max_yaw_rate_dps / rate_hz``. The limit is in deg/s, so the same physical turn
    is produced at every capture rate. ``None``/<=0 disables limiting (old headings,
    minus the last-frame snap).

    ``lookahead`` (frames, default 1 = the original behaviour) aims each frame at the
    position ``lookahead`` frames ahead instead of the next one. The grid planner uses
    ~0.5 m of look-ahead so the heading anticipates a corner instead of reacting to it.
    """
    n = len(eyes)
    if n == 0:
        return np.zeros(0)
    d = np.zeros((n, 2))
    if n > 1:
        k = max(1, int(lookahead))
        ahead = np.minimum(np.arange(n) + k, n - 1)
        d = eyes[ahead, :2] - eyes[:, :2]
        d[-1] = d[-2]
    yaw = np.full(n, np.nan)
    for i in range(n):
        if np.linalg.norm(d[i]) > 1e-9:
            yaw[i] = np.arctan2(d[i, 1], d[i, 0])
    # Stationary frames (clamped tail, dwell) inherit the last valid heading.
    valid = np.where(np.isfinite(yaw))[0]
    if len(valid) == 0:
        return np.zeros(n)
    yaw[:valid[0]] = yaw[valid[0]]
    for i in range(1, n):
        if not np.isfinite(yaw[i]):
            yaw[i] = yaw[i - 1]
    yaw = np.unwrap(yaw)
    if not max_yaw_rate_dps or max_yaw_rate_dps <= 0:
        return yaw
    m = np.radians(float(max_yaw_rate_dps)) / max(float(rate_hz), 1e-6)
    fwd = yaw.copy()
    for i in range(1, n):
        fwd[i] = fwd[i - 1] + np.clip(yaw[i] - fwd[i - 1], -m, m)
    out = fwd.copy()
    for i in range(n - 2, -1, -1):
        out[i] = out[i + 1] + np.clip(fwd[i] - out[i + 1], -m, m)
    return out


def poses_from_yaw(eyes: np.ndarray, yaw: np.ndarray) -> np.ndarray:
    """Level camera-to-world poses (OpenCV camera, world Z-up) looking along ``yaw``."""
    poses = np.empty((len(eyes), 4, 4))
    for i in range(len(eyes)):
        tgt = eyes[i] + np.array([np.cos(yaw[i]), np.sin(yaw[i]), 0.0])
        poses[i] = _look_at(eyes[i], tgt)
    return poses


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


def synthetic_spline(waypoints: np.ndarray, camera_height: float = 1.7,
                     speed_mps: float = 0.5, rate_hz: float = 2.0,
                     max_frames: int = 1000, close_loop: bool = False,
                     path_target_m: float | None = None,
                     target_frames: int | None = None, max_laps: int = 12,
                     min_speed_mps: float = 0.15,
                     min_frames: int = 32,
                     max_yaw_rate_dps: float | None = 45.0) -> np.ndarray:
    """Variant B: constant-velocity walkthrough on a Catmull-Rom spline.

    Frames are sampled by ARC LENGTH at spacing = speed/rate, so they simulate a capture
    at `rate_hz` while moving at `speed_mps` — the real Theta-X operating point. The
    inter-frame baseline is therefore physical and identical for every method (they all
    consume these same frames). Returns (n,4,4) c2w poses.

    THE PATH IS THE INVARIANT, NOT THE FRAME COUNT
    ----------------------------------------------
    ``path_target_m`` fixes the physical distance walked, and the frame count follows
    from the rate: 74.75 m gives 300 frames at 2 Hz and 748 at 5 Hz. That is what
    "capture rate" actually means — one motion, sampled more or less often — and it is
    the only definition under which a rate comparison isolates the rate.

    The alternative (fix the frame count, let the path follow) was tried first and is
    unusable. Holding 300 frames at a fixed baseline forces path_len = 299 x baseline,
    so 2 Hz walks 75 m while 5 Hz walks 30 m of the same circuit. In the 2026-08-10
    pre-flight apartment_0 seed 5678 came out as 118 m / 3 laps at 2 Hz against 34 m /
    1 lap at 5 Hz, and its extent fell from 12.99 m to 11.65 m because the 5 Hz walk
    never finished the circuit. Three things then varied with "rate" at once: path length
    (2.5x more accumulated drift at 2 Hz), how much of the room was ever observed (so
    reconstruction completeness was penalised at 5 Hz), and how many revisits a
    loop-closure method got. None of those is the rate.

    ``target_frames`` keeps the older frame-count-driven behaviour for callers that want
    it (the stop-and-go family, whose dwell budget is defined in frames). When it is used
    instead of ``path_target_m``, the path is lengthened by laps first and only then by
    slowing the walk, because slowing changes the baseline — see the warning below.

    ``close_loop=True`` appends the first waypoints to the end so the path returns to
    (and re-observes) its start — the loop-closure stress test: streaming methods with
    no loop closure (PRISM/LASER) reveal uncorrected drift, while VGGT-SLAM's loop
    closure can fire. The revisit is what makes SL(4) projective drift visible.
    """
    wp0 = np.asarray(waypoints, dtype=np.float64)
    if len(wp0) < 4:
        raise ValueError("need >= 4 waypoints for Catmull-Rom")

    def _polyline(wp):
        dense = _catmull_rom(wp, 4000)
        seg = np.linalg.norm(np.diff(dense, axis=0), axis=1)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        return dense, cum, float(cum[-1])

    wp = np.concatenate([wp0, wp0[:2]], axis=0) if close_loop else wp0
    dense, cum, total_len = _polyline(wp)

    spacing = max(speed_mps / max(rate_hz, 1e-6), 1e-3)
    laps, eff_speed = 1, float(speed_mps)
    path_mode = path_target_m is not None

    if path_mode:
        need_len = float(path_target_m)
        target = None
    else:
        target = min(int(target_frames or max_frames), int(max_frames))
        need_len = (target - 1) * spacing

    # Lever 1 (a longer circuit) lives in free_space_waypoints. Lever 2: laps.
    if total_len < need_len:
        laps = min(int(max_laps), int(np.ceil(need_len / max(total_len, 1e-6))))
        if laps > 1:
            wp = np.concatenate([wp0] * laps + ([wp0[:2]] if close_loop else []), axis=0)
            dense, cum, total_len = _polyline(wp)
        # Lever 3 — slow down. ONLY in frame-count mode: in path mode the walking speed
        # is part of what is being held constant, so a scene that cannot reach the target
        # path simply walks a shorter one (equally, at every rate) and says so. Also
        # skipped for a shortfall under 1%, which used to emit "speed 0.5->0.50 m/s"
        # warnings whose baseline was unchanged — noise that trains you to ignore the one
        # warning that matters.
        if not path_mode and total_len < need_len * 0.99:
            eff_speed = max(min_speed_mps, total_len * rate_hz / max(target - 1, 1))
            spacing = max(eff_speed / max(rate_hz, 1e-6), 1e-3)

    # Walk exactly need_len when the path affords it, so EVERY rate traverses the same
    # distance over the same geometry.
    walk_len = min(total_len, need_len)
    n = int(walk_len / spacing) + 1
    if target is not None:
        n = min(n, target)
    n = min(n, int(max_frames))
    if n < min_frames:
        # Do NOT silently emit a 4-frame "trajectory". On 2026-08-09 the old
        # `max(4, ...)` floor turned office_0's 0.6 m waypoint cluster into twelve
        # 4-to-8-frame sequences whose ATEs were degenerate-Umeyama artifacts, and
        # ~65 runs were spent on them before anyone could tell.
        raise RuntimeError(
            f"trajectory too short: walk_len={walk_len:.1f}m at spacing={spacing:.2f}m "
            f"gives only {n} frames (minimum {min_frames}). The waypoint circuit does "
            f"not cover enough of this scene — check the [waypoints] debug above.")
    targets = np.minimum(np.arange(n) * spacing, walk_len)

    xy = np.empty((n, 2))
    for k, tt in enumerate(targets):
        j = int(np.clip(np.searchsorted(cum, tt), 1, len(dense) - 1))
        seg_len = cum[j] - cum[j - 1]
        frac = 0.0 if seg_len < 1e-9 else (tt - cum[j - 1]) / seg_len
        xy[k] = dense[j - 1] * (1 - frac) + dense[j] * frac

    eyes = np.column_stack([xy, np.full(n, camera_height)])
    # Heading: follows the path, turning at most max_yaw_rate_dps (see rate_limited_yaw).
    yaw = rate_limited_yaw(eyes, rate_hz, max_yaw_rate_dps)
    poses = poses_from_yaw(eyes, yaw)
    _steps = np.degrees(np.abs(np.diff(yaw))) if n > 1 else np.zeros(0)

    lever = []
    if laps > 1:
        lever.append(f"{laps} laps")
    if abs(eff_speed - speed_mps) > 0.01 * max(speed_mps, 1e-6):
        lever.append(f"speed {speed_mps}->{eff_speed:.2f} m/s")
    lev = f"  [lengthened: {', '.join(lever)}]" if lever else ""
    lev += (f"  [yaw <= {max_yaw_rate_dps:g} deg/s; max step {_steps.max():.1f} deg]"
            if (max_yaw_rate_dps and len(_steps)) else "")
    goal = (f"path target {need_len:.1f}m" if path_mode
            else f"target {target} frames")
    print(f"[traj] walked {walk_len:.1f}m of {total_len:.1f}m at spacing={spacing:.2f}m "
          f"(speed {eff_speed:.2f} m/s @ {rate_hz} Hz) -> {n} frames "
          f"({goal}, cap {max_frames}){lev}")
    if abs(eff_speed - speed_mps) > 0.01 * max(speed_mps, 1e-6):
        print(f"[traj] WARNING: walking speed reduced {speed_mps} -> {eff_speed:.2f} m/s "
              f"to reach {target} frames, so this sequence's inter-frame baseline is "
              f"{spacing:.2f} m instead of the nominal "
              f"{speed_mps / max(rate_hz, 1e-6):.2f} m. A rate comparison assumes a FIXED "
              f"baseline per rate — a scene that lands here is not comparable across "
              f"rates. Raise max_laps (currently {max_laps}) to avoid it.")
    if path_mode and walk_len < need_len * 0.99:
        print(f"[traj] WARNING: walked only {walk_len:.1f}m of the {need_len:.1f}m target "
              f"even after {laps} lap(s) — this scene's circuit is too short. The path is "
              f"still identical across rates, so the rate comparison stays valid, but "
              f"this sequence is shorter than the others.")
    if n >= int(max_frames):
        print(f"[traj] NOTE: hit the hard frame cap ({max_frames}). At {rate_hz} Hz this "
              f"path wanted {int(walk_len / spacing) + 1} frames, so this rate's path is "
              f"TRUNCATED relative to the others and the rate comparison is compromised. "
              f"Raise max_frames_hard.")
    return poses


def stop_and_go(waypoints: np.ndarray, camera_height: float = 1.7,
                speed_mps: float = 0.5, rate_hz: float = 2.0, max_frames: int = 200,
                n_stops: int = 2, dwell_s: float = 5.0,
                max_yaw_rate_dps: float | None = 45.0) -> np.ndarray:
    """Walk → stand still (dwell) → walk again, repeated ``n_stops`` times.

    Built from the smooth spline, then each stop DUPLICATES the current pose for
    ``dwell_s * rate`` frames — the camera is stationary while time advances. Zero
    parallax makes the feed-forward backbone's near-ground depth degenerate, so this
    is the trajectory that actually exercises PRISM's still-guard and lets drift/noise
    accumulate around a parked robot (the 'square gap' failure). Frame budget is split
    so moving + dwell frames total ≤ ``max_frames``.
    """
    dwell_frames = max(1, int(round(dwell_s * rate_hz)))
    total_dwell = max(0, n_stops) * dwell_frames
    moving_cap = max(4, int(max_frames) - total_dwell)
    poses = synthetic_spline(waypoints, camera_height, speed_mps, rate_hz,
                             max_frames=moving_cap, target_frames=moving_cap,
                             max_yaw_rate_dps=max_yaw_rate_dps)
    n = len(poses)
    if n < 3 or n_stops < 1:
        return poses
    # Stops evenly spaced in the interior (never the very first/last frame).
    stop_idx = sorted({int(round(x)) for x in np.linspace(0, n - 1, n_stops + 2)[1:-1]})
    out = []
    for i in range(n):
        out.append(poses[i])
        if i in stop_idx:
            out.extend(poses[i].copy() for _ in range(dwell_frames))
    out = np.array(out[:int(max_frames)])
    print(f"[traj] stop_and_go: {n} moving + {len(stop_idx)}×{dwell_frames} dwell "
          f"-> {len(out)} frames (dwell {dwell_s}s @ {rate_hz} Hz)")
    return out


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


def _column_surfaces(scene, xy, z_top, max_hits: int = 12, eps: float = 2e-3):
    """Every surface under each (x,y) column, top to bottom, with its facing.

    ``RaycastingScene.cast_rays`` returns only the FIRST intersection, so one downward
    ray from above a closed room reports the CEILING and never sees the floor. This
    re-casts from just past each hit to walk the whole stack of surfaces in a column,
    and keeps each hit's normal so a floor (faces up) can be told from a ceiling
    (faces down).

    Returns a list per column of (z, normal_z) ordered from high to low.
    """
    import open3d as o3d
    xy = np.asarray(xy, dtype=np.float32)
    n = len(xy)
    cur = np.full(n, float(z_top), dtype=np.float32)
    alive = np.ones(n, dtype=bool)
    cols = [[] for _ in range(n)]
    for _ in range(int(max_hits)):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        rays = np.concatenate([
            xy[idx], cur[idx, None],
            np.zeros((idx.size, 2), np.float32), -np.ones((idx.size, 1), np.float32),
        ], axis=1).astype(np.float32)
        res = scene.cast_rays(o3d.core.Tensor(rays))
        t = res["t_hit"].numpy()
        nrm = res["primitive_normals"].numpy()
        for k, j in enumerate(idx):
            if not np.isfinite(t[k]):
                alive[j] = False
                continue
            z = float(cur[j] - t[k])
            cols[j].append((z, float(nrm[k][2])))
            cur[j] = z - eps
    return cols


def estimate_floor_z(scene, lo, hi, n_probe: int = 1024, seed: int = 0,
                     bin_m: float = 0.05, min_headroom_m: float = 1.5,
                     up_dot: float = 0.7, max_hits: int = 12,
                     candidates=None, tol_m: float = 0.10,
                     debug: bool = True) -> float | None:
    """Estimate the floor height by ray casting, and SCORE it against alternatives.

    Three estimators have now been tried on these six Replica scenes and the first two
    were each wrong on a different subset, which is why this one ends in a scored
    comparison rather than a single formula:

    * ``np.percentile(vertex_z, 1)`` — right for apartment_0/1, room_0/1. Wrong for
      room_2, whose mesh extends ~0.8 m BELOW its floor: p1 landed under the floor, no
      downward ray came within tolerance, and the scene was silently dropped from the
      2026-08-09 matrix.
    * "the height most downward rays land on" — wrong for closed rooms, because
      ``cast_rays`` returns the FIRST intersection and a ray from above hits the
      CEILING. It reported +1.05 m for apartment_0 (floor -1.53 m), which put the camera
      above the roof and left office_0, room_0 and room_1 unable to find any floor.

    What actually defines a floor is physical: **an upward-facing surface with standing
    room above it.** This walks the whole stack of surfaces per column
    (``_column_surfaces``), keeps hits whose normal points up and which have at least
    ``min_headroom_m`` of clear space before the next surface above, and takes the
    histogram peak — preferring the LOWEST well-supported height, since a floor always
    sits below the tables that also pass the standable test.

    Then it scores that answer, and any ``candidates`` the caller supplies (pass the p1
    value), by the only thing that matters downstream: **what fraction of columns have a
    standable surface within ``tol_m`` of this height** — i.e. how much bare floor the
    waypoint sampler would actually find. The best-scoring height wins, and every
    candidate's score is printed, so a bad estimate is visible in one log line instead of
    six scenes' worth of confusing failures.

    Returns None if no standable surface exists anywhere.
    """
    rng = np.random.default_rng(seed)
    m = max(4, int(np.sqrt(n_probe)))
    gx = np.linspace(lo[0], hi[0], m)
    gy = np.linspace(lo[1], hi[1], m)
    xx, yy = np.meshgrid(gx, gy)
    xy = np.column_stack([xx.ravel(), yy.ravel()])
    # Jitter so a grid aligned with a wall does not systematically sample the same edge.
    step = np.array([gx[1] - gx[0] if m > 1 else 0.0,
                     gy[1] - gy[0] if m > 1 else 0.0])
    xy = xy + rng.uniform(-0.5, 0.5, xy.shape) * step
    z_top = float(hi[2]) + 0.5

    cols = _column_surfaces(scene, xy, z_top, max_hits=max_hits)

    # Standable surfaces per column: upward-facing, with headroom to the next one up.
    per_col, flat = [], []
    for col in cols:
        zs = [z for z, _ in col]                    # already ordered high -> low
        keep = []
        for k, (z, nz) in enumerate(col):
            if nz < up_dot:
                continue                            # ceiling / wall / downward face
            above = zs[k - 1] if k > 0 else z_top   # nearest surface above this one
            if (above - z) >= min_headroom_m:
                keep.append(z)
        per_col.append(keep)
        flat.extend(keep)
    if not flat:
        if debug:
            print(f"[floor] no upward-facing surface with {min_headroom_m:.1f} m "
                  f"headroom in any of {len(cols)} columns")
        return None

    def _coverage(zf: float) -> float:
        """Fraction of columns with a standable surface within tol_m of zf."""
        if zf is None:
            return -1.0
        return sum(1 for keep in per_col
                   if any(abs(z - zf) <= tol_m for z in keep)) / max(len(per_col), 1)

    arr = np.asarray(flat, dtype=float)
    edges = np.arange(arr.min(), arr.max() + bin_m, bin_m)
    if len(edges) < 2:
        peak = float(np.median(arr))
    else:
        counts, _ = np.histogram(arr, bins=edges)
        best = int(counts.max())
        # Among heights nearly as well supported as the best, take the LOWEST.
        near = np.flatnonzero(counts >= 0.60 * best)
        peak = float(edges[int(near[0])] + bin_m / 2)

    cand = [("raycast", peak)]
    for i, c in enumerate(candidates or []):
        if c is not None:
            cand.append((f"candidate{i}", float(c)))
    scored = [(name, z, _coverage(z)) for name, z in cand]
    scored.sort(key=lambda t: (-t[2], t[1]))         # best coverage, then lowest
    name, fz, cov = scored[0]

    if debug:
        detail = ", ".join(f"{n}={z:+.2f} (cov {100*c:.0f}%)" for n, z, c in scored)
        print(f"[floor] floor_z={fz:+.2f} via {name} — {detail} "
              f"[{len(flat)} standable hits / {len(cols)} columns]")
        if cov < 0.10:
            print(f"[floor] WARNING: the winning height covers only {100*cov:.0f}% of "
                  f"columns. The waypoint sampler will struggle; this scene may have a "
                  f"split-level floor or a broken mesh.")
    return fz


def free_space_waypoints(mesh, n_waypoints: int, min_clearance_m: float, seed: int,
                         probe_z: float | None = None, floor_z: float | None = None,
                         ground_tol_m: float = 0.12, min_span_m: float = 3.0,
                         debug: bool = True) -> np.ndarray:
    """Sample n collision-free INTERIOR waypoints that sit OVER BARE FLOOR.

    A point is kept only if it is (a) >= min_clearance from any surface, (b) interior
    (most rays hit the mesh), AND (c) over bare floor — a ray cast straight down hits
    a surface within `ground_tol_m` of the global floor_z (i.e. NOT over furniture).
    (c) matters because PRISM's metric scale comes from a RANSAC floor fit under the
    camera; starting over a sofa gives the wrong camera-to-floor height (scale error).

    TWO GUARDS ADDED AFTER THE 2026-08-09 RUN, both for silent failures that produced
    a full night of unusable data:

    * **Floor repair.** If almost nothing passes the bare-floor test, the supplied
      `floor_z` is assumed wrong and is re-estimated by ray casting
      (`estimate_floor_z`) before giving up. This is what killed `room_2`.

    * **Minimum span.** `office_0` returned a full 8/8 waypoints — all of them inside
      a 0.6 m patch, because its `interior` score only clears 0.8 in one corner of the
      room. The result was a 4-frame "trajectory" with the camera essentially
      stationary, which then produced meaningless ATEs (PRISM and PanoVGGT agreed to
      six significant figures because Umeyama on 4 near-coincident points is
      degenerate) across ~65 runs. A waypoint set whose extent is under `min_span_m`
      is now rejected, the interior threshold is relaxed, and the sampling retried.
    """
    import open3d as o3d  # local import: renderer env only

    aabb = mesh.get_axis_aligned_bounding_box()
    lo = aabb.get_min_bound()
    hi = aabb.get_max_bound()
    z = probe_z if probe_z is not None else (lo[2] + hi[2]) / 2
    fz = float(floor_z) if floor_z is not None else float(lo[2])
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))

    # A room smaller than the requested span cannot satisfy it; scale the requirement
    # to the room so a genuinely small office is not rejected for being small.
    #
    # The bar is 2.0 m, not the 3.0 m first tried. What this guard exists to catch is a
    # NEAR-STATIONARY camera: office_0's original failure was a 0.6 m circuit yielding
    # 4-frame sequences on which Umeyama is degenerate. A 2.4 m extent walked over 300
    # frames is not that — it is 240 cm of parallax against metrics quoted in cm and an
    # F-score at 5 cm, and it is well conditioned. At 3.0 m the guard was rejecting
    # room_2 entirely and one seed of office_0, which would have cost a scene and left
    # office_0 with uneven seeds — a worse problem than a confined trajectory.
    room_diag = float(np.hypot(hi[0] - lo[0], hi[1] - lo[1]))
    span_req = min(min_span_m, 0.35 * room_diag)

    if debug:
        print(f"[waypoints] AABB lo={np.round(lo,2)} hi={np.round(hi,2)} "
              f"probe_z={z:.2f} floor_z={fz:.2f} ground_tol={ground_tol_m} "
              f"room_diag={room_diag:.1f}m span_req={span_req:.1f}m")

    # Collect a POOL of acceptable points, then choose the spread-maximising subset.
    # Taking the first n_waypoints that pass (the old behaviour) makes the circuit's
    # extent a lottery: office_0 seed 9012 spanned 2.24 m while seeds 1234/5678 spanned
    # 3.5-3.9 m in the same room, purely from sampling order. Farthest-point selection
    # makes the span depend on the room's accessible free space rather than on the seed,
    # which is what a benchmark trajectory should be — and it makes the span check below
    # meaningful, because a failure then really means "this scene cannot do better".
    pool_target = max(int(n_waypoints) * 6, 48)

    def _sample(interior_min: float, fz_use: float, rng):
        kept, tries, shown, n_floor_seen = [], 0, 0, 0
        budget = n_waypoints * 1200
        while len(kept) < pool_target and tries < budget:
            tries += 1
            xy = rng.uniform(lo[:2], hi[:2])
            pt = np.array([xy[0], xy[1], z], dtype=np.float32)
            dist = scene.compute_distance(o3d.core.Tensor(pt[None])).numpy()[0]
            score = _interior_score(scene, pt)
            floor_frac, gz = clean_floor_patch(scene, xy[0], xy[1], z, fz_use,
                                               tol=ground_tol_m)
            n_floor_seen += (gz is not None)
            ok = (dist >= min_clearance_m and score >= interior_min
                  and floor_frac >= 0.85)
            if debug and shown < 10:
                gzs = f"{gz:.2f}" if gz is not None else "none"
                print(f"[waypoints] cand xy={np.round(xy,2)} clearance={dist:.2f} "
                      f"interior={score:.2f} floor_frac={floor_frac:.2f} "
                      f"ground_z={gzs} -> {'KEEP' if ok else 'reject'}")
                shown += 1
            if ok:
                kept.append((xy, floor_frac))
        return _farthest_point_subset(kept, int(n_waypoints)), tries, n_floor_seen

    # Pass 1 at the strict thresholds. If it finds no floor at ALL, the floor_z we were
    # handed is wrong -> re-estimate it and try again before relaxing anything else.
    rng = np.random.default_rng(seed)
    kept, tries, n_floor = _sample(0.80, fz, rng)
    if n_floor == 0:
        fz_new = estimate_floor_z(scene, lo, hi, seed=seed, debug=debug)
        if fz_new is not None and abs(fz_new - fz) > ground_tol_m:
            print(f"[waypoints] NO candidate found bare floor at floor_z={fz:.2f} — "
                  f"re-estimating by raycast -> {fz_new:.2f} (delta {fz_new - fz:+.2f} m) "
                  f"and resampling")
            fz = fz_new
            rng = np.random.default_rng(seed)
            kept, tries, n_floor = _sample(0.80, fz, rng)

    # Relax the interior threshold until the waypoints actually SPAN the room. A tight
    # cluster passes every per-point test and still yields a stationary camera.
    for interior_min in (0.65, 0.50):
        if len(kept) >= 4 and _span(kept) >= span_req:
            break
        if debug:
            print(f"[waypoints] kept {len(kept)} span={_span(kept):.2f}m "
                  f"< required {span_req:.2f}m — relaxing interior>={interior_min:.2f}")
        rng = np.random.default_rng(seed)
        kept, tries, n_floor = _sample(interior_min, fz, rng)

    span = _span(kept)
    if debug:
        print(f"[waypoints] kept {len(kept)}/{n_waypoints} after {tries} tries, "
              f"span={span:.2f}m (required {span_req:.2f}m)")
    if len(kept) < 4:
        raise RuntimeError(
            f"free-space-over-floor sampling failed (kept {len(kept)} in {tries} tries). "
            f"Loosen ground_tol_m/min_clearance, or check the [mesh] floor_z. Debug above.")
    if span < span_req:
        raise RuntimeError(
            f"waypoints span only {span:.2f} m (need {span_req:.2f} m in a "
            f"{room_diag:.1f} m room) — every kept point is in one small patch, which "
            f"yields a near-stationary camera and meaningless pose metrics. This is the "
            f"office_0 failure from 2026-08-09. Debug above.")
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


def _farthest_point_subset(kept, k: int):
    """Pick k of the accepted waypoints to maximise spatial spread.

    Greedy farthest-point sampling, seeded from the point with the CLEANEST floor patch
    (the tour starts there, and PRISM locks its metric scale from the floor under the
    first frames — so the start should be the most reliable floor in the room). Each
    subsequent pick is the candidate furthest from everything chosen so far.

    Returns the same ``[(xy, floor_frac), ...]`` shape it was given, so callers are
    unaffected. If fewer than k candidates were found, returns all of them.
    """
    if len(kept) <= k:
        return list(kept)
    pts = np.array([xy for xy, _ in kept], dtype=float)
    start = int(np.argmax([ff for _, ff in kept]))
    chosen = [start]
    dmin = np.linalg.norm(pts - pts[start], axis=1)
    while len(chosen) < k:
        nxt = int(np.argmax(dmin))
        if dmin[nxt] <= 0:
            break
        chosen.append(nxt)
        dmin = np.minimum(dmin, np.linalg.norm(pts - pts[nxt], axis=1))
    return [kept[i] for i in chosen]


def _span(kept) -> float:
    """Largest pairwise distance in a kept-waypoint list (0.0 for < 2 points)."""
    if len(kept) < 2:
        return 0.0
    pts = np.array([xy for xy, _ in kept])
    d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=-1)
    return float(d.max())


# ════════════════════════════════════════════════════════════════════════════
# Grid planner (rerun-v3): collision-free by construction
# ════════════════════════════════════════════════════════════════════════════
# WHY. The spline planner checks only its WAYPOINTS against the mesh. The Catmull-Rom
# curve between two waypoints is a straight-ish line, so in a multi-room scene it cuts
# straight through walls and door frames. scripts/traj_audit.py on the rerun-v2 inputs:
# apartment_0/1 had 5-16 wall crossings per 300-frame sequence and 16-53 frames with
# the camera inside or against geometry — exactly the frames where every method
# (PRISM, VGGT-SLAM, LASER) lost track at once. The rooms had none, but room_0 seeds
# 1-2 passed within 0.11-0.14 m of furniture.
#
# HOW. Rasterise the walkable free space at camera height into a 2D grid, plan every
# leg between waypoints with Dijkstra on that grid (the cost pushes the path towards
# the middle of corridors and doorways), shortcut the cell path where a straight line
# stays at least as clear, round the corners (Chaikin), then sample by arc length.
# The final poses are re-checked against the exact mesh distance; a violation raises.
#
# A cell is walkable when, at the same time:
#   * a ray straight down from camera height lands on the floor (not furniture, not
#     outside the building), and the nearest non-floor cell is >= r_body away
#     (horizontal clearance from table legs, sofas, beds, walls);
#   * the distance to any surface at camera height is >= r_cam;
#   * the distance to any surface at body height (floor + 1 m) is >= r_body;
#   (r_cam = min_clearance_m 0.30, r_body = body_clearance_m 0.20: at 0.30 the body
#    test split room_0, a furnished living room, into 4 pieces)
#   * it belongs to the largest 8-connected free component (no islands).
#
# LAPS. The old planner repeated ONE circuit up to 12 times (11 laps in the small
# rooms: 66-86% of frames revisited a place passed >= 20 s earlier, on the identical
# route). Here every lap draws a FRESH set of waypoints and tours them from wherever
# the camera is, so the scene is revisited along different routes and headings.
#
# LOOP FAMILY. With laps, the old `loop_*` trajectories were the same poses as
# `synthetic_*` to within 5 mm (the two appended waypoints fell past the truncation
# point). Here `close_loop=True` makes the walk END at its start: waypoints are added
# until the remaining budget equals the geodesic way home, then it walks home.


def free_space_grid(scene, lo, hi, floor_z: float, cam_z: float, res: float = 0.05,
                    r_cam: float = 0.30, r_body: float = 0.30, ground_tol: float = 0.12,
                    body_h: float = 1.0) -> dict:
    """Walkable-space grid at camera height (see the block comment above)."""
    import open3d as o3d
    from scipy import ndimage
    xs = np.arange(lo[0], hi[0] + res, res)
    ys = np.arange(lo[1], hi[1] + res, res)
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    xy = np.column_stack([XX.ravel(), YY.ravel()]).astype(np.float32)
    n = len(xy)

    def _dist(z):
        p = np.column_stack([xy, np.full(n, z, np.float32)])
        return scene.compute_distance(o3d.core.Tensor(p)).numpy().reshape(XX.shape)

    d_cam = _dist(cam_z)
    d_body = _dist(floor_z + body_h)
    rays = np.column_stack([xy, np.full(n, cam_z, np.float32),
                            np.zeros((n, 2), np.float32), -np.ones((n, 1), np.float32)])
    t = scene.cast_rays(o3d.core.Tensor(rays.astype(np.float32)))["t_hit"].numpy().reshape(XX.shape)
    floor_ok = np.isfinite(t) & (np.abs((cam_z - t) - floor_z) <= ground_tol)
    d_floor = ndimage.distance_transform_edt(floor_ok) * res      # to nearest non-floor cell
    clr = np.minimum(np.minimum(d_cam, d_body), d_floor)
    free = floor_ok & (d_cam >= r_cam) & (d_body >= r_body) & (d_floor >= r_body)
    lab, nlab = ndimage.label(free, structure=np.ones((3, 3), bool))
    if nlab == 0:
        raise RuntimeError("free_space_grid: no walkable cell (check floor_z / clearances)")
    sizes = ndimage.sum(free, lab, index=np.arange(1, nlab + 1))
    big = int(np.argmax(sizes)) + 1
    comp = lab == big
    return dict(xs=xs, ys=ys, res=res, lo=np.asarray(lo[:2], float), clr=clr, free=comp,
                n_free_all=int(free.sum()), n_free=int(comp.sum()), n_components=int(nlab),
                floor_ok=floor_ok)


def _grid_graph(G: dict, pref: float, r_min: float, alpha: float = 4.0):
    """Sparse 8-connected graph over the free cells. Edge cost = length x (1 + alpha x
    p^2), p = how far below the PREFERRED clearance the edge is (0 when >= pref), so
    shortest paths keep to the middle of corridors and doorways."""
    from scipy.sparse import csr_matrix
    free, clr, res = G["free"], G["clr"], G["res"]
    nx, ny = free.shape
    idx = -np.ones(free.shape, np.int64)
    cells = np.argwhere(free)
    idx[free] = np.arange(len(cells))
    pen = np.clip((pref - clr) / max(pref - r_min, 1e-6), 0.0, 1.0) ** 2
    rows, cols, w = [], [], []
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        a = cells
        b = a + np.array([dx, dy])
        ok = (b[:, 0] >= 0) & (b[:, 0] < nx) & (b[:, 1] >= 0) & (b[:, 1] < ny)
        a, b = a[ok], b[ok]
        ok = free[b[:, 0], b[:, 1]]
        a, b = a[ok], b[ok]
        L = res * np.hypot(dx, dy)
        p = 0.5 * (pen[a[:, 0], a[:, 1]] + pen[b[:, 0], b[:, 1]])
        ww = L * (1.0 + alpha * p)
        ia, ib = idx[a[:, 0], a[:, 1]], idx[b[:, 0], b[:, 1]]
        rows += [ia, ib]; cols += [ib, ia]; w += [ww, ww]
    M = csr_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))),
                   shape=(len(cells), len(cells)))
    return M, cells, idx


def _cell_xy(G, cells):
    return np.column_stack([G["xs"][cells[:, 0]], G["ys"][cells[:, 1]]])


def _clr_at(G, xy):
    """Nearest-cell clearance (and free flag) at world xy (N,2)."""
    i = np.clip(np.rint((xy[:, 0] - G["xs"][0]) / G["res"]).astype(int), 0, len(G["xs"]) - 1)
    j = np.clip(np.rint((xy[:, 1] - G["ys"][0]) / G["res"]).astype(int), 0, len(G["ys"]) - 1)
    return G["clr"][i, j], G["free"][i, j]


def _shortcut(G, pts, pref):
    """Greedy line-of-sight shortcutting of a cell path. A shortcut i->j is taken only
    if every point on it is free and at least as clear as min(pref, the clearest the
    original sub-path i..j ever got), so straightening never pulls the path towards a
    wall that the cost-weighted plan had kept away from."""
    clr_path, _ = _clr_at(G, pts)
    out, i, n = [pts[0]], 0, len(pts)
    step = G["res"] * 0.5
    while i < n - 1:
        j_ok = i + 1
        run_min = clr_path[i]
        for j in range(i + 1, n):
            run_min = min(run_min, clr_path[j])
            thr = min(pref, run_min) - 1e-6
            seg = pts[j] - pts[i]
            L = float(np.linalg.norm(seg))
            m = max(2, int(L / step) + 1)
            s = pts[i] + np.linspace(0, 1, m)[:, None] * seg
            c, f = _clr_at(G, s)
            if f.all() and (c >= thr).all():
                j_ok = j
            else:
                break
        out.append(pts[j_ok])
        i = j_ok
    return np.array(out)


def _chaikin_safe(G, pts, iters, thr):
    """Chaikin corner cutting that only cuts a corner when the cut stays walkable and
    >= thr clear (grid lookup); a corner that would graze furniture is kept sharp
    (the yaw-rate limit then turns the camera through it)."""
    step = G["res"] * 0.5
    for _ in range(int(iters)):
        if len(pts) < 3:
            return pts
        out = [pts[0]]
        for i in range(1, len(pts) - 1):
            q = 0.75 * pts[i] + 0.25 * pts[i - 1]
            r = 0.75 * pts[i] + 0.25 * pts[i + 1]
            L = float(np.linalg.norm(r - q))
            m = max(2, int(L / step) + 1)
            smp = q + np.linspace(0, 1, m)[:, None] * (r - q)
            c, f = _clr_at(G, smp)
            if f.all() and (c >= thr).all():
                out += [q, r]
            else:
                out.append(pts[i])
        out.append(pts[-1])
        pts = np.array(out)
    return pts


def _chaikin(pts, iters):
    for _ in range(int(iters)):
        if len(pts) < 3:
            return pts
        q = 0.75 * pts[:-1] + 0.25 * pts[1:]
        r = 0.25 * pts[:-1] + 0.75 * pts[1:]
        mid = np.empty((2 * (len(pts) - 1), 2))
        mid[0::2], mid[1::2] = q, r
        pts = np.vstack([pts[:1], mid[1:-1], pts[-1:]])
    return pts


def _densify(pts, step):
    out = [pts[:1]]
    for a, b in zip(pts[:-1], pts[1:]):
        L = float(np.linalg.norm(b - a))
        m = max(1, int(np.ceil(L / step)))
        out.append(a + np.linspace(0, 1, m + 1)[1:, None] * (b - a))
    return np.vstack(out)


def grid_walk(scene, lo, hi, floor_z: float, cam_z: float, seed: int,
              speed_mps: float = 0.5, rate_hz: float = 2.0,
              path_target_m: float = 74.75, close_loop: bool = False,
              n_waypoints: int = 12, min_clearance_m: float = 0.30,
              body_clearance_m: float = 0.20, pref_clearance_m: float = 0.60, max_laps: int = 12,
              min_span_m: float = 2.0, min_frames: int = 32, max_frames: int = 1000,
              max_yaw_rate_dps: float | None = 45.0, lookahead_m: float = 0.5,
              res: float = 0.05, chaikin_iters: int = 3, debug: bool = True,
              return_info: bool = False):
    """Collision-free constant-speed walk on the free-space grid. Returns (n,4,4) c2w.

    Same contract as ``synthetic_spline`` in path mode: the physical path length
    ``path_target_m`` is the invariant and the frame count follows from the rate (a
    loop walk ends exactly at its start, so its length is within a leg of the target).
    """
    import open3d as o3d
    from scipy.sparse.csgraph import dijkstra
    rng = np.random.default_rng(seed)
    G = free_space_grid(scene, lo, hi, floor_z, cam_z, res=res,
                        r_cam=min_clearance_m, r_body=body_clearance_m)
    M, cells, idx = _grid_graph(G, pref_clearance_m, body_clearance_m)
    cxy = _cell_xy(G, cells)
    cclr = G["clr"][cells[:, 0], cells[:, 1]]
    if debug:
        print(f"[grid] {G['free'].shape[0]}x{G['free'].shape[1]} cells @ {res} m: "
              f"walkable {G['n_free']} in the main component ({G['n_free'] * res * res:.1f} m^2; "
              f"{G['n_components']} component(s), {G['n_free_all']} free in total)")

    room_diag = float(np.hypot(*(cxy.max(0) - cxy.min(0))))
    span_req = min(min_span_m, 0.35 * room_diag)
    # Waypoint candidates: cells at least 0.4 m clear (or pref, if smaller), so the
    # camera does not arrive nose-to-wall at a waypoint and turn round there. Not
    # `>= pref`: in a furnished room only the middle of the floor is 0.6 m clear, and
    # the walk shrank to a 2.5 m patch of room_0.
    good = np.flatnonzero(cclr >= min(pref_clearance_m, 0.40))
    if len(good) < 4 * n_waypoints:
        good = np.arange(len(cells))
    pool_n = max(6 * n_waypoints, 48)

    def _draw(start_node=None):
        pool = rng.choice(good, size=min(pool_n, len(good)), replace=False)
        if start_node is not None:
            pool = np.concatenate([[start_node], pool])
            seed_i = 0
        else:
            seed_i = int(np.argmax(cclr[pool]))           # clearest cell starts the walk
        P = cxy[pool]
        chosen = [seed_i]
        dmin = np.linalg.norm(P - P[seed_i], axis=1)
        while len(chosen) < min(n_waypoints, len(pool)):
            k = int(np.argmax(dmin))
            if dmin[k] <= 0:
                break
            chosen.append(k)
            dmin = np.minimum(dmin, np.linalg.norm(P - P[k], axis=1))
        return [int(pool[c]) for c in chosen]

    wps = _draw()
    span = float(np.max(np.linalg.norm(cxy[wps][:, None] - cxy[wps][None], axis=-1)))
    if span < span_req:
        raise RuntimeError(f"grid waypoints span only {span:.2f} m (need {span_req:.2f} m)")
    start = wps[0]
    d_home = dijkstra(M, indices=start)

    def _leg(a, b):
        d, pred = dijkstra(M, indices=a, return_predecessors=True)
        seq, cur = [], b
        while cur != a and cur >= 0:
            seq.append(cur); cur = pred[cur]
        if cur < 0:
            return None, np.inf
        seq = seq[::-1]
        pts = cxy[[a] + seq]
        return seq, float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())

    need = float(path_target_m)

    def _order(cur, todo):
        """Open TSP order of `todo` starting from `cur` on geodesic distances: nearest
        neighbour, then 2-opt. A 2-opt tour is a smooth circuit through a room (fewer
        reversals than plain nearest-neighbour) and still sensible across rooms."""
        nodes_ = [cur] + list(todo)
        D = dijkstra(M, indices=nodes_)[:, nodes_]
        order, left = [0], set(range(1, len(nodes_)))
        while left:
            k = min(left, key=lambda j: D[order[-1], j])
            if not np.isfinite(D[order[-1], k]):
                break
            order.append(k); left.remove(k)
        improved = True
        while improved:
            improved = False
            for i in range(1, len(order) - 1):
                for j in range(i + 1, len(order)):
                    a_, b_ = order[i - 1], order[i]
                    c_ = order[j]
                    d_ = order[j + 1] if j + 1 < len(order) else None
                    old = D[a_, b_] + (D[c_, d_] if d_ is not None else 0.0)
                    new = D[a_, c_] + (D[b_, d_] if d_ is not None else 0.0)
                    if new < old - 1e-9:
                        order[i:j + 1] = order[i:j + 1][::-1]
                        improved = True
        return [nodes_[k] for k in order[1:]]

    def _leg_len(a, seq):
        """Length of a leg AFTER shortcutting (what will actually be walked)."""
        return float(np.linalg.norm(np.diff(_shortcut(G, cxy[[a] + seq], pref_clearance_m),
                                            axis=0), axis=1).sum())

    max_sets = max(4, 4 * int(max_laps))

    def _tour(target: float):
        """Waypoint tours (fresh waypoint set each lap) until the walked length reaches
        `target`. Deterministic for a given seed: re-draws from a fresh RNG."""
        nonlocal rng
        rng = np.random.default_rng(seed + 7919)
        nodes, length, cur, lap = [start], 0.0, start, 0
        todo, done = _order(start, wps[1:]), False
        while not done:
            if not todo:
                if lap + 1 >= max_sets:
                    print(f"[grid] WARNING: {max_sets} waypoint sets used at "
                          f"{length:.1f} m of {target:.1f} m")
                    break
                lap += 1
                todo = _order(cur, [w for w in _draw() if w != cur])
                if not todo:
                    continue
            w = todo.pop(0)
            seq, _ = _leg(cur, w)
            if seq is None or not seq:
                continue
            L = _leg_len(cur, seq)
            # d_home is the cost-weighted geodesic way back (>= its walked length), so a
            # loop turns home slightly early rather than overshooting the target.
            if close_loop and length + L + d_home[w] >= target:
                done = True
            nodes += seq; length += L; cur = w
            if not close_loop and length >= target:
                done = True
        if close_loop and cur != start:
            seq, L = _leg(cur, start)
            nodes += seq; length += L
        return nodes, lap

    def _smooth(nodes):
        raw = cxy[nodes]
        sc = _shortcut(G, raw, pref_clearance_m)
        sm = _chaikin_safe(G, sc, chaikin_iters, body_clearance_m)
        return raw, sc, _densify(sm, res * 0.5), int(chaikin_iters)

    # The cell path is longer than the smoothed one (8-connected zig-zag, cut corners),
    # so size the tour by the SMOOTHED length: rescale the raw target until it fits.
    spacing = speed_mps / max(rate_hz, 1e-6)
    target_raw = need * 1.03
    for _attempt in range(4):
        nodes, lap = _tour(target_raw)
        raw, sc, path, used_iters = _smooth(nodes)
        total = float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())
        ok = (total >= need * 0.97) if close_loop else (total >= need)
        if ok or lap + 1 >= max_sets:
            break
        target_raw *= 1.03 * need / max(total, 1e-6)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(cum[-1])
    walk = total if close_loop else min(total, need)
    n = int(walk / spacing) + 1
    n = min(n, int(max_frames))
    if n < min_frames:
        raise RuntimeError(f"grid walk too short: {walk:.1f} m -> {n} frames (< {min_frames})")
    tt = np.minimum(np.arange(n) * spacing, walk)
    xy = np.column_stack([np.interp(tt, cum, path[:, 0]), np.interp(tt, cum, path[:, 1])])
    eyes = np.column_stack([xy, np.full(n, cam_z)])
    la = max(1, int(round(lookahead_m / spacing)))
    yaw = rate_limited_yaw(eyes, rate_hz, max_yaw_rate_dps, lookahead=la)
    poses = poses_from_yaw(eyes, yaw)

    # Exact re-check against the mesh (not the grid): clearance and segment crossings.
    chk = check_poses(scene, poses)
    steps = np.degrees(np.abs(np.diff(yaw))) if n > 1 else np.zeros(1)
    if debug:
        print(f"[grid] path {total:.1f} m (target {need:.1f} m{', closed loop' if close_loop else ''}), "
              f"{lap + 1} lap(s), {len(sc)} legs after shortcut, chaikin x{used_iters}; "
              f"walked {walk:.1f} m at {spacing:.3f} m -> {n} frames; "
              f"min clearance {chk['clear_min']:.2f} m, crossings {chk['n_cross']}, "
              f"yaw step median {np.median(steps):.1f} / max {steps.max():.1f} deg")
    if chk["n_cross"] or chk["clear_min"] < 0.5 * min_clearance_m:
        raise RuntimeError(f"grid walk failed the mesh re-check: min clearance "
                           f"{chk['clear_min']:.2f} m, {chk['n_cross']} crossing(s)")
    if return_info:
        return poses, dict(G=G, raw=raw, shortcut=sc, path=path, waypoints=cxy[wps], laps=lap + 1)
    return poses


def check_poses(scene, poses) -> dict:
    """Exact mesh check of camera centres: min clearance, and how many frame-to-frame
    segments pass THROUGH a surface."""
    import open3d as o3d
    c = np.asarray(poses)[:, :3, 3].astype(np.float32)
    clear = scene.compute_distance(o3d.core.Tensor(c)).numpy()
    n_cross = 0
    if len(c) > 1:
        d = c[1:] - c[:-1]
        L = np.linalg.norm(d, axis=1)
        u = d / np.maximum(L[:, None], 1e-9)
        t = scene.cast_rays(o3d.core.Tensor(np.concatenate([c[:-1], u], 1).astype(np.float32)))["t_hit"].numpy()
        n_cross = int((np.isfinite(t) & (t < L) & (L > 1e-6)).sum())
    return dict(clear_min=float(clear.min()), clear_p5=float(np.percentile(clear, 5)),
                n_cross=n_cross)


def insert_dwells(poses: np.ndarray, rate_hz: float, n_stops: int, dwell_s: float,
                  max_frames: int) -> np.ndarray:
    """Stop-and-go from any moving trajectory: duplicate the pose at ``n_stops`` evenly
    spaced interior frames for ``dwell_s`` seconds each."""
    dwell_frames = max(1, int(round(dwell_s * rate_hz)))
    n = len(poses)
    if n < 3 or n_stops < 1:
        return poses
    stop_idx = sorted({int(round(x)) for x in np.linspace(0, n - 1, n_stops + 2)[1:-1]})
    out = []
    for i in range(n):
        out.append(poses[i])
        if i in stop_idx:
            out.extend(poses[i].copy() for _ in range(dwell_frames))
    return np.array(out[:int(max_frames)])


def fit_floor_plane(scene, lo, hi, n_side: int = 48, tol_m: float = 0.03,
                    min_headroom_m: float = 1.5, seed: int = 0):
    """Floor plane (unit normal n with n_z > 0, point p0) from the LOWEST standable
    surface in each column of an n_side x n_side grid (upward-facing, with headroom),
    RANSAC + SVD refine. Returns (n, p0, inlier_fraction) or None.

    Why: Replica room_2 is tilted 8.7 deg relative to its mesh Z axis (the other five
    are 0.1-1.5 deg). A level camera then sees a sloping floor, its height above the
    floor drifts by ~0.6 m along the walk (PRISM anchors metric scale on that height),
    and only a 1 m strip of the floor is within tolerance of a single floor_z.
    """
    g = np.stack(np.meshgrid(np.linspace(lo[0], hi[0], n_side),
                             np.linspace(lo[1], hi[1], n_side)), -1).reshape(-1, 2)
    z_top = float(hi[2]) + 0.5
    cols = _column_surfaces(scene, g, z_top)
    P = []
    for (x, y), col in zip(g, cols):
        zs = [z for z, _ in col]
        stand = [z for k, (z, nz) in enumerate(col)
                 if nz > 0.9 and ((zs[k - 1] if k > 0 else z_top) - z) >= min_headroom_m]
        if stand:
            P.append((x, y, min(stand)))
    P = np.asarray(P, float)
    if len(P) < 20:
        return None
    rng = np.random.default_rng(seed)
    best = (0, None)
    for _ in range(600):
        s = P[rng.choice(len(P), 3, replace=False)]
        n = np.cross(s[1] - s[0], s[2] - s[0])
        nn = np.linalg.norm(n)
        if nn < 1e-6:
            continue
        n /= nn
        if abs(n[2]) < 0.8:          # not a floor candidate (> ~37 deg)
            continue
        inl = np.abs((P - s[0]) @ n) < tol_m
        if inl.sum() > best[0]:
            best = (int(inl.sum()), inl)
    if best[1] is None:
        return None
    Q = P[best[1]]
    c = Q.mean(0)
    n = np.linalg.svd(Q - c)[2][2]
    n = n * np.sign(n[2])
    return n, c, best[0] / len(P)


def levelling_rotation(n) -> np.ndarray:
    """Rotation matrix taking unit vector n onto +Z (Rodrigues)."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(n, z)
    s, c = np.linalg.norm(v), float(n @ z)
    if s < 1e-12:
        return np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]) / s
    ang = np.arctan2(s, c)
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)
