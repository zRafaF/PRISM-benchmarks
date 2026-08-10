#!/usr/bin/env python
"""Refuse to benchmark on top of results that belong to a DIFFERENT matrix.

Why this exists
---------------
`adapters/base.py` resumes: a run whose `poses.tum` already exists is skipped unless
`PRISM_FORCE=1`. That is exactly right for continuing an interrupted night, and exactly
wrong after the trajectories change — and nothing was checking which situation you were
in.

`dataset/render_scene.py` does NOT skip; it re-renders unconditionally. So when the
2026-08-10 run started, Stage 1 regenerated every export with the new path-invariant
trajectories (300 frames at 2 Hz, 748 at 5 Hz), and then Stage 2 SKIPPED every
(method, scene, trajectory) that the 2026-08-09 matrix had already produced — leaving
results computed on the old 4-to-207-frame sequences sitting next to the new exports and
being aggregated as if they belonged together. `completion.csv` showed `n_total = 62` for
a matrix whose real size is 54, and eval_recon was still scoring a room_1 5 Hz run at
"97 poses" when that trajectory is now 748 frames long. Of the 54 runs the report needs,
45 would have been stale and 9 fresh.

Two failure modes, both silent, both caught here:

* **STALE** — a result whose `perf.json.n_frames_input` disagrees with the frame count in
  the export it supposedly consumed. The trajectory was re-rendered underneath it.
* **ORPHAN** — a result for a (scene, trajectory) that is not in the current matrix at
  all, e.g. the 0.5 Hz runs left over after that rate was removed. Harmless to the runs
  themselves, fatal to the aggregate, which globs the whole tree.

Exits non-zero when either is present, so it can gate the overnight.

    python eval/check_results_fresh.py --config config.yaml
    python eval/check_results_fresh.py --config config.yaml --list   # every offender
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench.config import REPO_ROOT, load_config, resolve_scenes, resolve_trajs


def _load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:                                            # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--list", action="store_true", help="print every offending run")
    args = ap.parse_args()
    cfg = load_config(args.config)

    trajs = set(resolve_trajs(cfg, "all"))
    scenes = {s for d in cfg["datasets"]["active"] for s in resolve_scenes(cfg, d, "")}
    results = REPO_ROOT / "results"
    exports = REPO_ROOT / "dataset" / "exports"

    if not results.exists():
        print("[fresh] no results/ tree — nothing to check, matrix starts clean.")
        return 0

    # results/<method>/<dataset>/<scene>/<traj>/<variant>/perf.json
    runs = sorted(results.glob("*/*/*/*/*/perf.json"))
    if not runs:
        print("[fresh] results/ holds no runs — matrix starts clean.")
        return 0

    stale, orphan, ok, unknown = [], [], 0, 0
    stale_by_traj: Counter = Counter()
    orphan_by_traj: Counter = Counter()
    for perf_path in runs:
        variant_dir = perf_path.parent
        method, dataset, scene, traj, variant = (
            variant_dir.parts[-5], variant_dir.parts[-4], variant_dir.parts[-3],
            variant_dir.parts[-2], variant_dir.parts[-1])
        tag = f"{method}/{scene}/{traj}"

        if traj not in trajs or scene not in scenes:
            orphan.append(tag)
            orphan_by_traj[f"{scene}/{traj}"] += 1
            continue

        perf = _load(perf_path) or {}
        n_res = perf.get("n_frames_input") or perf.get("n_frames")
        # The export the run consumed. Camera model differs per method, so search both.
        n_exp = None
        for meta in (exports / dataset / scene / traj).rglob("meta.json"):
            m = _load(meta) or {}
            if m.get("n_frames"):
                n_exp = int(m["n_frames"])
                break
        if not n_res or not n_exp:
            unknown += 1
            continue
        if int(n_res) != n_exp:
            stale.append(f"{tag} (result {int(n_res)}f vs export {n_exp}f)")
            stale_by_traj[f"{scene}/{traj}"] += 1
        else:
            ok += 1

    print(f"[fresh] {len(runs)} existing run(s): {ok} consistent, {len(stale)} STALE, "
          f"{len(orphan)} ORPHAN, {unknown} unverifiable")

    if stale:
        print(f"\n[fresh] STALE — the trajectory was re-rendered after these ran, so they "
              f"were scored on a DIFFERENT sequence than the one now on disk:")
        for k, v in sorted(stale_by_traj.items(), key=lambda kv: -kv[1])[:15]:
            print(f"    {k}: {v} run(s)")
        if args.list:
            for t in stale:
                print(f"      {t}")
    if orphan:
        print(f"\n[fresh] ORPHAN — not in the current matrix, but the aggregate globs the "
              f"whole tree and would include them:")
        for k, v in sorted(orphan_by_traj.items(), key=lambda kv: -kv[1])[:15]:
            print(f"    {k}: {v} run(s)")
        if args.list:
            for t in orphan:
                print(f"      {t}")

    if stale or orphan:
        print(f"""
[fresh] DO NOT RUN THE MATRIX ON THIS TREE.
        adapters/base.py resumes by SKIPPING any run that already has a poses.tum, so
        the {len(stale)} stale run(s) would never be recomputed — they would be reported
        as if they came from the current trajectories. The {len(orphan)} orphan(s) would
        be averaged in by the aggregate regardless.

        Fix, pick one:
          make clean-results          # wipe results/ and run the matrix fresh (safest)
          FORCE=1 make bench-overnight  # re-run everything, but orphans REMAIN and must
                                        # still be deleted by hand
""")
        return 1
    print("[fresh] every existing run matches the current exports — safe to resume.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
