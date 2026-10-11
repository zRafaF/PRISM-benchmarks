"""Self-contained IO for runners (executed inside each METHOD's env).

NOTE: named `runner_io` (NOT `_io`) because `_io` is a CPython built-in module —
`import _io` resolves to the stdlib one, shadowing a local file of that name.

Only depends on numpy + a best-effort image reader (imageio | PIL | open3d).
Never imports the orchestrator's bench package (different env). Defines the exact
common-layout writers so every method emits identical poses.tum / cloud.ply.
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



def _read_png(path: Path) -> np.ndarray:
    try:
        import imageio.v2 as imageio
        return np.asarray(imageio.imread(path))
    except Exception:
        pass
    try:
        from PIL import Image
        return np.asarray(Image.open(path))
    except Exception:
        pass
    import open3d as o3d
    return np.asarray(o3d.io.read_image(str(path)))


def load_sequence(in_dir: Path):
    """Return dict with rgb (list HxWx3 uint8), depth (list HxW float or None),
    mask (list HxW or None), meta (dict), intrinsics (dict)."""
    in_dir = Path(in_dir)
    meta = json.loads((in_dir / "meta.json").read_text())
    intr = json.loads((in_dir / "intrinsics.json").read_text())
    names = sorted(p.stem for p in (in_dir / "rgb").glob("*.png"))
    rgb, depth, mask = [], [], []
    for nm in names:
        rgb.append(_read_png(in_dir / "rgb" / f"{nm}.png")[..., :3])
        depth.append(load_depth(in_dir, nm))
        mp = in_dir / "mask" / f"{nm}.png"
        mask.append(_read_png(mp) if mp.exists() else None)
    return {"names": names, "rgb": rgb, "depth": depth, "mask": mask,
            "meta": meta, "intrinsics": intr}


def _mat_to_quat(m: np.ndarray):
    """Rotation matrix -> (qx, qy, qz, qw). numpy-only (no scipy — method envs lack it)."""
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    return x, y, z, w


def write_tum(path: Path, timestamps, poses):
    """poses: (N,4,4) camera-to-world. TUM: ts tx ty tz qx qy qz qw."""
    lines = []
    for ts, T in zip(timestamps, poses):
        T = np.asarray(T, dtype=np.float64)
        t = T[:3, 3]
        qx, qy, qz, qw = _mat_to_quat(T[:3, :3])
        lines.append(f"{ts} {t[0]:.6f} {t[1]:.6f} {t[2]:.6f} "
                     f"{qx:.6f} {qy:.6f} {qz:.6f} {qw:.6f}")
    Path(path).write_text("\n".join(lines) + "\n")


def write_cloud(path: Path, points: np.ndarray, colors: np.ndarray | None = None):
    """Binary-little-endian PLY writer (numpy-only; open3d reads it fine in eval)."""
    pts = np.asarray(points, dtype=np.float32)
    n = len(pts)
    has_c = colors is not None and len(colors) == n and n > 0
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {n}",
              "property float x", "property float y", "property float z"]
    if has_c:
        header += ["property uchar red", "property uchar green", "property uchar blue"]
    header.append("end_header")
    if has_c:
        c = np.asarray(colors, dtype=np.float64)
        if c.size and c.max() <= 1.0:
            c = c * 255.0
        c = np.clip(c, 0, 255).astype(np.uint8)
        dt = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                       ("r", "u1"), ("g", "u1"), ("b", "u1")])
        arr = np.empty(n, dt)
        arr["x"], arr["y"], arr["z"] = pts[:, 0], pts[:, 1], pts[:, 2]
        arr["r"], arr["g"], arr["b"] = c[:, 0], c[:, 1], c[:, 2]
    else:
        dt = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4")])
        arr = np.empty(n, dt)
        if n:
            arr["x"], arr["y"], arr["z"] = pts[:, 0], pts[:, 1], pts[:, 2]
    with open(path, "wb") as f:
        f.write(("\n".join(header) + "\n").encode())
        f.write(arr.tobytes())


def write_runner_perf(out_dir: Path, per_window_latency_s=None, latency_end_to_end_s=0.0,
                      ckpt_size_mb=0.0, extra=None):
    d = {"per_window_latency_s": per_window_latency_s or [],
         "latency_end_to_end_s": latency_end_to_end_s,
         "ckpt_size_mb": ckpt_size_mb,
         "extra": extra or {}}
    (Path(out_dir) / "perf_runner.json").write_text(json.dumps(d, indent=2))


# -- cube-face inputs (rerun-v3, decisions D28) ---------------------------------
# A `cube` input dir holds the 360 deg view as n pinhole cube faces per timestep,
# interleaved: image 4t+k is face k of timestep t (faces.json gives the order and each
# face's rotation in the body camera frame). The method sees every face as a frame of
# its own; afterwards its per-image poses are collapsed back to one pose per timestep.

def _quat_to_mat(q):
    x, y, z, w = q
    n = np.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def read_tum(path: Path):
    out = {}
    for ln in Path(path).read_text().splitlines():
        v = ln.split()
        if len(v) < 8 or ln.lstrip().startswith("#"):
            continue
        T = np.eye(4)
        T[:3, :3] = _quat_to_mat([float(a) for a in v[4:8]])
        T[:3, 3] = [float(a) for a in v[1:4]]
        out[int(round(float(v[0])))] = T
    return out


def collapse_cube_faces(in_dir: Path, out_dir: Path):
    """If `in_dir` is a cube-face input, rewrite out_dir/poses.tum to one pose per
    timestep (the FRONT face, whose camera frame is the body camera frame), keep the
    per-face poses in poses_faces.tum, and return rig-consistency stats:

      rig_rot_deg_*   how far the 4 faces' implied body orientations disagree
                      (face pose x R_face^-1 should be identical for all faces)
      rig_trans_rel_* spread of the 4 face centres (same optical centre in truth),
                      relative to the median step between timesteps

    Returns None for a normal (non-cube) input."""
    in_dir, out_dir = Path(in_dir), Path(out_dir)
    fj = in_dir / "faces.json"
    pt = out_dir / "poses.tum"
    if not fj.exists() or not pt.exists():
        return None
    faces = json.loads(fj.read_text())
    nf = int(faces["n_faces"])
    Rf = [np.asarray(r, float) for r in faces["R_body_face"]]
    est = read_tum(pt)
    (out_dir / "poses_faces.tum").write_text(pt.read_text())
    ts = sorted({i // nf for i in est})
    keep_t, keep_T, rot_err, tr_spread = [], [], [], []
    for t in ts:
        got = {k: est[nf * t + k] for k in range(nf) if (nf * t + k) in est}
        if 0 not in got:
            continue
        keep_t.append(t)
        keep_T.append(got[0])
        if len(got) == nf:
            Rb = [got[k][:3, :3] @ Rf[k].T for k in range(nf)]
            for k in range(1, nf):
                c = (np.trace(Rb[0].T @ Rb[k]) - 1) / 2
                rot_err.append(float(np.degrees(np.arccos(np.clip(c, -1, 1)))))
            C = np.stack([got[k][:3, 3] for k in range(nf)])
            tr_spread.append(float(np.linalg.norm(C - C.mean(0), axis=1).max()))
    write_tum(pt, keep_t, keep_T)
    P = np.stack([T[:3, 3] for T in keep_T]) if keep_T else np.zeros((0, 3))
    step = float(np.median(np.linalg.norm(np.diff(P, axis=0), axis=1))) if len(P) > 1 else 0.0
    rel = [s / step for s in tr_spread] if step > 0 else []
    stats = {"cube_faces": nf, "n_timesteps_posed": len(keep_t),
             "n_face_poses": len(est),
             "rig_rot_deg_median": float(np.median(rot_err)) if rot_err else None,
             "rig_rot_deg_p95": float(np.percentile(rot_err, 95)) if rot_err else None,
             "rig_trans_rel_median": float(np.median(rel)) if rel else None}
    print(f"[cube] {len(est)} face poses -> {len(keep_t)} timestep poses; rig rotation "
          f"disagreement median {stats['rig_rot_deg_median']} deg")
    return stats
