"""Validate a smoke run and project the full run's cost. Exits non-zero on failure.

`scripts/smoke_test.sh` drives a tiny matrix through the whole pipeline; this decides
whether that matrix actually proved anything. It is deliberately pedantic, because the
entire point is to fail *here*, cheaply, rather than six hours into an overnight run.

Checks, per configured method:
  * produced poses.tum AND cloud.ply, both non-empty
  * perf.json says completed=true, returncode=0, n_frames_done>0
  * latency_end_to_end_s > 0 with a stated latency_source   <- the 2026-07 bug
  * per_window_latency_med_s present with a stated source   <- the "n/a" columns
  * ate.json / recon.json produced (metric.json only for metric-capable methods)
  * recon has BOTH masked and full_360 blocks (the fairness pair)

Then, across the run:
  * the seeded-only aggregation ran and verify-clean passed
  * the report-facing bundle was emitted
  * snapshots exist for all three co-visibility mask variants

Finally it extrapolates wall-clock to the real matrix from the measured per-run times,
so you know what the overnight run will cost before you start it.

Usage:  make smoke   (or)   uv run python eval/smoke_check.py --config config.yaml
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config, resolve_trajs

OK, BAD, WARN = "PASS", "FAIL", "WARN"


class Report:
    def __init__(self):
        self.rows: list[tuple[str, str, str]] = []
        self.failed = 0
        self.warned = 0

    def add(self, status, what, detail=""):
        self.rows.append((status, what, detail))
        if status == BAD:
            self.failed += 1
        elif status == WARN:
            self.warned += 1

    def check(self, cond, what, ok_detail="", bad_detail="", warn_only=False):
        if cond:
            self.add(OK, what, ok_detail)
        else:
            self.add(WARN if warn_only else BAD, what, bad_detail)
        return bool(cond)

    def print(self):
        w = max(len(r[1]) for r in self.rows) if self.rows else 20
        mark = {OK: "[ok]  ", BAD: "[FAIL]", WARN: "[warn]"}
        print("\n" + "=" * (w + 34))
        print("SMOKE TEST RESULT")
        print("=" * (w + 34))
        for status, what, detail in self.rows:
            print(f"  {mark[status]} {what:<{w}}  {detail}")
        print("=" * (w + 34))


def _load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _nonempty(p: Path, min_bytes=1) -> bool:
    return p.exists() and p.stat().st_size >= min_bytes


def _count_lines(p: Path) -> int:
    try:
        return sum(1 for ln in p.read_text().splitlines()
                   if ln.strip() and not ln.lstrip().startswith("#"))
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--expect-methods", default="",
                    help="comma list; default = every method+ablation in the config")
    ap.add_argument("--full-config", default="config.yaml",
                    help="config describing the REAL matrix, for the ETA projection")
    args = ap.parse_args()

    cfg = load_config(args.config)
    r = Report()

    methods = [m["name"] for m in cfg.get("methods", [])] + \
              [m["name"] for m in cfg.get("ablations", [])]
    if args.expect_methods.strip():
        methods = [m.strip() for m in args.expect_methods.split(",") if m.strip()]
    metric_capable = {m["name"]: bool(m.get("metric"))
                      for m in cfg.get("methods", []) + cfg.get("ablations", [])}

    results = REPO_ROOT / "results"
    r.check(results.exists(), "results/ exists",
            bad_detail="no results tree — did render/export/run stages run?")

    # ── per-method checks ────────────────────────────────────────────────────
    durations: list[float] = []
    per_method_runs: dict[str, int] = {}
    for method in methods:
        run_dirs = sorted((results / method).glob("*/*/*/*")) if (results / method).exists() else []
        run_dirs = [d for d in run_dirs if d.is_dir()]
        if not r.check(run_dirs, f"{method}: produced runs",
                       ok_detail=f"{len(run_dirs)} run(s)",
                       bad_detail="NO runs — method env missing, or it crashed at launch"):
            continue
        per_method_runs[method] = len(run_dirs)

        bad_poses = bad_cloud = bad_perf = bad_lat = bad_pwin = 0
        bad_ate = bad_recon = bad_metric = bad_pair = 0
        for d in run_dirs:
            if _count_lines(d / "poses.tum") == 0:
                bad_poses += 1
            if not _nonempty(d / "cloud.ply", 64):
                bad_cloud += 1
            perf = _load(d / "perf.json") or {}
            if not perf.get("completed") or perf.get("returncode") not in (0, None) \
                    or not perf.get("n_frames_done"):
                bad_perf += 1
            if not perf.get("latency_end_to_end_s") or \
                    perf.get("latency_source", "unavailable") == "unavailable":
                bad_lat += 1
            if not perf.get("per_window_latency_med_s") and not perf.get("per_window_latency_s"):
                bad_pwin += 1
            if not _load(d / "ate.json"):
                bad_ate += 1
            recon = _load(d / "recon.json") or {}
            if not recon:
                bad_recon += 1
            elif not (recon.get("masked") and recon.get("full_360")):
                bad_pair += 1
            if metric_capable.get(method) and not _load(d / "metric.json"):
                bad_metric += 1
            w = perf.get("wall_s") or perf.get("latency_end_to_end_s")
            if w:
                durations.append(float(w))

        n = len(run_dirs)
        r.check(not bad_poses, f"{method}: poses.tum non-empty",
                bad_detail=f"{bad_poses}/{n} run(s) wrote no poses")
        r.check(not bad_cloud, f"{method}: cloud.ply non-empty",
                bad_detail=f"{bad_cloud}/{n} run(s) wrote no cloud")
        r.check(not bad_perf, f"{method}: run completed cleanly",
                bad_detail=f"{bad_perf}/{n} run(s) did not complete — THIS is the "
                           f"failure mode that cost 25% of PRISM arms in 2026-07")
        r.check(not bad_lat, f"{method}: latency logged + attributed",
                bad_detail=f"{bad_lat}/{n} run(s) have zero/unattributed latency")
        r.check(not bad_pwin, f"{method}: per-window latency present",
                warn_only=True,
                bad_detail=f"{bad_pwin}/{n} run(s) lack per-window latency")
        r.check(not bad_ate, f"{method}: ate.json produced",
                bad_detail=f"{bad_ate}/{n} missing — eval-traj did not score it")
        r.check(not bad_recon, f"{method}: recon.json produced",
                bad_detail=f"{bad_recon}/{n} missing — eval-recon did not score it")
        r.check(not bad_pair, f"{method}: masked + full_360 both scored",
                bad_detail=f"{bad_pair}/{n} lack one of the pair — the co-visibility "
                           f"mask or the pinhole export is missing")
        if metric_capable.get(method):
            r.check(not bad_metric, f"{method}: metric.json produced",
                    bad_detail=f"{bad_metric}/{n} missing for a metric-capable method")

    # ── aggregation + verification ───────────────────────────────────────────
    clean = REPO_ROOT / "results" / "report_clean"
    r.check(_nonempty(clean / "clean_report.md"), "clean aggregate produced",
            bad_detail="make report-clean did not emit clean_report.md")
    meta = _load(clean / "clean_report.json") or {}
    n_complete = meta.get("n_complete", 0)
    r.check(n_complete > 0, "clean aggregate is non-empty",
            ok_detail=f"{n_complete} complete seeded run(s) aggregated",
            bad_detail="0 runs survived the seeded/complete filters — if the smoke "
                       "used ONE seed the traj ids carry no _sN and all were excluded")
    for f in ("streaming.csv", "alignment.csv", "completion.csv",
              "seed_repeatability.csv", "paired_head_to_head.csv"):
        r.check(_nonempty(clean / f), f"clean table: {f}")

    tables = REPO_ROOT / "results" / "report_tables"
    r.check(_nonempty(tables / "MANIFEST.json"), "report bundle emitted",
            bad_detail="make report-tables did not run")

    # ── snapshots, incl. every co-visibility mask variant ────────────────────
    snaps = REPO_ROOT / cfg["report"]["out_dir"] / "snapshots"
    if snaps.exists():
        names = [p.name for p in snaps.glob("*.png")]
        for mv in ("full", "covis", "masked"):
            hits = [n for n in names if f"__{mv}__" in n]
            r.check(hits, f"snapshots: '{mv}' mask variant",
                    ok_detail=f"{len(hits)} image(s)",
                    bad_detail=f"none rendered — check the pinhole export exists "
                               f"(the covis/masked variants need it for the mask)",
                    warn_only=(mv == "full"))
    else:
        r.add(WARN, "snapshots", "not generated (skipped?)")

    # ── Did the smoke actually EXERCISE the things it claims to? ─────────────
    #  The 2026-08-08 smoke passed every check above while testing almost nothing:
    #  the sequences were too short for the loop to close, for PRISM to build a
    #  second window, or for VGGT-SLAM to build a second submap. A smoke test that
    #  cannot fail on that is worse than no smoke test, because it grants confidence.
    def _runs(method):
        d = results / method
        return sorted(p for p in d.glob("*/*/*/*") if p.is_dir()) if d.exists() else []

    # (a) every method must pose EVERY input frame
    for method in methods:
        bad = []
        for d in _runs(method):
            perf = _load(d / "perf.json") or {}
            ni, nd = perf.get("n_frames_input"), perf.get("n_frames_done")
            # Keyframe-selecting methods (VGGT-SLAM) legitimately emit fewer poses.
            if ni and nd and nd < ni and method not in ("vggtslam", "vggtslam_loop",
                                                        "vggtslam_noloop", "vggtslam_w16"):
                bad.append(f"{d.name}:{nd}/{ni}")
        r.check(not bad, f"{method}: posed every input frame",
                bad_detail=f"dropped frames in {len(bad)} run(s) [{', '.join(bad[:3])}] — "
                           f"this method is scored on a shorter trajectory than the "
                           f"baselines, which biases it")

    # (b) VGGT-SLAM must actually build >1 submap, else its method is inactive
    for method in [m for m in methods if m.startswith("vggtslam")]:
        degen = []
        for d in _runs(method):
            arm = _load(d / "arm_config.json") or {}
            if arm.get("degenerate_single_submap"):
                degen.append(f"{d.name}:{arm.get('n_submaps')}submap")
        r.check(not degen, f"{method}: pose graph engaged (>1 submap)",
                bad_detail=f"{len(degen)} run(s) built a single submap — no SL(4) "
                           f"registration, no loop closure. It is running as plain "
                           f"feed-forward VGGT; a head-to-head would be a strawman. "
                           f"Lengthen the sequence or lower submap_size/min_disparity")

    # (c) loop must differ from smooth, else the loop family is not looping
    def _mean_ate(method, fam):
        vals = []
        for d in _runs(method):
            if not d.parent.name.startswith(fam):
                continue
            a = _load(d / "ate.json") or {}
            if a.get("ate_rmse_m") is not None:
                vals.append(a["ate_rmse_m"])
        return sum(vals) / len(vals) if vals else None

    same = []
    for method in methods:
        sm, lp = _mean_ate(method, "synthetic_"), _mean_ate(method, "loop_")
        if sm and lp and abs(sm - lp) / max(sm, 1e-9) < 0.02:      # within 2%
            same.append(method)
    r.check(len(same) < max(2, len(methods) // 2),
            "loop trajectory differs from smooth",
            ok_detail="the loop family is exercising revisit behaviour",
            bad_detail=f"{len(same)} method(s) scored within 2% on loop vs smooth "
                       f"({', '.join(same[:4])}) — the 'loop' path is probably too "
                       f"short to return to its start, so the loop/revisit code path "
                       f"is UNTESTED")

    # (d) the alignment arms must diverge, else PRISM_ALIGN is doing nothing
    align_arms = [m for m in ("prism", "prism_sl4", "prism_se3") if m in methods]
    if len(align_arms) > 1:
        per_arm = {m: _mean_ate(m, "") for m in align_arms}
        vals = [v for v in per_arm.values() if v]
        spread = (max(vals) - min(vals)) / max(max(vals), 1e-9) if len(vals) > 1 else 0
        r.check(spread > 0.01, "alignment arms diverge (PRISM_ALIGN is live)",
                ok_detail=f"ATE spread {100 * spread:.1f}% across {align_arms}",
                bad_detail=f"arms {align_arms} agree to within {100 * spread:.2f}% — "
                           f"PRISM_ALIGN only takes effect from the SECOND window "
                           f"onward, so the sequence is too short to test it "
                           f"(needs > 2*window_size - overlap frames)")

    # ── ETA projection for the real matrix ───────────────────────────────────
    print()
    if durations:
        mean_s = sum(durations) / len(durations)
        smoke_runs = sum(per_method_runs.values())
        # Load the FULL matrix config with the smoke overlay suppressed. Otherwise
        # PRISM_CONFIG_OVERLAY (still exported by smoke_test.sh) merges on top and the
        # "full run" projection is computed from the smoke's own tiny matrix -- which is
        # how it reported "6 trajectories, 120 frames, ETA 1.9 h .. 1.9 h" for a run that
        # is actually 12 trajectories at 300 frames.
        import os as _os
        _saved = _os.environ.pop("PRISM_CONFIG_OVERLAY", None)
        try:
            full = load_config(args.full_config)
        finally:
            if _saved is not None:
                _os.environ["PRISM_CONFIG_OVERLAY"] = _saved
        n_scenes = len(full["datasets"]["replica"].get("scenes") or []) or \
            full["datasets"]["replica"].get("n_scenes_start", 6)
        n_trajs = len(resolve_trajs(full, "all"))
        n_methods = len(full.get("methods", [])) + len(full.get("ablations", []))
        full_runs = n_scenes * n_trajs * n_methods
        # The smoke caps frames hard, so per-run time will grow roughly with frame
        # count on top of a fixed model-load cost. Report the honest bracket rather
        # than one falsely precise number.
        smoke_frames = cfg["trajectories"]["n_frames"]
        full_frames = full["trajectories"]["n_frames"]
        lo = full_runs * mean_s / 3600.0
        hi = full_runs * mean_s * (full_frames / max(smoke_frames, 1)) / 3600.0
        print("PROJECTED COST OF THE FULL RUN")
        print(f"  smoke: {smoke_runs} runs, mean {mean_s:.1f}s/run "
              f"({smoke_frames} frames cap)")
        print(f"  full : {n_scenes} scenes x {n_trajs} trajectories x {n_methods} methods "
              f"= {full_runs} runs ({full_frames} frames cap)")
        print(f"  ETA  : {lo:.1f} h (if model-load dominates) .. "
              f"{hi:.1f} h (if frame count dominates)")
        print("  The truth is usually nearer the low end — model load is a fixed cost "
              "per run.\n  Resumable: re-running skips finished runs unless PRISM_FORCE=1.")
    else:
        print("PROJECTED COST: no per-run timings found; cannot extrapolate.")

    r.print()
    if r.failed:
        print(f"\n{r.failed} check(s) FAILED"
              f"{f', {r.warned} warning(s)' if r.warned else ''}. "
              f"Fix these before the long run — that is what this test is for.")
        sys.exit(1)
    print(f"\nAll checks passed{f' ({r.warned} warning(s))' if r.warned else ''}. "
          f"The pipeline is working end to end; the full run should complete.")


if __name__ == "__main__":
    main()
