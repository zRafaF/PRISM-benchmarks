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
    args = ap.parse_args()

    cfg = load_config(args.config)
    dataset = args.dataset or cfg["datasets"]["active"][0]
    n = args.n if args.n is not None else cfg["datasets"][dataset].get("n_scenes_start", 1)

    found = discover_scenes(cfg, dataset)
    if not found:
        print(f"[make_split] no scenes found for {dataset} — run 'make download' first.")
        return
    import random
    random.seed(cfg["datasets"]["seed"])
    chosen = sorted(random.sample(found, min(n, len(found))))

    cfg_path = REPO_ROOT / args.config
    raw = yaml.safe_load(cfg_path.read_text())
    raw["datasets"][dataset]["scenes"] = chosen
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False))
    print(f"[make_split] {dataset}: froze {len(chosen)} scene(s): {chosen}")


if __name__ == "__main__":
    main()
