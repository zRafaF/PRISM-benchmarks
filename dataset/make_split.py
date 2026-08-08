"""Freeze the scene list for a dataset (fixed seed, small start).

Writes the chosen scene ids back into config.yaml under datasets.<name>.scenes so
every downstream step is reproducible. Start tiny: one ScanNet++ room.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config


def discover_scenes(cfg: dict, dataset: str) -> list[str]:
    dcfg = cfg["datasets"][dataset]
    root = REPO_ROOT / dcfg["root"]
    if not root.exists():
        return []
    if dcfg["kind"] == "mesh_render":
        # Scene id = the first path component under root (works for both
        # Replica '<scene>/mesh.ply' and ScanNet++ '<scene>/scans/*.ply').
        glob = dcfg.get("mesh_glob", "*/mesh.ply")
        return sorted({p.relative_to(root).parts[0] for p in root.glob(glob)})
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def main():
    ap = argparse.ArgumentParser(description="Freeze the scene split into config.yaml")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dataset", default=None, help="default: first in datasets.active")
    ap.add_argument("--n", type=int, default=None, help="override n_scenes_start")
    ap.add_argument("--must-include", default=None,
                    help="comma-separated scene ids always pinned into the split "
                         "(overrides datasets.<name>.must_include)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    dataset = args.dataset or cfg["datasets"]["active"][0]
    n = args.n if args.n is not None else cfg["datasets"][dataset].get("n_scenes_start", 1)

    found = discover_scenes(cfg, dataset)
    if not found:
        print(f"[make_split] no scenes found for {dataset} — run 'make download' first.")
        return
    # `must_include` scenes are pinned into every split before the random draw.
    # Rationale: the 2026-07 big run drew its scenes uniformly and happened to land on
    # four large multi-room apartments plus a hotel, with NO small/easy room in the
    # seeded set. Every absolute number from that matrix is therefore pessimistic and
    # not comparable to small-room results in the literature. Pinning at least one
    # small room makes the difficulty spread a property of the config, not of the RNG.
    dcfg = cfg["datasets"][dataset]
    must = [s.strip() for s in (args.must_include.split(",") if args.must_include
                                else dcfg.get("must_include", []) or []) if s and s.strip()]
    missing = [s for s in must if s not in found]
    if missing:
        print(f"[make_split] WARNING: must_include scene(s) absent from {dataset}: "
              f"{missing} — skipped. Available: {found}")
    pinned = [s for s in must if s in found]

    import random
    random.seed(cfg["datasets"]["seed"])
    pool = [s for s in found if s not in pinned]
    n_extra = max(0, min(n, len(found)) - len(pinned))
    chosen = sorted(pinned + random.sample(pool, min(n_extra, len(pool))))
    if pinned:
        print(f"[make_split] pinned via must_include: {pinned}")

    # Write the frozen scene list to the gitignored overlay (config.local.yaml), NOT
    # the tracked config.yaml — so `git pull` never clobbers it or conflicts.
    #
    # If a temporary run profile is active (PRISM_CONFIG_OVERLAY, e.g. the smoke test's
    # config.smoke.yaml), freeze into THAT file instead. Otherwise `make split` during a
    # smoke run would overwrite the real frozen scene list in config.local.yaml — an
    # expensive thing to lose, and a surprising side effect of running a test.
    import os
    from bench.config import LOCAL_CONFIG
    target = LOCAL_CONFIG
    active = os.environ.get("PRISM_CONFIG_OVERLAY", "").strip()
    if active:
        target = Path(active)
        if not target.is_absolute():
            target = REPO_ROOT / target
        print(f"[make_split] PRISM_CONFIG_OVERLAY active -> freezing into {target.name} "
              f"(config.local.yaml left untouched)")
    overlay = {}
    if target.exists():
        overlay = yaml.safe_load(target.read_text()) or {}
    overlay.setdefault("datasets", {}).setdefault(dataset, {})["scenes"] = chosen
    target.write_text(yaml.safe_dump(overlay, sort_keys=False))
    print(f"[make_split] {dataset}: froze {len(chosen)} scene(s): {chosen}")
    print(f"[make_split] -> {target.name} (gitignored; survives git pull)")


if __name__ == "__main__":
    main()
