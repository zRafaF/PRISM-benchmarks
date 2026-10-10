#!/usr/bin/env python
"""Trajectory diagnosis for one sequence: WHERE and HOW each method goes wrong.

    make diag SCENE=apartment_1 TRAJ=synthetic_2.0hz_s0          # every method that ran it
    make diag SCENE=room_0 TRAJ=loop_2.0hz_s0 METHODS="prism vggtslam"

CPU only, a few seconds, reads results/<method>/... and dataset/exports/.../poses_gt.tum.
Prints a table and writes results/diag/<scene>_<traj>.png (top-down paths + heading
error over time). What each column tells you:

  ATE all / ATE 30   Sim(3)-aligned position error over the whole run / the first 30
                     frames. Small "30" + large "all" = the method works locally and DRIFTS.
  head. drift        heading (yaw) error at the end after aligning only the first 30
                     frames: the slow rotation that makes a lapped path come back as
                     rotated "ghost" copies of the scene.
  jumps >5deg        frame-to-frame rotation errors above 5 deg — sudden registration
                     failures (window / submap alignment), with the worst frames listed.
  conv test          relative rotations re-checked with the camera axes flipped
                     (OpenCV <-> OpenGL). If the flipped version is much better, the
                     method's poses use a different camera convention than the GT: a
                     harness bug, not method behaviour.
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config

FLIP = np.diag([1.0, -1.0, -1.0])        # OpenCV <-> OpenGL camera axes


def load_tum(p: Path) -> dict[int, np.ndarray]:
    out = {}
    for ln in p.read_text().splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        v = [float(x) for x in ln.split()]
        T = np.eye(4)
        T[:3, :3] = R.from_quat(v[4:8]).as_matrix()
        T[:3, 3] = v[1:4]
        out[int(round(v[0]))] = T
    return out


def umeyama(src: np.ndarray, dst: np.ndarray):
    ms, md = src.mean(0), dst.mean(0)
    A, B = src - ms, dst - md
    U, S, Vt = np.linalg.svd(B.T @ A / len(src))
    D = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        D[2, 2] = -1
    Rm = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / max(A.var(0).sum(), 1e-12)
    return s, Rm, md - s * Rm @ ms


def ang(Rm: np.ndarray) -> float:
    return float(np.degrees(np.arccos(np.clip((np.trace(Rm) - 1) / 2, -1, 1))))


def yaw_of(Rm: np.ndarray) -> float:
    f = Rm[:, 2]                         # camera forward (+z, OpenCV) in world
    return float(np.degrees(np.arctan2(f[1], f[0])))


def analyse(est: dict, gt: dict):
    k = sorted(set(est) & set(gt))
    if len(k) < 10:
        return None
    E = np.stack([est[i] for i in k]); G = np.stack([gt[i] for i in k])
    pe, pg = E[:, :3, 3], G[:, :3, 3]
    s, Ra, ta = umeyama(pe, pg)
    ate_all = np.sqrt(((pg - (s * (Ra @ pe.T).T + ta)) ** 2).sum(1).mean())
    n0 = min(30, len(k))
    s0, R0, t0 = umeyama(pe[:n0], pg[:n0])
    al0 = s0 * (R0 @ pe.T).T + t0
    ate_30 = np.sqrt(((pg[:n0] - al0[:n0]) ** 2).sum(1).mean())
    # heading error over time after aligning only the first 30 frames
    yaw_err = np.array([((yaw_of(R0 @ E[i, :3, :3]) - yaw_of(G[i, :3, :3]) + 180) % 360) - 180
                        for i in range(len(k))])
    # frame-to-frame rotation error, as-is and with flipped camera axes
    rpe, rpe_flip = [], []
    for i in range(1, len(k)):
        rg = G[i - 1, :3, :3].T @ G[i, :3, :3]
        re = E[i - 1, :3, :3].T @ E[i, :3, :3]
        rpe.append(ang(rg.T @ re))
        rpe_flip.append(ang(rg.T @ (FLIP @ re @ FLIP)))
    rpe, rpe_flip = np.array(rpe), np.array(rpe_flip)
    worst = np.argsort(rpe)[::-1][:5]
    return {
        "n": len(k), "frames": k, "scale": s, "ate_all": ate_all, "ate_30": ate_30,
        "yaw_err": yaw_err, "yaw_end": float(yaw_err[-1]), "yaw_max": float(np.abs(yaw_err).max()),
        "rpe_med": float(np.median(rpe)), "rpe_flip_med": float(np.median(rpe_flip)),
        "jumps": int((rpe > 5).sum()), "worst": [(k[j + 1], float(rpe[j])) for j in worst],
        "aligned": s * (Ra @ pe.T).T + ta, "gt": pg,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--traj", required=True)
    ap.add_argument("--methods", default="")
    ap.add_argument("--no-plot", action="store_true")
    a = ap.parse_args()
    cfg = load_config("config.yaml")
    ds = cfg["datasets"]["active"][0]
    gt_p = REPO_ROOT / "dataset" / "exports" / ds / a.scene / a.traj / "poses_gt.tum"
    if not gt_p.exists():
        print(f"!! no GT at {gt_p}"); return 1
    gt = load_tum(gt_p)
    pg = np.stack([gt[i][:3, 3] for i in sorted(gt)])
    gt_yaw = np.array([yaw_of(gt[i][:3, :3]) for i in sorted(gt)])
    gt_turn = np.abs((np.diff(gt_yaw) + 180) % 360 - 180)
    print(f"=== {ds}/{a.scene}/{a.traj}: {len(gt)} GT frames, path {np.linalg.norm(np.diff(pg, axis=0), axis=1).sum():.1f} m, "
          f"span {np.ptp(pg[:, 0]):.1f} x {np.ptp(pg[:, 1]):.1f} m, GT turn/frame median {np.median(gt_turn):.1f} deg (max {gt_turn.max():.1f})")

    methods = a.methods.split() or sorted({Path(p).parts[-6] for p in glob.glob(
        str(REPO_ROOT / "results" / "*" / ds / a.scene / a.traj / "*" / "poses.tum"))})
    rows = {}
    print(f"\n{'method':17s} {'n':>4s} {'ATE all':>8s} {'ATE 30':>7s} {'head. drift':>12s} {'jumps>5deg':>10s}  {'RPE med':>8s} {'conv test (flipped)':>20s}  worst frames (frame:deg)")
    for m in methods:
        ps = sorted(glob.glob(str(REPO_ROOT / "results" / m / ds / a.scene / a.traj / "*" / "poses.tum")))
        if not ps:
            print(f"{m:17s}  (no poses.tum)"); continue
        r = analyse(load_tum(Path(ps[0])), gt)
        if r is None:
            print(f"{m:17s}  (too few matching frames)"); continue
        rows[m] = r
        conv = "SUSPECT" if r["rpe_flip_med"] < 0.5 * r["rpe_med"] and r["rpe_med"] > 1 else "ok"
        print(f"{m:17s} {r['n']:4d} {100 * r['ate_all']:6.1f}cm {100 * r['ate_30']:5.1f}cm "
              f"{r['yaw_end']:+7.1f}deg end {r['jumps']:6d}      {r['rpe_med']:5.2f}deg {r['rpe_flip_med']:7.2f}deg {conv:>7s}  "
              + " ".join(f"{f}:{d:.0f}" for f, d in r["worst"]))
    if rows and not a.no_plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        ax1.plot(pg[:, 0], pg[:, 1], "k-", lw=2.5, label="GT")
        ax1.plot(pg[0, 0], pg[0, 1], "ko", ms=8)
        for m, r in rows.items():
            ax1.plot(r["aligned"][:, 0], r["aligned"][:, 1], lw=1.2, label=f"{m} ({100 * r['ate_all']:.0f} cm)")
            ax2.plot(r["frames"], r["yaw_err"], lw=1.2, label=m)
        ax1.set_aspect("equal"); ax1.legend(fontsize=8); ax1.set_title("top-down, Sim(3)-aligned to GT")
        ax2.axhline(0, color="k", lw=0.8); ax2.set_xlabel("frame"); ax2.set_ylabel("heading error (deg)")
        ax2.set_title("heading error vs GT (aligned on the first 30 frames)"); ax2.legend(fontsize=8)
        out = REPO_ROOT / "results" / "diag" / f"{a.scene}_{a.traj}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout(); fig.savefig(out, dpi=110)
        print(f"\n>> plot: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
