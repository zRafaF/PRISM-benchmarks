#!/usr/bin/env python
"""PRISM-VGGT runner — executed by submodules/PRISM-VGGT/.venv/bin/python.

Consumes the exported PANO sequence, drives the StreamingWindowEngine in the
STREAMING harness (windowed, incremental), and writes the common outputs:
poses.tum, cloud.ply, perf_runner.json. Uses the verified public API
(prism_vggt: PanoVGGTBackend, StreamingWindowEngine, FrameInput, download_weights).

We deliberately do NOT run a single full-batch pass — that would only benchmark
PanoVGGT, not the streaming engine (decision 2026-07-13).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent))
import runner_io as _io


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", dest="out_dir", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)

    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())
    eng = cfg["engine"]

    from prism_vggt import PanoVGGTBackend, StreamingWindowEngine, FrameInput, download_weights

    # Weights live in the PRISM submodule (placed by setup_prism.sh); the runner runs
    # from the repo root, so resolve an absolute path. URL is overridable via env.
    import os
    repo_root = Path(__file__).resolve().parents[2]
    default_ckpt = repo_root / "submodules" / "PRISM-VGGT" / "checkpoints" / "model.pt"
    ckpt = Path(os.environ.get("PANOVGGT_WEIGHTS_PATH", str(default_ckpt)))
    if not ckpt.exists():
        url = os.environ.get("PANOVGGT_WEIGHTS_URL")
        download_weights(str(ckpt), url=url) if url else download_weights(str(ckpt))
    # PanoVGGTBackend's default config_path is relative; pass it absolute so the
    # backend loads regardless of the process working directory.
    prism_dir = repo_root / "submodules" / "PRISM-VGGT"
    config_path = prism_dir / "third_party" / "PanoVGGT" / "training" / "config" / "default.yaml"
    perception = PanoVGGTBackend(config_path=str(config_path), weights_path=str(ckpt))
    # Voxel / max-depth overrides for the fidelity-vs-memory sweep. These are read
    # ONLY here, never from cfg["engine"], because panovggt_runner.py and pi3_runner.py
    # use cfg["engine"]["voxel_size"] for their OWN fusion dedup — sweeping the config
    # key would silently re-tune the baselines alongside PRISM and invalidate the
    # comparison. Env vars keep the sweep strictly PRISM-side.
    import os as _os
    _voxel = float(_os.environ.get("PRISM_VOXEL_SIZE", eng["voxel_size"]))
    _maxd = float(_os.environ.get("PRISM_MAX_DEPTH", eng["max_depth"]))
    if _voxel != eng["voxel_size"] or _maxd != eng["max_depth"]:
        print(f"[prism_runner] SWEEP override: voxel_size={_voxel} (cfg "
              f"{eng['voxel_size']}), max_depth={_maxd} (cfg {eng['max_depth']})")

    engine = StreamingWindowEngine(
        perception,
        voxel_size=_voxel,
        max_depth=_maxd,
        face_size=eng["face_size"],
    )
    engine.processing_mode = eng.get("processing_mode", "parallel")

    seq = _io.load_sequence(args.in_dir)
    ch = seq["meta"].get("camera_height_m", 1.7)
    frames = []
    for i, (img, msk) in enumerate(zip(seq["rgb"], seq["mask"])):
        mask = msk if msk is not None else np.ones(img.shape[:2], dtype=np.uint8) * 255
        frames.append(FrameInput(image=img.astype(np.uint8), mask=mask,
                                  camera_height=float(ch), timestamp=i))

    # Streaming: process the whole sequence in overlapping windows (the engine's
    # native mode). If the sequence is SHORTER than a window (e.g. 0.5 Hz on a small
    # room -> ~12 frames), clamp to a single batch window over all frames so a map is
    # still produced instead of nothing.
    n = len(frames)
    ws = min(int(eng["window_size"]), n)
    ov = min(int(eng["overlap"]), max(0, ws - 1))
    if ws < int(eng["window_size"]):
        print(f"[prism_runner] short sequence ({n} frames) -> single batch window={ws} overlap={ov}")
    per_window = []
    t_prev = time.perf_counter()
    t0 = t_prev
    for _mesh, _pcd, _traj, _floor in engine.process_sequence(
            frames, window_size=ws, overlap=ov):
        now = time.perf_counter()
        per_window.append(now - t_prev)
        t_prev = now
    wall = time.perf_counter() - t0

    ts, poses = engine.get_poses()
    _io.write_tum(out / "poses.tum", list(ts), poses)

    cloud = engine.get_current_cloud()
    pts = np.asarray(cloud.get("points") if isinstance(cloud, dict) else cloud)
    cols = np.asarray(cloud["colors"]) if isinstance(cloud, dict) and "colors" in cloud else None
    _io.write_cloud(out / "cloud.ply", pts, cols)

    extra = {}
    try:
        extra["tsdf_block_count"] = int(getattr(engine.tsdf, "num_blocks", 0) or 0)
    except Exception:
        pass
    ckpt_mb = ckpt.stat().st_size / 1e6 if ckpt.exists() else 0.0
    import json as _json
    # ── Metric-scale provenance ───────────────────────────────────────────────
    # PRISM's map size comes from a floor-plane RANSAC committed once, early. When that
    # commit is wrong the trajectory can still be excellent while the reconstruction is
    # unusable — exactly apartment_1 in the 2026-08-09 run: best ATE of any method
    # (0.84 m vs 1.9-2.2 m) with a 31% scale error and masked F 0.070. A scale-dependent
    # metric is not interpretable without knowing whether the scale ever locked, so
    # record it per run and let the aggregate separate the two populations.
    _scale = {
        "metric_scale": float(getattr(engine, "current_metric_scale", float("nan"))),
        "scale_locked": bool(getattr(engine, "_scale_committed", False)),
        "scale_provisional": (None if getattr(engine, "_provisional_scale", None) is None
                              else float(engine._provisional_scale)),
        "floor_scale_samples": [round(float(x), 5)
                                for x in getattr(engine, "floor_scale_samples", [])],
        "scale_buffer_enabled": bool(getattr(engine, "scale_buffer_enabled", False)),
    }
    if not _scale["scale_locked"]:
        print(f"[prism_runner] WARNING: metric scale NEVER LOCKED "
              f"({len(_scale['floor_scale_samples'])} confident floor sample(s)) — "
              f"scale-dependent metrics for this run are unverified")
    (out / "arm_config.json").write_text(_json.dumps(
        {"voxel_size": _voxel, "max_depth": _maxd,
         "window_size": ws, "overlap": ov,
         "is_sweep_arm": bool(_voxel != eng["voxel_size"] or _maxd != eng["max_depth"]),
         **_scale},
        indent=2))
    extra.update(_scale)
    _io.write_runner_perf(out, per_window_latency_s=per_window,
                          latency_end_to_end_s=wall, ckpt_size_mb=ckpt_mb, extra=extra)
    print(f"[prism_runner] {len(poses)} poses, {len(pts)} pts, {len(per_window)} windows, "
          f"{wall:.1f}s, s={_scale['metric_scale']:.4f} "
          f"(locked={_scale['scale_locked']})")


if __name__ == "__main__":
    main()
