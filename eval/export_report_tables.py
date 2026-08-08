"""Emit the report-facing table bundle that `uofa-2026-report` ingests.

`eval/aggregate_clean.py` is the analysis layer; this is the *interface* layer. It
takes the clean aggregate and writes one directory whose column semantics are frozen
to match the report's existing tables (ATE cm, Masked F, Outlier %, Map MB, VRAM GB,
per-window s, scale %, 360 F), so the report can swap numbers in without touching its
Typst table code.

Emitted per table: `<name>.csv` (machine-readable), and all of them together in
`report_tables.json` and `report_tables.md`. A `MANIFEST.json` records provenance —
source run, filters applied, run counts, and which tables are backed by real runs vs
awaiting a GPU run — so a stale table can never be silently cited.

Usage
    make report-tables
    uv run python eval/export_report_tables.py --source archive --run-id bigrun_2026-07
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT

# name -> (source csv in report_clean/, human title, one-line caption for the report)
TABLES = {
    "streaming_comparison": (
        "streaming.csv",
        "Streaming methods (native online mode)",
        "All methods driven incrementally. Throughput (Eff.FPS) is included so the "
        "real-time claim is checkable against the 2.5 Hz capture rate."),
    "offline_upper_bound": (
        "offline.csv",
        "Full-batch offline upper bound",
        "Feed-forward methods ingesting all views at once — an upper bound, not a "
        "like-for-like competitor to a streaming engine."),
    "alignment_study": (
        "alignment.csv",
        "Alignment-group study",
        "Same backbone, fusion and trajectory; only the submap registration group varies."),
    "alignment_by_motion": (
        "motion_alignment.csv",
        "Alignment group stratified by motion (2 Hz)",
        "Where the group choice actually matters: SL(4) leads on open paths and loses "
        "on loops."),
    "ate_by_motion": (
        "motion.csv",
        "ATE by motion family, all methods (2 Hz)",
        "Trajectory accuracy split by smooth / stop-and-go / loop."),
    "per_method_aggregate": (
        "aggregate_per_method.csv",
        "Per-method aggregate (clean, seeded, complete runs only)",
        "Replaces the contaminated 'Global aggregate'."),
    "headline_errorbars": (
        "headline_errorbars.csv",
        "Headline metrics with error bars",
        "Pooled mean ± within-cell seed std; the ± isolates seed noise from "
        "scene/motion heterogeneity."),
    "seed_repeatability": (
        "seed_repeatability.csv",
        "Seed repeatability",
        "How much each metric moves when only the render seed changes."),
    "paired_head_to_head": (
        "paired_head_to_head.csv",
        "Paired head-to-head",
        "Runs matched on (scene, traj) and differenced, cancelling scene/motion spread."),
    "completion": (
        "completion.csv",
        "Run completion / failure rate",
        "How many runs each method actually finished. Read this before any mean."),
    "vram_vs_sequence_length": (
        "vram_vs_frames.csv",
        "Peak VRAM vs sequence length",
        "The deployability figure: streaming stays bounded, full-batch grows."),
}


def read_csv(p: Path):
    if not p.exists():
        return None
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return {"header": rows[0], "rows": rows[1:]} if rows else None


def md_table(header, rows) -> str:
    out = "| " + " | ".join(str(h) for h in header) + " |\n"
    out += "| " + " | ".join("---" for _ in header) + " |\n"
    for r in rows:
        out += "| " + " | ".join(str(c) for c in r) + " |\n"
    return out


def build_vram_table(clean_dir: Path, out_dir: Path):
    """Peak VRAM vs #frames, per method, from the clean run dump."""
    src = clean_dir / "runs_clean.csv"
    if not src.exists():
        return
    buckets: dict[str, dict[int, list[float]]] = {}
    with open(src, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                n, v = int(float(r["n_frames"])), float(r["vram_peak_gb"])
            except (TypeError, ValueError, KeyError):
                continue
            if not n or not v:
                continue
            buckets.setdefault(r["method"], {}).setdefault(n, []).append(v)
    rows = []
    for m in sorted(buckets):
        for n in sorted(buckets[m]):
            vals = buckets[m][n]
            rows.append([m, n, len(vals), f"{sum(vals) / len(vals):.3f}",
                         f"{max(vals):.3f}"])
    with open(out_dir / "vram_vs_frames.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["method", "n_frames", "n_runs", "vram_peak_gb_mean", "vram_peak_gb_max"])
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--clean-dir", default="results/report_clean")
    ap.add_argument("--out", default="results/report_tables")
    # results/ is gitignored (run outputs are never committed), but uofa-2026-report
    # needs to cite these tables from a tracked path. documentation/docs/data/ is the
    # convention the repo already uses for citable artifacts (the 2026-07 snapshot
    # lives there), so the bundle is mirrored into it.
    ap.add_argument("--publish-dir", default="documentation/docs/data/clean_latest",
                    help="tracked location to mirror the bundle into ('' to skip)")
    args = ap.parse_args()

    clean_dir = REPO_ROOT / args.clean_dir
    if not (clean_dir / "clean_report.json").exists():
        raise SystemExit(f"[export_report_tables] {clean_dir}/clean_report.json missing — "
                         "run 'make report-clean' first.")
    meta = json.loads((clean_dir / "clean_report.json").read_text(encoding="utf-8"))
    out = REPO_ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    build_vram_table(clean_dir, clean_dir)

    bundle, manifest_tables, md = {}, {}, []
    md.append("# PRISM-benchmarks — report-facing tables\n")
    md.append(f"*Source `{meta['source']}` · {meta['n_complete']} complete seeded runs "
              f"of {meta['n_input']} input records · generated by "
              f"`eval/export_report_tables.py`.*\n")
    md.append("> Column semantics are frozen to match the report's existing tables. "
              "Regenerate with `make report-tables`; do not hand-edit.\n")

    for name, (fname, title, caption) in TABLES.items():
        t = read_csv(clean_dir / fname)
        if t is None:
            manifest_tables[name] = {"status": "absent", "reason": f"{fname} not produced"}
            continue
        with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(t["header"])
            w.writerows(t["rows"])
        bundle[name] = {"title": title, "caption": caption, **t}
        manifest_tables[name] = {"status": "ok", "rows": len(t["rows"]),
                                 "csv": f"{name}.csv"}
        md += [f"## {title}\n", f"*{caption}*\n", md_table(t["header"], t["rows"]), ""]

    (out / "report_tables.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    (out / "report_tables.md").write_text("\n".join(md), encoding="utf-8")

    manifest = {
        "generated_by": "eval/export_report_tables.py",
        "source": meta["source"],
        "n_input_records": meta["n_input"],
        "n_seeded_kept": meta["n_seeded_kept"],
        "n_complete_aggregated": meta["n_complete"],
        "n_incomplete_excluded": meta["n_incomplete"],
        "scenes": meta["scenes"],
        "seeds": meta["seeds"],
        "exclusions_applied": meta["exclusion_reasons"],
        "alignment_arms": meta.get("alignment_arms"),
        "tables": manifest_tables,
        # Anything the current data cannot support is named here rather than left for
        # a reader to infer from an absent row.
        "not_yet_run": [
            {"item": "small/easy scene (room_0, office_0)",
             "status": "config pinned via datasets.replica.must_include; NOT rendered or run",
             "command": "make split && make render && make export && make run-all"},
            {"item": "VGGT-SLAM loop-closure-ON arm",
             "status": "arm defined (vggtslam_loop, VGGTSLAM_MAX_LOOPS=1); NOT run",
             "command": "make run-vggtslam-arms"},
            {"item": "seeds 9012 / 3456",
             "status": "config extended to 4 seeds; only 1234/5678 have data",
             "command": "make render && make export && make run-all"},
            {"item": "latency for the 2026-07 archive",
             "status": "instrumentation fixed for future runs; the 43 archived "
                       "zero-latency runs cannot be retro-filled and stay excluded",
             "command": "n/a — requires re-running the matrix"},
        ],
        "standing_caveats": [
            "Rendered frames are noise-free -> optimistic upper bound vs real captures.",
            "Metric scale degrades on loops (Sim(3) ~20%, SL(4) ~31%).",
            "Shipped PRISM has no loop closure.",
        ],
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.publish_dir:
        pub = REPO_ROOT / args.publish_dir
        pub.mkdir(parents=True, exist_ok=True)
        for f in sorted(out.iterdir()):
            if f.is_file():
                shutil.copy2(f, pub / f.name)
        print(f"[export_report_tables] mirrored into tracked path -> {pub}")

    ok = sum(1 for v in manifest_tables.values() if v["status"] == "ok")
    print(f"[export_report_tables] {ok}/{len(TABLES)} tables -> {out}")
    for name, v in manifest_tables.items():
        if v["status"] != "ok":
            print(f"[export_report_tables]   absent: {name} ({v['reason']})")
    print(f"[export_report_tables] manifest -> {out / 'MANIFEST.json'}")


if __name__ == "__main__":
    main()
