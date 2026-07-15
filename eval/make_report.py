"""Aggregate results into reports. Reads only results/<...>/{perf,ate,recon,metric}.json.

Writes:
  results/report/<scene>/report.md   — full tables (A/B/C/C2/D/traj) for ONE scene
  results/report/report.md           — GLOBAL: a per-method mean across all scenes×rates
                                        (the aggregate) + the full per-run tables

Aggregation = arithmetic mean of each metric over all of a method's runs (scenes ×
capture-rates × camera variants), with N = number of runs averaged. Scale error is
averaged only over metric-capable methods.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config, traj_rate_hz


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


def build_tables(runs, cfg, title) -> str:
    """Full A/B/C/C2/D/traj tables for a set of runs (one scene, or all)."""
    lab = cfg["report"]["label"]
    thr = int(cfg["eval"]["fscore_threshold_m"] * 100)
    speed = cfg["trajectories"]["synthetic_spline"].get("speed_mps", 0.5)
    md = [f"# PRISM-benchmarks — {title}\n",
          f"*{lab.capitalize()} results; full evaluation is future work. "
          f"Hardware: {cfg['hardware']['hw_id']}.*",
          "",
          "**Inter-frame baseline = speed/rate is the quality-driving quantity (not FPS):** "
          f"at {speed} m/s, 0.5 Hz→{speed/0.5*100:.0f} cm, 2 Hz→{speed/2*100:.0f} cm, "
          f"5 Hz→{speed/5*100:.0f} cm between frames.", ""]

    a = [[r["method"], f"{r['scene']}/{r['traj']}/{r['variant']}",
          f"{speed / traj_rate_hz(r['traj']) * 100:.0f}",
          _fmt((r['perf'] or {}).get("eff_fps"), 1, 2),
          _fmt((r['perf'] or {}).get("latency_end_to_end_s"), 1, 1),
          _fmt((r['perf'] or {}).get("vram_peak_gb"), 1, 2),
          _fmt((r['perf'] or {}).get("gpu_util_avg_pct"), 1, 0)]
         for r in runs if r["perf"]]
    md += ["## Table A — Performance & resources\n",
           _md_table(["Method", "Run", "Baseline cm", "Eff.FPS↑", "Latency s↓", "VRAM peak GB↓", "GPU %"], a), ""]

    b = []
    for r in runs:
        m = r["metric"]
        if not m:
            continue
        if not m.get("metric_capable"):
            b.append([r["method"], f"{r['scene']}/{r['traj']}", "N/A (scale-free)", "—", "—"])
        else:
            b.append([r["method"], f"{r['scene']}/{r['traj']}",
                      _fmt(m.get("scale_estimate"), 1, 3),
                      _fmt(m.get("metric_scale_error_pct"), 1, 1),
                      _fmt(m.get("extent_error_pct"), 1, 1)])
    md += ["## Table B — Metric accuracy (absolute scale vs. rendered GT)\n",
           _md_table(["Method", "Run", "Scale est.", "Scale err %↓", "Extent err %↓"], b), ""]

    def recon_rows(key):
        rows = []
        for r in runs:
            rc = r["recon"]
            if not rc or key not in rc:
                continue
            mm = rc[key]
            rows.append([r["method"], f"{r['scene']}/{r['traj']}/{r['variant']}",
                         _fmt(mm.get("accuracy_m"), 100, 1), _fmt(mm.get("completeness_m"), 100, 1),
                         _fmt(mm.get("chamfer_m"), 100, 1), _fmt(mm.get("fscore"), 1, 3)])
        return rows
    md += [f"## Table C — Reconstruction, co-visibility masked (fair)\n",
           _md_table(["Method", "Run", "Acc cm↓", "Compl cm↓", "Chamfer cm↓", f"F@{thr}cm↑"],
                     recon_rows("masked")), ""]
    md += [f"## Table C2 — Reconstruction, full-360 (no mask; pano methods)\n",
           _md_table(["Method", "Run", "Acc cm↓", "Compl cm↓", "Chamfer cm↓", f"F@{thr}cm↑"],
                     recon_rows("full_360")), ""]

    d = []
    for r in runs:
        rc = r["recon"]
        if not rc:
            continue
        mm = rc.get("masked", rc.get("full_360", {}))
        d.append([r["method"], f"{r['scene']}/{r['traj']}/{r['variant']}",
                  rc.get("point_count", "—"), _fmt(rc.get("map_size_mb"), 1, 1),
                  _fmt(rc.get("sor_outlier_pct"), 100, 1),
                  _fmt(mm.get("acc_p95_m"), 100, 1),
                  _fmt(mm.get("noise_frac"), 100, 1), _fmt(mm.get("precision_tight"), 100, 1)])
    md += ["## Table D — Cloud cleanliness & size\n",
           "*Outlier% = kNN statistical outliers (density-independent fluffiness — the fair "
           "noise measure across sparse vs dense clouds); Acc-p95 = 95th-pct pred→GT distance "
           "(worst floaters); noise% = points >10 cm from GT; prec@2cm = within 2 cm.*\n",
           _md_table(["Method", "Run", "Points", "Size MB↓", "Outlier %↓", "Acc-p95 cm↓",
                      "Noise %↓", "Prec@2cm %↑"], d), ""]

    t = [[r["method"], f"{r['scene']}/{r['traj']}/{r['variant']}",
          _fmt((r['ate'] or {}).get("ate_rmse_m"), 100, 1),
          _fmt((r['ate'] or {}).get("rpe_rmse_m"), 100, 1)]
         for r in runs if r["ate"]]
    md += ["## Trajectory (ATE/RPE, Sim(3)-aligned)\n",
           _md_table(["Method", "Run", "ATE RMSE cm↓", "RPE RMSE cm↓"], t), ""]
    return "\n".join(md)


def _run_metrics(r):
    p, a, rc, m = r["perf"] or {}, r["ate"] or {}, r["recon"] or {}, r["metric"] or {}
    masked, full = rc.get("masked", {}), rc.get("full_360", {})
    ate = a.get("ate_rmse_m")
    return {
        "eff_fps": p.get("eff_fps"),
        "scale_err": m.get("metric_scale_error_pct") if m.get("metric_capable") else None,
        "ate_cm": ate * 100 if ate is not None else None,
        "mF": masked.get("fscore"),
        "fF": full.get("fscore"),
        "map_mb": rc.get("map_size_mb"),
        "outlier": rc.get("sor_outlier_pct") * 100 if rc.get("sor_outlier_pct") is not None else None,
        "prec2": masked.get("precision_tight") * 100 if masked.get("precision_tight") is not None else None,
    }


def aggregate_global(runs, cfg) -> str:
    """Per-method mean of each metric across all runs (scenes × rates × variants)."""
    import statistics as st
    by_method = {}
    for r in runs:
        by_method.setdefault(r["method"], []).append(_run_metrics(r))
    keys = ["eff_fps", "scale_err", "ate_cm", "mF", "fF", "map_mb", "outlier", "prec2"]

    def mean(vals):
        v = [x for x in vals if x is not None]
        return st.mean(v) if v else None

    rows = []
    for method in sorted(by_method):
        rs = by_method[method]
        agg = {k: mean([m[k] for m in rs]) for k in keys}
        scale = "N/A" if agg["scale_err"] is None else _fmt(agg["scale_err"], 1, 1)
        rows.append([method, len(rs), _fmt(agg["eff_fps"], 1, 2), scale,
                     _fmt(agg["ate_cm"], 1, 1), _fmt(agg["mF"], 1, 3), _fmt(agg["fF"], 1, 3),
                     _fmt(agg["map_mb"], 1, 1), _fmt(agg["outlier"], 1, 1), _fmt(agg["prec2"], 1, 1)])
    hdr = ["Method", "N", "Eff.FPS↑", "Scale err %↓", "ATE cm↓", "Masked F↑",
           "Full-360 F↑", "Map MB↓", "Outlier %↓", "Prec@2cm %↑"]
    return ("## Global aggregate — mean per method (over all scenes × rates × variants)\n"
            "*N = runs averaged. Scale err averaged over metric-capable runs only.*\n\n"
            + _md_table(hdr, rows) + "\n")


def _write_plots(out: Path, runs):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fps = [(r["method"], r["perf"]["eff_fps"]) for r in runs if r["perf"] and r["perf"].get("eff_fps")]
    if fps:
        plt.figure(figsize=(6, 3))
        plt.bar(range(len(fps)), [v for _, v in fps])
        plt.xticks(range(len(fps)), [m for m, _ in fps], rotation=30, ha="right")
        plt.ylabel("Effective FPS"); plt.title("Throughput (preliminary)")
        plt.tight_layout(); plt.savefig(out / "fps.png", dpi=120); plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    out = REPO_ROOT / cfg["report"]["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    runs = _load_all()
    if not runs:
        print("[make_report] no results found"); return

    scenes = sorted({r["scene"] for r in runs})
    for scene in scenes:
        sr = [r for r in runs if r["scene"] == scene]
        sdir = out / scene
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "report.md").write_text(build_tables(sr, cfg, f"scene: {scene}"))
        _write_plots(sdir, sr)
        print(f"[make_report] scene report -> {sdir / 'report.md'} ({len(sr)} runs)")

    # Global: aggregate summary + full per-run tables across all scenes.
    glob = [f"# PRISM-benchmarks — global report ({len(scenes)} scene(s))\n",
            aggregate_global(runs, cfg),
            "---\n",
            build_tables(runs, cfg, "all runs (every scene / rate / variant)")]
    (out / "report.md").write_text("\n".join(glob))
    _write_plots(out, runs)
    print(f"[make_report] global report -> {out / 'report.md'} "
          f"({len(runs)} runs across {len(scenes)} scene(s))")


if __name__ == "__main__":
    main()
