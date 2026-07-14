"""Aggregate everything into the final preliminary report.

Reads only results/<...>/{perf.json,ate.json,recon.json,metric.json} + perf.csv,
and emits results/report/{report.md, table_*.csv, *.png}. Imports NO method.

Tables (all captioned "Preliminary; full evaluation is future work."):
  A  Performance & resources per method (same hardware)
  B  Metric accuracy — absolute-scale (our metric methods vs. rendered GT)
  C  Reconstruction, co-visibility masked (fair vs. pinhole)
  C2 Reconstruction, full-360 no mask (pano-capable methods)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config


def _load_all():
    runs = []
    for d in (REPO_ROOT / "results").glob("*/*/*/*/*"):
        if not d.is_dir():
            continue
        parts = d.parts
        i = parts.index("results")
        rec = {"method": parts[i + 1], "dataset": parts[i + 2], "scene": parts[i + 3],
               "traj": parts[i + 4], "variant": parts[i + 5]}
        for name in ("perf", "ate", "recon", "metric"):
            f = d / f"{name}.json"
            rec[name] = json.loads(f.read_text()) if f.exists() else None
        runs.append(rec)
    return runs


def _md_table(headers, rows) -> str:
    line = "| " + " | ".join(headers) + " |\n"
    line += "| " + " | ".join("---" for _ in headers) + " |\n"
    for r in rows:
        line += "| " + " | ".join(str(c) for c in r) + " |\n"
    return line


def _fmt(v, mult=1.0, nd=2, na="—"):
    return na if v is None else f"{v * mult:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    out = REPO_ROOT / cfg["report"]["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    runs = _load_all()
    label = cfg["report"]["label"]
    cap = f"*{label.capitalize()} results; full evaluation is future work. Hardware: {cfg['hardware']['hw_id']}.*"

    md = [f"# PRISM-benchmarks — {label} results\n", cap, ""]

    # Table A — performance
    a_rows = []
    for r in runs:
        p = r["perf"]
        if not p:
            continue
        a_rows.append([r["method"], f"{r['scene']}/{r['traj']}/{r['variant']}",
                       _fmt(p.get("eff_fps"), 1, 2),
                       _fmt(p.get("latency_end_to_end_s"), 1, 1),
                       _fmt(p.get("vram_avg_gb"), 1, 2),
                       _fmt(p.get("vram_peak_gb"), 1, 2),
                       _fmt(p.get("gpu_util_avg_pct"), 1, 0),
                       _fmt(p.get("gpu_power_avg_w"), 1, 0),
                       _fmt(p.get("ckpt_size_mb"), 1, 0)])
    md += ["## Table A — Performance & resources\n",
           _md_table(["Method", "Run", "Eff.FPS↑", "Latency s↓", "VRAM avg GB↓",
                      "VRAM peak GB↓", "GPU util %", "GPU W", "ckpt MB"], a_rows), ""]

    # Table B — metric accuracy (absolute scale)
    b_rows = []
    for r in runs:
        m = r["metric"]
        if not m:
            continue
        if not m.get("metric_capable"):
            b_rows.append([r["method"], f"{r['scene']}/{r['traj']}", "N/A (scale-free)", "—", "—"])
        else:
            b_rows.append([r["method"], f"{r['scene']}/{r['traj']}",
                           _fmt(m.get("scale_estimate"), 1, 3),
                           _fmt(m.get("metric_scale_error_pct"), 1, 1),
                           _fmt(m.get("extent_error_pct"), 1, 1)])
    md += ["## Table B — Metric accuracy (absolute scale vs. rendered GT)\n",
           _md_table(["Method", "Run", "Scale est.", "Scale err %↓", "Extent err %↓"], b_rows), ""]

    # Tables C / C2 — reconstruction
    def recon_rows(key):
        rows = []
        for r in runs:
            rc = r["recon"]
            if not rc or key not in rc:
                continue
            mm = rc[key]
            rows.append([r["method"], f"{r['scene']}/{r['traj']}/{r['variant']}",
                         _fmt(mm.get("accuracy_m"), 100, 1),
                         _fmt(mm.get("completeness_m"), 100, 1),
                         _fmt(mm.get("chamfer_m"), 100, 1),
                         _fmt(mm.get("fscore"), 1, 3)])
        return rows
    thr = int(cfg["eval"]["fscore_threshold_m"] * 100)
    md += [f"## Table C — Reconstruction, co-visibility masked (fair)\n",
           _md_table(["Method", "Run", "Acc cm↓", "Compl cm↓", "Chamfer cm↓", f"F@{thr}cm↑"],
                     recon_rows("masked")), ""]
    md += [f"## Table C2 — Reconstruction, full-360 (no mask; pano methods)\n",
           _md_table(["Method", "Run", "Acc cm↓", "Compl cm↓", "Chamfer cm↓", f"F@{thr}cm↑"],
                     recon_rows("full_360")), ""]

    # Table D — cloud cleanliness & size (sharpness / fluffiness / compactness)
    d_rows = []
    for r in runs:
        rc = r["recon"]
        if not rc:
            continue
        mm = rc.get("masked", rc.get("full_360", {}))
        d_rows.append([r["method"], f"{r['scene']}/{r['traj']}/{r['variant']}",
                       rc.get("point_count", "—"),
                       _fmt(rc.get("map_size_mb"), 1, 1),
                       _fmt(mm.get("noise_frac"), 100, 1),
                       _fmt(mm.get("precision_tight"), 100, 1)])
    md += ["## Table D — Cloud cleanliness & size\n",
           "*noise% = pred points far from any GT surface (fluffy floaters); "
           "precision@2cm = pred points within 2 cm of GT (sharpness).*\n",
           _md_table(["Method", "Run", "Points", "Size MB↓", "Noise %↓", "Prec@2cm %↑"],
                     d_rows), ""]

    md += ["## Trajectory (ATE/RPE, Sim(3)-aligned)\n"]
    t_rows = []
    for r in runs:
        a = r["ate"]
        if a:
            t_rows.append([r["method"], f"{r['scene']}/{r['traj']}/{r['variant']}",
                           _fmt(a.get("ate_rmse_m"), 100, 1), _fmt(a.get("rpe_rmse_m"), 100, 1)])
    md += [_md_table(["Method", "Run", "ATE RMSE cm↓", "RPE RMSE cm↓"], t_rows), ""]

    (out / "report.md").write_text("\n".join(md))
    _write_plots(out, runs)
    print(f"[make_report] wrote {out / 'report.md'}")


def _write_plots(out: Path, runs):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fps = [(r["method"], r["perf"]["eff_fps"]) for r in runs
           if r["perf"] and r["perf"].get("eff_fps")]
    if fps:
        labels = [f"{m}" for m, _ in fps]
        vals = [v for _, v in fps]
        plt.figure(figsize=(6, 3))
        plt.bar(range(len(vals)), vals)
        plt.xticks(range(len(vals)), labels, rotation=30, ha="right")
        plt.ylabel("Effective FPS")
        plt.title("Throughput (preliminary)")
        plt.tight_layout()
        plt.savefig(out / "fps.png", dpi=120)
        plt.close()


if __name__ == "__main__":
    main()
