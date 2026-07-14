"""Emit per-method input sequences in the adapter format.

The renderer already writes frames into dataset/exports/.../{pano,pinhole}/. This
step assembles the per-method `meta.json` (camera model, per-frame camera height,
fps, seed, config echo) that each adapter reads, so an adapter never has to know
which dataset produced the frames — only the fixed export layout (adapter contract,
docs/adapter_contract.md).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import common_args, export_dir, load_config, resolve_scenes, resolve_trajs


def _camera_models(cfg: dict) -> list[tuple[str, str]]:
    """(camera_model, variant) pairs present in the exports."""
    out = [("pano", "")]
    for vname in cfg["camera"]["pinhole"]["variants"]:
        out.append(("pinhole", vname))
    return out


def main():
    ap = common_args("Emit per-method adapter meta.json")
    args = ap.parse_args()
    cfg = load_config(args.config)

    for dataset in cfg["datasets"]["active"]:
        for scene in resolve_scenes(cfg, dataset, args.scenes):
            for traj in resolve_trajs(cfg, args.traj):
                # true camera height measured at render time (down-ray to floor);
                # falls back to the config value if the sidecar is absent.
                traj_root = export_dir(dataset, scene, traj, "pano", "").parent
                mh = traj_root / "measured_camera_height.json"
                cam_h = cfg["camera"]["camera_height_m"]
                if mh.exists():
                    cam_h = json.loads(mh.read_text()).get("camera_height_m", cam_h)
                for camera_model, variant in _camera_models(cfg):
                    d = export_dir(dataset, scene, traj, camera_model, variant)
                    if not (d / "rgb").exists():
                        continue
                    n = len(list((d / "rgb").glob("*.png")))
                    meta = {
                        "dataset": dataset, "scene": scene, "traj": traj,
                        "camera_model": camera_model, "variant": variant,
                        "n_frames": n,
                        "camera_height_m": cam_h,
                        "fps_nominal": 2.0,
                        "seed": cfg["datasets"]["seed"],
                        "engine_echo": cfg["engine"],
                        "streaming": cfg["streaming"],
                    }
                    (d / "meta.json").write_text(json.dumps(meta, indent=2))
                    print(f"[export] {dataset}/{scene}/{traj}/{camera_model}"
                          f"{('/' + variant) if variant else ''}: {n} frames")


if __name__ == "__main__":
    main()
