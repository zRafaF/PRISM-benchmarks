"""Clean, seeded-only aggregation — the publication-grade replacement for the
contaminated `Global aggregate` / `Alignment-group study` tables in report.md.

WHAT MAKES AN AGGREGATE "CLEAN" HERE
------------------------------------
Three independent filters, each of which the old `eval/make_report.py`
aggregation applied none of:

1. **Seeded-only.** Only trajectories whose id ends in `_sN` belong to the seeded
   matrix. The unsuffixed ids (`synthetic_2.0hz`, ...) are leftovers from the
   earlier 2-scene experiment; their VRAM is co-tenancy-inflated to 70-100 GB and
   their scenes (`office_4`) were never re-rendered under a seed.
2. **Explicit exclusions.** Anything matching EXCLUSIONS is dropped *by name with
   a stated reason*, so a stale run can never silently re-enter by being renamed
   or re-globbed.
3. **Complete runs only.** A run that produced no evaluable output (no ATE / no
   recon) is excluded from every aggregate, including the perf aggregate. This
   matters more than it sounds: `eff_fps` for such a run is computed from the
   *input* frame count (adapters/base.py takes n_frames from the input meta.json),
   so a run that died early reports a spuriously HIGH fps. Averaging those in
   inflates throughput. `--include-incomplete` shows the contrast.

Every table reports N_complete / N_total per method so the reader can see the
completion rate rather than having it hidden inside a mean.

OUTPUTS (all under results/report_clean/, both machine-readable and markdown)
    runs_clean.csv            every clean run-record actually aggregated
    aggregate_per_method.csv  the per-method table (replaces "Global aggregate")
    streaming.csv             streaming-only comparison, with throughput
    offline.csv               full-batch upper bound
    alignment.csv             Sim(3) / SL(4) / SE(3) study
    motion.csv                motion-stratified breakdown
    per_seed.csv              per-(scene,seed) values — the error-bar source
    variance.csv              mean / std / 95% CI per method x metric
    completion.csv            per-method completion + failure breakdown
    clean_report.md           all of the above as markdown
    clean_report.json         all of the above as one JSON blob

Usage
    make report-clean                                  # live results/ if present
    uv run python eval/aggregate_clean.py --source archive --run-id bigrun_2026-07
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT

SEEDED_RE = re.compile(r"_s\d+$")

# ---------------------------------------------------------------------------
# Named exclusions. Each entry is (predicate, reason) — the reason is printed and
# written to the changelog/report so no run is ever dropped silently.
# ---------------------------------------------------------------------------
EXCLUSIONS = [
    (lambda r: not SEEDED_RE.search(r["traj"]),
     "unseeded traj id — stale 2-scene experiment (co-tenancy-inflated VRAM 70-100 GB)"),
    (lambda r: r["scene"] == "office_4",
     "office_4 has stale data only; it was never rendered under a seed"),
    (lambda r: r["method"] == "prism_sl4" and not SEEDED_RE.search(r["traj"]),
     "prism_sl4 (N=6) is entirely stale 2-scene data — not comparable"),
]

# Motion families, keyed off the trajectory id prefix.
MOTION = [("smooth", "synthetic_"), ("stop-and-go", "stopgo_"), ("loop", "loop_")]

# Method taxonomy — native mode is never mixed (streaming vs full-batch).
STREAMING = ["prism", "prism_sim3", "prism_sl4", "prism_se3", "laser", "vggtslam",
             "vggtslam_noloop", "vggtslam_loop"]
OFFLINE = ["panovggt", "pi3", "mapanything"]
GUARD_ARMS = ["prism_nolock", "prism_nostill", "prism_noguards"]

# Fidelity-vs-memory sweep arms. They are the SAME engine at a different operating
# point, so putting them in the per-method aggregate or the streaming comparison would
# be double-counting PRISM and would flatter or muddy the headline depending on which
# way the knob went. They get their own table instead; `prism` is the reference point.
SWEEP_PREFIXES = ("prism_vox", "prism_depth")


def is_sweep(method: str) -> bool:
    return method.startswith(SWEEP_PREFIXES)

#  The arm named `prism` does NOT mean the same thing in every results era, and
#  silently mislabelling it would invert the study's conclusion:
#
#    2026-07 archive : `prism` ran SL(4) (the then-default), with prism_sim3 /
#                      prism_se3 as the ablation arms.
#    current config  : `prism` runs Sim(3) (the deployed default, set explicitly in
#                      config.yaml), with prism_sl4 / prism_se3 as the ablation arms.
#
#  So the alignment table is built from whichever arm names are actually present,
#  and `prism` is resolved by era. Anything ambiguous is labelled as such rather
#  than guessed.
ALIGN_ERAS = {
    "archive:bigrun_2026-07": [("prism_sim3", "Sim(3)", 7), ("prism", "SL(4)", 15),
                               ("prism_se3", "SE(3)", 6)],
    "default": [("prism", "Sim(3)", 7), ("prism_sl4", "SL(4)", 15),
                ("prism_se3", "SE(3)", 6)],
}


def align_arms_for(source: str, present: set[str]):
    """Resolve (arm, group-label, DoF) for this results era."""
    arms = ALIGN_ERAS.get(source, ALIGN_ERAS["default"])
    # If the era's expected arm names aren't the ones on disk, fall back to whichever
    # mapping actually matches rather than emitting a table of empty rows.
    if not any(a in present for a, _, _ in arms):
        for cand in ALIGN_ERAS.values():
            if any(a in present for a, _, _ in cand):
                return cand
    return arms


# ---------------------------------------------------------------------------
# Loading — live results/ tree or the archived snapshot. Same tidy schema either way.
# ---------------------------------------------------------------------------
def load_live_runs() -> list[dict]:
    """Read results/<method>/<ds>/<scene>/<traj>/<variant>/{perf,ate,recon,metric}.json."""
    runs = []
    for d in (REPO_ROOT / "results").glob("*/*/*/*/*"):
        if not d.is_dir():
            continue
        parts = d.parts
        i = parts.index("results")
        j = {}
        for name in ("perf", "ate", "recon", "metric"):
            f = d / f"{name}.json"
            j[name] = json.loads(f.read_text()) if f.exists() else {}
        _a = d / "arm_config.json"
        j["arm"] = json.loads(_a.read_text()) if _a.exists() else {}
        p, a, rc, mt = j["perf"], j["ate"], j["recon"], j["metric"]
        masked, full = rc.get("masked", {}) or {}, rc.get("full_360", {}) or {}
        runs.append({
            "method": parts[i + 1], "dataset": parts[i + 2], "scene": parts[i + 3],
            "traj": parts[i + 4], "variant": parts[i + 5],
            "n_frames": p.get("n_frames"),
            "n_frames_input": p.get("n_frames_input"),
            "n_frames_done": p.get("n_frames_done"),
            "oom": p.get("oom"), "failure_kind": p.get("failure_kind"),
            # Baseline self-reported engagement evidence (currently VGGT-SLAM's submap /
            # loop-closure counts). A run where the method's own machinery never engaged
            # is not a valid head-to-head datapoint, so it has to travel with the run.
            "n_submaps": (j.get("arm") or {}).get("n_submaps"),
            "n_loop_closures": (j.get("arm") or {}).get("n_loop_closures"),
            "degenerate": (j.get("arm") or {}).get("degenerate_single_submap"),
            "voxel_size": (j.get("arm") or {}).get("voxel_size"),
            "max_depth": (j.get("arm") or {}).get("max_depth"),
            "eff_fps": p.get("eff_fps"),
            "latency_end_to_end_s": p.get("latency_end_to_end_s"),
            "per_window_latency_med_s": (
                st.median(p["per_window_latency_s"]) if p.get("per_window_latency_s") else None),
            "latency_source": p.get("latency_source"),
            "vram_avg_gb": p.get("vram_avg_gb"), "vram_peak_gb": p.get("vram_peak_gb"),
            "gpu_util_avg_pct": p.get("gpu_util_avg_pct"),
            "ate_rmse_m": a.get("ate_rmse_m"), "rpe_per_m": a.get("rpe_per_m"),
            "metric_capable": mt.get("metric_capable"),
            "metric_scale_error_pct": (mt.get("metric_scale_error_pct")
                                       if mt.get("metric_capable") else None),
            "extent_error_pct": mt.get("extent_error_pct"),
            "masked_fscore": masked.get("fscore"),
            "masked_accuracy_m": masked.get("accuracy_m"),
            "masked_completeness_m": masked.get("completeness_m"),
            "masked_chamfer_m": masked.get("chamfer_m"),
            "full360_fscore": full.get("fscore"),
            "point_count": rc.get("point_count"), "map_size_mb": rc.get("map_size_mb"),
            "sor_outlier_pct": rc.get("sor_outlier_pct"),
            "acc_p95_m": masked.get("acc_p95_m"), "noise_frac": masked.get("noise_frac"),
            "precision_tight": masked.get("precision_tight"),
            "source": "live:results/",
        })
    return runs


def load_archive_runs(run_id: str) -> list[dict]:
    """Read the tidy CSV produced by eval/ingest_archive.py."""
    p = REPO_ROOT / "documentation" / "docs" / "data" / run_id / "runs_tidy.csv"
    if not p.exists():
        raise SystemExit(f"[aggregate_clean] {p} not found — run 'make ingest-archive' first.")
    out = []
    with open(p, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rec = {}
            for k, v in row.items():
                if v == "" or v is None:
                    rec[k] = None
                elif k in ("method", "dataset", "scene", "traj", "variant",
                           "gpu_name", "hw_id", "source", "latency_source",
                           "per_window_source", "failure_kind"):
                    rec[k] = v
                elif k == "metric_capable":
                    rec[k] = v in ("True", "true", "1")
                else:
                    try:
                        rec[k] = float(v)
                    except ValueError:
                        rec[k] = v
            out.append(rec)
    return out


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------
def is_complete(r: dict) -> bool:
    """A run counts as complete only if it produced evaluable geometry AND a pose track."""
    return r.get("ate_rmse_m") is not None and r.get("masked_fscore") is not None


def apply_exclusions(runs: list[dict]):
    kept, dropped = [], []
    for r in runs:
        why = next((reason for pred, reason in EXCLUSIONS if pred(r)), None)
        (dropped if why else kept).append({**r, "excluded_because": why} if why else r)
    return kept, dropped


def seed_of(traj: str) -> str | None:
    m = SEEDED_RE.search(traj)
    return m.group(0).lstrip("_") if m else None


def motion_of(traj: str) -> str:
    for name, prefix in MOTION:
        if traj.startswith(prefix):
            return name
    return "other"


def rate_of(traj: str) -> str | None:
    m = re.search(r"_(\d+\.?\d*)hz", traj)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------
def mean(vals):
    v = [x for x in vals if x is not None]
    return st.mean(v) if v else None


def stdev(vals):
    v = [x for x in vals if x is not None]
    return st.stdev(v) if len(v) > 1 else None


def ci95(vals):
    """Half-width of the 95% CI of the mean (normal approx.; thin with few seeds)."""
    v = [x for x in vals if x is not None]
    if len(v) < 2:
        return None
    return 1.96 * st.stdev(v) / math.sqrt(len(v))


def fmt(v, mult=1.0, nd=2, na="—"):
    return na if v is None else f"{v * mult:.{nd}f}"


def md_table(headers, rows) -> str:
    out = "| " + " | ".join(str(h) for h in headers) + " |\n"
    out += "| " + " | ".join("---" for _ in headers) + " |\n"
    for r in rows:
        out += "| " + " | ".join(str(c) for c in r) + " |\n"
    return out


# Canonical per-method metric block. Column semantics deliberately match the
# report's existing tables (ATE cm, Masked F, Outlier %, Map MB, VRAM GB,
# per-window s, scale %, 360 F) so uofa-2026-report can swap the numbers in place.
def method_block(rs: list[dict]) -> dict:
    return {
        "ate_cm": mean([r["ate_rmse_m"] for r in rs]) and mean([r["ate_rmse_m"] for r in rs]) * 100,
        "drift_pct_m": mean([r["rpe_per_m"] for r in rs]) and mean([r["rpe_per_m"] for r in rs]) * 100,
        "masked_f": mean([r["masked_fscore"] for r in rs]),
        # Accuracy / Completeness / Chamfer, in METRES, masked. These are the metrics
        # every baseline paper actually reports (VGGT-SLAM Tab.3 ATE/Acc/Compl/Chamfer;
        # LASER Tab.4 Acc/Comp/NC; VGGT and PanoVGGT Acc/Comp/Overall) and NONE of them
        # reports an F-score at any threshold — F@5cm is our own addition. Without these
        # columns our tables share no metric with the literature and cannot be placed
        # against a single published number.
        "masked_acc_m": mean([r["masked_accuracy_m"] for r in rs]),
        "masked_compl_m": mean([r["masked_completeness_m"] for r in rs]),
        "masked_chamfer_m": mean([r["masked_chamfer_m"] for r in rs]),
        "full360_f": mean([r["full360_fscore"] for r in rs]),
        "map_mb": mean([r["map_size_mb"] for r in rs]),
        "outlier_pct": (mean([r["sor_outlier_pct"] for r in rs]) or 0) * 100
                       if mean([r["sor_outlier_pct"] for r in rs]) is not None else None,
        "prec2cm_pct": (mean([r["precision_tight"] for r in rs]) or 0) * 100
                       if mean([r["precision_tight"] for r in rs]) is not None else None,
        "scale_err_pct": mean([r["metric_scale_error_pct"] for r in rs
                               if r.get("metric_capable")]),
        "vram_peak_gb": mean([r["vram_peak_gb"] for r in rs]),
        "vram_avg_gb": mean([r["vram_avg_gb"] for r in rs]),
        "per_window_lat_s": mean([r["per_window_latency_med_s"] for r in rs]),
        "eff_fps": mean([r["eff_fps"] for r in rs]),
        "n": len(rs),
    }


HEADLINE = ["ate_cm", "masked_f", "full360_f", "map_mb", "outlier_pct",
            "scale_err_pct", "vram_peak_gb", "eff_fps", "per_window_lat_s"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--source", choices=["auto", "live", "archive"], default="auto")
    ap.add_argument("--run-id", default="bigrun_2026-07")
    ap.add_argument("--include-incomplete", action="store_true",
                    help="also aggregate runs that produced no evaluable output "
                         "(shows how much they inflate throughput) — NOT for publication")
    ap.add_argument("--out", default="results/report_clean")
    args = ap.parse_args()

    # ---- load -------------------------------------------------------------
    src = args.source
    if src == "auto":
        src = "live" if any((REPO_ROOT / "results").glob("*/*/*/*/*/perf.json")) else "archive"
    runs = load_live_runs() if src == "live" else load_archive_runs(args.run_id)
    if not runs:
        raise SystemExit("[aggregate_clean] no runs found")

    kept, dropped = apply_exclusions(runs)
    complete = [r for r in kept if is_complete(r)]
    incomplete = [r for r in kept if not is_complete(r)]
    agg_set = kept if args.include_incomplete else complete

    for r in agg_set:
        r["seed"] = seed_of(r["traj"])
        r["motion"] = motion_of(r["traj"])
        r["rate_hz"] = rate_of(r["traj"])

    out = REPO_ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    blob: dict = {
        "source": f"{src}:{args.run_id if src == 'archive' else 'results/'}",
        "n_input": len(runs), "n_seeded_kept": len(kept),
        "n_excluded": len(dropped), "n_complete": len(complete),
        "n_incomplete": len(incomplete),
        "include_incomplete": args.include_incomplete,
        "scenes": sorted({r["scene"] for r in kept}),
        "trajectories": sorted({r["traj"] for r in kept}),
        "seeds": sorted({s for s in (seed_of(r["traj"]) for r in kept) if s}),
        "exclusion_reasons": sorted({d["excluded_because"] for d in dropped}),
    }

    def write_csv(name, headers, rows):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)

    methods = sorted({r["method"] for r in kept})
    ALIGN_ARMS = align_arms_for(blob["source"], set(methods))
    blob["alignment_arms"] = [{"arm": a, "group": g, "dof": d} for a, g, d in ALIGN_ARMS]

    # ---- completion (the failure-rate table) ------------------------------
    comp_rows = []
    for m in methods:
        tot = [r for r in kept if r["method"] == m]
        bad = [r for r in tot if not is_complete(r)]
        # OOM is separated out because it is a RESULT, not a defect: a full-batch
        # method exhausting VRAM at N frames is a publishable capacity limit, whereas
        # an 'error' incompletion is a bug to chase. Lumping them together would both
        # hide the capacity story and overstate the bug count.
        oomed = [r for r in tot if str(r.get("failure_kind") or "").lower() == "oom"]
        othr = [r for r in bad if r not in oomed]
        by_scene = ", ".join(f"{s}:{sum(1 for r in bad if r['scene'] == s)}"
                             for s in sorted({r["scene"] for r in bad})) or "—"
        by_motion = ", ".join(f"{mo}:{sum(1 for r in bad if motion_of(r['traj']) == mo)}"
                              for mo in sorted({motion_of(r["traj"]) for r in bad})) or "—"
        degen = [r for r in tot if r.get("degenerate")]
        comp_rows.append([m, len(tot), len(tot) - len(bad), len(othr), len(oomed),
                          len(degen),
                          f"{100 * len(bad) / len(tot):.1f}" if tot else "—",
                          by_scene, by_motion])
    comp_h = ["method", "n_total", "n_complete", "n_failed", "n_oom", "n_degenerate",
              "incomplete_pct", "incomplete_by_scene", "incomplete_by_motion"]
    write_csv("completion.csv", comp_h, comp_rows)
    blob["completion"] = [dict(zip(comp_h, r)) for r in comp_rows]

    # ---- capacity / OOM table -------------------------------------------------
    #  The deployability result: how long a sequence each method survives. For the
    #  full-batch methods this is the ceiling their design implies; for the streaming
    #  ones it should simply not appear.
    cap_rows = []
    for m in methods:
        tot = [r for r in kept if r["method"] == m]
        ok = [r for r in tot if is_complete(r)]
        oomed = [r for r in tot if str(r.get("failure_kind") or "").lower() == "oom"]

        def _nf(r):
            v = r.get("n_frames_input") or r.get("n_frames")
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return None
        ok_f = [x for x in (_nf(r) for r in ok) if x]
        oom_f = [x for x in (_nf(r) for r in oomed) if x]
        peak = [r["vram_peak_gb"] for r in ok if r.get("vram_peak_gb")]
        cap_rows.append([
            m, len(tot), len(oomed),
            max(ok_f) if ok_f else "—",          # longest sequence completed
            min(oom_f) if oom_f else "—",        # shortest sequence that OOMed
            fmt(max(peak), 1, 2) if peak else "—",
        ])
    cap_h = ["method", "n_runs", "n_oom", "max_frames_completed",
             "min_frames_oom", "max_vram_peak_gb"]
    write_csv("capacity.csv", cap_h, cap_rows)
    blob["capacity"] = [dict(zip(cap_h, r)) for r in cap_rows]

    # ---- per-method aggregate (replaces "Global aggregate") ---------------
    methods_main = [m for m in methods if not is_sweep(m)]
    agg = {m: method_block([r for r in agg_set if r["method"] == m])
           for m in methods_main}
    agg = {m: v for m, v in agg.items() if v["n"]}
    hdr = ["Method", "N", "ATE cm↓", "drift %/m↓", "Acc m↓", "Compl m↓", "Chamfer m↓",
           "Masked F↑", "Full-360 F↑", "Map MB↓",
           "Outlier %↓", "Prec@2cm %↑", "Scale err %↓", "VRAM peak GB↓",
           "per-win lat s↓", "Eff.FPS↑"]
    rows = [[m, a["n"], fmt(a["ate_cm"], 1, 1), fmt(a["drift_pct_m"], 1, 1),
             fmt(a["masked_acc_m"], 1, 4), fmt(a["masked_compl_m"], 1, 4),
             fmt(a["masked_chamfer_m"], 1, 4),
             fmt(a["masked_f"], 1, 3), fmt(a["full360_f"], 1, 3), fmt(a["map_mb"], 1, 1),
             fmt(a["outlier_pct"], 1, 2), fmt(a["prec2cm_pct"], 1, 1),
             fmt(a["scale_err_pct"], 1, 1, na="N/A"), fmt(a["vram_peak_gb"], 1, 2),
             fmt(a["per_window_lat_s"], 1, 2), fmt(a["eff_fps"], 1, 2)]
            for m, a in sorted(agg.items())]
    write_csv("aggregate_per_method.csv", hdr, rows)
    blob["aggregate_per_method"] = agg

    # ---- fidelity vs memory sweep -----------------------------------------
    #  The operating curve. `prism` is the reference point (the deployed 0.02 m /
    #  4.5 m config); each sweep arm moves ONE knob. Read it as "what does the knob
    #  buy", not as a menu to pick the best F from — the baselines get no equivalent
    #  tuning, so quoting a swept number as the headline would be tuning on the test
    #  set. Only runs on the reduced sweep scene/trajectory set.
    sweep_present = [m for m in methods if is_sweep(m)]
    if sweep_present:
        sw_rows = []
        for m in ["prism"] + sorted(sweep_present):
            rs = [r for r in agg_set if r["method"] == m]
            if not rs:
                continue
            b = method_block(rs)
            arm = next((r for r in rs if r.get("voxel_size")), {})
            sw_rows.append([
                m, b["n"],
                arm.get("voxel_size", "0.02 (default)"),
                arm.get("max_depth", "4.5 (default)"),
                fmt(b["masked_f"], 1, 3), fmt(b["full360_f"], 1, 3),
                fmt(b["masked_acc_m"], 1, 4), fmt(b["masked_compl_m"], 1, 4),
                fmt(b["map_mb"], 1, 1), fmt(b["vram_peak_gb"], 1, 2),
                fmt(b["per_window_lat_s"], 1, 2), fmt(b["outlier_pct"], 1, 2),
            ])
        sw_h = ["Arm", "N", "voxel m", "max_depth m", "Masked F↑", "360 F↑",
                "Acc m↓", "Compl m↓", "Map MB↓", "VRAM peak GB↓", "per-win s↓",
                "Outlier %↓"]
        write_csv("voxel_sweep.csv", sw_h, sw_rows)
        blob["voxel_sweep"] = [dict(zip(sw_h, r)) for r in sw_rows]
    else:
        sw_rows, sw_h = [], []

    # ---- literature-comparable recon table --------------------------------
    #  Column semantics deliberately match the published baseline tables so our numbers
    #  can be placed next to theirs: ATE (m), Accuracy (m), Completeness (m), Chamfer
    #  (m) -- exactly VGGT-SLAM's Table 3. No thresholded F-score here on purpose.
    #  Caveat that belongs with any such comparison: they measure on real captures
    #  (TUM / 7-Scenes / ScanNet), we measure on rendered Replica with co-visibility
    #  masking and ICP refinement, so these are NOT drop-in comparable -- they are
    #  comparable in KIND, which is the most that can honestly be claimed.
    lit_rows = []
    for m, a in sorted(agg.items()):
        lit_rows.append([m, a["n"],
                         fmt(a["ate_cm"] and a["ate_cm"] / 100.0, 1, 4),
                         fmt(a["masked_acc_m"], 1, 4),
                         fmt(a["masked_compl_m"], 1, 4),
                         fmt(a["masked_chamfer_m"], 1, 4)])
    lit_h = ["Method", "N", "ATE m↓", "Accuracy m↓", "Completeness m↓", "Chamfer m↓"]
    write_csv("recon_literature.csv", lit_h, lit_rows)
    blob["recon_literature"] = [dict(zip(lit_h, r)) for r in lit_rows]

    # ---- streaming vs offline (native modes never mixed) ------------------
    def subset_table(names, fname, key):
        sub = [(m, agg[m]) for m in names if m in agg]
        r = [[m, a["n"], fmt(a["ate_cm"], 1, 1), fmt(a["masked_f"], 1, 3),
              fmt(a["full360_f"], 1, 3), fmt(a["outlier_pct"], 1, 2), fmt(a["map_mb"], 1, 1),
              fmt(a["vram_peak_gb"], 1, 2), fmt(a["per_window_lat_s"], 1, 2),
              fmt(a["eff_fps"], 1, 2), fmt(a["scale_err_pct"], 1, 1, na="N/A")]
             for m, a in sub]
        h = ["Method", "N", "ATE cm↓", "Masked F↑", "360 F↑", "Outlier %↓", "Map MB↓",
             "VRAM GB↓", "per-win s↓", "Eff.FPS↑", "Scale %↓"]
        write_csv(fname, h, r)
        blob[key] = {m: a for m, a in sub}
        return h, r

    stream_h, stream_r = subset_table(STREAMING, "streaming.csv", "streaming")
    off_h, off_r = subset_table(OFFLINE, "offline.csv", "offline")

    # ---- alignment-group study --------------------------------------------
    align_rows = []
    for m, group, dof in ALIGN_ARMS:
        if m not in agg:
            continue
        a = agg[m]
        align_rows.append([f"{group} ({m})", dof, a["n"], fmt(a["eff_fps"], 1, 2),
                           fmt(a["per_window_lat_s"], 1, 2), fmt(a["vram_peak_gb"], 1, 2),
                           fmt(a["scale_err_pct"], 1, 1), fmt(a["ate_cm"], 1, 1),
                           fmt(a["drift_pct_m"], 1, 1), fmt(a["masked_f"], 1, 3),
                           fmt(a["outlier_pct"], 1, 2)])
    align_h = ["Group (arm)", "DoF", "N", "Eff.FPS↑", "per-win s↓", "VRAM GB↓",
               "Scale err %↓", "ATE cm↓", "Drift %/m↓", "Masked F↑", "Outlier %↓"]
    write_csv("alignment.csv", align_h, align_rows)

    # ---- motion-stratified alignment table (2 Hz only: the matched comparison) --
    mot_rows = []
    for motion, _ in MOTION:
        cells = [motion]
        for m, group, _dof in ALIGN_ARMS:
            rs = [r for r in agg_set if r["method"] == m and r["motion"] == motion
                  and r["rate_hz"] == "2.0"]
            b = method_block(rs)
            cells.append(f"{fmt(b['ate_cm'], 1, 1)} / {fmt(b['masked_f'], 1, 2)} / "
                         f"{fmt(b['scale_err_pct'], 1, 1)} (N={b['n']})")
        mot_rows.append(cells)
    mot_h = ["Trajectory (2 Hz)"] + [f"{g} ATE / F / scale%" for _, g, _ in ALIGN_ARMS]
    write_csv("motion_alignment.csv", mot_h, mot_rows)

    # ---- motion breakdown, all methods ------------------------------------
    mb_rows = []
    for m in methods:
        cells = [m]
        for motion, _ in MOTION:
            rs = [r for r in agg_set if r["method"] == m and r["motion"] == motion
                  and r["rate_hz"] == "2.0"]
            b = method_block(rs)
            cells.append(fmt(b["ate_cm"], 1, 1))
        mb_rows.append(cells)
    mb_h = ["Method"] + [f"ATE cm — {mo}" for mo, _ in MOTION]
    write_csv("motion.csv", mb_h, mb_rows)
    blob["motion_ate_cm"] = [dict(zip(mb_h, r)) for r in mb_rows]

    # ---- per-seed values + variance (the error-bar source) ----------------
    #  There are two very different dispersions here and conflating them produces
    #  a meaningless error bar:
    #
    #    (a) BETWEEN-CELL heterogeneity — apartment_0-loop vs hotel_0-smooth differ
    #        by ~70 cm ATE. Averaging over cells and taking a std across them mostly
    #        measures "scenes and motions are different", which we already know.
    #    (b) WITHIN-CELL seed repeatability — the same scene, same trajectory family,
    #        same rate, re-rendered under a different seed. THIS is the error bar that
    #        answers "would this number replicate?", and it is what the paper needs.
    #
    #  The replicate cell is therefore (method, scene, traj-without-seed); the seeds
    #  inside it are the repeats. We report the pooled within-cell std (sqrt of the
    #  mean within-cell variance) alongside the pooled mean, so the central value is
    #  identical to the main aggregate table and only the ± comes from seed noise.
    def traj_base(t: str) -> str:
        return SEEDED_RE.sub("", t)

    ps_rows, cells_by_method = [], {}
    for m in methods:
        rs_m = [r for r in agg_set if r["method"] == m]
        for scene in sorted({r["scene"] for r in rs_m}):
            for tb in sorted({traj_base(r["traj"]) for r in rs_m if r["scene"] == scene}):
                cell = {}
                for seed in sorted({r["seed"] for r in rs_m
                                    if r["scene"] == scene and traj_base(r["traj"]) == tb
                                    and r["seed"]}):
                    rs = [r for r in rs_m if r["scene"] == scene
                          and traj_base(r["traj"]) == tb and r["seed"] == seed]
                    b = method_block(rs)
                    cell[seed] = b
                    ps_rows.append([m, scene, tb, seed, b["n"]]
                                   + [fmt(b[k], 1, 4) for k in HEADLINE])
                if cell:
                    cells_by_method.setdefault(m, []).append(cell)
    write_csv("per_seed.csv",
              ["method", "scene", "traj_base", "seed", "n_runs"] + HEADLINE, ps_rows)

    def seed_stats(m: str, k: str):
        """Pooled mean over all runs + pooled within-cell (seed) std for metric k."""
        pooled = mean([b[k] for c in cells_by_method.get(m, []) for b in c.values()])
        variances, deltas = [], []
        for cell in cells_by_method.get(m, []):
            vals = [b[k] for b in cell.values() if b[k] is not None]
            if len(vals) > 1:
                variances.append(st.variance(vals))
                deltas.append(max(vals) - min(vals))
        sd = math.sqrt(st.mean(variances)) if variances else None
        return pooled, sd, len(variances), (st.mean(deltas) if deltas else None)

    var_rows = []
    for m in sorted(cells_by_method):
        for k in HEADLINE:
            mu, sd, ncell, mdelta = seed_stats(m, k)
            if mu is None:
                continue
            rel = f"{100 * sd / abs(mu):.1f}" if sd is not None and mu else "—"
            var_rows.append([m, k, ncell, fmt(mu, 1, 4), fmt(sd, 1, 4), rel,
                             fmt(mdelta, 1, 4)])
    var_h = ["method", "metric", "n_paired_cells", "pooled_mean",
             "within_cell_seed_std", "seed_std_pct_of_mean", "mean_abs_seed_delta"]
    write_csv("seed_repeatability.csv", var_h, var_rows)
    blob["seed_repeatability"] = [dict(zip(var_h, r)) for r in var_rows]

    # Between-cell dispersion kept separately, clearly labelled as heterogeneity.
    het_rows = []
    for m in sorted(cells_by_method):
        for k in HEADLINE:
            vals = [b[k] for c in cells_by_method[m] for b in c.values() if b[k] is not None]
            if not vals:
                continue
            het_rows.append([m, k, len(vals), fmt(mean(vals), 1, 4), fmt(stdev(vals), 1, 4),
                             fmt(ci95(vals), 1, 4), fmt(min(vals), 1, 4), fmt(max(vals), 1, 4)])
    write_csv("variance.csv",
              ["method", "metric", "n_cells", "mean", "between_cell_std",
               "ci95_halfwidth", "min", "max"], het_rows)

    # ---- headline with error bars (pooled mean ± seed std) ----------------
    eb_rows = []
    for m in sorted(cells_by_method):
        npaired = max((seed_stats(m, k)[2] for k in HEADLINE), default=0)
        cells = [m, npaired]
        for k in ("ate_cm", "masked_f", "vram_peak_gb", "eff_fps"):
            mu, sd, _n, _d = seed_stats(m, k)
            nd = 3 if k == "masked_f" else 1
            cells.append("—" if mu is None else
                         f"{mu:.{nd}f} ± {sd:.{nd}f}" if sd is not None else f"{mu:.{nd}f}")
        eb_rows.append(cells)
    eb_h = ["Method", "Paired cells", "ATE cm", "Masked F", "VRAM peak GB", "Eff.FPS"]
    write_csv("headline_errorbars.csv", eb_h, eb_rows)

    # ---- paired head-to-head vs the reference arm -------------------------
    #  Marginal means carry the full scene x motion spread, which is wide enough to
    #  make most method gaps look inseparable. But every method saw the SAME rendered
    #  trajectories, so the comparison is naturally paired: match runs on
    #  (scene, traj) and difference them run-by-run. That cancels the scene/motion
    #  variance and is the honest way to ask "is A actually better than B here".
    #
    #  Reported per pair: n matched runs, mean paired delta (A - B) with a 95% CI,
    #  and a win rate with an exact two-sided sign-test p. The sign test makes no
    #  normality assumption, which matters because ATE is heavy-tailed.
    def sign_test_p(wins: int, losses: int) -> float | None:
        n = wins + losses
        if n == 0:
            return None
        c = min(wins, losses)
        cum = sum(math.comb(n, i) for i in range(c + 1))
        return min(1.0, 2.0 * cum / (2 ** n))

    LOWER_BETTER = {"ate_cm": True, "masked_f": False, "full360_f": False,
                    "map_mb": True, "outlier_pct": True, "scale_err_pct": True,
                    "vram_peak_gb": True, "eff_fps": False, "per_window_lat_s": True}

    def run_metric(r, k):
        b = method_block([r])
        return b[k]

    ref = "prism_sim3" if any(r["method"] == "prism_sim3" for r in agg_set) else "prism"
    pair_rows = []
    for other in [m for m in methods_main if m != ref]:
        idx_a = {(r["scene"], r["traj"]): r for r in agg_set if r["method"] == ref}
        idx_b = {(r["scene"], r["traj"]): r for r in agg_set if r["method"] == other}
        shared = sorted(set(idx_a) & set(idx_b))
        if not shared:
            continue
        for k in ("ate_cm", "masked_f", "map_mb", "outlier_pct", "eff_fps", "vram_peak_gb"):
            deltas = []
            for key in shared:
                va, vb = run_metric(idx_a[key], k), run_metric(idx_b[key], k)
                if va is not None and vb is not None:
                    deltas.append(va - vb)
            if len(deltas) < 2:
                continue
            lower_better = LOWER_BETTER[k]
            wins = sum(1 for d in deltas if (d < 0) == lower_better and d != 0)
            losses = sum(1 for d in deltas if (d > 0) == lower_better and d != 0)
            mu, ci = st.mean(deltas), ci95(deltas)
            pair_rows.append([
                ref, other, k, len(deltas), fmt(mu, 1, 3), fmt(ci, 1, 3),
                f"{wins}/{wins + losses}",
                fmt(sign_test_p(wins, losses), 1, 4),
                "yes" if (ci is not None and abs(mu) > ci) else "no",
            ])
    pair_h = [f"reference", "comparator", "metric", "n_matched", "mean_delta_ref_minus_cmp",
              "ci95_halfwidth", "ref_wins", "sign_test_p", "ci_excludes_zero"]
    write_csv("paired_head_to_head.csv", pair_h, pair_rows)
    blob["paired_head_to_head"] = [dict(zip(pair_h, r)) for r in pair_rows]

    # ---- clean run dump ----------------------------------------------------
    cols = list(agg_set[0].keys())
    with open(out / "runs_clean.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(agg_set)

    # ---- markdown ----------------------------------------------------------
    seeds = blob["seeds"]
    md = [
        "# PRISM-benchmarks — clean seeded-only results\n",
        f"*Source: `{blob['source']}`. "
        f"{blob['n_input']} input run-records → {blob['n_seeded_kept']} seeded "
        f"({blob['n_excluded']} excluded) → **{blob['n_complete']} complete runs aggregated** "
        f"({blob['n_incomplete']} produced no evaluable output).*\n",
        f"Scenes: {', '.join(blob['scenes'])} · Seeds: {', '.join(seeds)} · "
        f"Trajectories: {len(blob['trajectories'])} ids\n",
        "## Exclusions applied\n",
    ]
    md += [f"- {reason}" for reason in blob["exclusion_reasons"]] + [""]
    md += [
        "> **Incomplete runs are excluded from every aggregate, including perf.** "
        "`eff_fps` is computed from the *input* frame count, so a run that died early "
        "reports a spuriously high fps; averaging those in inflates throughput. "
        "See the completion table for the failure breakdown.\n",
        "## Completion / failure rate\n",
        "*`N oom` is counted separately from `N failed`: an out-of-memory run is a "
        "recorded capacity result, not a defect.*\n",
        "> **`N degenerate`** counts runs where the method's own machinery never "
        "engaged — currently VGGT-SLAM runs that built a single submap, so no SL(4) "
        "registration and no loop closure ran and the result is plain feed-forward "
        "VGGT. Those runs are NOT a valid head-to-head datapoint; if this column is "
        "non-zero, say so or exclude them before claiming a win over that baseline.\n",
        md_table(["Method", "N total", "N complete", "N failed", "N OOM", "N degenerate",
                  "Incomplete %", "By scene", "By motion"], comp_rows), "",
        "## Capacity — how long a sequence each method survives\n",
        "*The deployability result. Full-batch methods ingest every view at once, so "
        "their memory grows with sequence length until it doesn't fit; a bounded-memory "
        "streaming engine should simply never appear in the OOM column. Sequence lengths "
        "are deliberately NOT capped to protect the offline methods.*\n",
        md_table(["Method", "N runs", "N OOM", "Longest completed (frames)",
                  "Shortest OOM (frames)", "Max peak VRAM GB"], cap_rows), "",
        "## Per-method aggregate (clean, seeded, complete runs only)\n",
        md_table(hdr, rows), "",
        *( ["## Fidelity vs memory — the engine's operating curve\n",
             "*PRISM is the only method here with a tunable memory/fidelity trade; the "
             "feed-forward baselines have exactly one operating point, at 25-45 GB. "
             "`prism` is the deployed reference (0.02 m voxel, 4.5 m max_depth) and each "
             "arm moves one knob. Report the CURVE — quoting the best swept F as the "
             "headline would be tuning on the test set, since no baseline gets "
             "equivalent tuning. Reduced scene/trajectory set, so N is small.*\n",
             md_table(sw_h, sw_rows), ""] if sw_rows else [] ),
        "## Reconstruction in literature units (metres, no threshold)\n",
        "*Column semantics match the published baseline tables (VGGT-SLAM Tab. 3 is "
        "ATE / Acc / Compl / Chamfer in metres; LASER, VGGT and PanoVGGT report "
        "Acc / Comp / Overall). **No baseline paper reports an F-score at any "
        "threshold** — F@5cm is our addition, so these are the only columns that can be "
        "placed beside a published number. They are comparable in KIND only: the "
        "published numbers come from real captures (TUM / 7-Scenes / ScanNet), ours "
        "from rendered Replica with co-visibility masking and ICP refinement.*\n",
        md_table(lit_h, lit_rows), "",
        "## Streaming comparison (native streaming mode; throughput included)\n",
        md_table(stream_h, stream_r), "",
        "## Full-batch offline upper bound (ingest all views at once)\n",
        md_table(off_h, off_r), "",
        "## Alignment-group study — Sim(3) vs SL(4) vs SE(3)\n",
        "*Same backbone / fusion / trajectory; only the submap registration group varies.*\n",
        md_table(align_h, align_rows), "",
        "## Alignment group stratified by motion (2 Hz)\n",
        md_table(mot_h, mot_rows), "",
        "## ATE by motion family, all methods (2 Hz)\n",
        md_table(mb_h, mb_rows), "",
        f"## Headline metrics with error bars\n",
        f"*Pooled mean ± **within-cell seed std** — the replicate cell is "
        f"(scene, trajectory family, rate) and the {len(seeds)} seeds inside it are the "
        f"repeats, so the ± isolates seed noise rather than scene/motion heterogeneity "
        f"(the central value is identical to the aggregate table above). "
        f"With only {len(seeds)} seeds per cell each variance estimate has 1 d.o.f.; "
        f"pooling across cells is what makes it usable, but this is still indicative "
        f"dispersion, not a converged interval — add seeds to tighten it. "
        f"Between-cell heterogeneity is reported separately in `variance.csv`.*\n",
        md_table(eb_h, eb_rows), "",
        f"## Paired head-to-head vs `{ref}`\n",
        "*Every method saw the same rendered trajectories, so runs are matched on "
        "(scene, traj) and differenced run-by-run — cancelling the scene/motion spread "
        "that dominates the marginal means. `mean_delta` is reference − comparator "
        "(so **negative is better for the reference** on ↓ metrics). `ci_excludes_zero` "
        "and the exact sign test are the two independent separability checks; the sign "
        "test assumes no distribution, which matters because ATE is heavy-tailed.*\n",
        md_table(pair_h, pair_rows), "",
        "## Standing caveats\n",
        "- Rendered frames are noise-free → an **optimistic upper bound** vs real "
        "Theta-X captures.\n"
        "- Metric scale degrades on loops (Sim(3) ~20%, SL(4) ~31%).\n"
        "- Shipped PRISM has **no loop closure**; the full-batch nets implicitly close loops.\n"
        "- All seeded scenes are large/hard unless a small room has been added to the "
        "matrix — check the scene list above.\n",
    ]
    (out / "clean_report.md").write_text("\n".join(md), encoding="utf-8")
    (out / "clean_report.json").write_text(json.dumps(blob, indent=2, default=str),
                                           encoding="utf-8")

    print(f"[aggregate_clean] source={blob['source']}")
    print(f"[aggregate_clean] {blob['n_input']} in -> {blob['n_seeded_kept']} seeded "
          f"-> {blob['n_complete']} complete ({blob['n_incomplete']} incomplete)")
    for reason in blob["exclusion_reasons"]:
        print(f"[aggregate_clean]   excluded: {reason}")
    print(f"[aggregate_clean] -> {out}/clean_report.md (+ csv/json)")


if __name__ == "__main__":
    main()
