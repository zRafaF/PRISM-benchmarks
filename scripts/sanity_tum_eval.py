#!/usr/bin/env python
"""Table for scripts/sanity_tum.sh: VGGT-SLAM on TUM fr1, its own pipeline vs ours.

theirs : RMSE from VGGT-SLAM's evals/eval_tum.sh (evo_ape -as: Sim(3)-aligned APE)
ours   : our runner's poses.tum vs the associated GT, Sim(3)-aligned RMSE (same metric)
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from diag import load_tum, umeyama  # noqa: E402


def ate(est, gt):
    k = sorted(set(est) & set(gt))
    if len(k) < 10:
        return None, len(k)
    pe = np.stack([est[i][:3, 3] for i in k]); pg = np.stack([gt[i][:3, 3] for i in k])
    s, R, t = umeyama(pe, pg)
    return float(np.sqrt(((pg - (s * (R @ pe.T).T + t)) ** 2).sum(1).mean())), len(k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seqs", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    theirs = {}
    tf = out / "theirs_tum_results_w32.csv"
    if tf.exists():
        for r in csv.DictReader(open(tf)):
            try:
                theirs[r["Dataset"].replace("rgbd_dataset_freiburg1_", "fr1_")] = float(r["RMSE"])
            except (KeyError, ValueError):
                pass
    rows = []
    for s in a.seqs.split():
        name = f"fr1_{s}"
        gt_p = ROOT / "dataset" / "exports" / "tum" / name / "native" / "poses_gt.tum"
        est_p = out / "ours" / name / "poses.tum"
        o, n = (None, 0)
        if gt_p.exists() and est_p.exists():
            o, n = ate(load_tum(est_p), load_tum(gt_p))
        rows.append(dict(seq=name, theirs_m=theirs.get(name), ours_m=o, n_ours=n))
    with open(out / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    fmt = lambda v: "—" if v is None else f"{100 * v:6.1f}"
    print(f"\n{'sequence':12s} {'theirs cm':>10s} {'ours cm':>9s} {'poses':>6s}")
    for r in rows:
        print(f"{r['seq']:12s} {fmt(r['theirs_m']):>10s} {fmt(r['ours_m']):>9s} {r['n_ours']:6d}")
    th = [r["theirs_m"] for r in rows if r["theirs_m"] is not None]
    ou = [r["ours_m"] for r in rows if r["ours_m"] is not None]
    if th or ou:
        print(f"{'mean':12s} {fmt(np.mean(th) if th else None):>10s} {fmt(np.mean(ou) if ou else None):>9s}")
    print("\nCompare 'theirs' with the TUM table of the VGGT-SLAM paper for the pinned version "
          "(the 1.0 paper reports ~5.3 cm mean for SL(4), w=32). 'ours' should match 'theirs' "
          "within run-to-run noise (the method is stochastic: RANSAC).")
    print(f">> {out / 'summary.csv'}")


if __name__ == "__main__":
    main()
