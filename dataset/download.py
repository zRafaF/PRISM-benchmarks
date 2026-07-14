"""Dataset download dispatcher.

Each dataset needs a signed Terms-of-Use and its own official downloader — we
NEVER wget raw data. This wrapper documents the ToU step and stops with clear
instructions rather than silently failing. Nothing here commits data (dataset/raw
is gitignored).

Supported (config.datasets.active drives which run):
  replica       -> Replica-Dataset download.sh (NO approval)             [START HERE, today]
  scannetpp     -> ScanNet++ official toolkit (ToU + token)              [slower]
  kitti360      -> KITTI-360 download scripts (ToU; heavy 2D images)     [stretch]
  matterport3d  -> Matterport3D download_mp.py (ToU; slow approval)      [panorama-native]
  stanford2d3d  -> 2D-3D-S request form (ToU; slow approval)             [panorama-native]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config

TOU = {
    "replica": (
        "Replica: NO approval needed. Fastest path to render today.\n"
        "    apt-get install -y wget pigz unzip        # download.sh needs these\n"
        "    git clone https://github.com/facebookresearch/Replica-Dataset\n"
        "    cd Replica-Dataset && ./download.sh \"$(pwd)/../dataset/raw/replica\" && cd ..\n"
        "  Each scene dir must contain mesh.ply (+ textures) at\n"
        "  dataset/raw/replica/<scene>/mesh.ply. Then: make split && make render."),
    "scannetpp": (
        "ScanNet++: sign the ToU at https://kaldir.vc.in.tum.de/scannetpp/ and use the\n"
        "  official `scannetpp` toolkit (Python) with your access token to fetch the\n"
        "  per-scene `scans/mesh_aligned_0.05.ply`.\n"
        "  Place scenes under dataset/raw/scannetpp/<scene_id>/scans/."),
    "kitti360": (
        "KITTI-360: register at https://www.cvlibs.net/datasets/kitti-360/ , accept the\n"
        "  ToU, and use their download scripts. We need the 2 fisheye cams (-> equirect\n"
        "  for ours), a perspective cam (pinhole baselines), and the laser/GPS GT.\n"
        "  Heavy: the 2D image sets are ~100GB+ and fisheye->equirect stitching is extra."),
    "matterport3d": (
        "Matterport3D: sign the ToU and email for `download_mp.py`\n"
        "  (https://niessner.github.io/Matterport/). Equirectangular RGB-D + GT geometry."),
    "stanford2d3d": (
        "Stanford 2D-3D-S: fill the request form at\n"
        "  http://buildingparser.stanford.edu/dataset.html . Equirectangular RGB-D + GT."),
}


def main():
    ap = argparse.ArgumentParser(description="Download active datasets (ToU-gated)")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)

    for dataset in cfg["datasets"]["active"]:
        root = REPO_ROOT / cfg["datasets"][dataset]["root"]
        root.mkdir(parents=True, exist_ok=True)
        has_data = any(root.iterdir()) if root.exists() else False
        state = "data present" if has_data else "EMPTY"
        print(f"\n=== {dataset}  ({state}) -> {root}")
        if has_data:
            print("  [ok] data found; skipping. (delete to re-fetch)")
            continue
        print("  [MANUAL STEP]")
        print("  " + TOU[dataset].replace("\n", "\n  "))
        print(f"  Then: python dataset/make_split.py --dataset {dataset}  &&  make render")


if __name__ == "__main__":
    main()
