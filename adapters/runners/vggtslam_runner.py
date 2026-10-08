#!/usr/bin/env python
"""VGGT-SLAM runner — executed by submodules/VGGT-SLAM/.venv/bin/python.

VGGT-SLAM 2.0 (MIT-SPARK @ 35327ac) is a real-time INCREMENTAL SLAM: it streams the
pinhole frames, selects keyframes by optical flow, builds SL(4) submaps in a GTSAM
factor graph with DINO-SALAD loop closure. It's the primary *streaming* comparison for
PRISM (both process frames online).

We drive the repo's own `main.py` (its documented entrypoint) and convert its outputs:
  * `--log_results --log_path poses.txt` -> TUM lines "frame_id tx ty tz qx qy qz qw"
    (frame_id = number parsed from the file name = our global frame index).
  * `<log>_points.pcd` -> colored dense cloud.
Scale-free -> metric=false. Emits poses.tum, cloud.ply, perf_runner.json, arm_config.json.

rerun-v2 changes (see RESULTS_CHANGELOG.md, 2026-10):
  * KEYFRAMING. VGGT-SLAM drops every frame whose mean optical flow from the last
    keyframe is below `min_disparity` px. Its default (50 px) is tuned for 30 fps video,
    where most frames are redundant. Our inputs are already sampled at 2-5 Hz, so the
    default kept only ~35% (2 Hz) / ~17% (5 Hz) of the frames every other method gets:
    VGGT-SLAM was effectively running at ~0.7 Hz. `min_disparity` now comes from
    config (`vggtslam.min_disparity`, default 0 = keep every frame) and the kept
    fraction is recorded (`keyframe_ratio`).
  * One pose per frame. main.py writes the frame shared between consecutive submaps
    once per submap; duplicates are dropped (first occurrence kept).
  * TIMING. The old latency was the wall time of the whole subprocess, i.e. it
    included loading VGGT-1B + DINO-SALAD and the final Viser update. The runner now
    reports VGGT-SLAM's own "Total time" (first image -> last submap optimised), the
    same span the other runners time.
  * CLOUD. The raw dump (every confident pixel of every submap, incl. loop-closure
    submaps, ~5M points / ~150 MB) is deduplicated on a FINE voxel
    (`vggtslam.cloud_dedup_voxel`, default 0.005 in VGGT's own units, ~2 cm in metres
    at the ~3.5-4.5x alignment scale seen in 2026-08), which removes repeated points
    without coarsening anything below the 5 cm F-score threshold.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import runner_io as _io


def _grab(text, pattern, cast=float, default=None):
    m = re.findall(pattern, text)
    return cast(m[-1]) if m else default


def _dedupe_tum(src: Path, dst: Path) -> tuple[int, int]:
    """Copy a TUM file keeping the FIRST pose per timestamp. Returns (kept, dropped)."""
    seen, out, dropped = set(), [], 0
    for ln in src.read_text().splitlines():
        v = ln.split()
        if len(v) < 8:
            continue
        key = round(float(v[0]), 6)
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        out.append(ln)
    dst.write_text("\n".join(out) + ("\n" if out else ""))
    return len(out), dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True)
    ap.add_argument("--out", dest="out_dir", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    import yaml
    cfg = yaml.safe_load(Path(args.config).read_text())
    vs = cfg.get("vggtslam", {}) or {}
    # Per-arm overrides via run_env, so loop-ON / loop-OFF are independently named arms.
    submap = int(os.environ.get("VGGTSLAM_SUBMAP_SIZE",
                                vs.get("submap_size", cfg["engine"]["window_size"])))
    max_loops = int(os.environ.get("VGGTSLAM_MAX_LOOPS", vs.get("max_loops", 1)))
    min_disp = float(os.environ.get("VGGTSLAM_MIN_DISPARITY", vs.get("min_disparity", 0)))
    lc_thres = float(os.environ.get("VGGTSLAM_LC_THRES", vs.get("lc_thres", 0.95)))
    conf_thr = float(os.environ.get("VGGTSLAM_CONF_THRESHOLD", vs.get("conf_threshold", 25.0)))
    cloud_voxel = float(vs.get("cloud_dedup_voxel", 0.005))
    print(f"[vggtslam_runner] submap_size={submap} max_loops={max_loops} "
          f"(loop closure {'ON' if max_loops else 'OFF'}) min_disparity={min_disp} "
          f"lc_thres={lc_thres} conf_threshold={conf_thr}")

    rgb_dir = Path(args.in_dir) / "rgb"
    n_input = len(list(rgb_dir.glob("*.png")))
    raw_txt = out / "poses_raw.txt"

    # cwd is the VGGT-SLAM repo (set by the adapter); main.py is its entrypoint.
    cmd = [sys.executable, "main.py",
           "--image_folder", str(rgb_dir),
           "--log_results", "--log_path", str(raw_txt),
           "--submap_size", str(submap),
           "--max_loops", str(max_loops),
           "--min_disparity", str(min_disp),
           "--lc_thres", str(lc_thres),
           "--conf_threshold", str(conf_thr)]
    print("[vggtslam_runner] $", " ".join(cmd))
    t0 = time.perf_counter()
    # Capture stdout so submap / loop-closure / timing lines can be parsed, while still
    # echoing everything to our own stdout (the adapter tees it to run.log).
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    captured = []
    for line in proc.stdout:
        captured.append(line)
        sys.stdout.write(line)
    rc = proc.wait()
    wall = time.perf_counter() - t0
    if rc != 0:
        print(f"[vggtslam_runner] main.py exited {rc}")
    log_text = "".join(captured)

    n_submaps = _grab(log_text, r"Total number of submaps in map\s+(\d+)", int)
    n_loops = _grab(log_text, r"Total number of loop closures in map\s+(\d+)", int)
    n_keyframes = _grab(log_text, r"(\d+) frames processed", int)
    slam_total_s = _grab(log_text, r"Total time:\s*([0-9.eE+-]+)")
    slam_fps = _grab(log_text, r"Average FPS:\s*([0-9.eE+-]+)")
    keyframe_ratio = (n_keyframes / n_input) if (n_keyframes and n_input) else None

    # ── Degeneracy check ────────────────────────────────────────────────────
    # VGGT-SLAM's contribution IS the multi-submap SL(4) pose graph plus loop closure.
    # With a single submap there is no inter-submap registration and no loop closure:
    # it degenerates to plain feed-forward VGGT, and a head-to-head is meaningless.
    degenerate = (n_submaps is not None and n_submaps < 2)
    if degenerate:
        print(f"[vggtslam_runner] *** WARNING: only {n_submaps} submap(s), {n_loops} loop "
              f"closure(s), {n_keyframes}/{n_input} frames kept. VGGT-SLAM's pose graph "
              f"did NOT engage — this run measures plain feed-forward VGGT. Do not cite it "
              f"as a head-to-head.")
    elif n_submaps is not None:
        print(f"[vggtslam_runner] {n_submaps} submaps, {n_loops} loop closures, "
              f"{n_keyframes}/{n_input} frames kept — method engaged")
    if keyframe_ratio is not None and keyframe_ratio < 0.8:
        print(f"[vggtslam_runner] NOTE: only {100 * keyframe_ratio:.0f}% of the input frames "
              f"were used (min_disparity={min_disp}). Every other method sees every frame.")

    # poses: dedupe the overlap frame written once per submap
    n_poses, n_dup = 0, 0
    if raw_txt.exists():
        n_poses, n_dup = _dedupe_tum(raw_txt, out / "poses.tum")
    else:
        print("[vggtslam_runner] WARN: no poses produced")

    # dense cloud: <log>_points.pcd -> voxel-deduplicated cloud.ply
    pcd_path = out / "poses_raw_points.pcd"
    n_raw_pts = n_pts = 0
    if pcd_path.exists():
        import open3d as o3d
        pc = o3d.io.read_point_cloud(str(pcd_path))
        n_raw_pts = len(pc.points)
        if cloud_voxel > 0 and n_raw_pts:
            pc = pc.voxel_down_sample(cloud_voxel)
        o3d.io.write_point_cloud(str(out / "cloud.ply"), pc)
        n_pts = len(pc.points)
        try:
            pcd_path.unlink()          # raw dump is ~150 MB; the deduped ply is the result
        except OSError:
            pass

    arm = {"max_loops": max_loops, "loop_closure": bool(max_loops),
           "submap_size": submap, "min_disparity": min_disp,
           "lc_thres": lc_thres, "conf_threshold": conf_thr,
           "n_input_frames": n_input, "n_keyframes": n_keyframes,
           "keyframe_ratio": keyframe_ratio,
           "n_submaps": n_submaps, "n_loop_closures": n_loops,
           "method_engaged": (not degenerate) if n_submaps is not None else None,
           "degenerate_single_submap": degenerate,
           "n_poses": n_poses, "n_duplicate_poses_dropped": n_dup,
           "cloud_points_raw": n_raw_pts, "cloud_points": n_pts}
    (out / "arm_config.json").write_text(json.dumps(arm, indent=2))

    # Latency: VGGT-SLAM's own processing span when it printed one (excludes model
    # loading, like every other runner); otherwise the subprocess wall time.
    latency = slam_total_s if (slam_total_s and slam_total_s > 0) else wall
    _io.write_runner_perf(out, per_window_latency_s=[], latency_end_to_end_s=latency,
                          extra={"subprocess_wall_s": wall, "slam_total_s": slam_total_s,
                                 "slam_reported_fps": slam_fps,
                                 "latency_excludes_model_load": bool(slam_total_s),
                                 **{k: arm[k] for k in ("n_keyframes", "keyframe_ratio",
                                                        "n_submaps", "n_loop_closures")}})
    print(f"[vggtslam_runner] {n_poses} poses ({n_dup} duplicate overlap poses dropped), "
          f"{n_pts} pts (raw {n_raw_pts}), slam {slam_total_s}s / wall {wall:.1f}s")


if __name__ == "__main__":
    main()
