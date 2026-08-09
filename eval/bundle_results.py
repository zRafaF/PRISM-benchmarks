"""Package the benchmark outputs into one downloadable .zip.

WHY THIS IS NOT JUST `zip -r results/`
--------------------------------------
`results/` is dominated by per-run point clouds. At the 2026-07 run's sizes
(6-103 MB per cloud) a full matrix of ~1500 runs is tens of gigabytes — far past
what a browser download, or a Gradio temp dir, will tolerate. So content is split
into named categories and the heavy one is OFF by default:

    reports    aggregated tables + markdown (report_clean, report_tables, report)  tiny
    metrics    per-run ate/recon/metric/perf JSON — the numbers behind every table  small
    snapshots  standardized PNGs incl. all co-visibility mask variants             medium
    figures    report figures (VRAM plot, cubemap, fusion)                         small
    logs       run logs, overnight progress, smoke logs                            small
    config     config.yaml + bench.env + the changelog, for provenance             tiny
    poses      per-run poses.tum trajectories                                      small
    clouds     per-run cloud.ply reconstructions                     ** VERY LARGE **

Always `--estimate` before building a bundle you intend to download.

Usage
    make bundle                          # everything except clouds
    make bundle BUNDLE_INCLUDE=all       # including point clouds (huge)
    uv run python eval/bundle_results.py --estimate
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT

# category -> (list of (root, glob), one-line description, default-on)
CATEGORIES: dict[str, tuple[list[tuple[str, str]], str, bool]] = {
    "reports": ([("results/report_clean", "**/*"),
                 ("results/report_tables", "**/*"),
                 ("results/report", "*.md"),
                 ("results/report", "*.csv"),
                 ("documentation/docs/data/clean_latest", "**/*")],
                "aggregated tables (clean + raw) in csv/json/markdown", True),
    "metrics": ([("results", "*/*/*/*/*/ate.json"),
                 ("results", "*/*/*/*/*/recon.json"),
                 ("results", "*/*/*/*/*/metric.json"),
                 ("results", "*/*/*/*/*/perf.json"),
                 ("results", "*/*/*/*/*/arm_config.json")],
                "per-run metric JSON — the numbers behind every table", True),
    "poses": ([("results", "*/*/*/*/*/poses.tum")],
              "per-run estimated trajectories (TUM format)", True),
    "snapshots": ([("results/report/snapshots", "*.png")],
                  "standardized cloud images (full / covis / masked variants)", True),
    "figures": ([("results/figures", "**/*")],
                "report figures (VRAM scaling, cubemap, fusion)", True),
    "logs": ([("logs", "*.log"), ("logs", "*.progress"),
              ("results", "*/*/*/*/*/run.log")],
             "orchestrator + per-run logs (why a run failed lives here)", True),
    "config": ([(".", "config.yaml"), (".", "config.smoke.yaml"), (".", "bench.env"),
                (".", "RESULTS_CHANGELOG.md")],
               "config + changelog, so the bundle is self-describing", True),
    "clouds": ([("results", "*/*/*/*/*/cloud.ply")],
               "per-run reconstructed point clouds — VERY LARGE", False),
}
DEFAULT_ON = [k for k, (_, _, on) in CATEGORIES.items() if on]
BUNDLE_DIR = REPO_ROOT / "results" / "bundles"


def collect(categories: list[str]) -> dict[str, list[Path]]:
    """Resolve each category to a de-duplicated list of existing files."""
    out: dict[str, list[Path]] = {}
    seen: set[Path] = set()
    for cat in categories:
        spec = CATEGORIES.get(cat)
        if not spec:
            continue
        files: list[Path] = []
        for root, pattern in spec[0]:
            base = REPO_ROOT / root
            if not base.exists():
                continue
            for p in base.glob(pattern):
                # Never let a previously-built bundle end up inside a new one.
                if BUNDLE_DIR in p.parents:
                    continue
                if p.is_file() and p not in seen:
                    seen.add(p)
                    files.append(p)
        out[cat] = sorted(files)
    return out


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def estimate(categories: list[str]):
    """Size EVERY category, not just the selected ones.

    The whole point of the estimate is deciding whether to include the clouds, so
    scanning only the selected categories would report the excluded ones as "0 files"
    and hide the number the decision turns on.
    """
    found = collect(list(CATEGORIES))
    rows, total, count = [], 0, 0
    for cat in CATEGORIES:
        files = found.get(cat, [])
        size = sum(f.stat().st_size for f in files if f.exists())
        if cat in categories:
            total += size
            count += len(files)
        rows.append((cat, len(files), size, cat in categories))
    return rows, total, count


def build(categories: list[str], out_path: Path, compress=True, progress=None) -> Path:
    found = collect(categories)
    all_files = [f for cat in categories for f in found.get(cat, [])]
    total = len(all_files)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    manifest = [
        "PRISM-benchmarks results bundle",
        f"created         : {stamp}",
        f"repo            : {REPO_ROOT}",
        f"categories      : {', '.join(categories)}",
        f"excluded        : {', '.join(c for c in CATEGORIES if c not in categories) or 'none'}",
        f"files           : {total}",
        "",
        "WHAT TO READ FIRST",
        "  results/report_clean/clean_report.md    the citable, seeded-only analysis",
        "  results/report_clean/completion.csv     per-method completion — read BEFORE any mean",
        "  results/report_tables/                  frozen tables for uofa-2026-report",
        "  RESULTS_CHANGELOG.md                    what changed vs the 2026-07 run and why",
        "",
        "NOTE: results/report/report.md aggregates EVERY run in results/ (seeded or not,",
        "complete or crashed). The citable numbers are the report_clean/ ones.",
        "",
    ]
    if "clouds" not in categories:
        manifest.append("Point clouds (cloud.ply) were EXCLUDED to keep the archive "
                        "downloadable. Re-run with the 'clouds' category to include them.")

    # Deflate is worth it for JSON/TUM/logs; near-useless for PNG and PLY, where it
    # mostly burns CPU. Store those instead so a big bundle doesn't take an hour.
    STORED_EXT = {".png", ".jpg", ".jpeg", ".ply", ".zip", ".gz"}
    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(out_path, "w", compression=mode, allowZip64=True) as z:
        z.writestr("MANIFEST.txt", "\n".join(manifest))
        z.writestr("bundle_contents.json", json.dumps(
            {cat: [str(f.relative_to(REPO_ROOT)) for f in found.get(cat, [])]
             for cat in categories}, indent=2))
        for i, f in enumerate(all_files, 1):
            try:
                arc = f.relative_to(REPO_ROOT)
            except ValueError:
                arc = Path(f.name)
            comp = zipfile.ZIP_STORED if f.suffix.lower() in STORED_EXT else mode
            try:
                z.write(f, arcname=str(arc), compress_type=comp)
            except (OSError, ValueError) as e:
                # A file vanishing mid-bundle (an active run rotating a log) must not
                # destroy an otherwise good archive.
                z.writestr(f"SKIPPED_{arc.name}.txt", f"could not add {arc}: {e}")
            if progress and (i % 200 == 0 or i == total):
                progress(i, total)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--include", default=",".join(DEFAULT_ON),
                    help="comma list of categories, or 'all' / 'default'")
    ap.add_argument("--out", default="", help="output .zip path (default: auto-named)")
    ap.add_argument("--estimate", action="store_true",
                    help="report what WOULD be bundled and how big, without writing")
    ap.add_argument("--no-compress", action="store_true")
    args = ap.parse_args()

    inc = args.include.strip().lower()
    if inc == "all":
        cats = list(CATEGORIES)
    elif inc in ("default", ""):
        cats = list(DEFAULT_ON)
    else:
        cats = [c.strip() for c in args.include.split(",") if c.strip() in CATEGORIES]
    if not cats:
        raise SystemExit(f"[bundle] no valid categories in {args.include!r}. "
                         f"Choose from: {', '.join(CATEGORIES)}")

    rows, total, count = estimate(cats)
    print(f"{'category':<11} {'files':>7} {'size':>11}   included  description")
    print("-" * 92)
    for cat, n, size, included in rows:
        print(f"{cat:<11} {n:>7} {human(size):>11}   "
              f"{'yes' if included else 'no ':<8}  {CATEGORIES[cat][1]}")
    print("-" * 92)
    print(f"{'TOTAL':<11} {count:>7} {human(total):>11}   (uncompressed, before zipping)")

    if args.estimate:
        if total > 2 * 1024 ** 3:
            print("\n!! Over 2 GB — that is awkward to download through a browser.")
            print("   Drop the 'clouds' category, or copy it off the box with rsync/scp.")
        return

    if total == 0:
        raise SystemExit("\n[bundle] nothing to bundle — has the benchmark run yet?")

    out = Path(args.out) if args.out else (
        REPO_ROOT / "results" / "bundles" /
        f"prism-benchmarks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    if not out.is_absolute():
        out = REPO_ROOT / out

    print(f"\n[bundle] writing {out} ...")
    build(cats, out, compress=not args.no_compress,
          progress=lambda i, n: print(f"[bundle]   {i}/{n} files", flush=True))
    size = out.stat().st_size
    print(f"[bundle] done: {out}")
    print(f"[bundle] {count} files, {human(size)} zipped "
          f"({100 * size / total:.0f}% of {human(total)})")


if __name__ == "__main__":
    main()
