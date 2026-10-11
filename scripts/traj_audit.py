#!/usr/bin/env python
"""Geometric audit of camera trajectories against the scene mesh (CPU only, no render).

For every pose of a trajectory this ray-casts the scene mesh and reports:

  clearance   distance from the camera centre to the nearest surface (m)
  crossing    the straight segment from frame i to i+1 passes THROUGH a surface
              (a ray from p_i towards p_{i+1} hits something before reaching it)
  pano_near   fraction of a coarse 360 deg ray set that hits a surface < NEAR_M away
  pin_med     median depth inside the 90 deg pinhole frustum (coarse ray set)
  pin_near    fraction of the pinhole frustum closer than NEAR_M

A frame is FLAGGED when it is inside/against geometry (clearance < --min-clear, or
crossing, or pin_near > 0.5 / pano_near > 0.3). This is exactly the failure that made
every method lose track at the same apartment frames in the rerun-v2 pilot.

Two modes:
  * audit existing GT (default): reads dataset/exports/<ds>/<scene>/<traj>/poses_gt.tum
  * --generate: runs the CURRENT trajectory generator (dataset/trajectories.py) with
    config.yaml and audits the poses it would render, without rendering anything.
    Use it after changing the generator, BEFORE spending hours on `make inputs`.

Usage:
  uv run python scripts/traj_audit.py --scenes "apartment_1 room_0" --traj synthetic_2.0hz_s0
  uv run python scripts/traj_audit.py --generate --traj all          # every scene x traj
  uv run python scripts/traj_audit.py --generate --overlay config.dense.yaml --traj all
Writes results/traj_audit/<mode>/<scene>__<traj>.csv and a summary table on stdout
(and summary.csv). Exit code 1 if any audited trajectory has a flagged frame
(so it can gate `make inputs`).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dataset"))

NEAR_M = 0.30


def read_tum(path: Path) -> np.ndarray:
    from scipy.spatial.transform import Rotation
    rows = [ln.split() for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    out = np.zeros((len(rows), 4, 4))
    for i, r in enumerate(rows):
        v = [float(x) for x in r[1:8]]
        out[i] = np.eye(4)
        out[i][:3, :3] = Rotation.from_quat(v[3:7]).as_matrix()
        out[i][:3, 3] = v[:3]
    return out


def load_scene(cfg: dict, dataset: str, scene: str, gt_mesh: Path | None = None):
    """Mesh + raycaster + floor_z. With `gt_mesh` (the rendered sequence's own
    gt_mesh.ply) the audit uses exactly the geometry that was rendered; otherwise the
    mesh is prepared the way render_scene prepares it now."""
    import open3d as o3d
    import render_scene as rs
    import trajectories as tm
    if gt_mesh is not None and gt_mesh.exists():
        mesh = o3d.io.read_triangle_mesh(str(gt_mesh))
    else:
        mesh = rs.prepare_mesh(cfg, dataset, rs._find_mesh(cfg, dataset, scene), debug=False)
    scene_rc = o3d.t.geometry.RaycastingScene()
    scene_rc.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
    aabb = mesh.get_axis_aligned_bounding_box()
    lo, hi = aabb.get_min_bound(), aabb.get_max_bound()
    p1 = float(np.percentile(np.asarray(mesh.vertices)[:, 2], 1.0))
    fz = tm.estimate_floor_z(scene_rc, lo, hi, seed=0, candidates=[p1], debug=False)
    return mesh, scene_rc, (fz if fz is not None else p1)


def _coarse_dirs(cfg):
    from bench import cameras
    pano = cameras.equirect_rays_cam(72, 36)
    v = cfg["camera"]["pinhole"]["variants"]["synthetic_fov"]
    intr = cameras.PinholeIntrinsics.from_fov(32, 24, v["fov_deg"])
    return pano, cameras.pinhole_rays_cam(intr)


def audit_poses(scene_rc, poses: np.ndarray, pano_dirs, pin_dirs) -> dict:
    import open3d as o3d
    from bench import cameras
    n = len(poses)
    c = poses[:, :3, 3].astype(np.float32)
    clear = scene_rc.compute_distance(o3d.core.Tensor(c)).numpy()
    crossing = np.zeros(n, bool)
    if n > 1:
        d = c[1:] - c[:-1]
        L = np.linalg.norm(d, axis=1)
        u = d / np.maximum(L[:, None], 1e-9)
        t = scene_rc.cast_rays(o3d.core.Tensor(np.concatenate([c[:-1], u], 1).astype(np.float32)))["t_hit"].numpy()
        crossing[:-1] = np.isfinite(t) & (t < L) & (L > 1e-6)
    pano_near = np.zeros(n); pin_med = np.zeros(n); pin_near = np.zeros(n)
    for i, T in enumerate(poses):
        o, dd = cameras.rays_to_world(pano_dirs, T)
        t = scene_rc.cast_rays(o3d.core.Tensor(np.concatenate([o, dd], 1).astype(np.float32)))["t_hit"].numpy()
        pano_near[i] = np.mean(np.isfinite(t) & (t < NEAR_M))
        o, dd = cameras.rays_to_world(pin_dirs, T)
        t = scene_rc.cast_rays(o3d.core.Tensor(np.concatenate([o, dd], 1).astype(np.float32)))["t_hit"].numpy()
        tf = np.where(np.isfinite(t), t, 50.0)
        pin_med[i] = float(np.median(tf))
        pin_near[i] = float(np.mean(tf < NEAR_M))
    return dict(clearance=clear, crossing=crossing, pano_near=pano_near,
                pin_med=pin_med, pin_near=pin_near)


def path_stats(poses: np.ndarray, rate: float) -> dict:
    c = poses[:, :3, 3]
    step = np.linalg.norm(np.diff(c, axis=0), axis=1)
    fwd = poses[:, :3, 2]
    yaw = np.unwrap(np.arctan2(fwd[:, 1], fwd[:, 0]))
    dyaw = np.degrees(np.abs(np.diff(yaw)))
    # Revisit: fraction of frames whose position is within 0.5 m of a frame >= 20 s earlier.
    lag = int(20 * rate)
    rev = 0
    for i in range(lag, len(c)):
        if np.min(np.linalg.norm(c[: i - lag + 1] - c[i], axis=1)) < 0.5:
            rev += 1
    return dict(n=len(c), length_m=float(step.sum()), step_med=float(np.median(step)) if len(step) else 0,
                yaw_med=float(np.median(dyaw)) if len(dyaw) else 0,
                yaw_p95=float(np.percentile(dyaw, 95)) if len(dyaw) else 0,
                extent_m=float(np.linalg.norm(c[:, :2].max(0) - c[:, :2].min(0))),
                revisit_frac=rev / max(len(c), 1))


def flags(a: dict, min_clear: float) -> np.ndarray:
    return ((a["clearance"] < min_clear) | a["crossing"]
            | (a["pin_near"] > 0.5) | (a["pano_near"] > 0.3))


def generate_poses(cfg, mesh, scene_rc, floor_z, traj) -> np.ndarray:
    """Run the generator the renderer would run, without rendering."""
    import render_scene as rs
    return rs.make_trajectory(cfg, mesh, scene_rc, floor_z, traj)


def plot_audit(cfg, scene_rc, mesh, floor_z, poses, a, f, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trajectories as tm
    sp = cfg["trajectories"]["synthetic_spline"]
    bb = mesh.get_axis_aligned_bounding_box()
    G = tm.free_space_grid(scene_rc, bb.get_min_bound(), bb.get_max_bound(), floor_z,
                           floor_z + cfg["camera"]["camera_height_m"],
                           res=float(sp.get("grid_res_m", 0.05)),
                           r_cam=float(sp["min_clearance_m"]),
                           r_body=float(sp.get("body_clearance_m", 0.20)))
    ext = [G["xs"][0], G["xs"][-1], G["ys"][0], G["ys"][-1]]
    fig, ax = plt.subplots(figsize=(9, 9 * (ext[3] - ext[2]) / max(ext[1] - ext[0], 1e-6) + 0.8))
    ax.imshow((0.35 * G["floor_ok"] + 0.65 * G["free"]).T, origin="lower", extent=ext,
              cmap="Greys", vmin=0, vmax=1.6)
    c = poses[:, :3, 3]
    ax.plot(c[:, 0], c[:, 1], "-", color="tab:blue", lw=0.8)
    fw = poses[:, :3, 2]
    k = max(1, len(c) // 120)
    ax.quiver(c[::k, 0], c[::k, 1], fw[::k, 0], fw[::k, 1], color="tab:blue", scale=35, width=0.002)
    ax.plot(c[0, 0], c[0, 1], "go", ms=7)
    if f.any():
        ax.plot(c[f, 0], c[f, 1], "rx", ms=6, label="flagged")
        for i in np.flatnonzero(f)[:: max(1, int(f.sum()) // 12)]:
            ax.annotate(str(i), c[i, :2], fontsize=7, color="red")
        ax.legend(loc="upper right", fontsize=8)
    ax.set_aspect("equal"); ax.set_title(title, fontsize=9)
    ax.set_xlabel("x (m)  —  dark: walkable at clearance, light: floor, white: blocked")
    fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)


def runs(s):
    """'1,2,3,7,8' style run-length text of flagged indices."""
    idx = list(np.flatnonzero(s))
    if not idx:
        return ""
    out, a, b = [], idx[0], idx[0]
    for k in idx[1:]:
        if k == b + 1:
            b = k
        else:
            out.append(f"{a}-{b}" if b > a else f"{a}"); a = b = k
    out.append(f"{a}-{b}" if b > a else f"{a}")
    return ",".join(out)


def main():
    from bench.config import derived_source, load_config, resolve_scenes, resolve_trajs, traj_rate_hz
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--overlay", default="", help="extra config overlay (sets PRISM_CONFIG_OVERLAY)")
    ap.add_argument("--scenes", default="")
    ap.add_argument("--traj", default="all")
    ap.add_argument("--generate", action="store_true", help="audit the generator's output, not the rendered GT")
    ap.add_argument("--min-clear", type=float, default=0.25)
    ap.add_argument("--save-poses", action="store_true", help="(--generate) also write the generated poses as TUM")
    ap.add_argument("--plot", action="store_true",
                    help="also write a top-down PNG per sequence (walkable grid, path, flagged frames)")
    ap.add_argument("--no-level", action="store_true",
                    help="do not level the floor (the rerun-v2 geometry; use when auditing "
                         "v2 inputs without their gt_mesh.ply)")
    args = ap.parse_args()
    if args.overlay:
        os.environ["PRISM_CONFIG_OVERLAY"] = args.overlay
    cfg = load_config(args.config)
    if args.no_level:
        for ds in cfg["datasets"]["active"]:
            cfg["datasets"][ds]["level_floor"] = False
    mode = "generated" if args.generate else "rendered"
    out_dir = ROOT / "results" / "traj_audit" / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    pano_dirs, pin_dirs = _coarse_dirs(cfg)
    summary, any_bad = [], False
    for dataset in cfg["datasets"]["active"]:
        for scene in resolve_scenes(cfg, dataset, args.scenes):
            trajs = [t for tok in args.traj.split() for t in resolve_trajs(cfg, tok)]
            gt = None
            if not args.generate:
                gtp = ROOT / "dataset" / "exports" / dataset / scene / (trajs[0] if trajs else "") / "gt_mesh.ply"
                gt = gtp if gtp.exists() else None
            mesh, scene_rc, fz = load_scene(cfg, dataset, scene, gt_mesh=gt)
            for traj in trajs:
                rate = traj_rate_hz(traj)
                if args.generate and derived_source(cfg, traj):
                    continue                     # cut from its base render; audit that
                if args.generate:
                    poses = generate_poses(cfg, mesh, scene_rc, fz, traj)
                    if args.save_poses:
                        import render_scene as rs
                        rs._write_tum(out_dir / f"{scene}__{traj}.tum", poses)
                else:
                    p = ROOT / "dataset" / "exports" / dataset / scene / traj / "poses_gt.tum"
                    if not p.exists():
                        print(f"[audit] skip {scene}/{traj}: no {p}")
                        continue
                    poses = read_tum(p)
                a = audit_poses(scene_rc, poses, pano_dirs, pin_dirs)
                st = path_stats(poses, rate)
                f = flags(a, args.min_clear)
                any_bad |= bool(f.any())
                with open(out_dir / f"{scene}__{traj}.csv", "w", newline="") as fh:
                    w = csv.writer(fh)
                    w.writerow(["frame", "x", "y", "z", "clearance", "crossing", "pano_near", "pin_med", "pin_near", "flag"])
                    for i in range(len(poses)):
                        x, y, z = poses[i][:3, 3]
                        w.writerow([i, f"{x:.3f}", f"{y:.3f}", f"{z:.3f}", f"{a['clearance'][i]:.3f}",
                                    int(a["crossing"][i]), f"{a['pano_near'][i]:.3f}",
                                    f"{a['pin_med'][i]:.3f}", f"{a['pin_near'][i]:.3f}", int(f[i])])
                if args.plot:
                    plot_audit(cfg, scene_rc, mesh, fz, poses, a, f, out_dir / f"{scene}__{traj}.png",
                               f"{scene} / {traj} ({mode}): {int(f.sum())} flagged, "
                               f"{int(a['crossing'].sum())} crossings, min clearance "
                               f"{a['clearance'].min():.2f} m")
                row = dict(scene=scene, traj=traj, **st,
                           clear_min=float(a["clearance"].min()),
                           clear_p5=float(np.percentile(a["clearance"], 5)),
                           n_cross=int(a["crossing"].sum()),
                           n_flag=int(f.sum()), pin_med_p5=float(np.percentile(a["pin_med"], 5)),
                           flagged=runs(f))
                summary.append(row)
                print(f"[audit] {scene:12s} {traj:20s} n={st['n']:4d} len={st['length_m']:5.1f}m "
                      f"ext={st['extent_m']:4.1f}m yaw_med={st['yaw_med']:4.1f} revisit={st['revisit_frac']:.2f} "
                      f"clear_min={row['clear_min']:.2f} cross={row['n_cross']:3d} FLAG={row['n_flag']:3d} "
                      f"{row['flagged'][:80]}")
    if summary:
        with open(out_dir / "summary.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
            w.writeheader(); w.writerows(summary)
        print(f"[audit] wrote {out_dir}/summary.csv")
    sys.exit(1 if any_bad else 0)


if __name__ == "__main__":
    main()
