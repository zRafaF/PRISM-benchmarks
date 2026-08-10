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


def synthetic_spline(waypoints: np.ndarray, camera_height: float = 1.7,
                     speed_mps: float = 0.5, rate_hz: float = 2.0,
                     max_frames: int = 1000, close_loop: bool = False,
                     path_target_m: float | None = None,
                     target_frames: int | None = None, max_laps: int = 12,
                     min_speed_mps: float = 0.15,
                     min_frames: int = 32) -> np.ndarray:
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
    poses = np.empty((n, 4, 4))
    for i in range(n):
        nxt = eyes[min(i + 1, n - 1)]
        tgt = nxt if not np.allclose(nxt, eyes[i]) else eyes[i] + np.array([1.0, 0, 0])
        poses[i] = _look_at(eyes[i], tgt)

    lever = []
    if laps > 1:
        lever.append(f"{laps} laps")
    if abs(eff_speed - speed_mps) > 0.01 * max(speed_mps, 1e-6):
        lever.append(f"speed {speed_mps}->{eff_speed:.2f} m/s")
    lev = f"  [lengthened: {', '.join(lever)}]" if lever else ""
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
                n_stops: int = 2, dwell_s: float = 5.0) -> np.ndarray:
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
                             max_frames=moving_cap, target_frames=moving_cap)
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
