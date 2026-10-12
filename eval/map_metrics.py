#!/usr/bin/env python
"""Map-centric scores, independent of the trajectory (decisions D35).

eval_recon.py places every cloud with the Sim(3) that aligns its TRAJECTORY to the GT
(+ a 15 cm ICP). A map whose trajectory is poor is then judged partly by its trajectory.
This script scores the map on its own:

  map-only alignment   starting from the trajectory Sim(3), a coarse-to-fine trimmed
                       Sim(3) ICP of the cloud against the GT (radii halve each stage),
                       so each method gets the placement that best fits ITS map.
  global accuracy      distances map -> GT after that alignment: median, mean (capped),
                       precision at several thresholds (Replica 2/5/10 cm, real 10/20/50 cm),
                       and the GT -> map completeness / recall at the same thresholds.
  local accuracy       the map cut into square tiles (Replica 2 m, real 5 m); each tile is
                       re-aligned on its own (rigid ICP) and scored: median of tile medians
                       and the share of points farther than tau after local alignment
                       ("ghost share"). This is the map analogue of RPE vs. ATE: global
                       drift is removed, doubled / misregistered surfaces are not.

Region: only map points within R of this sequence's GT cameras (R = the eval co-visibility
range: 4.5 m, 10 m on the hall) and within 3 m of a GT surface point are scored (the GT
map does not exist farther away; on 360Loc query routes it comes from the reference
route). Completeness uses GT points within R of the GT cameras (no occlusion test:
coverage-dependent, so it favours wide-FoV input; accuracy and the local scores do not).

Numpy/scipy only. Output: <run>/map.json; summary printed.

  python eval/map_metrics.py [--config config.yaml] [--glob 'results/*/replica/*/*/*'] [--force]
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import lost_metrics as lm  # noqa: E402

SKIP = ("report", "bundles", "figures", "lost", "real360", "_deepdive")


# ---------------------------------------------------------------- I/O
def _ply_header(p):
    tm = {"float": "<f4", "float32": "<f4", "double": "<f8", "float64": "<f8", "uchar": "u1", "uint8": "u1",
          "int": "<i4", "int32": "<i4", "uint": "<u4", "uint32": "<u4", "char": "i1", "short": "<i2", "ushort": "<u2"}
    els, cur = [], None
    with open(p, "rb") as f:
        while True:
            ln = f.readline().decode("ascii", "ignore").strip()
            if ln.startswith("element"):
                _, name, n = ln.split()
                cur = [name, int(n), []]; els.append(cur)
            elif ln.startswith("property list"):
                _, _, ct, it, name = ln.split()
                cur[2].append((name, ("list", tm[ct], tm[it])))
            elif ln.startswith("property"):
                _, t, name = ln.split()[:3]
                cur[2].append((name, tm[t]))
            elif ln == "end_header":
                return els, f.tell()


def read_points(p, n_max, seed=0):
    els, off = _ply_header(p)
    name, nv, props = els[0]
    mm = np.memmap(p, dtype=np.dtype(props), mode="r", offset=off, shape=(nv,))
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(nv, n_max, replace=False)) if nv > n_max else slice(None)
    a = mm[idx]
    return np.stack([a["x"], a["y"], a["z"]], 1).astype(np.float64)


def sample_mesh(p, n, seed=0):
    """Area-uniform samples of a binary PLY triangle mesh (vertex element, then faces)."""
    els, off = _ply_header(p)
    (vn, nv, vprops), (fn, nf, fprops) = els[0], els[1]
    vdt = np.dtype(vprops)
    V = np.memmap(p, dtype=vdt, mode="r", offset=off, shape=(nv,))
    _, (_, ct, it) = fprops[0]
    fdt = np.dtype([("n", ct), ("i", it, (3,))])
    F = np.memmap(p, dtype=fdt, mode="r", offset=off + nv * vdt.itemsize, shape=(nf,))
    assert (F["n"][:1000] == 3).all(), "triangle meshes only"
    X = np.stack([V["x"], V["y"], V["z"]], 1).astype(np.float64)
    tri = X[np.asarray(F["i"])]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(seed)
    f = rng.choice(nf, n, p=area / area.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    t = tri[f]
    return t[:, 0] * (1 - s)[:, None] + t[:, 1] * (s * (1 - r2))[:, None] + t[:, 2] * (s * r2)[:, None]


# ---------------------------------------------------------------- geometry
def apply(T, X):
    s, R, t = T
    return s * (R @ X.T).T + t


def compose(A, B):
    """A after B."""
    sa, Ra, ta = A
    sb, Rb, tb = B
    return sa * sb, Ra @ Rb, sa * (Ra @ tb) + ta


def icp(X, tree, Y, T0, radii, iters=8, scale=True, trim=0.9):
    """Trimmed point-to-point (Sim(3) or SE(3)) ICP, coarse-to-fine radii."""
    T = T0
    for r in radii:
        for _ in range(iters):
            P = apply(T, X)
            d, j = tree.query(P, distance_upper_bound=r, workers=-1)
            ok = np.isfinite(d)
            if ok.sum() < 50:
                break
            dk = d[ok]
            keep = dk <= np.quantile(dk, trim)
            src, dst = P[ok][keep], Y[j[ok][keep]]
            if scale:
                s, R, t = lm.umeyama(src, dst)
            else:
                mu_s, mu_d = src.mean(0), dst.mean(0)
                U, _, Vt = np.linalg.svd((dst - mu_d).T @ (src - mu_s))
                D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
                R = U @ D @ Vt; s = 1.0; t = mu_d - R @ mu_s
            T = compose((s, R, t), T)
    return T


# ---------------------------------------------------------------- scoring
_GT: dict = {}


def score(run, cfg_far, taus, tile, radii, n_pred=600_000, n_gt=1_000_000):
    arm, ds, sc, tj, var = run.parts[-5:]
    exp = ROOT / "dataset" / "exports" / ds / sc / tj
    est, gt = lm.load_tum(run / "poses.tum"), lm.load_tum(exp / "poses_gt.tum")
    k = sorted(set(est) & set(gt))
    E = np.stack([est[i][:3, 3] for i in k]); G = np.stack([gt[i][:3, 3] for i in k])
    Ttraj = lm.umeyama(E, G)
    Gcam = np.stack([gt[i][:3, 3] for i in sorted(gt)])
    key = (ds, sc, "cloud" if (exp / "gt_cloud.ply").exists() else "mesh")
    if key not in _GT:                     # same GT for every run of a scene (sorted glob)
        _GT.clear()
        if (exp / "gt.npz").exists():      # pre-subsampled copy (same sampling as below)
            _GT[key] = np.load(exp / "gt.npz")["xyz"].astype(np.float64)
        else:
            _GT[key] = read_points(exp / "gt_cloud.ply", n_gt) if key[2] == "cloud" else sample_mesh(exp / "gt_mesh.ply", n_gt)
    Y = _GT[key]
    camtree = cKDTree(Gcam)
    Y = Y[camtree.query(Y, distance_upper_bound=cfg_far, workers=-1)[0] < cfg_far]
    ytree = cKDTree(Y)
    X = np.load(run / "cloud.npz")["xyz"].astype(np.float64) if (run / "cloud.npz").exists() \
        else read_points(run / "cloud.ply", n_pred, seed=1)

    def region(P):
        return (camtree.query(P, distance_upper_bound=cfg_far, workers=-1)[0] < cfg_far) & \
               (ytree.query(P, distance_upper_bound=3.0, workers=-1)[0] < 3.0)

    # map-only alignment (ICP on a 100k subset of the region)
    P0 = apply(Ttraj, X)
    sub = np.where(region(P0))[0]
    rng = np.random.default_rng(2)
    sub = rng.choice(sub, min(len(sub), 100_000), replace=False) if len(sub) else sub
    Tmap = icp(X[sub], ytree, Y, Ttraj, radii) if len(sub) > 100 else Ttraj

    out = {"arm": arm, "dataset": ds, "scene": sc, "traj": tj, "variant": var,
           "region_m": cfg_far, "taus_m": taus, "tile_m": tile,
           "scale_traj": Ttraj[0], "scale_map": Tmap[0],
           "T_traj": {"s": float(Ttraj[0]), "R": np.asarray(Ttraj[1]).tolist(), "t": np.asarray(Ttraj[2]).tolist()},
           "T_map": {"s": float(Tmap[0]), "R": np.asarray(Tmap[1]).tolist(), "t": np.asarray(Tmap[2]).tolist()},
           "map_vs_traj_shift_m": float(np.median(np.linalg.norm(apply(Tmap, X[sub]) - apply(Ttraj, X[sub]), axis=1))) if len(sub) else None}
    for tag, T in (("traj", Ttraj), ("map", Tmap)):
        P = apply(T, X)
        P = P[region(P)]
        if len(P) < 100:
            out[tag] = None
            continue
        da, _ = ytree.query(P, workers=-1)
        dc, _ = cKDTree(P).query(Y, workers=-1)
        o = {"n_scored": int(len(P)), "acc_median_m": float(np.median(da)),
             "acc_mean_m": float(np.mean(np.minimum(da, 1.0))),
             "comp_median_m": float(np.median(dc))}
        for tau in taus:
            pr, rc = float((da < tau).mean()), float((dc < tau).mean())
            o[f"P@{tau:g}"], o[f"R@{tau:g}"] = pr, rc
            o[f"F@{tau:g}"] = 2 * pr * rc / (pr + rc) if pr + rc > 0 else 0.0
        out[tag] = o
        if tag == "map":
            # local accuracy: tiles in the ground plane (smallest-extent GT axis = vertical)
            v = int(np.argmin(np.ptp(Gcam, 0))) if ds != "replica" else 2
            h = [i for i in range(3) if i != v]
            cell = np.floor(P[:, h] / tile).astype(np.int64)
            key = cell[:, 0] * 1_000_003 + cell[:, 1]
            order = np.argsort(key); ks, starts = np.unique(key[order], return_index=True)
            ends = np.r_[starts[1:], len(order)]
            meds, ghost, wts = [], [], []
            for a, b in zip(starts, ends):
                if b - a < 300:
                    continue
                Q = P[order[a:b]]
                if len(Q) > 20000:
                    Q = Q[rng.choice(len(Q), 20000, replace=False)]
                lo, hi = Q.min(0) - tile / 2, Q.max(0) + tile / 2
                Yi = Y[np.all((Y >= lo) & (Y <= hi), 1)]
                if len(Yi) < 300:
                    continue
                ti = cKDTree(Yi)
                Tl = icp(Q, ti, Yi, (1.0, np.eye(3), np.zeros(3)), [r / 2 for r in radii[-3:]], iters=6, scale=False)
                dl, _ = ti.query(apply(Tl, Q))
                meds.append(np.median(dl)); ghost.append([(dl > tau).mean() for tau in taus]); wts.append(b - a)
            if meds:
                w = np.asarray(wts, float)
                out["local"] = {"n_tiles": len(meds), "acc_median_of_tiles_m": float(np.median(meds)),
                                **{f"ghost@{tau:g}": float(np.average(np.asarray(ghost)[:, i], weights=w))
                                   for i, tau in enumerate(taus)}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--glob", default="results/*/*/*/*/*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--budget", type=float, default=0, help="stop starting new runs after N s (0 = no limit)")
    a = ap.parse_args()
    from bench.config import load_config
    cfg = load_config(a.config)
    mk = cfg["eval"]["mask"]
    dirs = sorted(glob.glob(str(ROOT / a.glob)), key=lambda d: Path(d).parts[-4:-1] + Path(d).parts[-5:-4])
    import time
    t0 = time.time()
    for d in dirs:
        if a.budget and time.time() - t0 > a.budget:
            print("[map] budget reached"); break
        run = Path(d)
        if run.parts[-5] in SKIP or run.parts[-5].startswith(("p3_", "prism-benchmarks_")):
            continue
        if not (((run / "cloud.ply").exists() or (run / "cloud.npz").exists()) and (run / "poses.tum").exists()):
            continue
        pf = json.loads((run / "perf.json").read_text()) if (run / "perf.json").exists() else {}
        if not pf.get("completed"):
            continue
        if (run / "map.json").exists() and not a.force and \
                (run / "map.json").stat().st_mtime > max((run / n).stat().st_mtime for n in ("cloud.ply", "cloud.npz") if (run / n).exists()):
            continue
        ds, sc = run.parts[-4], run.parts[-3]
        far = float((mk.get("frustum_far_m_by_scene") or {}).get(sc, mk["frustum_far_m"]))
        real = ds != "replica"
        taus = [0.10, 0.20, 0.50] if real else [0.02, 0.05, 0.10]
        tile = 5.0 if real else 2.0
        radii = [2.0, 1.0, 0.5, 0.25] if real else [0.5, 0.25, 0.10, 0.05]
        try:
            o = score(run, far, taus, tile, radii)
        except Exception as e:  # one broken run must not stop the pass
            print(f"[map] {run}: FAILED {e!r}")
            continue
        (run / "map.json").write_text(json.dumps(o, indent=2))
        m, t, l = o.get("map") or {}, o.get("traj") or {}, o.get("local") or {}
        tau = taus[1]
        print(f"[map] {'/'.join(run.parts[-5:])}: acc med traj {t.get('acc_median_m', float('nan')):.3f} -> map "
              f"{m.get('acc_median_m', float('nan')):.3f} m, F@{tau:g} {t.get(f'F@{tau:g}', float('nan')):.2f} -> "
              f"{m.get(f'F@{tau:g}', float('nan')):.2f}, local med {l.get('acc_median_of_tiles_m', float('nan')):.3f} m, "
              f"ghost@{tau:g} {l.get(f'ghost@{tau:g}', float('nan')):.2f}")


if __name__ == "__main__":
    main()
