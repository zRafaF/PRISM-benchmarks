#!/usr/bin/env python
"""Same-back-end control: fuse a baseline's per-frame depth with its own poses through a
TSDF with PRISM's voxel size and depth cap, and write the result as a separate arm
(default `laser_tsdf`) that the normal evaluation then scores like any other method.

PRISM's map comes out of a TSDF (nvblox, cube faces) while the baselines output their
raw per-frame point maps. This control answers "is PRISM's map better only because of
the fusion back-end?": if LASER's map stays far from the reference after the same
fusion, the difference is in the geometry/poses, not in the TSDF.

Input: <run>/_depth/fNNNNN.npz (depth float16 z-depth, K, c2w, rgb), written by
laser_runner.py when LASER_SAVE_DEPTH=1. A sparse projective TSDF in numpy (below;
Open3D 0.20's ScalableTSDFVolume returned empty clouds in our tests), truncation 4
voxels, every 2nd pixel, surface = interpolated zero crossings. The _depth folder is
deleted afterwards unless --keep.

  python eval/fuse_tsdf.py --config config.yaml --run results/laser/loc360/atrium/ref/synthetic_fov
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import load_config  # noqa: E402


# ---- sparse TSDF in numpy (no Open3D: its ScalableTSDFVolume returns empty clouds in 0.20)
_OFF = 1 << 20


def _pack(ijk):
    ijk = ijk.astype(np.int64) + _OFF
    return (ijk[:, 0] << 42) | (ijk[:, 1] << 21) | ijk[:, 2]


def _unpack(k):
    m = (1 << 21) - 1
    return np.stack([(k >> 42) & m, (k >> 21) & m, k & m], 1) - _OFF


class SparseTSDF:
    """Weighted running-average TSDF on a hashed voxel grid (keys sorted, merged in
    batches). Projective SDF along each pixel ray, truncated at `trunc`; free space
    beyond the truncation band is not carved (as in KinectFusion-style fusion)."""

    def __init__(self, voxel, trunc, max_depth, stride=2):
        self.v, self.t, self.maxd, self.st = float(voxel), float(trunc), float(max_depth), int(stride)
        self.k = np.zeros(0, np.int64); self.s = np.zeros(0); self.w = np.zeros(0); self.c = np.zeros((0, 3))
        self._buf = []

    def integrate(self, depth, K, c2w, rgb):
        st = self.st
        d = depth[::st, ::st].astype(np.float64)
        H, W = d.shape
        u, vv = np.meshgrid(np.arange(W) * st, np.arange(H) * st)
        ok = np.isfinite(d) & (d > 0) & (d < self.maxd)
        d, u, vv = d[ok], u[ok], vv[ok]
        col = rgb[::st, ::st].reshape(-1, 3)[ok.reshape(-1)].astype(np.float64)
        ray = np.stack([(u - K[0, 2]) / K[0, 0], (vv - K[1, 2]) / K[1, 1], np.ones_like(d)], 1)
        nrm = np.linalg.norm(ray, axis=1)
        n = int(np.ceil(self.t / self.v))
        R, c = c2w[:3, :3], c2w[:3, 3]
        ks, ss, cs = [], [], []
        for j in range(-n, n + 1):                      # samples in the band around the surface
            zz = d + j * self.v / nrm                   # step of one voxel along the ray
            sdf = np.clip((d - zz) * nrm / self.t, -1, 1)
            p = (R @ (ray * zz[:, None]).T).T + c
            ks.append(_pack(np.floor(p / self.v))); ss.append(sdf); cs.append(col)
        self._buf.append((np.concatenate(ks), np.concatenate(ss), np.concatenate(cs)))
        if sum(len(b[0]) for b in self._buf) > 3e7:
            self._merge()

    def _merge(self):
        if not self._buf:
            return
        k = np.concatenate([self.k] + [b[0] for b in self._buf])
        s = np.concatenate([self.s * self.w] + [b[1] for b in self._buf])
        w = np.concatenate([self.w] + [np.ones(len(b[0])) for b in self._buf])
        c = np.concatenate([self.c * self.w[:, None]] + [b[2] for b in self._buf])
        self._buf = []
        uk, inv = np.unique(k, return_inverse=True)
        W_ = np.bincount(inv, w)
        self.s = np.bincount(inv, s) / W_
        self.c = np.stack([np.bincount(inv, c[:, i]) for i in range(3)], 1) / W_[:, None]
        self.k, self.w = uk, W_

    def extract(self, min_weight=1.0):
        """Zero crossings between face neighbours, linearly interpolated (points + colours)."""
        self._merge()
        keep = self.w >= min_weight
        k, s, c = self.k[keep], self.s[keep], self.c[keep]
        ijk = _unpack(k)
        P, C = [], []
        for ax in range(3):
            nb = ijk.copy(); nb[:, ax] += 1
            nk = _pack(nb)
            idx = np.searchsorted(k, nk); idx[idx >= len(k)] = 0
            hit = k[idx] == nk
            a, b = np.where(hit)[0], idx[hit]
            s0, s1 = s[a], s[b]
            cr = (np.sign(s0) != np.sign(s1)) & (np.abs(s0) < 0.999) & (np.abs(s1) < 0.999)
            a, b, s0, s1 = a[cr], b[cr], s0[cr], s1[cr]
            f = s0 / (s0 - s1)
            p = (ijk[a] + 0.5).astype(np.float64)
            p[:, ax] += f
            P.append(p * self.v); C.append(c[a] * (1 - f[:, None]) + c[b] * f[:, None])
        return np.concatenate(P), np.clip(np.concatenate(C), 0, 255).astype(np.uint8)


def write_ply(p, P, C):
    v = np.empty(len(P), dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("red", "u1"), ("green", "u1"), ("blue", "u1")])
    v["x"], v["y"], v["z"] = P[:, 0], P[:, 1], P[:, 2]
    v["red"], v["green"], v["blue"] = C[:, 0], C[:, 1], C[:, 2]
    with open(p, "wb") as f:
        f.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(P)}\n"
                 "property float x\nproperty float y\nproperty float z\n"
                 "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n").encode())
        f.write(v.tobytes())


def prism_fusion_params(cfg, scene=None) -> tuple[float, float]:
    """Voxel size and range of the PRISM arm in the config: the one named FUSE_LIKE
    (env), else `prism`, else the first arm that runs the PRISM runner (e.g. prism_r8)."""
    import os
    eng = cfg["engine"]
    vox, maxd = float(eng["voxel_size"]), float(eng["max_depth"])
    ms = cfg.get("methods", [])
    like = os.environ.get("FUSE_LIKE")
    pick = [m for m in ms if m["name"] == like] or [m for m in ms if m["name"] == "prism"] or \
        [m for m in ms if m.get("runner") == "prism" or m["name"].startswith("prism")]
    for m in pick[:1]:
        env = dict(m.get("run_env") or {})
        env.update((m.get("scene_env") or {}).get(scene) or {})
        vox = float(env.get("PRISM_VOXEL_SIZE", vox))
        maxd = float(env.get("PRISM_MAX_DEPTH", maxd))
    return vox, maxd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--run", required=True, help="results/<arm>/<ds>/<scene>/<traj>/<variant>")
    ap.add_argument("--arm", default=None, help="output arm name (default <arm>_tsdf)")
    ap.add_argument("--keep", action="store_true", help="keep the _depth folder")
    a = ap.parse_args()
    cfg = load_config(a.config)
    run = Path(a.run)
    files = sorted((run / "_depth").glob("f*.npz"))
    if not files:
        sys.exit(f"[fuse_tsdf] no {run}/_depth/f*.npz (run with LASER_SAVE_DEPTH=1)")
    parts = run.parts
    i = parts.index("results")
    vox, maxd = prism_fusion_params(cfg, parts[i + 3])
    # The baseline's depth is in its own (arbitrary) scale. Fuse at PRISM's resolution
    # in METRES: voxel and cap divided by the Sim(3) scale that maps its trajectory onto
    # the GT (the same scale the evaluation applies to its cloud).
    ds, scene, traj = parts[i + 2:i + 5]
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import lost_metrics as lm
    est = lm.load_tum(run / "poses.tum")
    gt = lm.load_tum(Path(__file__).resolve().parents[1] / "dataset" / "exports" / ds / scene / traj / "poses_gt.tum")
    k = sorted(set(est) & set(gt))
    s_gt, _, _ = lm.umeyama(np.stack([est[j][:3, 3] for j in k]), np.stack([gt[j][:3, 3] for j in k]))
    vox, maxd = vox / s_gt, maxd / s_gt
    print(f"[fuse_tsdf] {parts[i + 1]} scale to metres {s_gt:.4f}: voxel {vox:.4f}, cap {maxd:.3f} (own units)")
    arm = a.arm or parts[i + 1] + "_tsdf"
    out = Path(*parts[:i + 1], arm, *parts[i + 2:])
    out.mkdir(parents=True, exist_ok=True)
    T = SparseTSDF(vox, 4 * vox, maxd, stride=2)
    for f in files:
        z = np.load(f)
        rgb = z["rgb"]
        if rgb.shape[:2] != z["depth"].shape:
            from PIL import Image
            rgb = np.asarray(Image.fromarray(rgb).resize(z["depth"].shape[::-1]))
        T.integrate(z["depth"].astype(np.float32), z["K"].astype(np.float64), z["c2w"].astype(np.float64), rgb)
    P, C = T.extract()
    write_ply(out / "cloud.ply", P, C)
    for n in ("poses.tum", "perf.json", "perf_runner.json", "config_resolved.yaml"):
        if (run / n).exists():
            shutil.copy2(run / n, out / n)
    (out / "arm_config.json").write_text(json.dumps(
        {"source_arm": parts[i + 1], "fusion": "sparse projective TSDF (eval/fuse_tsdf.py)", "voxel": vox,
         "sdf_trunc": 4 * vox, "max_depth": maxd, "units": "baseline's own (metric / scale_to_gt)",
         "scale_to_gt": s_gt, "frames": len(files)}, indent=2))
    print(f"[fuse_tsdf] {len(files)} frames, voxel {vox:.4f}, cap {maxd:.3f} (own units) -> {out}/cloud.ply ({len(P)} pts)")
    if not a.keep:
        shutil.rmtree(run / "_depth", ignore_errors=True)


if __name__ == "__main__":
    main()
