"""Ingest an archived big-run snapshot into canonical tidy per-run records.

WHY THIS EXISTS
---------------
The 2026-07 big run's raw `results/` tree no longer exists on disk; the only
surviving record is the committed snapshot

    documentation/docs/data/<run_id>/perf.csv        (per-run performance)
    documentation/docs/data/<run_id>/report_raw.md   (per-run tables A/B/C/C2/D/traj)

which together carry every per-run number the report was built from. This script
converts that snapshot into the SAME tidy schema `eval/aggregate_clean.py` reads
from a live `results/` tree, so the clean re-aggregation is reproducible today
without re-running any method.

It is a *transcription* step only: every value is copied verbatim from the
snapshot. Nothing is interpolated, imputed, or recomputed. Values absent from
the snapshot stay absent (None), and units are converted only where the snapshot
states them explicitly in the column header (e.g. "cm" -> metres).

Usage
-----
    make ingest-archive                       # default run id from config
    uv run python eval/ingest_archive.py --run-id bigrun_2026-07

Writes `documentation/docs/data/<run_id>/runs_tidy.{csv,json}`.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT

# Canonical tidy schema. Mirrors what `aggregate_clean.load_live_runs()` produces
# from results/<...>/{perf,ate,recon,metric}.json so both sources are interchangeable.
TIDY_COLUMNS = [
    "method", "dataset", "scene", "traj", "variant",
    # --- perf (from perf.csv) ---
    "n_frames", "eff_fps", "latency_end_to_end_s", "latency_source",
    "per_window_latency_med_s", "per_window_source",
    "vram_avg_gb", "vram_peak_gb", "gpu_util_avg_pct", "gpu_power_avg_w",
    "cpu_ram_peak_gb", "ckpt_size_mb", "gpu_name", "hw_id",
    # --- trajectory ---
    "ate_rmse_m", "rpe_per_m",
    # --- metric scale (Table B) ---
    "metric_capable", "scale_estimate", "metric_scale_error_pct", "extent_error_pct",
    # --- recon masked (Table C) ---
    "masked_accuracy_m", "masked_completeness_m", "masked_chamfer_m", "masked_fscore",
    # --- recon full-360 (Table C2) ---
    "full360_accuracy_m", "full360_completeness_m", "full360_chamfer_m", "full360_fscore",
    # --- cleanliness / size (Table D) ---
    "point_count", "map_size_mb", "sor_outlier_pct", "acc_p95_m", "noise_frac",
    "precision_tight",
    # --- provenance ---
    "source",
]

_NA = {"—", "-", "", "n/a", "N/A", "N/A (scale-free)", "nan", "None"}


def _num(s):
    """Parse a table cell to float, or None for the snapshot's explicit N/A markers."""
    if s is None:
        return None
    s = str(s).strip()
    if s in _NA:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _cm(s):
    """Snapshot columns labelled 'cm' -> metres (the canonical unit in results/*.json)."""
    v = _num(s)
    return None if v is None else v / 100.0


def _pct_to_frac(s):
    """Snapshot columns labelled '%' that live as fractions in recon.json."""
    v = _num(s)
    return None if v is None else v / 100.0


def _split_run(run: str):
    """'scene/traj/variant' or 'scene/traj' -> (scene, traj, variant|None)."""
    parts = run.strip().split("/")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], None
    raise ValueError(f"unparseable run key: {run!r}")


def _parse_md_tables(md_path: Path) -> dict[str, list[list[str]]]:
    """Split report_raw.md into {section_heading: [row_cells, ...]}.

    Only the *per-run* tables are extracted (those whose second column is a
    'scene/traj[/variant]' run key). The snapshot's own summary tables at the top
    are deliberately ignored — they are the contaminated ones.
    """
    text = md_path.read_text(encoding="utf-8")
    sections: dict[str, list[list[str]]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## ") or line.startswith("# "):
            current = line.lstrip("#").strip()
            sections.setdefault(current, [])
            continue
        if current is None or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or all(set(c) <= {"-", ":"} for c in cells):
            continue  # separator row
        sections[current].append(cells)
    return sections


def _find_section(sections: dict, *needles: str):
    """Locate a section by substring match on its heading (headings carry markup)."""
    for head, rows in sections.items():
        low = head.lower()
        if all(n.lower() in low for n in needles):
            return rows
    return []


def _index_rows(rows: list[list[str]], with_variant: bool):
    """{(method, scene, traj, variant): cells} for a per-run table, skipping its header."""
    out = {}
    for cells in rows:
        if len(cells) < 3:
            continue
        method, run = cells[0], cells[1]
        if method.lower() == "method" or "/" not in run:
            continue  # header row
        try:
            scene, traj, variant = _split_run(run)
        except ValueError:
            continue
        key = (method, scene, traj, variant if with_variant else None)
        out[key] = cells
    return out


def ingest(run_id: str, dataset_default: str = "replica") -> list[dict]:
    data_dir = REPO_ROOT / "documentation" / "docs" / "data" / run_id
    perf_csv = data_dir / "perf.csv"
    raw_md = data_dir / "report_raw.md"
    if not perf_csv.exists() or not raw_md.exists():
        raise SystemExit(f"[ingest_archive] missing snapshot files under {data_dir}")

    sections = _parse_md_tables(raw_md)
    t_perf = _index_rows(_find_section(sections, "Table A"), with_variant=True)
    t_metric = _index_rows(_find_section(sections, "Table B"), with_variant=False)
    t_masked = _index_rows(_find_section(sections, "Table C —"), with_variant=True)
    t_full = _index_rows(_find_section(sections, "Table C2"), with_variant=True)
    t_clean = _index_rows(_find_section(sections, "Table D"), with_variant=True)
    t_traj = _index_rows(_find_section(sections, "Trajectory (ATE"), with_variant=True)

    runs = []
    with open(perf_csv, newline="", encoding="utf-8") as f:
        for p in csv.DictReader(f):
            method, scene = p["method"], p["scene"]
            traj, variant = p["traj"], p["variant"]
            kv = (method, scene, traj, variant)      # variant-qualified tables
            kn = (method, scene, traj, None)         # Table B (no variant in its key)

            rec = {c: None for c in TIDY_COLUMNS}
            rec.update({
                "method": method, "dataset": p.get("dataset") or dataset_default,
                "scene": scene, "traj": traj, "variant": variant,
                "n_frames": _num(p.get("n_frames")),
                "eff_fps": _num(p.get("eff_fps")),
                "latency_end_to_end_s": _num(p.get("latency_end_to_end_s")),
                "per_window_latency_med_s": _num(p.get("per_window_latency_med_s")),
                # The archive predates the latency_source field, so provenance is
                # reconstructed from the value alone: a zero is the pre-fix logging
                # gap (adapters/base.py left the default when a runner wrote no
                # perf_runner.json), anything else was runner-reported but cannot be
                # re-attributed after the fact.
                "latency_source": ("unavailable"
                                   if not _num(p.get("latency_end_to_end_s"))
                                   else "archive_unspecified"),
                "per_window_source": ("unavailable"
                                      if _num(p.get("per_window_latency_med_s")) is None
                                      else "archive_unspecified"),
                "vram_avg_gb": _num(p.get("vram_avg_gb")),
                "vram_peak_gb": _num(p.get("vram_peak_gb")),
                "gpu_util_avg_pct": _num(p.get("gpu_util_avg_pct")),
                "gpu_power_avg_w": _num(p.get("gpu_power_avg_w")),
                "cpu_ram_peak_gb": _num(p.get("cpu_ram_peak_gb")),
                "ckpt_size_mb": _num(p.get("ckpt_size_mb")),
                "gpu_name": p.get("gpu_name") or None,
                "hw_id": p.get("hw_id") or None,
                "source": f"archive:{run_id}",
            })

            if kv in t_traj:                      # | Method | Run | ATE cm | Drift %/m |
                c = t_traj[kv]
                rec["ate_rmse_m"] = _cm(c[2])
                rec["rpe_per_m"] = _pct_to_frac(c[3]) if len(c) > 3 else None

            if kn in t_metric:                    # | Method | Run | Scale est | Scale err % | Extent err % |
                c = t_metric[kn]
                rec["metric_capable"] = "scale-free" not in c[2].lower()
                if rec["metric_capable"]:
                    rec["scale_estimate"] = _num(c[2])
                    rec["metric_scale_error_pct"] = _num(c[3]) if len(c) > 3 else None
                    rec["extent_error_pct"] = _num(c[4]) if len(c) > 4 else None

            for key, pre, tbl in (("masked", "masked_", t_masked),
                                  ("full_360", "full360_", t_full)):
                if kv in tbl:                     # | M | Run | Acc cm | Compl cm | Chamfer cm | F |
                    c = tbl[kv]
                    rec[pre + "accuracy_m"] = _cm(c[2])
                    rec[pre + "completeness_m"] = _cm(c[3]) if len(c) > 3 else None
                    rec[pre + "chamfer_m"] = _cm(c[4]) if len(c) > 4 else None
                    rec[pre + "fscore"] = _num(c[5]) if len(c) > 5 else None

            if kv in t_clean:                     # | M | Run | Points | MB | Outlier% | p95 cm | Noise% | Prec@2cm% |
                c = t_clean[kv]
                rec["point_count"] = _num(c[2])
                rec["map_size_mb"] = _num(c[3]) if len(c) > 3 else None
                rec["sor_outlier_pct"] = _pct_to_frac(c[4]) if len(c) > 4 else None
                rec["acc_p95_m"] = _cm(c[5]) if len(c) > 5 else None
                rec["noise_frac"] = _pct_to_frac(c[6]) if len(c) > 6 else None
                rec["precision_tight"] = _pct_to_frac(c[7]) if len(c) > 7 else None

            runs.append(rec)
    return runs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-id", default="bigrun_2026-07",
                    help="snapshot dir under documentation/docs/data/")
    args = ap.parse_args()

    runs = ingest(args.run_id)
    out_dir = REPO_ROOT / "documentation" / "docs" / "data" / args.run_id
    with open(out_dir / "runs_tidy.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=TIDY_COLUMNS)
        w.writeheader()
        w.writerows(runs)
    (out_dir / "runs_tidy.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")

    seeded = [r for r in runs if re.search(r"_s\d+$", r["traj"])]
    print(f"[ingest_archive] {len(runs)} run-records "
          f"({len(seeded)} seeded, {len(runs) - len(seeded)} unseeded/stale) "
          f"-> {out_dir / 'runs_tidy.csv'}")
    missing = [k for k in ("ate_rmse_m", "masked_fscore", "vram_peak_gb")
               if sum(1 for r in seeded if r[k] is not None) == 0]
    if missing:
        print(f"[ingest_archive] WARNING: no seeded values parsed for {missing}")


if __name__ == "__main__":
    main()
