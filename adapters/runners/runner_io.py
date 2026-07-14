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
        dp = in_dir / "depth" / f"{nm}.npy"
        depth.append(np.load(dp) if dp.exists() else None)
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
