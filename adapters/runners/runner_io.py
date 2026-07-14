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


def write_tum(path: Path, timestamps, poses):
    """poses: (N,4,4) camera-to-world. TUM: ts tx ty tz qx qy qz qw."""
    from scipy.spatial.transform import Rotation
    lines = []
    for ts, T in zip(timestamps, poses):
        T = np.asarray(T)
        t = T[:3, 3]
        q = Rotation.from_matrix(T[:3, :3]).as_quat()
        lines.append(f"{ts} {t[0]:.6f} {t[1]:.6f} {t[2]:.6f} "
                     f"{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}")
    Path(path).write_text("\n".join(lines) + "\n")


def write_cloud(path: Path, points: np.ndarray, colors: np.ndarray | None = None):
    import open3d as o3d
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64))
    if colors is not None:
        c = np.asarray(colors, dtype=np.float64)
        if c.size and c.max() > 1.0:
            c = c / 255.0
        pcd.colors = o3d.utility.Vector3dVector(c)
    o3d.io.write_point_cloud(str(path), pcd)


def write_runner_perf(out_dir: Path, per_window_latency_s=None, latency_end_to_end_s=0.0,
                      ckpt_size_mb=0.0, extra=None):
    d = {"per_window_latency_s": per_window_latency_s or [],
         "latency_end_to_end_s": latency_end_to_end_s,
         "ckpt_size_mb": ckpt_size_mb,
         "extra": extra or {}}
    (Path(out_dir) / "perf_runner.json").write_text(json.dumps(d, indent=2))
