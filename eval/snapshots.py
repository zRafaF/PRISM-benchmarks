"""Standardized point-cloud snapshots for the paper.

For every reconstructed cloud (and the GT), this renders fixed, comparable images:
  * aligned to the GT frame (Sim(3)+ICP) so orientation is IDENTICAL for all methods
    ("ground on the floor" — fixes the tilted baseline clouds),
  * optional ceiling removal so the room interior is visible from above,
  * a couple of fixed viewpoints, on BOTH black and white backgrounds,
  * identical axis framing per scene/traj so methods are directly comparable.

Headless-safe: uses matplotlib (Agg), not an Open3D GL window. Output ->
results/report/snapshots/<method>__<scene>_<traj>_<variant>__<view>__<bg>.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.config import REPO_ROOT, load_config
from eval.eval_recon import _align_pred_to_gt, _icp_refine, _export_base

VIEWS = {"oblique": dict(elev=55, azim=-60), "top": dict(elev=88, azim=-90)}


def _load_points(path: Path):
    import open3d as o3d
    pcd = o3d.io.read_point_cloud(str(path))
    pts = np.asarray(pcd.points)
    cols = np.asarray(pcd.colors) if pcd.has_colors() else None
    return pts, cols


def _clip_ceiling(pts, cols, floor_z, keep_h):
    if keep_h <= 0:
        return pts, cols
    m = pts[:, 2] <= (floor_z + keep_h)
    return pts[m], (cols[m] if cols is not None else None)


def _subsample(pts, cols, n):
    if len(pts) > n:
        idx = np.random.default_rng(0).choice(len(pts), n, replace=False)
        return pts[idx], (cols[idx] if cols is not None else None)
    return pts, cols


def _render(pts, cols, limits, view, bg, out_path, point_size):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fg = "white" if bg == "black" else "black"
    fig = plt.figure(figsize=(6, 6), facecolor=bg)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor(bg)
    c = cols if cols is not None else np.full((len(pts), 3), 0.6)
    ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=np.clip(c, 0, 1),
               s=point_size, marker=".", linewidths=0, depthshade=False)
    (xlo, xhi), (ylo, yhi), (zlo, zhi) = limits
    ax.set_xlim(xlo, xhi); ax.set_ylim(ylo, yhi); ax.set_zlim(zlo, zhi)
    ax.set_box_aspect((xhi - xlo, yhi - ylo, zhi - zlo))
    ax.view_init(elev=view["elev"], azim=view["azim"])
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    fig.savefig(out_path, dpi=150, facecolor=bg, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def generate(cfg, keep_h=2.0, max_points=120000, point_size=0.6,
             bgs=("black", "white"), views=None):
    views = views or VIEWS
    out_dir = REPO_ROOT / cfg["report"]["out_dir"] / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    correct_scale = cfg["eval"]["align"]["correct_scale"]
    written = []

    # group runs by (dataset, scene, traj) so GT framing is shared and GT rendered once
    runs = sorted((REPO_ROOT / "results").glob("*/*/*/*/*/cloud.ply"))
    seen_gt = set()
    for cloud in runs:
        parts = cloud.parent.parts
        i = parts.index("results")
        method, dataset, scene, traj, variant = parts[i + 1:i + 6]
        base = _export_base(dataset, scene, traj)
        gt_mesh = base / "gt_mesh.ply"
        gt_tum = base / "poses_gt.tum"
        if not gt_mesh.exists():
            print(f"[snapshots] no GT for {scene}/{traj}; skip {method}"); continue

        gt_pts, gt_cols = _load_points(gt_mesh)
        floor_z = float(np.percentile(gt_pts[:, 2], 1.0))
        gt_pts_c, gt_cols_c = _clip_ceiling(gt_pts, gt_cols, floor_z, keep_h)
        pad = 0.2
        limits = ((gt_pts_c[:, 0].min() - pad, gt_pts_c[:, 0].max() + pad),
                  (gt_pts_c[:, 1].min() - pad, gt_pts_c[:, 1].max() + pad),
                  (floor_z - 0.05, floor_z + keep_h))

        # GT reference images (once per scene/traj)
        gt_key = (dataset, scene, traj)
        if gt_key not in seen_gt:
            seen_gt.add(gt_key)
            gp, gc = _subsample(gt_pts_c, gt_cols_c, max_points)
            for vn, v in views.items():
                for bg in bgs:
                    p = out_dir / f"GT__{scene}_{traj}__{vn}__{bg}.png"
                    _render(gp, gc, limits, v, bg, p, point_size); written.append(p)

        # method cloud: align to GT frame (ground on floor), clip ceiling, render
        pred, pcols = _load_points(cloud)
        if len(pred) == 0:
            continue
        pred, _ = _align_pred_to_gt(pred, cloud.parent / "poses.tum", gt_tum, correct_scale)
        try:
            pred = _icp_refine(pred, gt_pts, cfg["eval"].get("icp", {}).get("max_dist_m", 0.15))
        except Exception:
            pass
        pred, pcols = _clip_ceiling(pred, pcols, floor_z, keep_h)
        pred, pcols = _subsample(pred, pcols, max_points)
        for vn, v in views.items():
            for bg in bgs:
                p = out_dir / f"{method}__{scene}_{traj}_{variant}__{vn}__{bg}.png"
                _render(pred, pcols, limits, v, bg, p, point_size); written.append(p)
        print(f"[snapshots] {method} {scene}/{traj}/{variant}: {len(views)*len(bgs)} images")
    print(f"[snapshots] wrote {len(written)} images -> {out_dir}")
    return [str(p) for p in written]


def main():
    ap = argparse.ArgumentParser(description="Standardized cloud snapshots for the paper")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--keep-height", type=float, default=2.0, help="metres above floor to keep (ceiling clip)")
    ap.add_argument("--max-points", type=int, default=120000)
    args = ap.parse_args()
    cfg = load_config(args.config)
    generate(cfg, keep_h=args.keep_height, max_points=args.max_points)


if __name__ == "__main__":
    main()
