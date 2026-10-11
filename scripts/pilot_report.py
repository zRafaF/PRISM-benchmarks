#!/usr/bin/env python
"""Pilot summary: trajectory accuracy + cost for every pilot arm, scene and rate.

Reads results/<arm>/<ds>/<scene>/<traj>/<variant>/{poses.tum,perf.json} and the GT
poses, and prints (and writes results/pilot/pilot_summary.csv):

  ATE      Sim(3)-aligned RMSE over every frame of the sequence (cm)
  ATE@2Hz  the same, but only on the frames that also exist in the 2 Hz sequence
           (every 5th frame of 10 Hz, every 2nd... of 5 Hz), so rates are compared on
           identical GT poses
  RPE      median frame-to-frame rotation error (deg) and jumps > 5 deg
  wall / proc  run time (s) and the method's own processing time; peak VRAM (GB)

No eval env or depth needed — it runs on the pod right after the runs, CPU only.
Usage:  PRISM_CONFIG_OVERLAY=config.pilot.yaml uv run python scripts/pilot_report.py
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
from bench.config import load_config, resolve_trajs, traj_rate_hz  # noqa: E402
from diag import analyse, load_tum, umeyama  # noqa: E402


def ate_on(est: dict, gt: dict, keys) -> float | None:
    k = [i for i in keys if i in est and i in gt]
    if len(k) < 10:
        return None
    pe = np.stack([est[i][:3, 3] for i in k])
    pg = np.stack([gt[i][:3, 3] for i in k])
    s, Rm, t = umeyama(pe, pg)
    return float(np.sqrt(((pg - (s * (Rm @ pe.T).T + t)) ** 2).sum(1).mean()))


def main() -> int:
    cfg = load_config("config.yaml")
    ds = cfg["datasets"]["active"][0]
    scenes = cfg["datasets"][ds].get("scenes") or []
    trajs = resolve_trajs(cfg, "all")
    arms = [m["name"] for m in cfg.get("ablations", []) if m.get("role") == "pilot"]
    rows = []
    for sc in scenes:
        for tj in trajs:
            gt_p = ROOT / "dataset" / "exports" / ds / sc / tj / "poses_gt.tum"
            if not gt_p.exists():
                continue
            gt = load_tum(gt_p)
            rate = traj_rate_hz(tj)
            # Frames shared with the 2 Hz sequence (same GT poses at every rate).
            stride_to_2 = int(round(rate / 2.0)) if rate >= 2.0 else 1
            common = list(range(0, len(gt), max(1, stride_to_2)))
            for arm in arms:
                ps = sorted(glob.glob(str(ROOT / "results" / arm / ds / sc / tj / "*" / "poses.tum")))
                if not ps:
                    continue
                run = Path(ps[0]).parent
                est = load_tum(Path(ps[0]))
                r = analyse(est, gt)
                perf = {}
                if (run / "perf.json").exists():
                    perf = json.loads((run / "perf.json").read_text())
                row = dict(scene=sc, rate_hz=rate, arm=arm, n_gt=len(gt), n_est=len(est),
                           ate_cm=None, ate2hz_cm=None, rpe_med_deg=None, jumps5=None,
                           wall_s=perf.get("wall_s"), proc_s=perf.get("latency_end_to_end_s"),
                           vram_gb=perf.get("vram_peak_gb"),
                           status=perf.get("failure_kind") or ("ok" if r else "too few poses"))
                if r:
                    a2 = ate_on(est, gt, common)
                    row.update(ate_cm=100 * r["ate_all"], ate2hz_cm=None if a2 is None else 100 * a2,
                               rpe_med_deg=r["rpe_med"], jumps5=r["jumps"])
                rows.append(row)
    if not rows:
        print("!! no pilot results found under results/p3_*")
        return 1
    out = ROOT / "results" / "pilot"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "pilot_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    def fmt(v, p=1):
        return "—" if v is None else f"{v:.{p}f}"

    print(f"\n{'scene':12s} {'Hz':>5s} {'arm':18s} {'frames':>6s} {'ATE cm':>7s} {'ATE@2Hz':>8s} "
          f"{'RPE°':>5s} {'jumps':>5s} {'wall s':>7s} {'proc s':>7s} {'VRAM':>5s}  status")
    for r in sorted(rows, key=lambda r: (r["scene"], -r["rate_hz"], r["arm"])):
        print(f"{r['scene']:12s} {r['rate_hz']:5.1f} {r['arm']:18s} {r['n_est']:6d} {fmt(r['ate_cm']):>7s} "
              f"{fmt(r['ate2hz_cm']):>8s} {fmt(r['rpe_med_deg'], 2):>5s} {str(r['jumps5'] if r['jumps5'] is not None else '—'):>5s} "
              f"{fmt(r['wall_s'], 0):>7s} {fmt(r['proc_s'], 0):>7s} {fmt(r['vram_gb']):>5s}  {r['status']}")

    # Best PRISM window per rate (mean ATE@2Hz over the scenes that have every arm).
    print("\nPRISM window sweep — mean ATE@2Hz (cm) over scenes, per rate:")
    prism_arms = [a for a in arms if a.startswith("p3_prism")]
    for rate in sorted({r["rate_hz"] for r in rows}, reverse=True):
        line = []
        for a in prism_arms:
            v = [r["ate2hz_cm"] for r in rows if r["arm"] == a and r["rate_hz"] == rate and r["ate2hz_cm"] is not None]
            if v:
                line.append(f"{a.replace('p3_prism', 'w16o4' if a == 'p3_prism' else '').lstrip('_') or 'w16o4'}={np.mean(v):.1f} (n={len(v)})")
        if line:
            print(f"  {rate:4.1f} Hz: " + "  ".join(line))
    print(f"\n>> {out.relative_to(ROOT)}/pilot_summary.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
