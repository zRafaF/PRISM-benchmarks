#!/usr/bin/env python
"""When did the mapper get lost?  Tracking-continuity metrics from poses + GT only.

ATE says how far off a trajectory is on average. It does not say whether the method
drifted smoothly (a recoverable, globally-wrong-but-locally-right map) or lost track
(the map tears and the scene is duplicated: the "three copies" failure). These metrics
separate the two. All of them need only poses.tum and poses_gt.tum, so they apply to
every method, scale-free or metric.

Per sequence:
  tracked_pct   LOCAL continuity. Slide a window of WIN_M metres of GT path (step
                STEP_M) along the sequence, Sim(3)-align each window on its own, and
                call it tracked if its RMSE < TAU_LOC_M and its worst rotation error
                < TAU_ROT_DEG. Smooth drift passes (each window is locally right);
                a tear/jump fails every window that straddles it.
  n_lost        Number of loss EVENTS: maximal runs of untracked windows. 0 = never
                lost.
  lost_at_m     Path distance (m) where the first loss event starts (inf if none).
  segments      Greedy re-anchoring: grow a segment while its own Sim(3)-aligned RMSE
                stays < TAU_SEG_M; when it breaks, start a new one. segments-1 is how
                many times the method would need re-localising to stay within
                TAU_SEG_M; mean_seg_m is the average length tracked before that.
  survive_m     Distance-to-failure: align on the first ANCHOR_M metres only, then the
                path distance until the error first exceeds TAU_FAIL_M (drift or loss,
                whichever first; = path length if never). Pooled over sequences it
                gives a survival curve: fraction of runs still on track vs distance.

Usage:  python scripts/lost_metrics.py [--root .] [--glob 'p3_*'] [--plot]
Writes results/lost/lost_metrics.csv (+ survival.png with --plot).
"""
from __future__ import annotations

import argparse
import csv
import glob
import re
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

WIN_M, STEP_M = 2.0, 0.25
TAU_LOC_M, TAU_ROT_DEG = 0.05, 5.0
TAU_SEG_M = 0.10
ANCHOR_M, TAU_FAIL_M = 2.0, 0.30


def load_tum(p):
    out = {}
    for ln in Path(p).read_text().splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        v = [float(x) for x in ln.split()]
        T = np.eye(4)
        T[:3, :3] = R.from_quat(v[4:8]).as_matrix()
        T[:3, 3] = v[1:4]
        out[int(round(v[0]))] = T
    return out


def umeyama(src, dst):
    ms, md = src.mean(0), dst.mean(0)
    A, B = src - ms, dst - md
    U, S, Vt = np.linalg.svd(B.T @ A / len(src))
    D = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        D[2, 2] = -1
    Rm = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / max(A.var(0).sum(), 1e-12)
    return s, Rm, md - s * Rm @ ms


def seg_err(E, G, a, b):
    """Sim(3)-align frames a..b-1; return (rmse_m, max_rot_err_deg)."""
    pe, pg = E[a:b, :3, 3], G[a:b, :3, 3]
    if np.ptp(pe, axis=0).max() < 1e-6:
        return np.inf, 180.0
    s, Rm, t = umeyama(pe, pg)
    rmse = float(np.sqrt(((pg - (s * (Rm @ pe.T).T + t)) ** 2).sum(1).mean()))
    Re = np.einsum("ij,njk->nik", Rm, E[a:b, :3, :3])
    rel = np.einsum("nji,njk->nik", G[a:b, :3, :3], Re)        # G^T (R E)
    ang = np.degrees(np.arccos(np.clip((np.trace(rel, axis1=1, axis2=2) - 1) / 2, -1, 1)))
    # remove the window's mean rotation offset (heading of a scale-free method)
    return rmse, float(np.max(np.abs(ang - np.median(ang)))) if len(ang) else 0.0


def analyse(E, G):
    pg = G[:, :3, 3]
    cum = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pg, axis=0), axis=1))])
    L = float(cum[-1])
    # local windows
    starts = np.arange(0.0, max(L - WIN_M, 0.0) + 1e-9, STEP_M)
    ok, at = [], []
    for s0 in starts:
        a = int(np.searchsorted(cum, s0))
        b = int(np.searchsorted(cum, s0 + WIN_M)) + 1
        if b - a < 4:
            continue
        rm, rot = seg_err(E, G, a, b)
        ok.append(rm < TAU_LOC_M and rot < TAU_ROT_DEG)
        at.append(s0)
    ok = np.array(ok, bool)
    events = int(np.sum(~ok[1:] & ok[:-1]) + (0 if ok.size == 0 or ok[0] else 1)) if ok.size else 0
    lost_at = float(at[int(np.argmax(~ok))]) if ok.size and (~ok).any() else float("inf")
    # greedy segments (step 1 frame, coarse-to-fine)
    segs, a, n = [], 0, len(E)
    while a < n - 3:
        b = a + 4
        while b < n:
            nb = min(n, b + 3)
            if seg_err(E, G, a, nb)[0] >= TAU_SEG_M:
                break
            b = nb
        segs.append(cum[min(b, n) - 1] - cum[a])
        a = b
    # distance to failure
    k = max(4, int(np.searchsorted(cum, ANCHOR_M)) + 1)
    s, Rm, t = umeyama(E[:k, :3, 3], pg[:k])
    err = np.linalg.norm(pg - (s * (Rm @ E[:, :3, 3].T).T + t), axis=1)
    bad = np.flatnonzero(err > TAU_FAIL_M)
    survive = float(cum[bad[0]]) if len(bad) else L
    return dict(path_m=L, tracked_pct=100.0 * ok.mean() if ok.size else float("nan"),
                n_lost=events, lost_at_m=lost_at, segments=len(segs),
                mean_seg_m=float(np.mean(segs)) if segs else 0.0,
                survive_m=survive, survived=bool(len(bad) == 0))


def main():
    global TAU_LOC_M
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--glob", default="*")
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--tau-loc", type=float, default=TAU_LOC_M, help="local-window RMSE threshold (m)")
    a = ap.parse_args()
    TAU_LOC_M = a.tau_loc
    root = Path(a.root)
    rows = []
    for p in sorted(glob.glob(str(root / "results" / a.glob / "*" / "*" / "*" / "*" / "poses.tum"))):
        parts = Path(p).parts
        method, ds, scene, traj = parts[-6], parts[-5], parts[-4], parts[-3]
        gt_p = root / "dataset" / "exports" / ds / scene / traj / "poses_gt.tum"
        if not gt_p.exists():
            continue
        est, gt = load_tum(p), load_tum(gt_p)
        k = sorted(set(est) & set(gt))
        if len(k) < 10:
            continue
        E = np.stack([est[i] for i in k]); G = np.stack([gt[i] for i in k])
        m = re.search(r"([0-9.]+)hz", traj)
        r = dict(method=method, scene=scene, traj=traj, rate_hz=float(m.group(1)) if m else None,
                 n=len(k), **analyse(E, G))
        rows.append(r)
        print(f"{method:18s} {scene:12s} {traj:18s} tracked {r['tracked_pct']:5.1f}%  "
              f"lost x{r['n_lost']:<2d} first@{r['lost_at_m']:5.1f}m  segments {r['segments']:3d} "
              f"(mean {r['mean_seg_m']:4.1f} m)  survive {r['survive_m']:5.1f}/{r['path_m']:.0f} m")
    out = root / "results" / "lost"
    out.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(out / "lost_metrics.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    if a.plot and rows:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for meth in sorted({r["method"] for r in rows}):
            rr = [r for r in rows if r["method"] == meth]
            d = np.linspace(0, max(r["path_m"] for r in rr), 200)
            frac = [np.mean([r["survived"] or r["survive_m"] >= x for r in rr]) for x in d]   # survivors are censored, not failed
            ax.plot(d, frac, label=f"{meth} (n={len(rr)})")
        ax.set_xlabel("distance travelled (m)"); ax.set_ylabel(f"fraction of runs within {TAU_FAIL_M} m")
        ax.set_ylim(0, 1.02); ax.legend(fontsize=8); ax.grid(alpha=0.3)
        ax.set_title(f"Distance to failure (anchored on the first {ANCHOR_M:g} m)")
        fig.tight_layout(); fig.savefig(out / "survival.png", dpi=120)
    print(f">> {out}/lost_metrics.csv")


if __name__ == "__main__":
    main()
