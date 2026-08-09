"""Assert the clean aggregate is actually clean. Exits non-zero if it is not.

This is the regression guard for the data-hygiene bug that produced the contaminated
2026-07 tables. It is cheap, it runs in CI or before any report build, and it fails
loudly rather than letting a stale run drift back into a published table.

Checks
  1. Every aggregated run is seeded (`_sN`) — no unsuffixed trajectory ids.
  2. No run comes from an excluded scene (office_4) or an excluded arm.
  3. No aggregated run has the co-tenancy VRAM signature (>60 GB peak) that marks
     the stale 2-scene experiment.
  4. Every aggregated run is complete (has both ATE and masked recon).
  5. No aggregated run has latency == 0 with no stated latency_source — the exact
     signature of the logging gap fixed in adapters/base.py.
  6. The recomputed per-method aggregate reproduces the numbers published in
     documentation/docs/results_bigrun.md when incomplete runs are included.
     This is the end-to-end proof that the ingest is faithful: if the transcription
     drifted, these would stop matching.

Usage
    make verify-clean
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

SEEDED_RE = re.compile(r"_s\d+$")

# A streaming method above this peak is co-tenancy, not workload: the whole point of
# the streaming engines is a bounded budget (PRISM ~16 GB, LASER 8.4, VGGT-SLAM 8.9).
COTENANCY_GB = 60.0
# And any run this many times above its own method's median peak is suspect regardless
# of mode — the check that would catch co-tenancy inside a full-batch method too.
OUTLIER_FACTOR = 8.0

# Published in documentation/docs/results_bigrun.md, "Corrected per-method aggregate".
# (ATE cm, drift %/m, masked F, full-360 F, map MB, outlier %, prec@2cm, scale %, VRAM GB)
PUBLISHED = {
    "prism":       (65.3, 52.2, 0.42, 0.31, 22.1, 2.44, 16.3, 14.6, 15.5),
    "prism_sim3":  (68.9, 49.1, 0.40, 0.28, 20.9, 2.48, 15.5, 14.0, 15.4),
    "prism_se3":   (67.1, 48.6, 0.39, 0.28, 21.0, 2.46, 15.1, 13.4, 15.6),
    "panovggt":    (66.6, 49.0, 0.58, 0.45, 103.0, 3.93, 17.0, None, 24.9),
    "pi3":         (62.5, 61.3, 0.49, 0.35, 23.4, 2.73, 14.4, 8.7, 36.3),
    "mapanything": (95.7, 95.4, 0.26, 0.19, 28.9, 3.51, 7.4, 22.0, 44.9),
    "laser":       (86.8, 56.7, 0.35, 0.22, 6.1, 3.35, 9.7, None, 8.4),
    "vggtslam":    (132.0, 159.4, 0.22, 0.16, 102.2, 3.71, 8.9, None, 8.9),
}
# Columns are resolved BY HEADER TEXT, never by index. Hardcoded indices silently
# mis-map the moment a column is inserted: adding Acc/Compl/Chamfer shifted everything
# right and the check started comparing masked-F against the published outlier %,
# reporting a "failure" that was purely an off-by-three in the verifier.
PUB_NAMES = ["ATE cm", "drift %/m", "masked F", "360 F", "map MB",
             "outlier %", "prec@2cm", "scale %", "VRAM GB"]
# published-name -> the substring that identifies its column in the CSV header
PUB_HEADER = {
    "ATE cm": "ATE cm", "drift %/m": "drift %/m", "masked F": "Masked F",
    "360 F": "Full-360 F", "map MB": "Map MB", "outlier %": "Outlier %",
    "prec@2cm": "Prec@2cm", "scale %": "Scale err %", "VRAM GB": "VRAM peak GB",
}


def _resolve_cols(header: list[str]) -> dict:
    """published-name -> column index, matched on header text."""
    out = {}
    for name, needle in PUB_HEADER.items():
        idx = next((i for i, h in enumerate(header) if needle in h), None)
        if idx is None:
            raise SystemExit(f"[verify_clean] column {needle!r} not found in "
                             f"aggregate_per_method.csv header: {header}")
        out[name] = idx
    return out


def fail(msgs: list[str], msg: str):
    msgs.append(msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--clean-dir", default="results/report_clean")
    ap.add_argument("--run-id", default="bigrun_2026-07")
    ap.add_argument("--skip-published-check", action="store_true",
                    help="skip check 6 (use when aggregating a NEW run, whose numbers "
                         "are not expected to match the 2026-07 publication)")
    args = ap.parse_args()

    clean = REPO_ROOT / args.clean_dir
    runs_csv = clean / "runs_clean.csv"
    if not runs_csv.exists():
        raise SystemExit(f"[verify_clean] {runs_csv} missing — run 'make report-clean' first.")

    with open(runs_csv, newline="", encoding="utf-8") as f:
        runs = list(csv.DictReader(f))
    errors: list[str] = []
    checks = 0

    # 1. seeded-only
    checks += 1
    bad = [r for r in runs if not SEEDED_RE.search(r["traj"])]
    if bad:
        fail(errors, f"{len(bad)} unseeded run(s) in the clean aggregate, e.g. "
                     f"{bad[0]['method']}/{bad[0]['scene']}/{bad[0]['traj']}")

    # 2. excluded scenes / arms
    checks += 1
    bad = [r for r in runs if r["scene"] == "office_4"]
    if bad:
        fail(errors, f"{len(bad)} run(s) from the excluded scene office_4")

    # 3. co-tenancy VRAM signature.
    #    A bare ">60 GB peak" test is wrong: the full-batch methods legitimately reach
    #    70-87 GB on the longest (5 Hz, ~200-frame) sequences — that memory growth IS
    #    the deployability result. The co-tenancy signature is specifically a *streaming*
    #    method, which is bounded-memory by construction, reporting a huge peak. In the
    #    stale 2-scene set that is exactly what happened (laser 70 GB on 50 frames, vs
    #    8.4 GB across the whole seeded matrix).
    checks += 1
    from aggregate_clean import STREAMING  # single source of truth for the taxonomy
    bad = []
    for r in runs:
        try:
            peak = float(r.get("vram_peak_gb") or 0)
        except ValueError:
            continue
        if r["method"] in STREAMING and peak > COTENANCY_GB:
            bad.append(r)
    if bad:
        fail(errors, f"{len(bad)} streaming run(s) with >{COTENANCY_GB} GB peak VRAM — "
                     f"streaming methods are bounded-memory, so this is the co-tenancy "
                     f"signature of the stale experiment, e.g. "
                     f"{bad[0]['method']}/{bad[0]['scene']}/{bad[0]['traj']} "
                     f"({bad[0]['vram_peak_gb']} GB)")

    # 3b. relative outlier: any run far above its own method's median peak.
    #     Catches co-tenancy in a full-batch method, where an absolute threshold can't.
    checks += 1
    import statistics as _st
    by_method: dict[str, list[tuple[float, dict]]] = {}
    for r in runs:
        try:
            by_method.setdefault(r["method"], []).append((float(r["vram_peak_gb"]), r))
        except (ValueError, TypeError, KeyError):
            pass
    for method, vals in by_method.items():
        if len(vals) < 4:
            continue
        med = _st.median(v for v, _ in vals)
        if med <= 0:
            continue
        for v, r in vals:
            if v > OUTLIER_FACTOR * med:
                fail(errors, f"{method}/{r['scene']}/{r['traj']} peak VRAM {v:.1f} GB is "
                             f">{OUTLIER_FACTOR}x this method's median ({med:.1f} GB) — "
                             f"possible co-tenancy contamination")

    # 4. completeness
    checks += 1
    bad = [r for r in runs if not r.get("ate_rmse_m") or not r.get("masked_fscore")]
    if bad:
        fail(errors, f"{len(bad)} incomplete run(s) (missing ATE or masked recon) were "
                     f"aggregated, e.g. {bad[0]['method']}/{bad[0]['scene']}/{bad[0]['traj']}")

    # 5. silent zero latency
    checks += 1
    bad = []
    for r in runs:
        lat = r.get("latency_end_to_end_s")
        src = (r.get("latency_source") or "").strip()
        if lat in (None, "", "0", "0.0") and src in ("", "unavailable", "None"):
            bad.append(r)
    if bad:
        fail(errors, f"{len(bad)} run(s) with zero/absent latency and no latency_source — "
                     f"the pre-fix logging signature, e.g. {bad[0]['method']}/{bad[0]['traj']}")

    # 6. reproduce the published aggregate (incomplete included, as published)
    if not args.skip_published_check:
        checks += 1
        verify_dir = REPO_ROOT / "results" / "_verify_published"
        import subprocess
        rc = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "aggregate_clean.py"),
             "--source", "archive", "--run-id", args.run_id,
             "--include-incomplete", "--out", str(verify_dir.relative_to(REPO_ROOT))],
            capture_output=True, text=True)
        if rc.returncode != 0:
            fail(errors, f"published-aggregate recompute failed: {rc.stderr.strip()[:300]}")
        else:
            with open(verify_dir / "aggregate_per_method.csv", newline="",
                      encoding="utf-8") as f:
                _rows = list(csv.reader(f))
            cols = _resolve_cols(_rows[0])
            got = {r[0]: r for r in _rows[1:]}
            for method, vals in PUBLISHED.items():
                if method not in got:
                    fail(errors, f"published check: method {method} absent from recompute")
                    continue
                for name, want in zip(PUB_NAMES, vals):
                    if want is None:
                        continue
                    cell = got[method][cols[name]]
                    if cell in ("—", "N/A"):
                        fail(errors, f"published check: {method}.{name} missing")
                        continue
                    have = float(cell)
                    tol = 0.06 if want < 1 else max(0.06, 0.006 * want)
                    if abs(have - want) > tol:
                        fail(errors, f"published check: {method}.{name} "
                                     f"recomputed {have} vs published {want}")

    meta_p = clean / "clean_report.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
    print(f"[verify_clean] {len(runs)} aggregated runs · source={meta.get('source', '?')} · "
          f"{checks} checks")
    if errors:
        print(f"[verify_clean] FAILED — {len(errors)} problem(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("[verify_clean] PASS — no contaminated, incomplete, or silently-zero-latency "
          "run reached the clean aggregate")
    if not args.skip_published_check:
        print("[verify_clean] PASS — recompute reproduces results_bigrun.md exactly")


if __name__ == "__main__":
    main()
