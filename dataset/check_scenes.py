#!/usr/bin/env python
"""Validate that every frozen scene can produce every trajectory — WITHOUT rendering.

Why this exists
---------------
The 2026-08-09 overnight burned ~7 h of GPU and came back unusable for two reasons that
were both decidable in seconds, before a single image was rendered:

  * **room_2 produced nothing.** Its floor height was estimated from the 1st percentile
    of vertex Z, but that mesh extends ~0.8 m below the floor, so the estimate was 0.85 m
    too low, no candidate waypoint could pass the "is this bare floor?" test, and
    `render_scene.py` raised. `make render` was called with `|| true`, so the night
    proceeded on 5 scenes with nothing in the summary saying so.

  * **office_0 produced twelve near-stationary trajectories.** Its `interior` score only
    clears 0.8 in one corner, so all 8 waypoints landed inside a 0.6 m patch. That
    yielded 4-to-8-frame sequences, on which Umeyama alignment is degenerate — PRISM and
    PanoVGGT "agreed" on ATE to six significant figures — and ~65 runs were spent on it.

Trajectory construction needs only the mesh and a raycasting scene; the expensive part of
`make render` is writing images. So this runs the exact same waypoint + spline code the
renderer uses, for every (scene, trajectory) pair, and reports what each one WOULD
produce. Seconds per scene, and it fails non-zero so it can gate the overnight.

    python dataset/check_scenes.py --config config.yaml
    python dataset/check_scenes.py --config config.yaml --json out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# Same import style as render_scene.py: repo root for `bench`, dataset/ for the
# trajectory module, so this file runs under the orchestrator venv unchanged.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import open3d as o3d

from bench.config import (REPO_ROOT, load_config, resolve_scenes, resolve_trajs,
                          traj_kind, traj_rate_hz, traj_seed)
import trajectories as traj_mod
from render_scene import _load_mesh_legacy           # same loader the renderer uses


def _prepared_mesh(cfg, dataset, mesh_path):
    """Load and Z-up-normalise exactly as render_scene.render_scene does.

    Kept in step with the renderer deliberately: a pre-flight that prepares the mesh
    differently from the real thing can pass while the real thing fails.
    """
    mesh = _load_mesh_legacy(mesh_path)
    a0 = mesh.get_axis_aligned_bounding_box()
    up_axis = cfg["datasets"][dataset].get("up_axis", "auto")
    ext = np.asarray(a0.get_extent())
    if up_axis == "auto":
        up_axis = "xyz"[int(np.argmin(ext))]
    if up_axis == "y":
        mesh.rotate(o3d.geometry.get_rotation_matrix_from_axis_angle(
            [np.pi / 2, 0, 0]), (0, 0, 0))
    elif up_axis == "x":
        mesh.rotate(o3d.geometry.get_rotation_matrix_from_axis_angle(
            [0, -np.pi / 2, 0]), (0, 0, 0))
    mesh.compute_vertex_normals()
    return mesh, up_axis


def _check_one(cfg, mesh, raycast, lo, hi, floor_z, cam_z, traj) -> dict:
    """Build one trajectory and describe it. Never raises — records the failure."""
    sp = cfg["trajectories"]["synthetic_spline"]
    extra = cfg["trajectories"].get("extra_kinds") or {}
    n_target = int(cfg["trajectories"]["n_frames"])
    kind = traj_kind(traj)
    rate = traj_rate_hz(traj, default=2.0)
    seed = traj_seed(cfg, traj)
    out = {"traj": traj, "kind": kind, "rate_hz": rate, "seed": seed,
           "ok": False, "n_frames": None, "path_span_m": None, "error": None}
    try:
        wps = traj_mod.free_space_waypoints(
            mesh, n_waypoints=int(sp.get("n_waypoints", 12)),
            min_clearance_m=sp["min_clearance_m"], seed=seed,
            probe_z=cam_z, floor_z=floor_z,
            min_span_m=float(sp.get("min_span_m", 3.0)), debug=False)
        if kind == "stopgo":
            sg = extra.get("stopgo", {})
            poses = traj_mod.stop_and_go(
                wps, camera_height=cam_z, speed_mps=sp.get("speed_mps", 0.5),
                rate_hz=rate, max_frames=n_target,
                n_stops=int(sg.get("n_stops", 2)), dwell_s=float(sg.get("dwell_s", 5.0)))
        else:
            poses = traj_mod.synthetic_spline(
                wps, camera_height=cam_z, speed_mps=sp.get("speed_mps", 0.5),
                rate_hz=rate, max_frames=n_target, close_loop=(kind == "loop"),
                target_frames=n_target, max_laps=int(sp.get("max_laps", 4)),
                min_speed_mps=float(sp.get("min_speed_mps", 0.15)),
                min_frames=int(sp.get("min_frames", 32)))
        pos = np.asarray(poses)[:, :3, 3]
        span = float(np.linalg.norm(pos.max(0) - pos.min(0)))
        out.update(ok=True, n_frames=len(poses), path_span_m=round(span, 2))
    except Exception as exc:                                    # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--json", default=None, help="write the full report here")
    ap.add_argument("--min-frames", type=int, default=None,
                    help="override the minimum acceptable sequence length")
    args = ap.parse_args()
    cfg = load_config(args.config)
    sp = cfg["trajectories"]["synthetic_spline"]
    n_target = int(cfg["trajectories"]["n_frames"])
    min_frames = args.min_frames or int(sp.get("min_frames", 32))
    trajs = resolve_trajs(cfg, "all")

    # Echo the config that is actually in force. A stale config.yaml on the GPU box (or
    # a config.local.yaml overlay) is otherwise invisible, and it is what silently kept
    # the 0.5 Hz rate alive after it had been removed.
    print("[check_scenes] effective config:")
    print(f"    n_frames (target) : {n_target}")
    print(f"    rates_hz          : {cfg['trajectories'].get('rates_hz')}")
    print(f"    extra_kinds       : {list((cfg['trajectories'].get('extra_kinds') or {}))}")
    print(f"    seeds             : {cfg['datasets'].get('seeds')}")
    print(f"    n_waypoints       : {sp.get('n_waypoints', 12)}   "
          f"min_span_m: {sp.get('min_span_m', 3.0)}")
    print(f"    max_laps          : {sp.get('max_laps', 4)}   "
          f"min_speed_mps: {sp.get('min_speed_mps', 0.15)}   min_frames: {min_frames}")
    print(f"    scenes            : {[s for d in cfg['datasets']['active'] for s in resolve_scenes(cfg, d, '')]}")
    print(f"    trajectories      : {len(trajs)} -> {' '.join(trajs)}")
    if any("0.5hz" in t for t in trajs):
        print("    !! 0.5 Hz is STILL in the trajectory list. It was removed from "
              "config.yaml on 2026-08-10 (6-21 frame sequences, degenerate Umeyama). "
              "The config in force here is stale, or config.local.yaml overrides it.")

    report, n_bad, n_short = [], 0, 0
    for dataset in cfg["datasets"]["active"]:
        for scene in resolve_scenes(cfg, dataset, ""):
            mesh_path = (REPO_ROOT / "dataset" / "raw" / dataset / scene / "mesh.ply")
            print(f"\n=== {dataset}/{scene}")
            if not mesh_path.exists():
                print(f"  !! no mesh at {mesh_path}")
                report.append({"dataset": dataset, "scene": scene,
                               "error": "mesh missing", "trajs": []})
                n_bad += 1
                continue
            mesh, up_axis = _prepared_mesh(cfg, dataset, mesh_path)
            aabb = mesh.get_axis_aligned_bounding_box()
            lo, hi = aabb.get_min_bound(), aabb.get_max_bound()
            raycast = o3d.t.geometry.RaycastingScene()
            raycast.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))

            floor_p1 = float(np.percentile(np.asarray(mesh.vertices)[:, 2], 1.0))
            floor_ray = traj_mod.estimate_floor_z(raycast, lo, hi, seed=0,
                                                  candidates=[floor_p1], debug=True)
            floor_z = float(floor_ray) if floor_ray is not None else floor_p1
            cam_z = floor_z + cfg["camera"]["camera_height_m"]
            print(f"  up_axis={up_axis}")
            print(f"  floor_z={floor_z:.2f} (raycast "
                  f"{'n/a' if floor_ray is None else f'{floor_ray:.2f}'}, "
                  f"p1 {floor_p1:.2f})  room={np.round(hi - lo, 1)}  cam_z={cam_z:.2f}")
            if floor_ray is not None and abs(floor_ray - floor_p1) > 0.15:
                print(f"  NOTE: this mesh has geometry BELOW the floor "
                      f"({floor_ray - floor_p1:+.2f} m) — the old p1 estimator would "
                      f"have failed here (this is the room_2 failure)")

            rows = []
            for traj in trajs:
                res = _check_one(cfg, mesh, raycast, lo, hi, floor_z, cam_z, traj)
                rows.append(res)
                if not res["ok"]:
                    n_bad += 1
                    print(f"  [FAIL] {traj:24s} {res['error']}")
                elif res["n_frames"] < min_frames:
                    n_short += 1
                    print(f"  [SHORT] {traj:24s} {res['n_frames']} frames "
                          f"(< {min_frames}), span {res['path_span_m']} m")
                else:
                    flag = "" if res["n_frames"] >= n_target else "  (< target)"
                    print(f"  [ok]   {traj:24s} {res['n_frames']:4d} frames, "
                          f"span {res['path_span_m']:5.2f} m{flag}")
            report.append({"dataset": dataset, "scene": scene,
                           "floor_z": floor_z, "floor_z_raycast": floor_ray,
                           "floor_z_p1": floor_p1, "trajs": rows})

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))
        print(f"\n[check_scenes] wrote {args.json}")

    total = sum(len(r["trajs"]) for r in report)
    print(f"\n[check_scenes] {total} (scene, trajectory) pair(s): "
          f"{total - n_bad - n_short} ok, {n_short} too short, {n_bad} failed")
    if n_bad or n_short:
        print("[check_scenes] DO NOT START THE OVERNIGHT. Every failing pair would "
              "either vanish from the matrix (render error swallowed by `|| true`) or "
              "contribute a near-stationary sequence whose pose metrics are "
              "degenerate-Umeyama artifacts.")
        return 1
    print("[check_scenes] all scenes can produce all trajectories at usable length.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
