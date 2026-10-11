#!/usr/bin/env python
"""Quick-check table for the real 360 deg sequences (360Loc, decisions D31).

For every arm and camera variant under results/<arm>/<ds>/<scene>/<traj>/<variant>/:
  ATE        Sim(3)-aligned RMSE vs the lidar GT (cm)
  scale      for metric methods (PRISM): the Sim(3) scale est -> GT; 1.00 = metrically
             correct (scale error = |1 - scale|)
  tracked %, loss events, survive (m)   tracking continuity (scripts/lost_metrics.py)
  fps        input timesteps per second of processing (one 360 capture = one timestep,
             also for the cube-face variants), peak VRAM
  F@5cm      reconstruction F-score vs the GT map fused from 360Loc's depth maps, inside
             the pinhole co-visibility mask (needs `eval_recon.py` first: real360.sh fetch)
Writes results/real360/summary.csv.  Usage:
  PRISM_CONFIG_OVERLAY=config.real360.yaml uv run python scripts/real360_report.py
"""
from __future__ import annotations

import csv
import glob
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from bench.config import load_config, resolve_trajs  # noqa: E402
from diag import load_tum, umeyama  # noqa: E402
import lost_metrics as lm  # noqa: E402


def main() -> int:
    cfg = load_config("config.yaml")
    ds = cfg["datasets"]["active"][0]
    metric = {m["name"]: bool(m.get("metric")) for m in cfg.get("methods", []) + cfg.get("ablations", [])}
    arms = list(metric)
    # also arms run under another overlay (the offline references: panovggt, pi3)
    for d in sorted((ROOT / "results").glob(f"*/{ds}")):
        if d.parent.name not in arms:
            arms.append(d.parent.name)
            metric.setdefault(d.parent.name, d.parent.name == "pi3")   # Pi3X: approx. metric
    rows = []
    for sc in cfg["datasets"][ds].get("scenes") or []:
        for tj in resolve_trajs(cfg, "all"):
            gt_p = ROOT / "dataset" / "exports" / ds / sc / tj / "poses_gt.tum"
            if not gt_p.exists():
                continue
            gt = load_tum(gt_p)
            pg_all = np.stack([gt[i][:3, 3] for i in sorted(gt)])
            L = float(np.linalg.norm(np.diff(pg_all, axis=0), axis=1).sum())
            print(f"\n=== {ds}/{sc}/{tj}: {len(gt)} frames, GT path {L:.1f} m")
            for arm in arms:
                for pt in sorted(glob.glob(str(ROOT / "results" / arm / ds / sc / tj / "*" / "poses.tum"))):
                    run = Path(pt).parent
                    perf = json.loads((run / "perf.json").read_text()) if (run / "perf.json").exists() else {}
                    est = load_tum(Path(pt))
                    k = sorted(set(est) & set(gt))
                    row = dict(scene=sc, traj=tj, arm=arm, variant=run.name, n_gt=len(gt), n_est=len(k),
                               ate_cm=None, scale=None, tracked_pct=None, n_lost=None, survive_m=None,
                               path_m=L, fps=perf.get("proc_fps") or perf.get("eff_fps"),
                               vram_gb=perf.get("vram_peak_gb"), fscore=None, acc_cm=None,
                               status=perf.get("failure_kind") or ("ok" if perf.get("completed") else "incomplete"))
                    if len(k) >= 10:
                        E = np.stack([est[i] for i in k]); G = np.stack([gt[i] for i in k])
                        s, R, t = umeyama(E[:, :3, 3], G[:, :3, 3])
                        ate = np.sqrt(((G[:, :3, 3] - (s * (R @ E[:, :3, 3].T).T + t)) ** 2).sum(1).mean())
                        a = lm.analyse(E, G)
                        row.update(ate_cm=100 * float(ate), scale=float(s) if metric.get(arm) else None,
                                   tracked_pct=a["tracked_pct"], n_lost=a["n_lost"], survive_m=a["survive_m"])
                    rj = run / "recon.json"
                    if rj.exists():
                        rec = json.loads(rj.read_text())
                        m = rec.get("masked") or rec.get("full_360") or {}
                        if m:
                            row.update(fscore=m.get("fscore"),
                                       acc_cm=100 * m["accuracy_m"] if m.get("accuracy_m") is not None else None)
                    rows.append(row)
    if not rows:
        print("!! no results for this overlay's arms yet")
        return 1
    out = ROOT / "results" / "real360"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    f1 = lambda v, p=1: "—" if v is None else f"{v:.{p}f}"
    print(f"\n{'scene/traj':14s} {'arm':15s} {'variant':14s} {'poses':>6s} {'ATE cm':>7s} {'scale':>6s} "
          f"{'tracked%':>8s} {'lost':>4s} {'survive m':>10s} {'F@5cm':>6s} {'acc cm':>6s} {'fps':>5s} {'VRAM':>5s}  status")
    for r in rows:
        print(f"{r['scene'] + '/' + r['traj']:14s} {r['arm']:15s} {r['variant']:14s} {r['n_est']:6d} "
              f"{f1(r['ate_cm']):>7s} {f1(r['scale'], 2):>6s} {f1(r['tracked_pct']):>8s} "
              f"{str(r['n_lost']) if r['n_lost'] is not None else '—':>4s} "
              f"{f1(r['survive_m']):>5s}/{r['path_m']:<4.0f} {f1(r['fscore'], 3):>6s} {f1(r['acc_cm']):>6s} "
              f"{f1(r['fps']):>5s} {f1(r['vram_gb']):>5s}  {r['status']}")
    print(f"\n>> {(out / 'summary.csv').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
